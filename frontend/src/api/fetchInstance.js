const BASE_URL = import.meta.env.VITE_API_BASE_URL;

const fetchInstance = async (endpoint, options = {}) => {
  const token = localStorage.getItem("accessToken");

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // 인증 토큰 첨부
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

  // 응답 데이터가 없는 경우 처리 (204 No Content)
  if (response.status === 204) {
    return null;
  }

  return response.json();
};

export default fetchInstance;