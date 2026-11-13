const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const fetchInstance = async (endpoint, options = {}) => {
  const token = localStorage.getItem("accessToken");

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // 인증 토큰이 있으면 자동 첨부
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  // HTTP 오류 처리
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(
      errorData?.message || `HTTP Error: ${response.status}`
    );
  }

  // 응답 본문이 없는 경우
  if (response.status === 204) {
    return null;
  }

  // 빈 응답 본문 처리
  const text = await response.text();
  return text ? JSON.parse(text) : null;
};

export default fetchInstance;