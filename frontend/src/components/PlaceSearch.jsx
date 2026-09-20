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
  const [stayDuration, setStayDuration] = useState(60); // 기본 60분
  const [expectedCost, setExpectedCost] = useState(0);

  // 카카오 로컬 장소 검색
  const handleSearch = () => {
    if (!window.kakao || !window.kakao.maps) {
      alert('카카오맵 API 키가 등록되지 않았거나 로드되지 않았습니다.');
      return;
    }
    const ps = new window.kakao.maps.services.Places();
    ps.keywordSearch(keyword, (data, status) => {
      if (status === window.kakao.maps.services.Status.OK) {
        setSearchResults(data);
      } else {
        alert('검색 결과가 없거나 오류가 발생했습니다.');
      }
    });
  };

  // 장소 선택 시 카테고리별 체류시간 자동 제안 (보고서 5.7)
  const handleSelectPlace = (place) => {
    setSelectedPlace(place);
    let defaultStay = 60;
    if (place.category_name.includes('카페')) defaultStay = 45;
    else if (place.category_name.includes('음식점')) defaultStay = 60;
    else if (place.category_name.includes('전시') || place.category_name.includes('관광')) defaultStay = 90;
    setStayDuration(defaultStay);
  };

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
      stay_duration: parseInt(stayDuration),
      expected_cost: parseInt(expectedCost) || 0,
    });
    setSelectedPlace(null);
    setSearchResults([]);
    setKeyword('');
  };

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px', marginBottom: '16px' }}>
      <h3>1. 장소 검색 및 추가</h3>
      <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
        <input
          type="text"
          placeholder="가고 싶은 장소 검색 (예: 강남역 맛집)"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          style={{ flex: 1, padding: '8px' }}
        />
        <button onClick={handleSearch} style={{ padding: '8px 16px', cursor: 'pointer' }}>검색</button>
      </div>

      {searchResults.length > 0 && (
        <ul style={{ maxHeight: '150px', overflowY: 'auto', border: '1px solid #eee', padding: '8px', listStyle: 'none' }}>
          {searchResults.map((item) => (
            <li
              key={item.id}
              onClick={() => handleSelectPlace(item)}
              style={{ cursor: 'pointer', padding: '6px 0', borderBottom: '1px solid #f9f9f9' }}
            >
              <strong>{item.place_name}</strong> - <span style={{ fontSize: '12px', color: '#666' }}>{item.address_name}</span>
            </li>
          ))}
        </ul>
      )}

      {selectedPlace && (
        <div style={{ marginTop: '12px', background: '#f8f9fa', padding: '12px', borderRadius: '6px' }}>
          <h4>선택된 장소: {selectedPlace.place_name}</h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '8px' }}>
            <label>영업 시작: <input type="time" value={openTime} onChange={(e) => setOpenTime(e.target.value)} /></label>
            <label>영업 종료: <input type="time" value={closeTime} onChange={(e) => setCloseTime(e.target.value)} /></label>
            <label>체류시간(분): <input type="number" value={stayDuration} onChange={(e) => setStayDuration(e.target.value)} /></label>
            <label>예상 비용(원): <input type="number" value={expectedCost} onChange={(e) => setExpectedCost(e.target.value)} /></label>
          </div>
          <button onClick={handleAdd} style={{ marginTop: '12px', width: '100%', padding: '10px', backgroundColor: '#4CAF50', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}>
            코스에 장소 추가
          </button>
        </div>
      )}
    </div>
  );
};

export default PlaceSearch;