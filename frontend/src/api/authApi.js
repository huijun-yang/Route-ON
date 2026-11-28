import fetchInstance from './fetchInstance';

// 카카오 로그인 및 서비스 JWT 발급
export const loginWithKakao = async (kakaoAccessToken, signal) => {
  const result = await fetchInstance('/auth/kakao', {
    method: 'POST',
    body: JSON.stringify({
      access_token: kakaoAccessToken,
    }),
    signal,
  });

  return result;
};

// 닉네임 수정 (로그인 필요)
export const updateMyInfo = (nickname, signal) => {
  return fetchInstance('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify({ nickname }),
    signal,
  });
};

// 내 정보 조회 (로그인 필요)
export const getMyInfo = (signal) => {
  return fetchInstance('/auth/me', {
    method: 'GET',
    signal,
  });
};