from pydantic import BaseModel, ConfigDict, Field, field_validator


class PlaceCreate(BaseModel):
    """장소 저장 요청. 카카오 장소 검색 결과를 그대로 보내면 됩니다."""

    kakao_place_id: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=100)
    address: str = Field(max_length=200)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    category: str | None = None

    @field_validator("category")
    @classmethod
    def trim_category(cls, value: str | None) -> str | None:
        # 카카오 카테고리 문자열이 DB 컬럼 길이(50)보다 길 수 있어 오류 대신 잘라서 저장합니다.
        return value[:50] if value else value


class PlaceRead(PlaceCreate):
    model_config = ConfigDict(from_attributes=True)
