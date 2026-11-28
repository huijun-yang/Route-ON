import fetchInstance, { toQuery } from './fetchInstance';

// 코스 생성: 시간/도보/비용 우선순위 3개 버전을 한 번에 받습니다.
// body: { title, course_date, start: {lat, lng}, start_time, stops: [{place_id, stay_min?, estimated_cost, hours?}] }
export const createCourse = (body, signal) => {
  return fetchInstance('/courses', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
};

// 내 코스 목록 (히스토리). onlyActive=true 면 3개 버전 중 선택된 것만.
export const getMyCourses = ({ onlyActive = true, limit, offset } = {}, signal) => {
  return fetchInstance(
    `/courses${toQuery({ only_active: onlyActive, limit, offset })}`,
    { method: 'GET', signal }
  );
};

// 코스 상세 (주인 또는 그룹 멤버)
export const getCourse = (courseId, signal) => {
  return fetchInstance(`/courses/${courseId}`, { method: 'GET', signal });
};

// 공유 링크용 조회 (로그인 불필요)
export const getSharedCourse = (shareUuid, signal) => {
  return fetchInstance(`/courses/shared/${shareUuid}`, { method: 'GET', signal });
};

// 같은 요청에서 만든 3개 버전
export const getCourseGroup = (groupId, signal) => {
  return fetchInstance(`/courses/groups/${groupId}`, { method: 'GET', signal });
};

// 코스 이름 수정
export const renameCourse = (courseId, title, signal) => {
  return fetchInstance(`/courses/${courseId}`, {
    method: 'PATCH',
    body: JSON.stringify({ title }),
    signal,
  });
};

// 3개 버전 중 이 코스를 선택
export const activateCourse = (courseId, signal) => {
  return fetchInstance(`/courses/${courseId}/activate`, { method: 'POST', signal });
};

// 현재 위치·시각 기준 재계획
// body: { current_time: "HH:MM", current_lat, current_lng, visited_place_ids, stay_adjustments }
export const replanCourse = (courseId, body, signal) => {
  return fetchInstance(`/courses/${courseId}/replan`, {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
};

// 코스 삭제 (3개 버전 묶음 전체)
export const deleteCourse = (courseId, signal) => {
  return fetchInstance(`/courses/${courseId}`, { method: 'DELETE', signal });
};
