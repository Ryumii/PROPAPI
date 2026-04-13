"""School district response schema."""

from pydantic import BaseModel, Field


class SchoolDistrictInfo(BaseModel):
    school_type: str = Field(..., examples=["elementary"], description="elementary / junior_high")
    school_name: str = Field(..., examples=["戸塚第二小学校"])
    administrator: str | None = Field(None, examples=["新宿区立"])
    address: str | None = Field(None, examples=["新宿区高田馬場1-25-21"])
    source: str = Field(..., examples=["国土数値情報 小学校区データ (A27)"])
    source_url: str | None = Field(None, description="データソースのURL")


class SchoolDistrictResponse(BaseModel):
    elementary: SchoolDistrictInfo | None = Field(None, description="公立小学校学区")
    junior_high: SchoolDistrictInfo | None = Field(None, description="公立中学校学区")
