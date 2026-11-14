import fetchInstance from './fetchInstance';

// 장소 저장
export const createPlace = (placeData) => {
  return fetchInstance('/places', {
    method: 'POST',
    body: JSON.stringify(placeData),
  });
};

// 장소 조회
export const getPlace = (placeId) => {
  return fetchInstance(`/places/${placeId}`, {
    method: 'GET',
  });
};

// 영업시간 저장 및 수정
export const upsertBusinessHours = (placeId, businessHours) => {
  return fetchInstance(`/places/${placeId}/business-hours`, {
    method: 'POST',
    body: JSON.stringify(businessHours),
  });
};

// 영업시간 조회
export const getBusinessHours = (placeId) => {
  return fetchInstance(`/places/${placeId}/business-hours`, {
    method: 'GET'
  });
};

// 영업시간 삭제
export const deleteBusinessHours = (placeId, weekday) => {
  return fetchInstance(`/places/${placeId}/business-hours/${weekday}`, {
    method: 'DELETE',
  });
};