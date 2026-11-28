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

  // 지도에 그릴 경로: 결과 화면이면 선택한 우선순위 코스의 방문 순서, 아니면 입력한 장소
  const course = useMemo(() => {
    const current = plan?.courses?.find((c) => c.priority_type === selectedPriority);
    return (current?.stops ?? []).map((s) => ({
      kakao_place_id: s.place.kakao_place_id,
      name: s.place.name,
      lat: s.place.lat,
      lng: s.place.lng,
    }));
  }, [plan, selectedPriority]);

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
      <RouteMap places={places} course={course} selectedPlace={selectedPlace} step={step} />
    </div>
  );
}
