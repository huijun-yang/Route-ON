import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { getCourse, getCourseGroup, getSharedCourse } from "../api/coursesApi";
import RouteMap from "../components/map/RouteMap";
import PriorityView from "../components/common/PriorityView";
import StatusHandler from "../components/common/StatusHandler";
import WeatherFatigue from "../components/common/WeatherFatigue";
import Timeline from "../components/courses/Timeline";
import { minutesToHHMM } from "../utils/time";
import "../styles/workspace.css";

// 입력한 공유 링크/코스 ID 에서 마지막 경로 조각만 꺼냅니다.
const extractIdentifier = (text) => text.trim().split("?")[0].split("/").filter(Boolean).pop() ?? "";

// 주소 없이 "코스 조회하기" 메뉴로 들어왔을 때: 공유 링크나 코스 ID 를 붙여 넣는 화면
function CourseLookup() {
  const navigate = useNavigate();
  const [text, setText] = useState("");

  const handleOpen = () => {
    const identifier = extractIdentifier(text);
    if (!identifier) {
      alert("공유 링크 또는 코스 ID 를 입력하세요.");
      return;
    }
    navigate(`/course/view/${identifier}`);
  };

  return (
    <div className="page">
      <h2 className="page-title">코스 조회하기</h2>
      <p className="page-subtitle">친구에게 받은 공유 링크를 붙여 넣으세요. 내가 만든 코스는 "코스 히스토리"에서 볼 수 있어요.</p>
      <div className="card search-box">
        <input
          className="input"
          placeholder="공유 링크 또는 코스 ID"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleOpen()}
        />
        <button className="btn btn-primary" onClick={handleOpen}>
          열기
        </button>
      </div>
    </div>
  );
}

// 공유 링크(share_uuid) 또는 내 코스 ID 로 코스를 읽기 전용으로 보여줍니다.
// 로그인한 상태에서 같은 요청의 3개 버전(최단 시간/최소 도보/최저 비용)이 있으면 바꿔 볼 수 있습니다.
function CourseDetail({ identifier }) {
  const [course, setCourse] = useState(null);
  const [versions, setVersions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [selectedPlace, setSelectedPlace] = useState(null); // 지도에서 강조할 장소
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;

    // 공유 링크는 로그인 없이 열려야 하므로 먼저 share_uuid 로 찾고, 없으면 내 코스 ID 로 찾습니다.
    getSharedCourse(identifier, signal)
      .catch((error) => {
        if (error.status !== 404) throw error;
        return getCourse(identifier, signal);
      })
      .then(async (loaded) => {
        setCourse(loaded);
        setSelectedId(loaded.id);
        setErrorMessage("");
        // 같은 요청의 다른 버전은 로그인해야 볼 수 있습니다. 못 받아도 현재 코스만 보여주면 됩니다.
        const group = await getCourseGroup(loaded.group_id, signal).catch(() => null);
        if (group?.courses?.length > 1) setVersions(group.courses);
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        setErrorMessage(
          error.status === 404 || error.status === 401
            ? "코스를 찾을 수 없거나 볼 수 있는 권한이 없습니다."
            : error.message
        );
      })
      .finally(() => {
        if (!signal.aborted) setIsLoading(false);
      });

    return () => controller.abort();
  }, [identifier]);

  const shown = versions.find((v) => v.id === selectedId) ?? course;

  // 지도에 그릴 방문 순서
  const mapStops = useMemo(
    () =>
      (shown?.stops ?? []).map((s) => ({
        kakao_place_id: s.place.kakao_place_id,
        name: s.place.name,
        lat: s.place.lat,
        lng: s.place.lng,
      })),
    [shown]
  );

  // 출발지 (코스에 저장된 좌표)
  const startPoint = useMemo(
    () => (shown?.start_lat != null ? { lat: shown.start_lat, lng: shown.start_lng, label: '출발지' } : null),
    [shown?.start_lat, shown?.start_lng]
  );

  return (
    <div className="course-create-wrapper">
      <section className="course-create-workspace">
        <div className="step-workspace">
          <div className="step-scroll">
          <StatusHandler isLoading={isLoading} isError={Boolean(errorMessage)} errorMessage={errorMessage}>
            {shown && (
              <>
                <div>
                  <h2 className="page-title" style={{ fontSize: "20px" }}>{shown.title}</h2>
                  <div className="row-wrap">
                    <span className="badge">{shown.course_date}</span>
                    <span className="badge">{minutesToHHMM(shown.start_min)} 출발</span>
                    {shown.status === "PARTIAL" && <span className="badge badge-warning">일부 장소 제외</span>}
                  </div>
                </div>
                {versions.length > 1 && (
                  <PriorityView
                    variants={versions.map((v) => ({ ...v, title: v.priority_label }))}
                    selectedPriority={shown.priority_type}
                    onSelectVariant={(v) => setSelectedId(v.id)}
                  />
                )}
                <WeatherFatigue course={shown} />
                <Timeline
                  course={shown}
                  selectedId={selectedPlace?.kakao_place_id}
                  onSelectStop={(stop) =>
                    setSelectedPlace(selectedPlace?.kakao_place_id === stop.place.kakao_place_id ? null : stop.place)
                  }
                />
              </>
            )}
          </StatusHandler>
          </div>
        </div>
      </section>
      <RouteMap
        places={[]}
        course={mapStops}
        start={startPoint}
        selectedPlace={selectedPlace}
        step={3}
        onSelectPlace={setSelectedPlace}
      />
    </div>
  );
}

export default function CourseViewPage() {
  const { identifier } = useParams();
  return identifier ? <CourseDetail key={identifier} identifier={identifier} /> : <CourseLookup />;
}
