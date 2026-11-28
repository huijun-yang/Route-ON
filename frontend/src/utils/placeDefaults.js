// 장소 유형(카카오 카테고리)별 영업시간 기본값.
// 영업시간을 자동으로 알 수 없으므로, 사용자가 고치기 쉽도록 흔한 값을 미리 채워 둡니다.
// (규칙은 위에서부터 먼저 맞는 것을 씁니다. 실제 영업시간과 다를 수 있어 화면에 "기본값" 표시를 합니다.)
const RULES = [
  { keywords: ['카페', '커피', '디저트', '베이커리'], open: '10:00', close: '22:00' },
  { keywords: ['술집', '주점', '호프', '이자카야', '바(BAR)'], open: '17:00', close: '24:00' },
  { keywords: ['음식점', '식당', '한식', '양식', '일식', '중식', '분식'], open: '11:00', close: '21:00' },
  { keywords: ['박물관', '미술관', '전시', '갤러리', '과학관', '기념관'], open: '10:00', close: '18:00' },
  { keywords: ['궁', '사찰', '문화재', '관광', '명소'], open: '09:00', close: '18:00' },
  { keywords: ['시장'], open: '09:00', close: '20:00' },
  { keywords: ['쇼핑', '백화점', '아울렛', '마트'], open: '10:30', close: '20:00' },
];

const FALLBACK = { open: '10:00', close: '22:00' };

// 입력 폼이 쓰는 영업시간 값. 시간은 "HH:MM", 24시 마감은 백엔드가 받는 "00:00" 으로 바꿔 보냅니다.
export const defaultHoursFor = (category) => {
  const found = RULES.find((rule) => category && rule.keywords.some((k) => category.includes(k)));
  const base = found ?? FALLBACK;
  return {
    isClosed: false,
    openTime: base.open,
    closeTime: base.close === '24:00' ? '00:00' : base.close,
    hasBreak: false,
    breakStart: '15:00',
    breakEnd: '17:00',
  };
};

// 서버 시간 "HH:MM:SS" → input[type=time] 값 "HH:MM"
export const toInputTime = (value) => (value ? value.slice(0, 5) : '');

// 서버가 돌려준 영업시간 행(요일 값 또는 날짜별 예외) → 입력 폼 값
export const hoursFromServer = (row, category) => {
  const base = defaultHoursFor(category);
  return {
    isClosed: row.is_closed,
    openTime: toInputTime(row.open_time) || base.openTime,
    closeTime: toInputTime(row.close_time) || base.closeTime,
    hasBreak: Boolean(row.break_start),
    breakStart: toInputTime(row.break_start) || base.breakStart,
    breakEnd: toInputTime(row.break_end) || base.breakEnd,
  };
};

// 입력 폼 값 → 백엔드가 받는 영업시간 본문 (휴무면 시간 값을 모두 비움)
export const hoursToBody = (hours) =>
  hours.isClosed
    ? { is_closed: true }
    : {
        is_closed: false,
        open_time: hours.openTime,
        close_time: hours.closeTime,
        break_start: hours.hasBreak ? hours.breakStart : null,
        break_end: hours.hasBreak ? hours.breakEnd : null,
      };

const toMinutes = (hhmm) => {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
};

// 영업시간 입력값 검사. 문제가 있으면 안내 문구를, 없으면 null 을 돌려줍니다.
// 서버의 검증 규칙과 같습니다. (자정을 넘기는 영업과 휴식도 한 줄로 펴서 비교)
export const validateHours = (hours) => {
  if (hours.isClosed) return null;
  if (!hours.openTime || !hours.closeTime) return '영업 시작/종료 시각을 입력하세요.';
  if (!hours.hasBreak) return null;
  if (!hours.breakStart || !hours.breakEnd) return '휴식 시작/종료 시각을 입력하세요.';
  if (hours.breakStart === hours.breakEnd) return '휴식 시작과 종료가 같을 수 없습니다.';

  const open = toMinutes(hours.openTime);
  let close = toMinutes(hours.closeTime);
  if (close <= open) close += 1440;
  let start = toMinutes(hours.breakStart);
  let end = toMinutes(hours.breakEnd);
  if (start < open) start += 1440;
  if (end <= start) end += 1440;
  if (!(open <= start && start < end && end <= close)) return '휴식 시간은 영업시간 안에 있어야 합니다.';
  return null;
};
