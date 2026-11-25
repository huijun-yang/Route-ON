import React from 'react';

const PriorityView = ({ variants, onSelectVariant, selectedPriority }) => {
  return (
    <div style={{ marginBottom: '16px' }}>
      <h3>2. 경로 우선순위 선택</h3>
      <div style={{ display: 'flex', gap: '12px' }}>
        {variants.map((v) => (
          <div
            key={v.priority_type}
            onClick={() => onSelectVariant(v)}
            style={{
              flex: 1,
              padding: '12px',
              border: selectedPriority === v.priority_type ? '2px solid #007BFF' : '1px solid #ccc',
              borderRadius: '8px',
              cursor: 'pointer',
              backgroundColor: selectedPriority === v.priority_type ? '#e7f1ff' : '#fff',
            }}
          >
            <h4>{v.title}</h4>
            <p>총 소요시간: {v.total_time}분</p>
            <p>총 도보량: {v.total_walk}m</p>
            <p>총 교통비: {v.total_cost}원</p>
            <p style={{ fontWeight: 'bold', color: '#ff9800' }}>피로도: {v.fatigue_level}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PriorityView;