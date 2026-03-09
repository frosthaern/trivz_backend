from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from src.models import InviteStatus, RoomStatus

# models for user and tokens


# models for room
class RoomCreate(BaseModel):
    pass


class RoomOut(BaseModel):
    id: int
    room_code: str
    master_id: int
    status: RoomStatus

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class RoomMemberOut(BaseModel):
    user_id: int
    invite_status: InviteStatus

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class RoomDetailOut(BaseModel):
    id: int
    room_code: str
    master_id: int
    status: RoomStatus
    members: list[RoomMemberOut] = []

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class InviteRequest(BaseModel):
    username: str


class AcceptReject(BaseModel):
    user_id: int
    accept: bool
