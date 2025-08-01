from pydantic import BaseModel, Field


class SystemSettingBase(BaseModel):
    key: str
    value: str


class SystemSettingResponse(SystemSettingBase):
    class Config:
        from_attributes = True


class TopKUpdate(BaseModel):
    top_k: int = Field(
        ...,
        ge=1,
        description="The number of documents to retrieve from the vector store.",
        example=5,
    )
