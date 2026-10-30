import React, { useState } from 'react';
import PlaceSearch from './components/PlaceSearch';
import RouteMap from './components/RouteMap';
import PriorityView from './components/PriorityView';
import Timeline from './components/Timeline';
import GroupVote from './components/GroupVote';
import CourseHistory from './components/CourseHistory'; // 👈 8번 컴포넌트 추가
import './App.css'; // 👈 반응형 스타일 연동

function App() {
  const [places, setPlaces] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState('time');
  const [user, setUser] = useState(null);

  const sampleVariants = [
    { priority_type: 'time', title: '⏱️ 최단 시간', total_time: 120, total_walk: 800, total_cost: 2800, fatigue_level: '알찬 코스' },
    { priority_type: 'walk', title: '🚶 최소 도보', total_time: 140, total_walk: 300, total_cost: 3200, fatigue_level: '쉬엄쉬엄 코스' },
  ];

  const handleAddPlace = (newPlace) => {
    setPlaces([...places, newPlace]);
  };

  // 그룹 투표 확정 장소 연동
  const handleConfirmGroupPlaces = (confirmedPlaces) => {
    const formattedPlaces = confirmedPlaces.map((item) => ({
      place_id: item.id,
      name: item.name,
      category: item.category,
      lat: 37.5665,
      lng: 126.9780,
      open_time: '10:00',
      close_time: '22:00',
      stay_duration: item.category === '카페' ? 45 : 60,
      expected_cost: 10000,
    }));
    setPlaces((prev) => [...prev, ...formattedPlaces]);
  };

  // 히스토리 코스 불러오기 핸들러
  const handleLoadCourse = (loadedPlaces) => {
    setPlaces(loadedPlaces);
    alert('저장된 코스를 성공적으로 불러왔습니다!');
  };

  const handleReplan = (delayMinutes) => {
    alert(`현재 위치에서 ${delayMinutes}분 지연을 반영하여 남은 일정을 재계산합니다.`);
  };

  // 카카오 로그인
  const handleLogin = () => {
    if (!window.Kakao) {
      alert('카카오 SDK가 로드되지 않았습니다.');
      return;
    }
    if (!window.Kakao.isInitialized()) {
      window.Kakao.init(import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY);
    }
    window.Kakao.Auth.login({
      success: function (authObj) {
        window.Kakao.API.request({
          url: '/v2/user/me',
          success: function (res) {
            setUser({ nickname: res.kakao_account.profile.nickname });
            alert(`${res.kakao_account.profile.nickname}님 환영합니다!`);
          },
        });
      },
      fail: function (err) {
        alert('카카오 로그인 실패');
      },
    });
  };

  const handleLogout = () => {
    if (window.confirm('로그아웃 하시겠습니까?')) {
      setUser(null);
      alert('로그아웃 되었습니다.');
    }
  };

  const totalCost = places.reduce((sum, p) => sum + (p.expected_cost || 0), 0);

  return (
    <div className="app-container">
      {/* 헤더 */}
      <header className="app-header">
        <h2 style={{ margin: 0, fontSize: '22px' }}>🚩 Route:On - 대중교통 코스 최적화 Web App</h2>
        {user ? (
          <div>
            <strong>{user.nickname}</strong> 님
            <button onClick={handleLogout} style={{ marginLeft: '10px', padding: '6px 12px' }}>로그아웃</button>
          </div>
        ) : (
          <button onClick={handleLogin} style={{ padding: '6px 12px', backgroundColor: '#FEE500', border: 'none', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold' }}>
            카카오 로그인
          </button>
        )}
      </header>

      {/* 1. 장소 검색 */}
      <PlaceSearch onAddPlace={handleAddPlace} />

      {/* 7. 그룹 코스 투표 */}
      <GroupVote onConfirmPlaces={handleConfirmGroupPlaces} />

      {/* 8. 코스 히스토리 (저장/불러오기) */}
      <CourseHistory currentPlaces={places} onLoadCourse={handleLoadCourse} />

      {/* 2. 지도 표시 */}
      {places.length > 0 && <RouteMap stops={places} />}

      {/* 5. 우선순위 비교 */}
      {places.length > 1 && (
        <PriorityView
          variants={sampleVariants}
          selectedPriority={selectedVariant}
          onSelectVariant={(v) => setSelectedVariant(v.priority_type)}
        />
      )}

      {/* 6. 타임라인 및 비용/재계획 */}
      {places.length > 0 && (
        <Timeline stops={places} onReplan={handleReplan} totalCost={totalCost} />
      )}
    </div>
  );
}

export default App;