from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from schemas.room import AcceptReject, InviteRequest, RoomDetailOut, RoomOut
from src.models import InviteStatus, Room, RoomMember, RoomStatus, User
from src.services.auth import get_current_user
from src.services.db import get_db
from src.services.room import generate_room_code
from ws import manager

router = APIRouter(prefix="/rooms", tags=["rooms"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post("/", response_model=RoomOut)
async def create_room(db: DB, current_user: CurrentUser):
    while True:
        code = generate_room_code()
        exists = db.execute(select(Room).filter(Room.room_code == code)).scalars().first()
        if not exists:
            break

    room = Room(
        room_code=code,
        master_id=current_user.id,
    )
    db.add(room)
    db.flush()

    member = RoomMember(
        room_id=room.id,
        user_id=current_user.id,
        invite_status=InviteStatus.accepted,
    )
    db.add(member)
    db.commit()
    db.refresh(room)
    return room


@router.get("/{room_code}", response_model=RoomDetailOut)
async def get_room(room_code: str, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.delete("/{room_code}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(room_code: str, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can delete the room")
    db.delete(room)
    db.commit()


@router.post("/{room_code}/invite")
async def invite_user(room_code: str, body: InviteRequest, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can invite")
    if room.status != RoomStatus.waiting:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not in waiting state")

    target_user = db.execute(select(User).filter(User.username == body.username)).scalars().first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    already_member = db.execute(select(RoomMember).filter(RoomMember.room_id == room.id, RoomMember.user_id == target_user.id)).scalars().first()
    if already_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already in the room")

    member = RoomMember(
        room_id=room.id,
        user_id=target_user.id,
        invite_status=InviteStatus.invited,
    )
    db.add(member)
    db.commit()

    # notify the invited user via websocket if they're connected
    # this part you need to make event as a type with a shape and then initialize it and then send it
    await manager.send_to_user(
        room_code,
        target_user.id,
        {
            "event": "invite_received",
            "room_code": room_code,
            "invited_by": current_user.username,
        },
    )

    return {"message": f"Invite sent to {target_user.username}"}


@router.post("/{room_code}/request")
async def request_to_join(room_code: str, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.status != RoomStatus.waiting:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is not in waiting state")

    already_member = (
        db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.user_id == current_user.id,
            )
        )
        .scalars()
        .first()
    )
    if already_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member or request pending")

    member = RoomMember(
        room_id=room.id,
        user_id=current_user.id,
        invite_status=InviteStatus.requested,
    )
    db.add(member)
    db.commit()

    # notify the master via websocket if they're connected
    await manager.send_to_user(
        room_code,
        room.master_id,
        {
            "event": "join_requested",
            "user_id": current_user.id,
            "username": current_user.username,
        },
    )

    return {"message": "Join request sent"}


@router.post("/{room_code}/respond")
async def respond_to_request(room_code: str, body: AcceptReject, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can respond to requests")

    member = (
        db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.user_id == body.user_id,
                RoomMember.invite_status == InviteStatus.requested,
            )
        )
        .scalars()
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending request from this user")

    member.invite_status = InviteStatus.accepted if body.accept else InviteStatus.rejected
    db.commit()

    # notify the requesting user
    await manager.send_to_user(
        room_code,
        body.user_id,
        {
            "event": "request_accepted" if body.accept else "request_rejected",
            "room_code": room_code,
        },
    )

    # if accepted, notify everyone else in the room
    if body.accept:
        await manager.broadcast(
            room_code,
            {
                "event": "user_joined",
                "user_id": body.user_id,
            },
        )

    return {"message": "Request accepted" if body.accept else "Request rejected"}


@router.post("/{room_code}/respond-invite")
async def respond_to_invite(room_code: str, body: AcceptReject, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    member = (
        db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.user_id == current_user.id,
                RoomMember.invite_status == InviteStatus.invited,
            )
        )
        .scalars()
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No pending invite found")

    member.invite_status = InviteStatus.accepted if body.accept else InviteStatus.rejected
    db.commit()

    if body.accept:
        await manager.broadcast(
            room_code,
            {
                "event": "user_joined",
                "user_id": current_user.id,
                "username": current_user.username,
            },
        )

    return {"message": "Invite accepted" if body.accept else "Invite declined"}


@router.delete("/{room_code}/kick/{user_id}")
async def kick_member(room_code: str, user_id: int, db: DB, current_user: CurrentUser):
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can kick members")
    if user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Master cannot kick themselves")

    member = (
        db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.user_id == user_id,
            )
        )
        .scalars()
        .first()
    )
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    db.delete(member)
    db.commit()

    await manager.send_to_user(
        room_code,
        user_id,
        {
            "event": "kicked",
            "room_code": room_code,
        },
    )
    await manager.broadcast(
        room_code,
        {
            "event": "user_left",
            "user_id": user_id,
        },
    )

    return {"message": "User kicked"}
