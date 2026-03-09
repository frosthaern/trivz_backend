from typing import ClassVar

from pydantic import BaseModel, ConfigDict

from src.models import Difficulty, SessionType


class SessionCreate(BaseModel):
    difficulty: Difficulty = Difficulty.medium
    category: int | None = None
    type: SessionType = SessionType.multiple
    question_count: int = 10


class SessionOut(BaseModel):
    id: int
    room_id: int
    difficulty: Difficulty
    category: int | None
    type: SessionType
    question_count: int

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class SessionScoreOut(BaseModel):
    user_id: int
    score: int
    rank: int

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)


class LeaderboardOut(BaseModel):
    session_id: int
    scores: list[SessionScoreOut]

    model_config: ClassVar[ConfigDict] = ConfigDict(from_attributes=True)
