import { Check } from "lucide-react";
import PlaceStep from "./steps/PlaceStep";
import ResultStep from "./steps/ResultStep";
import LoadingStep from "./steps/LoadingStep";
import { createPlace, getRecommendedStay } from "../../api/placesApi";
import { defaultHoursFor } from "../../utils/placeDefaults";

// 코스 하나에 넣을 수 있는 최대 장소 수 (백엔드 제한과 같음)
export const MAX_PLACES = 8;

const STEPS = ["장소 입력", "계산", "결과"];

function Stepper({ step }) {
  return (
    <div className="stepper">
      {STEPS.map((label, index) => {
        const number = index + 1;
        const state = number < step ? "done" : number === step ? "active" : "";
        return (
          <div key={label} style={{ display: "contents" }}>
            <div className={`stepper-item ${state}`}>
              <span className="stepper-dot">{state === "done" ? <Check size={14} /> : number}</span>
              {label}
            </div>
            {number < STEPS.length && <div className="stepper-line" />}
          </div>
        );
      })}
    </div>
  );
}

export default function CourseCreateWorkspace({
  step,
  setStep,
  places,
  setPlaces,
  settings,
  setSettings,
  plan,
  setPlan,
  selectedPriority,
  setSelectedPriority,
  selectedPlace,
  setSelectedPlace,
}) {
  // 다음 단계 이동
  const gotoNextStep = () => {
    setStep((current) => current + 1);
  };

  // 이전 단계 이동
  const gotoPrevStep = () => {
    setStep((current) => current - 1);
  };

  // 장소 추가: 서버에 저장하고 추천 체류시간을 받아, 바로 입력할 수 있는 카드 상태로 넣습니다.
  // 영업시간은 카테고리별 기본값으로 채우고, 서버에 저장된 값이 있으면 PlaceStep 이 곧바로 덮어씁니다.
  const addPlace = async (newPlace) => {
    if (places.some((place) => place.kakao_place_id === newPlace.kakao_place_id)) {
      alert("이미 추가된 장소입니다.");
      return false;
    }
    if (places.length >= MAX_PLACES) {
      alert(`장소는 최대 ${MAX_PLACES}곳까지 넣을 수 있습니다.`);
      return false;
    }

    try {
      await createPlace(newPlace);
      const rec = await getRecommendedStay(newPlace.kakao_place_id).catch(() => null);
      setPlaces((prev) => [
        ...prev,
        {
          ...newPlace,
          stay_min: null, // 비우면 서버가 추천값을 씁니다
          recommended_stay_min: rec?.recommended_stay_min ?? 60,
          estimated_cost: 0,
          hours: defaultHoursFor(newPlace.category),
          // "default": 기본값 / "saved": 서버에 저장된 값 / "edited": 이번에 직접 고친 값
          hours_source: "default",
          hours_checked: null, // 저장값을 확인한 방문 날짜
          scope: "weekday", // 저장 범위: "weekday"(매주 이 요일) | "date"(이 날짜 하루만)
          save_hours: true, // 직접 고친 영업시간을 다음에도 쓰도록 저장할지
        },
      ]);
      return true;
    } catch (error) {
      alert(error.message);
      return false;
    }
  };

  // 장소 정보(체류시간, 예상 지출, 영업시간 등) 수정
  const modifyPlace = (placeId, patch) => {
    setPlaces((prev) =>
      prev.map((place) => (place.kakao_place_id === placeId ? { ...place, ...patch } : place))
    );
  };

  // 장소 삭제: 삭제하려는 장소(targetPlace)만 지웁니다.
  const removePlace = (targetPlace) => {
    if (selectedPlace?.kakao_place_id === targetPlace.kakao_place_id) {
      setSelectedPlace(null);
    }
    setPlaces((prev) => prev.filter((place) => place.kakao_place_id !== targetPlace.kakao_place_id));
  };

  return (
    <section className="course-create-workspace">
      <Stepper step={step} />

      {step === 1 && (
        <PlaceStep
          onNext={gotoNextStep}
          places={places}
          settings={settings}
          setSettings={setSettings}
          addPlace={addPlace}
          modifyPlace={modifyPlace}
          removePlace={removePlace}
          selectedPlace={selectedPlace}
          setSelectedPlace={setSelectedPlace}
        />
      )}

      {step === 2 && (
        <LoadingStep
          onNext={gotoNextStep}
          onPrev={gotoPrevStep}
          places={places}
          settings={settings}
          setPlan={setPlan}
          setSelectedPriority={setSelectedPriority}
        />
      )}

      {step === 3 && plan && (
        <ResultStep
          onEdit={() => setStep(1)}
          plan={plan}
          setPlan={setPlan}
          selectedPriority={selectedPriority}
          setSelectedPriority={setSelectedPriority}
          selectedPlace={selectedPlace}
          setSelectedPlace={setSelectedPlace}
        />
      )}
    </section>
  );
}
