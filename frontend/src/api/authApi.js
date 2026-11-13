import fetchInstance from "./fetchInstance";

// 카카오 로그인 및 서비스 JWT 발급
export const loginWithKakao = async (kakaoAccessToken) => {
  const result = await fetchInstance("/auth/kakao", {
    method: "POST",
    body: JSON.stringify({
      access_token: kakaoAccessToken,
    }),
  });

  // 백엔드에서 발급한 JWT 저장
  localStorage.setItem("accessToken", result.access_token);

  return result;
};

// 내 정보 조회 (로그인 필요)
export const getMyInfo = () => {
  return fetchInstance("/auth/me", {
    method: "GET",
  });
};