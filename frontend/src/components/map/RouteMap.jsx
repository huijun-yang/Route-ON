import React, { useEffect, useRef } from 'react';

const RouteMap = ({ places, course, selectedPlace, step }) => {
  const mapRef = useRef(null);
  const mapInstance = useRef(null);

  useEffect(() => {
    const container = mapRef.current;

    if (!container || !window.kakao?.maps) return;

    // 기본 지도 중심 좌표 (서울시청)
    const defaultPosition = new window.kakao.maps.LatLng(37.5665, 126.978);

    // 지도 최초 생성
    if (!mapInstance.current) {
      mapInstance.current = new window.kakao.maps.Map(
        container, {
          center: defaultPosition,
          level: 5,
        }
      );
    }

    const map = mapInstance.current;
    const stops = (step === 1 || step === 2) ? places : course;

    // 기존 마커 제거
    if (mapRef.current.markers) {
      mapRef.current.markers.forEach(
        marker => marker.setMap(null)
      );
    }

    // 기존 경로 제거
    if (mapRef.current.polyline) {
      mapRef.current.polyline.setMap(null);
    }

    // 장소가 없으면 기본 지도만 출력
    if (stops.length === 0) {
      map.setCenter(defaultPosition);
      map.relayout();
      return;
    }

    // 선택된 장소가 없으면 첫 번째 장소를 중심으로 설정
    targetPlace = selectedPlace ?? stops[0];
    map.setCenter(new window.kakao.maps.LatLng(targetPlace.lat, targetPlace.lng));

    const linePath = [];
    const markers = [];

    stops.forEach((stop, index) => {
      const position = new window.kakao.maps.LatLng(stop.lat, stop.lng);
      linePath.push(position);

      // 마커 생성
      const marker = new window.kakao.maps.Marker({
        position: position,
        map: map,
      });

      markers.push(marker);

      // 마커 인포윈도우 (순서 표시)
      const infowindow = new window.kakao.maps.InfoWindow({
        content: `<div style="padding:5px;font-size:12px;">${index + 1}. ${stop.name}</div>`,
      });
      infowindow.open(map, marker);
    });

    mapRef.current.markers = markers;

    if(step === 3) {
      // 이동 경로 선 그리기
      const polyline = new window.kakao.maps.Polyline({
        path: linePath,
        strokeWeight: 5,
        strokeColor: '#FF0000',
        strokeOpacity: 0.7,
        strokeStyle: 'solid',
      });
      polyline.setMap(map);
      mapRef.current.polyline = polyline;
    }

    // 지도 영역 재계산
    map.relayout();

  }, [places, course, step]);

  return <div ref={mapRef} style={{ flex: "1", minWidth: "0px" }}></div>;
};

export default RouteMap;