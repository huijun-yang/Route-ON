import fetchInstance from './fetchInstance';

const json = (method, body, signal) => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
  signal,
});

// 그룹 생성 (초대코드 발급)
export const createGroup = (title, signal) => fetchInstance('/groups', json('POST', { title }, signal));

// 초대코드로 참여
export const joinGroup = (inviteCode, signal) =>
  fetchInstance('/groups/join', json('POST', { invite_code: inviteCode }, signal));

// 내 그룹 목록
export const getMyGroups = (signal) => fetchInstance('/groups', { method: 'GET', signal });

// 그룹 상세 (멤버, 후보, 득표)
export const getGroup = (groupId, signal) => fetchInstance(`/groups/${groupId}`, { method: 'GET', signal });

// 후보 장소 추가. 장소는 먼저 createPlace 로 저장돼 있어야 합니다.
export const addCandidate = (groupId, placeId, signal) =>
  fetchInstance(`/groups/${groupId}/candidates`, json('POST', { place_id: placeId }, signal));

// 후보 삭제
export const removeCandidate = (groupId, candidateId, signal) =>
  fetchInstance(`/groups/${groupId}/candidates/${candidateId}`, { method: 'DELETE', signal });

// 투표 / 투표 취소
export const voteCandidate = (groupId, candidateId, signal) =>
  fetchInstance(`/groups/${groupId}/candidates/${candidateId}/vote`, { method: 'POST', signal });

export const unvoteCandidate = (groupId, candidateId, signal) =>
  fetchInstance(`/groups/${groupId}/candidates/${candidateId}/vote`, { method: 'DELETE', signal });

// 득표 상위 장소로 코스 확정 (그룹 대표만)
// body: { course_date, start: {lat, lng}, start_time, title?, max_places?, default_stay_min?, stay_overrides? }
export const finalizeGroup = (groupId, body, signal) =>
  fetchInstance(`/groups/${groupId}/finalize`, json('POST', body, signal));

// 그룹 나가기 / 삭제(대표)
export const leaveGroup = (groupId, signal) =>
  fetchInstance(`/groups/${groupId}/members/me`, { method: 'DELETE', signal });

export const deleteGroup = (groupId, signal) =>
  fetchInstance(`/groups/${groupId}`, { method: 'DELETE', signal });
