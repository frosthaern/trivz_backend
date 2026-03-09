import html
import random
from typing import Any

import httpx
from pydantic import BaseModel, field_validator


class RawQuestion(BaseModel):
    type: str
    difficulty: str
    category: str
    question: str
    correct_answer: str
    incorrect_answers: list[str]

    # open trivia db returns HTML encoded strings, decode them
    @field_validator("question", "correct_answer", mode="before")
    @classmethod
    def decode_html(cls, v: str) -> str:
        return html.unescape(v)

    @field_validator("incorrect_answers", mode="before")
    @classmethod
    def decode_incorrect(cls, v: list[str]) -> list[str]:
        return [html.unescape(s) for s in v]


class RawTriviaResponse(BaseModel):
    response_code: int
    results: list[RawQuestion]


class TriviaQuestion(BaseModel):
    index: int
    question: str
    correct_answer: str
    all_options: list[str]
    difficulty: str
    category: str
    type: str

    def validate_answer(self, answer: str) -> bool:
        return answer.strip().lower() == self.correct_answer.strip().lower()

    @classmethod
    def from_raw(cls, raw: RawQuestion, index: int) -> "TriviaQuestion":
        options = raw.incorrect_answers + [raw.correct_answer]
        random.shuffle(options)
        return cls(
            index=index,
            question=raw.question,
            correct_answer=raw.correct_answer,
            all_options=options,
            difficulty=raw.difficulty,
            category=raw.category,
            type=raw.type,
        )


class TriviaQuestionOut(BaseModel):
    index: int
    question: str
    all_options: list[str]
    difficulty: str
    category: str
    type: str

    @classmethod
    def from_question(cls, q: TriviaQuestion) -> "TriviaQuestionOut":
        return cls(
            index=q.index,
            question=q.question,
            all_options=q.all_options,
            difficulty=q.difficulty,
            category=q.category,
            type=q.type,
        )


class PlayerAnswer(BaseModel):
    question_index: int
    answer: str


class TriviaClient:
    BASE_URL: str = "https://opentdb.com/api.php"

    async def fetch(
        self,
        count: int,
        difficulty: str,
        q_type: str,
        category: int | None = None,
    ) -> list[TriviaQuestion]:
        params: dict[str, Any] = {
            "amount": count,
            "difficulty": difficulty,
            "type": q_type,
        }
        if category is not None:
            params["category"] = category

        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            _ = response.raise_for_status()
            data = response.json()

        parsed = RawTriviaResponse(**data)

        if parsed.response_code != 0:
            raise ValueError(f"Open Trivia DB returned response_code {parsed.response_code}")

        return [TriviaQuestion.from_raw(raw, index) for index, raw in enumerate(parsed.results)]


trivia_client = TriviaClient()  # singleton, import this anywhere you need it
