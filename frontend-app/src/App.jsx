import React, { useState } from 'react';
import PlaceSearch from './components/PlaceSearch';
import RouteMap from './components/RouteMap';
import PriorityView from './components/PriorityView';
import Timeline from './components/Timeline';

function App() {
  const [places, setPlaces] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState('time');

  const sampleVariants = [
    { priority_type: 'time', title: '⏱️ 최단 시간', total_time: 120, total_walk: 800, total_cost: 2800, fatigue_level: '알찬 코스' },
    { priority_type: 'walk', title: '🚶 최소 도보', total_time: 140, total_walk: 300, total_cost: 3200, fatigue_level: '쉬엄쉬엄 코스' },
  ];

  const handleAddPlace = (newPlace) => {
    setPlaces([...places, newPlace]);
  };

  const handleReplan = (delayMinutes) => {
    alert(`현재 위치에서 ${delayMinutes}분 지연을 반영하여 남은 일정을 재계산합니다.`);
  };

  const totalCost = places.reduce((sum, p) => sum + (p.expected_cost || 0), 0);

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <h2>🚩 Route:On - 대중교통 코스 최적화 Web App</h2>
      
      {/* 1. 장소 검색 및 추가 */}
      <PlaceSearch onAddPlace={handleAddPlace} />

      {/* 2. 지도 표시 */}
      {places.length > 0 && <RouteMap stops={places} />}

      {/* 3. 우선순위 비교 */}
      {places.length > 1 && (
        <PriorityView
          variants={sampleVariants}
          selectedPriority={selectedVariant}
          onSelectVariant={(v) => setSelectedVariant(v.priority_type)}
        />
      )}

      {/* 4. 타임라인 및 비용/재계획 */}
      {places.length > 0 && (
        <Timeline stops={places} onReplan={handleReplan} totalCost={totalCost} />
      )}
    </div>
  );
}

export default App;