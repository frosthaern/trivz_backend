import enum
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from src.models import GameSession


class RoomStatus(str, enum.Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    finished = "finished"


class Difficulty(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class InviteStatus(str, enum.Enum):
    invited = "invited"
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"


class Room(Base):
    __tablename__: str = "room"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_code: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    master_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    status: Mapped[RoomStatus] = mapped_column(Enum(RoomStatus), default=RoomStatus.waiting, nullable=False)
    # difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty), default=Difficulty.medium, nullable=False)
    # category: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Open Trivia DB category ID, null = any
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    members: Mapped[list[RoomMember]] = relationship(back_populates="room", cascade="all, delete-orphan")
    sessions: Mapped[list[GameSession]] = relationship(back_populates="room", cascade="all, delete-orphan")


class RoomMember(Base):
    __tablename__: str = "room_member"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey("room.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    invite_status: Mapped[InviteStatus] = mapped_column(Enum(InviteStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    room: Mapped[Room] = relationship(back_populates="members")
