from pydantic import BaseModel


class ResearchResponse(BaseModel):
    status: str
