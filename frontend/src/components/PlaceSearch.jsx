import React, { useState } from 'react';

const PlaceSearch = ({ onAddPlace }) => {
  const [keyword, setKeyword] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [selectedPlace, setSelectedPlace] = useState(null);

  // 세부 입력 정보
  const [openTime, setOpenTime] = useState('10:00');
  const [closeTime, setCloseTime] = useState('22:00');
  const [breakStart, setBreakStart] = useState('');
  const [breakEnd, setBreakEnd] = useState('');
  const [stayDuration, setStayDuration] = useState(60);
  const [expectedCost, setExpectedCost] = useState(0);

  // 카카오 로컬 장소 검색
  const handleSearch = () => {
    if (!keyword.trim()) {
      alert('검색어를 입력해 주세요.');
      return;
    }

    if (!window.kakao || !window.kakao.maps) {
      alert('카카오맵 API 키가 등록되지 않았거나 로드되지 않았습니다.');
      return;
    }

    window.kakao.maps.load(() => {
      if (!window.kakao.maps.services || !window.kakao.maps.services.Places) {
        alert('카카오 장소 검색 서비스(services)를 불러오지 못했습니다.');
        return;
      }

      const ps = new window.kakao.maps.services.Places();
      ps.keywordSearch(keyword, (data, status) => {
        if (status === window.kakao.maps.services.Status.OK) {
          setSearchResults(data);
          setSelectedPlace(null); // 새 검색 시 기존 선택 초기화
        } else if (status === window.kakao.maps.services.Status.ZERO_RESULT) {
          alert('검색 결과가 존재하지 않습니다.');
          setSearchResults([]);
        } else {
          alert('장소 검색 중 오류가 발생했습니다.');
          setSearchResults([]);
        }
      });
    });
  };

  // 장소 클릭 선택 핸들러
  const handleSelectPlace = (place) => {
    setSelectedPlace(place);

    // 카테고리별 기본 체류시간 제안
    let defaultStay = 60;
    const category = place.category_name || '';

    if (category.includes('카페')) defaultStay = 45;
    else if (category.includes('음식점')) defaultStay = 60;
    else if (category.includes('전시') || category.includes('관광') || category.includes('문화')) defaultStay = 90;

    setStayDuration(defaultStay);
  };

  // 코스에 장소 추가
  const handleAdd = () => {
    if (!selectedPlace) return;

    onAddPlace({
      place_id: selectedPlace.id,
      name: selectedPlace.place_name,
      lat: parseFloat(selectedPlace.y),
      lng: parseFloat(selectedPlace.x),
      category: selectedPlace.category_name,
      open_time: openTime,
      close_time: closeTime,
      break_start: breakStart,
      break_end: breakEnd,
      stay_duration: parseInt(stayDuration) || 0,
      expected_cost: parseInt(expectedCost) || 0,
    });

    // 추가 후 초기화
    setSelectedPlace(null);
    setSearchResults([]);
    setKeyword('');
  };

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px', marginBottom: '16px', backgroundColor: '#fff' }}>
      <h3 style={{ marginTop: 0, marginBottom: '12px' }}>1. 장소 검색 및 추가</h3>
      
      {/* 검색 입력창 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
        <input
          type="text"
          placeholder="가고 싶은 장소 검색 (예: 강남역 맛집)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button onClick={handleSearch} style={{ padding: '8px 16px', cursor: 'pointer', borderRadius: '4px', border: '1px solid #ccc', backgroundColor: '#f0f0f0' }}>
          검색
        </button>
      </div>

      {/* 검색 결과 목록 */}
      {searchResults.length > 0 && (
        <ul style={{ maxHeight: '180px', overflowY: 'auto', border: '1px solid #eee', padding: '0', margin: '0 0 12px 0', listStyle: 'none', borderRadius: '4px' }}>
          {searchResults.map((item) => {
            const isSelected = selectedPlace?.id === item.id;
            return (
              <li
                key={item.id}
                onClick={() => handleSelectPlace(item)}
                style={{
                  cursor: 'pointer',
                  padding: '10px 12px',
                  borderBottom: '1px solid #f0f0f0',
                  backgroundColor: isSelected ? '#e8f4ff' : '#ffffff',
                  borderLeft: isSelected ? '4px solid #2196F3' : 'none',
                  transition: 'background-color 0.2s'
                }}
              >
                <div style={{ fontWeight: isSelected ? 'bold' : 'normal', color: isSelected ? '#1976D2' : '#333' }}>
                  {item.place_name}
                </div>
                <div style={{ fontSize: '12px', color: '#666', marginTop: '2px' }}>
                  {item.address_name || item.road_address_name}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {/* 선택된 장소 세부 정보 입력창 */}
      {selectedPlace && (
        <div style={{ marginTop: '12px', background: '#f8f9fa', padding: '14px', borderRadius: '6px', border: '1px solid #e0e0e0' }}>
          <h4 style={{ margin: '0 0 10px 0', color: '#2196F3' }}>
            📍 선택된 장소: {selectedPlace.place_name}
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '8px' }}>
            <label style={{ fontSize: '13px' }}>
              영업 시작: <input type="time" value={openTime} onChange={(e) => setOpenTime(e.target.value)} style={{ width: '100%', padding: '4px', marginTop: '4px' }} />
            </label>
            <label style={{ fontSize: '13px' }}>
              영업 종료: <input type="time" value={closeTime} onChange={(e) => setCloseTime(e.target.value)} style={{ width: '100%', padding: '4px', marginTop: '4px' }} />
            </label>
            <label style={{ fontSize: '13px' }}>
              체류시간(분): <input type="number" value={stayDuration} onChange={(e) => setStayDuration(e.target.value)} style={{ width: '100%', padding: '4px', marginTop: '4px' }} />
            </label>
            <label style={{ fontSize: '13px' }}>
              예상 비용(원): <input type="number" value={expectedCost} onChange={(e) => setExpectedCost(e.target.value)} style={{ width: '100%', padding: '4px', marginTop: '4px' }} />
            </label>
          </div>
          <button
            onClick={handleAdd}
            style={{
              marginTop: '14px',
              width: '100%',
              padding: '10px',
              backgroundColor: '#4CAF50',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontWeight: 'bold',
              fontSize: '14px',
              cursor: 'pointer'
            }}
          >
            ➕ 코스에 장소 추가
          </button>
        </div>
      )}
    </div>
  );
};

export default PlaceSearch;