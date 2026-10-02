import React, { useEffect } from 'react';

const RouteMap = ({ stops }) => {
  useEffect(() => {
    if (!window.kakao || !window.kakao.maps || stops.length === 0) return;

    const container = document.getElementById('map');
    const options = {
      center: new window.kakao.maps.LatLng(stops[0].lat, stops[0].lng),
      level: 5,
    };
    const map = new window.kakao.maps.Map(container, options);

    const linePath = [];

    stops.forEach((stop, index) => {
      const position = new window.kakao.maps.LatLng(stop.lat, stop.lng);
      linePath.push(position);

      // 마커 생성
      const marker = new window.kakao.maps.Marker({
        position: position,
        map: map,
      });

      // 마커 인포윈도우 (순서 표시)
      const infowindow = new window.kakao.maps.InfoWindow({
        content: `<div style="padding:5px;font-size:12px;">${index + 1}. ${stop.name}</div>`,
      });
      infowindow.open(map, marker);
    });

    // 이동 경로 선 그리기
    const polyline = new window.kakao.maps.Polyline({
      path: linePath,
      strokeWeight: 5,
      strokeColor: '#FF0000',
      strokeOpacity: 0.7,
      strokeStyle: 'solid',
    });
    polyline.setMap(map);
  }, [stops]);

  return <div id="map" style={{ width: '100%', height: '350px', borderRadius: '8px', marginBottom: '16px', border: '1px solid #ccc' }}></div>;
};

export default RouteMap;