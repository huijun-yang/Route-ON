import { EXCLUDE_REASON_LABEL, formatDuration } from '../../utils/time';

// 영업시간 안내 문구
const hoursText = (hours) => {
  if (!hours) return '';
  if (hours.closed) return '휴무';
  if (hours.source === 'assumed') return '영업시간 미입력(24시간 가정)';
  const breakText = hours.break_start ? ` · 휴식 ${hours.break_start}~${hours.break_end}` : '';
  return `영업 ${hours.open}~${hours.close}${breakText}`;
};

// 코스(CourseRead) 한 개의 방문 순서를 시간순으로 보여줍니다.
// onExtend 를 넘기면 각 장소에 "30분 더" 버튼이 나옵니다. (재계획)
const Timeline = ({ course, onExtend, busy = false, showEstimateNote = true, selectedId, onSelectStop }) => {
  const stops = course?.stops ?? [];
  const excluded = course?.excluded ?? [];

  if (stops.length === 0) {
    return <div className="empty">방문할 수 있는 장소가 없습니다.</div>;
  }

  return (
    <div className="stack">
      <h3 className="card-title" style={{ margin: 0 }}>
        일정 타임라인
      </h3>

      {showEstimateNote && course.has_estimated_travel && (
        <div className="alert alert-warning">⚠️ 일부 구간의 이동시간은 직선거리 기반 추정값입니다.</div>
      )}

      <div className="timeline">
        {stops.map((stop, idx) => (
          <div key={stop.id}>
            {stop.travel_min > 0 && (
              <div className="tl-leg">
                이동 {stop.travel_min}분
                {stop.walk_min > 0 && ` · 도보 ${stop.walk_min}분(${stop.walk_m}m)`}
                {stop.fare > 0 && ` · ${stop.fare.toLocaleString()}원`}
                {stop.travel_source === 'estimate' && ' · 추정'}
              </div>
            )}

            <div className="tl-stop">
              <span className="tl-time">
                {stop.start_time}
                {stop.arrival_day_offset > 0 && <sup>+{stop.arrival_day_offset}</sup>}
              </span>
              <span className="tl-marker">{idx + 1}</span>
              <div
                className={`tl-body${onSelectStop ? ' clickable' : ''}${selectedId === stop.place.kakao_place_id ? ' selected' : ''}`}
                onClick={onSelectStop ? () => onSelectStop(stop) : undefined}
              >
                <div className="row-between">
                  <strong>{stop.place.name}</strong>
                  {onExtend && (
                    <button
                      className="btn btn-sm"
                      disabled={busy}
                      onClick={(e) => {
                        e.stopPropagation();
                        onExtend(stop, idx);
                      }}
                    >
                      +30분
                    </button>
                  )}
                </div>
                <div className="tl-meta">
                  {formatDuration(stop.stay_duration)} 체류 · {stop.departure_time}까지
                  {stop.wait_min > 0 && ` · 영업 시작까지 ${stop.wait_min}분 대기`}
                </div>
                <div className="tl-meta">
                  {hoursText(stop.hours)}
                  {stop.estimated_cost > 0 && ` · 예상 지출 ${stop.estimated_cost.toLocaleString()}원`}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {excluded.length > 0 && (
        <div className="alert alert-warning" style={{ flexDirection: 'column', gap: '4px' }}>
          <strong>코스에서 제외된 장소</strong>
          {excluded.map((e) => (
            <span key={e.place_id}>
              · {e.name ?? e.place_id}: {EXCLUDE_REASON_LABEL[e.reason] ?? e.reason}
            </span>
          ))}
        </div>
      )}

      <div className="total-bar">
        <span>총 예상 비용 (교통비 + 지출)</span>
        <span>{course.total_cost.toLocaleString()}원</span>
      </div>
    </div>
  );
};

export default Timeline;
