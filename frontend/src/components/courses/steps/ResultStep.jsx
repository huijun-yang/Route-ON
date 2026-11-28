import { useState } from "react";
import { useNavigate } from "react-router";
import { Link2, ListChecks } from "lucide-react";
import { activateCourse, replanCourse } from "../../../api/coursesApi";
import { minutesToHHMM } from "../../../utils/time";
import PriorityView from "../../common/PriorityView";
import WeatherFatigue from "../../common/WeatherFatigue";
import Timeline from "../Timeline";
import StepNavigation from "./StepNavigation";

// 계산된 코스 3개(최단 시간/최소 도보/최저 비용)를 비교하고, 하나를 골라 일정표를 봅니다.
export default function ResultStep({
  onEdit,
  plan,
  setPlan,
  selectedPriority,
  setSelectedPriority,
  selectedPlace,
  setSelectedPlace,
}) {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);

  const course = plan.courses.find((c) => c.priority_type === selectedPriority) ?? plan.courses[0];

  // PriorityView 가 쓰는 형태로 변환
  const variants = plan.courses.map((c) => ({ ...c, title: c.priority_label }));

  // 우선순위 선택: 서버에도 "선택된 버전"으로 저장합니다.
  const handleSelectVariant = async (variant) => {
    setSelectedPriority(variant.priority_type);
    if (variant.is_active) return;

    try {
      await activateCourse(variant.id);
      setPlan((prev) => ({
        ...prev,
        courses: prev.courses.map((c) => ({ ...c, is_active: c.id === variant.id })),
      }));
    } catch (error) {
      alert(`선택을 저장하지 못했습니다: ${error.message}`);
    }
  };

  // "+30분": 이 장소 도착 시점에 이 장소 위치에서, 지난 장소는 방문 완료로 두고 남은 일정을 다시 계산합니다.
  const handleExtend = async (stop, index) => {
    setBusy(true);
    try {
      const result = await replanCourse(course.id, {
        current_time: minutesToHHMM(stop.arrival_min),
        current_lat: stop.place.lat,
        current_lng: stop.place.lng,
        visited_place_ids: course.stops.slice(0, index).map((s) => s.place.kakao_place_id),
        stay_adjustments: { [stop.place.kakao_place_id]: 30 },
      });
      const active = result.courses.find((c) => c.is_active) ?? result.courses[0];
      setPlan({ ...result, guessedHoursPlaces: plan.guessedHoursPlaces });
      setSelectedPriority(active.priority_type);
    } catch (error) {
      alert(`재계획하지 못했습니다: ${error.message}`);
    } finally {
      setBusy(false);
    }
  };

  const handleCopyLink = async () => {
    const link = `${window.location.origin}/course/view/${course.share_uuid}`;
    try {
      await navigator.clipboard.writeText(link);
      alert("공유 링크를 복사했습니다.\n" + link);
    } catch {
      window.prompt("공유 링크", link);
    }
  };

  const guessed = plan.guessedHoursPlaces ?? [];
  const warnings = plan.warnings ?? [];

  return (
    <div className="step-workspace">
      <div className="step-scroll">
        {/* 이동시간 추정 경고에는 Tmap 실패 이유(한도 초과 등)가 함께 들어 있습니다 */}
        {warnings.length > 0 && (
          <div className="alert alert-warning" style={{ flexDirection: "column", gap: "2px" }}>
            {warnings.map((w) => (
              <span key={w}>⚠️ {w}</span>
            ))}
          </div>
        )}
        {guessed.length > 0 && (
          <div className="alert">
            ℹ️ {guessed.join(", ")}은(는) 기본 영업시간으로 계산했어요. 실제 영업시간과 다르면 "조건 수정"에서 고쳐 다시 만들어 보세요.
          </div>
        )}

        <PriorityView variants={variants} selectedPriority={course.priority_type} onSelectVariant={handleSelectVariant} />
        <WeatherFatigue course={course} />
        <Timeline
          course={course}
          onExtend={handleExtend}
          busy={busy}
          showEstimateNote={false}
          selectedId={selectedPlace?.kakao_place_id}
          onSelectStop={(stop) =>
            setSelectedPlace(selectedPlace?.kakao_place_id === stop.place.kakao_place_id ? null : stop.place)
          }
        />

        <div className="row-wrap">
          <button className="btn" onClick={handleCopyLink}>
            <Link2 size={16} /> 공유 링크 복사
          </button>
          <button className="btn" onClick={() => navigate("/history")}>
            <ListChecks size={16} /> 내 코스 보기
          </button>
        </div>
      </div>
      <StepNavigation onPrev={onEdit} prevText="조건 수정" showNext={false} />
    </div>
  );
}
