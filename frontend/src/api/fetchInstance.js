// .env 의 VITE_API_BASE_URL 이 비어 있으면 로컬 백엔드를 기본값으로 씁니다. (끝에 /api/v1 포함)
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

// 서버가 보낸 오류 본문에서 사람이 읽을 메시지를 뽑습니다.
// detail 은 문자열이거나, {message, excluded...} 객체이거나, 검증 오류 배열일 수 있습니다.
const extractMessage = (errorData, status) => {
  const detail = errorData?.detail;

  if (errorData?.message) return errorData.message;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => d.msg).filter(Boolean).join(', ') || `HTTP Error: ${status}`;
  }
  if (detail && typeof detail === 'object') {
    return detail.message || `HTTP Error: ${status}`;
  }
  return `HTTP Error: ${status}`;
};

const fetchInstance = async (endpoint, options = {}) => {
  const token = localStorage.getItem('accessToken');

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  // 인증 토큰이 있으면 자동 첨부
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  // 서버에 API 요청 및 네트워크 오류 처리
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers,
  }).catch((error) => {
    // 요청 취소(AbortError)는 그대로 던져서 호출한 쪽이 구분할 수 있게 합니다.
    if (error.name === 'AbortError') throw error;
    throw new Error('Network Error', {
      cause: error,
    });
  });

  // HTTP 오류 처리
  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    // 로그인 토큰이 만료/무효면 저장된 토큰을 지우고 앱에 알려 로그인 화면으로 보냅니다.
    if (response.status === 401 && token && !endpoint.startsWith('/auth/kakao')) {
      localStorage.removeItem('accessToken');
      window.dispatchEvent(new Event('auth:expired'));
    }
    const error = new Error(extractMessage(errorData, response.status));
    error.status = response.status;
    error.detail = errorData?.detail; // 코스 생성 422 의 excluded 목록 등을 화면에서 쓸 수 있게 보관
    throw error;
  }

  // 응답 본문이 없는 경우
  if (response.status === 204) {
    return null;
  }

  // 빈 응답 본문 처리
  const text = await response.text();
  return text ? JSON.parse(text) : null;
};

// ?a=1&b=2 형태의 쿼리 문자열. 값이 undefined/null/'' 인 항목은 뺍니다.
export const toQuery = (params = {}) => {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') search.append(key, value);
  });
  const text = search.toString();
  return text ? `?${text}` : '';
};

export default fetchInstance;
