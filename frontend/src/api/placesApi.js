import fetchInstance from './fetchInstance';

// 장소 저장
export const createPlace = (placeData, signal) => {
  return fetchInstance('/places', {
    method: 'POST',
    body: JSON.stringify(placeData),
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

// 영업시간 저장 및 수정
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