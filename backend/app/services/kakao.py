from collections.abc import Generator
from dataclasses import dataclass

import httpx

KAKAO_USER_ME_URL = "https://kapi.kakao.com/v2/user/me"
DEFAULT_NICKNAME = "카카오 사용자"


class KakaoAuthError(Exception):
    """카카오가 액세스 토큰을 거부했을 때(만료/위조 등)."""


class KakaoServiceError(Exception):
    """카카오 서버 장애, 네트워크 오류, 예상과 다른 응답일 때."""


@dataclass
class KakaoProfile:
    kakao_id: str
    nickname: str
    email: str | None


def get_kakao_client() -> Generator[httpx.Client, None, None]:
    """카카오 API 호출용 HTTP 클라이언트. 테스트에서는 이 의존성을 교체합니다."""
    with httpx.Client(timeout=5.0) as client:
        yield client


def fetch_kakao_profile(access_token: str, client: httpx.Client) -> KakaoProfile:
    """카카오 액세스 토큰으로 사용자 정보를 조회합니다. 토큰이 유효한지 검증하는 역할도 합니다."""
    try:
        response = client.get(KAKAO_USER_ME_URL, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        raise KakaoServiceError(f"kakao request failed: {exc.__class__.__name__}") from exc

    if response.status_code in (400, 401):
        raise KakaoAuthError("kakao rejected the access token")
    if response.status_code != 200:
        raise KakaoServiceError(f"kakao returned status {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise KakaoServiceError("kakao returned invalid json") from exc

    kakao_id = data.get("id")
    if kakao_id is None:
        raise KakaoServiceError("kakao response has no id")

    account = data.get("kakao_account") or {}
    # 닉네임은 kakao_account.profile 이 기준이고, properties.nickname 은 삭제 예정인 구 필드라 보조로만 사용합니다.
    nickname = (
        (account.get("profile") or {}).get("nickname")
        or (data.get("properties") or {}).get("nickname")
        or DEFAULT_NICKNAME
    )
    email = account.get("email")

    # DB 컬럼 길이(nickname 50, email 100)에 맞춥니다.
    return KakaoProfile(
        kakao_id=str(kakao_id),
        nickname=nickname[:50],
        email=email[:100] if email else None,
    )


# ---------------------------------------------------------------- 토큰 발급 앱 검증 ----------

KAKAO_TOKEN_INFO_URL = "https://kapi.kakao.com/v1/user/access_token_info"


def verify_token_app_id(access_token: str, client: httpx.Client, expected_app_id: str) -> None:
    """토큰이 '우리 앱'에서 발급된 것인지 확인합니다. (다른 앱의 토큰으로 로그인하는 것을 막음)

    expected_app_id 가 비어 있으면 검사를 건너뜁니다.
    """
    if not expected_app_id:
        return
    try:
        response = client.get(KAKAO_TOKEN_INFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    except httpx.HTTPError as exc:
        raise KakaoServiceError(f"kakao request failed: {exc.__class__.__name__}") from exc
    if response.status_code in (400, 401):
        raise KakaoAuthError("kakao rejected the access token")
    if response.status_code != 200:
        raise KakaoServiceError(f"kakao returned status {response.status_code}")
    try:
        app_id = response.json().get("appId", response.json().get("app_id"))
    except ValueError as exc:
        raise KakaoServiceError("kakao returned invalid json") from exc
    if str(app_id) != str(expected_app_id):
        raise KakaoAuthError("token was issued for a different app")


# ---------------------------------------------------------------- 장소 검색 (카카오 로컬) ----------

KAKAO_KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


class KakaoNotConfiguredError(Exception):
    """KAKAO_REST_API_KEY 가 설정되지 않았을 때."""


@dataclass
class KakaoPlace:
    kakao_place_id: str
    name: str
    address: str
    lat: float
    lng: float
    category: str | None


def search_places(
    query: str,
    client: httpx.Client,
    rest_api_key: str,
    *,
    lat: float | None = None,
    lng: float | None = None,
    radius_m: int | None = None,
    size: int = 10,
    page: int = 1,
) -> list[KakaoPlace]:
    """카카오 로컬 '키워드로 장소 검색'. lat/lng 를 주면 그 주변을 우선합니다."""
    if not rest_api_key:
        raise KakaoNotConfiguredError("KAKAO_REST_API_KEY is not set")
    params: dict[str, str | int | float] = {"query": query, "size": size, "page": page}
    if lat is not None and lng is not None:
        params["y"] = lat
        params["x"] = lng
        if radius_m:
            params["radius"] = radius_m
    try:
        response = client.get(
            KAKAO_KEYWORD_SEARCH_URL, params=params, headers={"Authorization": f"KakaoAK {rest_api_key}"}
        )
    except httpx.HTTPError as exc:
        raise KakaoServiceError(f"kakao request failed: {exc.__class__.__name__}") from exc
    if response.status_code in (401, 403):
        raise KakaoServiceError("kakao rejected the REST API key")
    if response.status_code != 200:
        raise KakaoServiceError(f"kakao returned status {response.status_code}")
    try:
        documents = response.json().get("documents") or []
    except ValueError as exc:
        raise KakaoServiceError("kakao returned invalid json") from exc

    places: list[KakaoPlace] = []
    for d in documents:
        try:
            places.append(
                KakaoPlace(
                    kakao_place_id=str(d["id"]),
                    name=d["place_name"][:100],
                    address=(d.get("road_address_name") or d.get("address_name") or "")[:200],
                    lat=float(d["y"]),
                    lng=float(d["x"]),
                    category=(d.get("category_name") or None) and d["category_name"][:50],
                )
            )
        except (KeyError, ValueError, TypeError):
            continue  # 형식이 이상한 항목은 건너뜁니다.
    return places
