import fetchInstance from './fetchInstance';

// 서버 상태 확인
export const getHealth = () => {
  return fetchInstance('/health', {
    method: 'GET',
  });
};

// DB 상태 확인
export const getHealthDb = () => {
  return fetchInstance('/health/db', {
    method: 'GET',
  });
};