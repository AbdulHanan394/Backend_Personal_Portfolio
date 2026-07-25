"""Assistant request and response schemas."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One prior conversation message."""

    role: str = Field(pattern="^(user|assistant)$")
    content: str


class AssistantQuery(BaseModel):
    """Portfolio chat request."""

    question: str = Field(min_length=1, max_length=2000)
    history: list[ChatMessage] = Field(default_factory=list)


class AssistantAnswer(BaseModel):
    """Portfolio chat response payload."""

    answer: str

