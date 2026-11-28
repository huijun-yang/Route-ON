import { useEffect, useState } from 'react';
import { getWeather } from '../../api/weatherApi';

const LEVEL_BADGE = { 여유로움: 'badge-success', 보통: 'badge-warning', 높음: 'badge-danger' };

// 방문일 날씨(기상청)와 코스 피로도(서버 계산값)를 보여줍니다.
const WeatherFatigue = ({ course }) => {
  const [weather, setWeather] = useState(null);
  const [weatherError, setWeatherError] = useState('');
  const [needsLogin, setNeedsLogin] = useState(false);

  const first = course?.stops?.[0]?.place;
  const date = course?.course_date;
  const hour = Math.floor(((course?.start_min ?? 720) % 1440) / 60);

  useEffect(() => {
    if (!first || !date) return;
    const controller = new AbortController();
    setWeather(null);
    setWeatherError('');

    getWeather({ lat: first.lat, lng: first.lng, date, hour }, controller.signal)
      .then(setWeather)
      .catch((error) => {
        if (error.name === 'AbortError') return;
        if (error.status === 401) setNeedsLogin(true);
        else setWeatherError(error.message);
      });

    return () => controller.abort();
  }, [first?.lat, first?.lng, date, hour]);

  if (!course) return null;

  return (
    <div className="info-grid">
      <div className="info-card">
        <h4>🌤️ 방문일 날씨</h4>
        {needsLogin && <span className="muted">로그인하면 방문일 날씨를 볼 수 있어요.</span>}
        {weatherError && <span className="muted">날씨를 불러오지 못했습니다.</span>}
        {!needsLogin && !weatherError && !weather && <span className="muted">불러오는 중...</span>}
        {weather && !weather.available && <span className="muted">예보 범위(약 3일)를 벗어났어요.</span>}
        {weather?.available && (
          <>
            <div style={{ fontWeight: 700 }}>
              {weather.summary ?? `${weather.sky ?? ''} ${weather.precipitation ?? ''}`}
            </div>
            <div className="muted">
              {weather.temp_c !== null && `${weather.temp_c}°C`}
              {weather.pop !== null && ` · 강수확률 ${weather.pop}%`}
            </div>
          </>
        )}
      </div>

      <div className="info-card">
        <h4>⚡ 코스 피로도</h4>
        <span className={`badge ${LEVEL_BADGE[course.fatigue_level] ?? ''}`}>
          {course.fatigue_level} · {course.fatigue_score}점
        </span>
        <div className="muted" style={{ marginTop: '4px' }}>
          도보 {(course.total_walk / 1000).toFixed(1)}km · 이동 {course.total_travel_min}분
        </div>
      </div>
    </div>
  );
};

export default WeatherFatigue;
