import fetchInstance from './fetchInstance';

// 서버 상태 확인
export const getHealth = (signal) => {
  return fetchInstance('/health', {
    method: 'GET',
    signal,
  });
};

// DB 상태 확인
export const getHealthDb = (signal) => {
  return fetchInstance('/health/db', {
    method: 'GET',
    signal,
  });
};