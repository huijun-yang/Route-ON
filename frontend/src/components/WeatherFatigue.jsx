import React from 'react';

const WeatherFatigue = ({ places }) => {
  // 1. 날씨 정보 (예시 데이터 또는 공공데이터 API 연동 지점)
  const currentWeather = {
    temp: '22°C',
    sky: '☀️ 맑음',
    pop: '강수확률 10%',
  };

  // 2. 총 이동거리 및 피로도 등급 계산 로직
  // (실제 좌표 간 직선/도보 거리를 기반으로 산출)
  const calculateFatigue = () => {
    if (!places || places.length === 0) return { distance: 0, level: '측정 불가', color: '#888' };
    
    // 단순 예시 계산 (장소 개수 및 체류시간 기반 체력 소모도)
    const totalPlaces = places.length;
    const estimatedDistance = (totalPlaces * 1.5).toFixed(1); // 장소당 평균 1.5km 이동 추정

    if (totalPlaces <= 2) {
      return { distance: estimatedDistance, level: '🟢 여유로움 (쉬엄쉬엄 코스)', color: '#4CAF50' };
    } else if (totalPlaces <= 4) {
      return { distance: estimatedDistance, level: '🟡 보통 (알찬 데이트/여행)', color: '#FF9800' };
    } else {
      return { distance: estimatedDistance, level: '🔴 피로도 높음 (강행군 코스)', color: '#F44336' };
    }
  };

  const fatigue = calculateFatigue();

  return (
    <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
      {/* 날씨 예보 카드 */}
      <div style={{ flex: 1, minWidth: '220px', padding: '14px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#eef7ff' }}>
        <h4 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#0288d1' }}>🌤️ 오늘/방문일 날씨 정보</h4>
        <div style={{ fontSize: '14px', color: '#333' }}>
          <div><strong>날씨:</strong> {currentWeather.sky}</div>
          <div><strong>기온:</strong> {currentWeather.temp} ({currentWeather.pop})</div>
        </div>
      </div>

      {/* 코스 피로도 지표 카드 */}
      <div style={{ flex: 1, minWidth: '220px', padding: '14px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#fffde7' }}>
        <h4 style={{ margin: '0 0 8px 0', fontSize: '15px', color: '#f57f17' }}>⚡ 코스 피로도 지표</h4>
        <div style={{ fontSize: '14px', color: '#333' }}>
          <div><strong>예상 총 이동거리:</strong> 약 {fatigue.distance} km</div>
          <div><strong>체력 등급:</strong> <span style={{ fontWeight: 'bold', color: fatigue.color }}>{fatigue.level}</span></div>
        </div>
      </div>
    </div>
  );
};

export default WeatherFatigue;