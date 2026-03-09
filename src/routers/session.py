from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import GameSession, InviteStatus, Room, RoomMember, RoomStatus, SessionScore, User
from schemas.session import LeaderboardOut, SessionCreate, SessionOut
from src.services.auth import get_current_user
from src.services.db import get_db
from ws import manager

router = APIRouter(prefix="/rooms", tags=["sessions"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_room_or_404(room_code: str, db: Session) -> Room:
    room = db.execute(select(Room).filter(Room.room_code == room_code)).scalars().first()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


def get_session_or_404(session_id: int, room_id: int, db: Session) -> GameSession:
    session = (
        db.execute(
            select(GameSession).filter(
                GameSession.id == session_id,
                GameSession.room_id == room_id,
            )
        )
        .scalars()
        .first()
    )
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


# async def fetch_questions(difficulty: str, category: int | None, q_type: str, count: int) -> list[dict]:  # make shape for questions or things that you get from opentrivia org
#     url = "https://opentdb.com/api.php"
#     params = {
#         "amount": count,
#         "difficulty": difficulty,
#         "type": q_type,
#     }
#     if category:
#         params["category"] = category

#     async with httpx.AsyncClient() as client:
#         response = await client.get(url, params=params)
#         data = response.json()

#     if data["response_code"] != 0:
#         raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch questions from Open Trivia DB")
#     return data["results"]


@router.post("/{room_code}/sessions", response_model=SessionOut)
async def create_session(room_code: str, body: SessionCreate, db: DB, current_user: CurrentUser):
    room = get_room_or_404(room_code, db)

    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can create a session")
    if room.status == RoomStatus.in_progress:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A session is already in progress")

    session = GameSession(
        room_id=room.id,
        difficulty=body.difficulty,
        category=body.category,
        type=body.type,
        question_count=body.question_count,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # notify everyone in the room that a session has been created with these settings
    await manager.broadcast(
        room_code,
        {
            "event": "session_created",
            "session_id": session.id,
            "difficulty": body.difficulty,
            "category": body.category,
            "type": body.type,
            "question_count": body.question_count,
        },
    )

    return session


@router.get("/{room_code}/sessions", response_model=list[SessionOut])
async def list_sessions(room_code: str, db: DB, current_user: CurrentUser):
    room = get_room_or_404(room_code, db)
    sessions = db.execute(select(GameSession).filter(GameSession.room_id == room.id)).scalars().all()
    return sessions


@router.get("/{room_code}/sessions/{session_id}", response_model=SessionOut)
async def get_session(room_code: str, session_id: int, db: DB, current_user: CurrentUser):
    room = get_room_or_404(room_code, db)
    session = get_session_or_404(session_id, room.id, db)
    return session


@router.post("/{room_code}/sessions/{session_id}/start")
async def start_session(room_code: str, session_id: int, db: DB, current_user: CurrentUser):
    room = get_room_or_404(room_code, db)

    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can start the session")
    if room.status == RoomStatus.in_progress:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A session is already in progress")

    session = get_session_or_404(session_id, room.id, db)

    # check at least 2 members are accepted
    accepted_members = (
        db.execute(
            select(RoomMember).filter(
                RoomMember.room_id == room.id,
                RoomMember.invite_status == InviteStatus.accepted,
            )
        )
        .scalars()
        .all()
    )
    if len(accepted_members) < 2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Need at least 2 players to start")

    # fetch questions from open trivia db
    questions = await fetch_questions(
        difficulty=session.difficulty.value,
        category=session.category,
        q_type=session.type.value,
        count=session.question_count,
    )

    # flip room status
    room.status = RoomStatus.in_progress
    db.commit()

    # broadcast game starting with all questions at once
    await manager.broadcast(
        room_code,
        {
            "event": "game_started",
            "session_id": session.id,
            "questions": questions,  # all questions sent at once
        },
    )

    return {"message": "Game started"}


@router.post("/{room_code}/sessions/{session_id}/end")
async def end_session(
    room_code: str,
    session_id: int,
    scores: list[dict],  # [{"user_id": 1, "score": 800}, ...]
    db: DB,
    current_user: CurrentUser,
):
    room = get_room_or_404(room_code, db)

    if room.master_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the master can end the session")

    session = get_session_or_404(session_id, room.id, db)

    # sort scores descending to assign ranks
    sorted_scores = sorted(scores, key=lambda x: x["score"], reverse=True)

    for rank, entry in enumerate(sorted_scores, start=1):
        session_score = SessionScore(
            session_id=session.id,
            user_id=entry["user_id"],
            score=entry["score"],
            rank=rank,
        )
        db.add(session_score)

    session.ended_at = datetime.now(UTC)
    room.status = RoomStatus.waiting  # room goes back to waiting for next session
    db.commit()

    await manager.broadcast(room_code, {"event": "game_over", "leaderboard": [{"user_id": e["user_id"], "score": e["score"], "rank": i + 1} for i, e in enumerate(sorted_scores)]})

    return {"message": "Session ended"}


@router.get("/{room_code}/sessions/{session_id}/leaderboard", response_model=LeaderboardOut)
async def get_leaderboard(room_code: str, session_id: int, db: DB, current_user: CurrentUser):
    room = get_room_or_404(room_code, db)
    session = get_session_or_404(session_id, room.id, db)

    scores = db.execute(select(SessionScore).filter(SessionScore.session_id == session.id).order_by(SessionScore.rank)).scalars().all()

    return LeaderboardOut(session_id=session.id, scores=scores)
