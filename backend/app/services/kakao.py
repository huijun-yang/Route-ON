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
