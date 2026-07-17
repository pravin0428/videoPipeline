from pydantic import BaseModel


class LLMResponse(BaseModel):
    summary: str
    facts: list[str]
