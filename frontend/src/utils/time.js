// "YYYY-MM-DD" → 백엔드 요일 번호 (0=월 ~ 6=일). JS 의 getDay() 는 0=일 이라 변환이 필요합니다.
export const backendWeekday = (dateString) => {
  if (!dateString) return null;
  const [y, m, d] = dateString.split('-').map(Number);
  return (new Date(y, m - 1, d).getDay() + 6) % 7;
};

export const WEEKDAY_LABEL = ['월', '화', '수', '목', '금', '토', '일'];

// 분(0시 기준, 1440 이상 가능) → "HH:MM"
export const minutesToHHMM = (minutes) => {
  if (minutes === null || minutes === undefined) return '';
  const m = ((minutes % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
};

// 오늘 날짜 "YYYY-MM-DD" (로컬 시간대)
export const todayString = () => {
  const now = new Date();
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  return `${now.getFullYear()}-${mm}-${dd}`;
};

// 어제 날짜 "YYYY-MM-DD" (서버는 시차를 고려해 어제까지 허용합니다)
export const yesterdayString = () => {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mm}-${dd}`;
};

// 소요시간(분) → "1시간 20분"
export const formatDuration = (minutes) => {
  if (!minutes) return '0분';
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}분`;
  return m === 0 ? `${h}시간` : `${h}시간 ${m}분`;
};

export const EXCLUDE_REASON_LABEL = {
  WINDOW_TOO_SHORT: '영업시간이 체류시간보다 짧음',
  ALREADY_CLOSED: '출발 시각 전에 이미 영업 종료',
  UNREACHABLE_IN_TIME: '이동시간/일정 때문에 영업시간 안에 갈 수 없음',
  CLOSED_ON_DAY: '그날 휴무',
};
