import fetchInstance, { toQuery } from './fetchInstance';

// 카카오 장소 검색 (백엔드 경유). 결과는 그대로 createPlace 에 보낼 수 있는 형태입니다.
export const searchPlaces = (query, { lat, lng, radius, size } = {}, signal) => {
  return fetchInstance(`/places/search${toQuery({ query, lat, lng, radius, size })}`, {
    method: 'GET',
    signal,
  });
};

// 장소 저장
export const createPlace = (placeData, signal) => {
  // 서버가 받는 필드만 보냅니다. (화면 상태에 붙은 stay_min 등은 제외)
  const { kakao_place_id, name, address, lat, lng, category } = placeData;
  return fetchInstance('/places', {
    method: 'POST',
    body: JSON.stringify({ kakao_place_id, name, address: address || '', lat, lng, category }),
    signal,
  });
};

// 장소 조회
export const getPlace = (placeId, signal) => {
  return fetchInstance(`/places/${placeId}`, {
    method: 'GET',
    signal,
  });
};

// 장소 유형별 추천 체류시간(분)
export const getRecommendedStay = (placeId, signal) => {
  return fetchInstance(`/places/${placeId}/recommended-stay`, {
    method: 'GET',
    signal,
  });
};

// 영업시간 저장 및 수정 (요일 단위)
// businessHours: { weekday, is_closed, open_time, close_time, break_start, break_end }  시간은 "HH:MM"
export const upsertBusinessHours = (placeId, businessHours, signal) => {
  return fetchInstance(`/places/${placeId}/business-hours`, {
    method: 'POST',
    body: JSON.stringify(businessHours),
    signal,
  });
};

// 영업시간 조회
export const getBusinessHours = (placeId, signal) => {
  return fetchInstance(`/places/${placeId}/business-hours`, {
    method: 'GET',
    signal,
  });
};

// 영업시간 삭제
export const deleteBusinessHours = (placeId, weekday, signal) => {
  return fetchInstance(`/places/${placeId}/business-hours/${weekday}`, {
    method: 'DELETE',
    signal,
  });
};

// 특정 날짜 하나에만 적용되는 영업시간/임시휴무 저장
// exception: { date: "YYYY-MM-DD", is_closed, open_time, close_time, break_start, break_end }
export const upsertBusinessHoursException = (placeId, exception, signal) => {
  return fetchInstance(`/places/${placeId}/business-hours/exceptions`, {
    method: 'POST',
    body: JSON.stringify(exception),
    signal,
  });
};

// 날짜별 예외 조회
export const getBusinessHoursExceptions = (placeId, fromDate, signal) => {
  return fetchInstance(
    `/places/${placeId}/business-hours/exceptions${toQuery({ from_date: fromDate })}`,
    { method: 'GET', signal }
  );
};

// 날짜별 예외 삭제
export const deleteBusinessHoursException = (placeId, date, signal) => {
  return fetchInstance(`/places/${placeId}/business-hours/exceptions/${date}`, {
    method: 'DELETE',
    signal,
  });
};
