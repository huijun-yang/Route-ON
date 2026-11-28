import fetchInstance, { toQuery } from './fetchInstance';

// 방문일 날씨 (기상청 단기예보, 약 3일 이내). date: "YYYY-MM-DD", hour: 0~23
export const getWeather = ({ lat, lng, date, hour }, signal) => {
  return fetchInstance(`/weather${toQuery({ lat, lng, date, hour })}`, {
    method: 'GET',
    signal,
  });
};
