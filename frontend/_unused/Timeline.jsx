import React from 'react';

const Timeline = ({ stops, onReplan, totalCost }) => {
  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>3. 일정 타임라인</h3>
        <button
          onClick={() => onReplan(30)}
          style={{ backgroundColor: '#ff5722', color: 'white', border: 'none', padding: '8px 12px', borderRadius: '4px', cursor: 'pointer' }}
        >
          ⏱️ 30분 더 머무르기 (실시간 재계획)
        </button>
      </div>

      <div style={{ marginTop: '12px' }}>
        {stops.map((stop, idx) => (
          <div key={idx} style={{ display: 'flex', gap: '16px', padding: '8px 0', borderBottom: '1px dashed #ccc' }}>
            <span style={{ fontWeight: 'bold', color: '#007BFF' }}>{stop.open_time || '10:00'}</span>
            <div>
              <strong>{idx + 1}. {stop.name}</strong> ({stop.stay_duration}분 체류)
              <span style={{ marginLeft: '10px', fontSize: '12px', color: '#666' }}>예상 지출: {stop.expected_cost}원</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '16px', textAlign: 'right', fontWeight: 'bold', fontSize: '16px' }}>
        총 예상 비용 합계: <span style={{ color: '#d32f2f' }}>{totalCost.toLocaleString()}원</span>
      </div>
    </div>
  );
};

export default Timeline;