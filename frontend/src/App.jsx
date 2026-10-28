import React, { useState } from 'react';
import PlaceSearch from './components/PlaceSearch';
import RouteMap from './components/RouteMap';
import PriorityView from './components/PriorityView';
import Timeline from './components/Timeline';

function App() {
  const [places, setPlaces] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState('time');
  
  // 로그인 상태 관리 (기본값: null -> 비로그인 상태)
  const [user, setUser] = useState(null);

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

  // 🔑 카카오 로그인 처리 함수 (카카오 SDK 활용)
  const handleLogin = () => {
    if (!window.Kakao) {
      alert('카카오 SDK가 로드되지 않았습니다. index.html을 확인해주세요.');
      return;
    }
    
    // 카카오 SDK 초기화 (본인의 자바스크립트 앱 키 입력)
   if (!window.Kakao.isInitialized()) {
  window.Kakao.init(import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY);
}

    // 카카오 로그인 팝업 실행
    window.Kakao.Auth.login({
      success: function (authObj) {
        console.log('로그인 성공 토큰:', authObj);
        // 카카오 사용자 정보 요청 API
        window.Kakao.API.request({
          url: '/v2/user/me',
          success: function (res) {
            const profile = res.kakao_account.profile;
            setUser({
              nickname: profile.nickname,
            });
            alert(`${profile.nickname}님 환영합니다!`);
          },
          fail: function (error) {
            console.error('사용자 정보 요청 실패:', error);
          },
        });
      },
      fail: function (err) {
        alert('카카오 로그인에 실패했습니다.');
        console.error(err);
      },
    });
  };

  // 🚪 로그아웃 처리 함수
  const handleLogout = () => {
    if (window.confirm('로그아웃 하시겠습니까?')) {
      if (window.Kakao && window.Kakao.Auth && window.Kakao.Auth.getAccessToken()) {
        window.Kakao.Auth.logout(() => {
          console.log('카카오 로그아웃 완료');
        });
      }
      localStorage.removeItem('token');
      setUser(null); // 사용자 정보 초기화 (로그아웃 상태)
      alert('로그아웃 되었습니다.');
    }
  };

  const totalCost = places.reduce((sum, p) => sum + (p.expected_cost || 0), 0);

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      {/* 上단 헤더: 제목 + 로그인 정보 / 로그인·로그아웃 버튼 */}
      <header style={{
        display: 'flex',
        justify: 'space-between',
        alignItems: 'center',
        paddingBottom: '16px',
        marginBottom: '20px',
        borderBottom: '2px solid #f0f0f0'
      }}>
        <h2 style={{ margin: 0, fontSize: '22px' }}>🚩 Route:On - 대중교통 코스 최적화 Web App</h2>
        
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '14px', color: '#333' }}>
              <strong>{user.nickname}</strong> 님
            </span>
            <button
              onClick={handleLogout}
              style={{
                padding: '6px 12px',
                backgroundColor: '#f5f5f5',
                border: '1px solid #ccc',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: 'bold',
                color: '#555'
              }}
            >
              로그아웃
            </button>
          </div>
        ) : (
          <button
            onClick={handleLogin} // 👈 alert 대신 handleLogin 함수 연결!
            style={{
              padding: '6px 12px',
              backgroundColor: '#FEE500', // 카카오 노란색
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 'bold',
              color: '#000'
            }}
          >
            카카오 로그인
          </button>
        )}
      </header>

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