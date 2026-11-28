import { useMemo, useState } from "react";
import RouteMap from "../components/map/RouteMap";
import CourseCreateWorkspace from "../components/courses/CourseCreateWorkspace";
import { DEFAULT_START } from "../utils/defaults";
import { todayString } from "../utils/time";
import "../styles/workspace.css";

export default function CourseCreatePage() {
  // 현재 진행 단계 (1: 장소/조건 입력, 2: 계산 중, 3: 결과)
  const [step, setStep] = useState(1);
  // 입력한 장소들
  const [places, setPlaces] = useState([]);
  // 지도/목록에서 선택한 장소
  const [selectedPlace, setSelectedPlace] = useState(null);
  // 코스 조건 (날짜, 출발 시각, 출발지)
  const [settings, setSettings] = useState({
    title: "",
    courseDate: todayString(),
    startTime: "10:00",
    start: DEFAULT_START,
  });
  // 서버가 계산한 결과: { group_id, courses: [시간, 도보, 비용], warnings }
  const [plan, setPlan] = useState(null);
  // 결과 화면에서 보고 있는 우선순위 ("time" | "walk" | "cost")
  const [selectedPriority, setSelectedPriority] = useState("time");

  // 결과 화면에서 보고 있는 코스
  const currentCourse = plan?.courses?.find((c) => c.priority_type === selectedPriority);

  // 지도의 출발지: 결과 화면이면 코스에 저장된 출발 좌표(재계획하면 바뀜), 아니면 입력한 출발지
  const mapStart = useMemo(
    () =>
      step === 3 && currentCourse?.start_lat != null
        ? { lat: currentCourse.start_lat, lng: currentCourse.start_lng, label: "출발지" }
        : settings.start,
    [step, currentCourse, settings.start]
  );

  // 지도에 그릴 경로: 결과 화면이면 선택한 우선순위 코스의 방문 순서, 아니면 입력한 장소
  const course = useMemo(() => {
    const current = currentCourse;
    return (current?.stops ?? []).map((s) => ({
      kakao_place_id: s.place.kakao_place_id,
      name: s.place.name,
      lat: s.place.lat,
      lng: s.place.lng,
    }));
  }, [currentCourse]);

  return (
    <div className="course-create-wrapper">
      <CourseCreateWorkspace
        step={step}
        setStep={setStep}
        places={places}
        setPlaces={setPlaces}
        settings={settings}
        setSettings={setSettings}
        plan={plan}
        setPlan={setPlan}
        selectedPriority={selectedPriority}
        setSelectedPriority={setSelectedPriority}
        selectedPlace={selectedPlace}
        setSelectedPlace={setSelectedPlace}
      />
      <RouteMap
        places={places}
        course={course}
        start={mapStart}
        selectedPlace={selectedPlace}
        step={step}
        onSelectPlace={setSelectedPlace}
      />
    </div>
  );
}
