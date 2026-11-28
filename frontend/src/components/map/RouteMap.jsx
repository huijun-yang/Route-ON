import { useEffect, useRef } from 'react';

// 지도에 출발지와 방문 장소를 번호 핀으로 표시하고, 결과 화면에서는 방문 순서대로 경로선을 그립니다.
//
//  - places:        입력 단계의 장소 목록 (입력한 순서대로 번호를 붙임)
//  - course:        결과 코스의 방문 순서 (결과 단계에서 번호와 경로선에 사용)
//  - start:         출발지 {lat, lng, label}
//  - selectedPlace: 강조해서 보여줄 장소
//  - step:          1·2 = 입력/계산 중(핀만), 3 = 결과(핀 + 경로선)
//  - onSelectPlace: 핀을 눌렀을 때 호출 (선택 사항)
//
// 경로선은 장소 사이를 직선으로 이은 것입니다. (실제 도로·대중교통 경로가 아니라 방문 순서를 보여주는 용도)
const SEOUL_CITY_HALL = { lat: 37.5665, lng: 126.978 };

// 핀 DOM 만들기. 장소 이름은 textContent 로만 넣어서 HTML 로 해석되지 않게 합니다.
const createPin = ({ text, name, variant, onClick }) => {
  const root = document.createElement('div');
  root.className = `map-pin ${variant}`;

  const circle = document.createElement('span');
  circle.className = 'map-pin-circle';
  circle.textContent = text;

  const label = document.createElement('span');
  label.className = 'map-pin-label';
  label.textContent = name;

  root.append(circle, label);
  if (onClick) root.addEventListener('click', onClick);
  return root;
};

// 지도에 필요한 값만 뽑아 문자열로 만듭니다. 체류시간 입력처럼 지도와 무관한 값이 바뀔 때 지도가 다시 그려지지 않게 합니다.
const toSignature = (list) =>
  JSON.stringify(list.map((p) => ({ kakao_place_id: p.kakao_place_id, name: p.name, lat: p.lat, lng: p.lng })));

const RouteMap = ({ places = [], course = [], start, selectedPlace, step, onSelectPlace }) => {
  const placesSig = toSignature(places);
  const courseSig = toSignature(course);
  const startSig = JSON.stringify(start ?? null);
  const selectedId = selectedPlace?.kakao_place_id ?? null;
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const overlaysRef = useRef([]); // 지금 그려 둔 핀과 경로선 (다시 그리기 전에 지웁니다)
  // 카카오 지도 SDK 가 로드되지 않았으면(키/도메인 문제) 안내 문구를 보여줍니다.
  const unavailable = !window.kakao?.maps;

  // 지도 만들기 (한 번만). 컨테이너 크기가 바뀌면 지도도 다시 맞춥니다.
  useEffect(() => {
    const container = containerRef.current;
    if (!container || !window.kakao?.maps) return;

    mapRef.current = new window.kakao.maps.Map(container, {
      center: new window.kakao.maps.LatLng(SEOUL_CITY_HALL.lat, SEOUL_CITY_HALL.lng),
      level: 5,
    });

    const observer = new ResizeObserver(() => mapRef.current?.relayout());
    observer.observe(container);
    return () => {
      observer.disconnect();
      mapRef.current = null;
    };
  }, []);

  // 핀과 경로선 그리기
  useEffect(() => {
    const map = mapRef.current;
    const kakao = window.kakao;
    if (!map || !kakao?.maps) return;

    overlaysRef.current.forEach((overlay) => overlay.setMap(null));
    overlaysRef.current = [];

    const isResult = step === 3;
    const stops = JSON.parse(isResult ? courseSig : placesSig);
    const startPoint = JSON.parse(startSig);
    const bounds = new kakao.maps.LatLngBounds();
    const path = [];

    const add = (overlay) => overlaysRef.current.push(overlay);
    const position = (lat, lng) => new kakao.maps.LatLng(lat, lng);

    // 출발지
    if (startPoint) {
      const pos = position(startPoint.lat, startPoint.lng);
      bounds.extend(pos);
      path.push(pos);
      const overlay = new kakao.maps.CustomOverlay({
        position: pos,
        yAnchor: 1,
        zIndex: 3,
        content: createPin({ text: '출발', name: startPoint.label ?? '출발지', variant: 'start' }),
      });
      overlay.setMap(map);
      add(overlay);
    }

    // 방문 장소
    stops.forEach((stop, index) => {
      const pos = position(stop.lat, stop.lng);
      bounds.extend(pos);
      path.push(pos);

      const selected = selectedId !== null && selectedId === stop.kakao_place_id;
      const overlay = new kakao.maps.CustomOverlay({
        position: pos,
        yAnchor: 1,
        zIndex: selected ? 10 : 2,
        content: createPin({
          text: String(index + 1),
          name: stop.name,
          variant: selected ? 'selected' : '',
          onClick: onSelectPlace ? () => onSelectPlace(stop) : undefined,
        }),
      });
      overlay.setMap(map);
      add(overlay);
    });

    // 결과 화면: 출발지 → 방문 순서대로 경로선 (직선)
    if (isResult && path.length >= 2) {
      const line = new kakao.maps.Polyline({
        path,
        strokeWeight: 5,
        strokeColor: '#1769AA',
        strokeOpacity: 0.85,
        strokeStyle: 'solid',
        endArrow: true,
      });
      line.setMap(map);
      add(line);
    }

    // 선택한 장소가 있으면 그곳으로, 없으면 전체가 보이도록 맞춥니다.
    const selectedStop = selectedId === null ? null : stops.find((s) => s.kakao_place_id === selectedId);
    if (selectedStop) {
      map.panTo(position(selectedStop.lat, selectedStop.lng));
    } else if (path.length > 1) {
      map.setBounds(bounds, 60, 60, 60, 60);
    } else if (path.length === 1) {
      map.setCenter(path[0]);
    }
  }, [placesSig, courseSig, startSig, selectedId, step, onSelectPlace]);

  return (
    <div className="map-area">
      <div ref={containerRef} className="map-canvas" />
      {unavailable && (
        <div className="map-unavailable">
          지도를 불러오지 못했어요.
          <br />
          카카오 JavaScript 키와 사이트 도메인 등록을 확인해 주세요.
        </div>
      )}
    </div>
  );
};

export default RouteMap;
