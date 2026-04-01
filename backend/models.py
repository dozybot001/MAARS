from pydantic import BaseModel


class StartRequest(BaseModel):
    input: str


class StageStatus(BaseModel):
    name: str
    state: str
    phase: str = ""
    output_length: int


class PipelineStatus(BaseModel):
    input: str
    stages: list[StageStatus]


class ActionResponse(BaseModel):
    stage: str
    state: str
    message: str = ""
