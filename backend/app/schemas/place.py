from pydantic import BaseModel, ConfigDict, Field


class PlaceRead(BaseModel):
    """장소 정보. 카카오 장소 검색 결과와 DB에 저장된 장소 모두에 사용합니다."""

    model_config = ConfigDict(from_attributes=True)

    kakao_place_id: str
    name: str
    address: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    category: str | None = None
