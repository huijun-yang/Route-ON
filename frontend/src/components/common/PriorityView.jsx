import { formatDuration } from '../../utils/time';

// 우선순위별 코스(최단 시간 / 최소 도보 / 최저 비용)를 나란히 비교하고 하나를 고릅니다.
const PriorityView = ({ variants, onSelectVariant, selectedPriority }) => {
  return (
    <div>
      <h3 className="card-title">우선순위별 코스 비교</h3>
      <div className="priority-grid">
        {variants.map((v) => (
          <button
            key={v.priority_type}
            className={`priority-card${selectedPriority === v.priority_type ? ' selected' : ''}`}
            onClick={() => onSelectVariant(v)}
          >
            <h4>{v.title}</h4>
            <p className="big">{formatDuration(v.total_time)}</p>
            <p>도보 {v.total_walk.toLocaleString()}m</p>
            <p>{v.total_cost.toLocaleString()}원</p>
            <p style={{ marginTop: '6px' }}>
              <span className="badge badge-accent" title="피로도">
                {v.fatigue_level}
              </span>
            </p>
          </button>
        ))}
      </div>
    </div>
  );
};

export default PriorityView;
