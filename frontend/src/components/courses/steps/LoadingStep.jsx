import { useEffect, useRef } from "react";
import { createCourse } from "../../../api/coursesApi";
import { hoursToBody } from "../../../utils/placeDefaults";
import { EXCLUDE_REASON_LABEL } from "../../../utils/time";

// 입력한 장소와 조건으로 백엔드에 코스 계산을 요청합니다. (시간/도보/비용 3개 버전)
// 화면에 보이는 영업시간을 그대로 요청에 담아 보내므로, 계산 결과는 사용자가 확인한 값과 같습니다.
export default function LoadingStep({ onNext, onPrev, places, settings, setPlan, setSelectedPriority }) {
  // StrictMode 에서 effect 가 두 번 실행돼도 요청(=코스 저장)은 한 번만 보냅니다.
  const startedRef = useRef(false);
  // 화면을 벗어났을 때만 결과를 버립니다.
  const aliveRef = useRef(true);

  useEffect(() => {
    aliveRef.current = true;
    return () => {
      aliveRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (startedRef.current) return;
    startedRef.current = true;

    const body = {
      title: settings.title || undefined,
      course_date: settings.courseDate,
      start: { lat: settings.start.lat, lng: settings.start.lng },
      start_time: settings.startTime,
      stops: places.map((place) => ({
        place_id: place.kakao_place_id,
        // 비워 두면(null) 서버가 장소 유형별 추천 체류시간을 씁니다.
        ...(place.stay_min ? { stay_min: place.stay_min } : {}),
        estimated_cost: place.estimated_cost || 0,
        hours: hoursToBody(place.hours),
      })),
    };

    // 기본값 영업시간으로 계산한 장소는 결과 화면에서 확인을 권하도록 알려 줍니다.
    const guessed = places.filter((p) => p.hours_source === "default" && !p.hours.isClosed).map((p) => p.name);

    createCourse(body)
      .then((result) => {
        if (!aliveRef.current) return;
        const active = result.courses.find((c) => c.is_active) ?? result.courses[0];
        setPlan({ ...result, guessedHoursPlaces: guessed });
        setSelectedPriority(active.priority_type);
        onNext();
      })
      .catch((error) => {
        if (!aliveRef.current) return;

        // 422: 영업시간/이동시간 때문에 방문 가능한 장소가 없을 때 사유 목록이 함께 옵니다.
        const excluded = error.detail?.excluded;
        const lines = Array.isArray(excluded)
          ? excluded.map((e) => `- ${e.name}: ${EXCLUDE_REASON_LABEL[e.reason] ?? e.reason}`)
          : [];
        alert([error.message, ...lines].join("\n"));
        onPrev();
      });
  }, []);

  return (
    <div className="loading-panel">
      <div className="spinner" />
      <h3>최적의 방문 순서를 계산하고 있어요</h3>
      <p>영업시간, 브레이크타임, 대중교통 이동시간을 반영해 3가지 코스를 만드는 중입니다.</p>
    </div>
  );
}
