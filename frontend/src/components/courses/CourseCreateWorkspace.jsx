import { useState } from "react";
import PlaceStep from "./steps/PlaceStep";
import ResultStep from "./steps/ResultStep";
import LoadingStep from "./steps/LoadingStep";

export default function CourseCreateWorkspace({
  step,
  setStep,
  places,
  setPlaces,
  course,
  setCourse,
  selectedPlace,
  setSelectedPlace
}) {
  // 다음 단계 이동
  const gotoNextStep = () => {
    setStep(step => step + 1);
  }

  // 이전 단계 이동
  const gotoPrevStep = () => {
    setStep(step => step - 1);
  }

  // 장소 추가
  const addPlace = (newPlace) => {
    setPlaces((prev) => {
      // 이미 추가된 장소라면 중복 추가 방지
      if (prev.some((place) => place.kakao_place_id === newPlace.kakao_place_id)) {
        return prev;
      }

      return [...prev, newPlace];
    });
  };

  // 장소 영업시간 수정
  const modifyPlace = (targetPlace) => {
    setPlaces((prev) => prev.map((place) =>
      place.kakao_place_id === targetPlace.kakao_place_id
        ? { ...place, ...targetPlace }
        : place
    ));
  }

  // 장소 삭제
  const removePlace = (targetPlace) => {
    // 삭제하려는 장소가 선택된 장소일 경우 선택 취소
    if (selectedPlace?.kakao_place_id === targetPlace.kakao_place_id)
      setSelectedPlace(null);

    // 장소 삭제
    setPlaces((prev) =>
      prev.filter((place) => place.kakao_place_id !== selectedPlace.kakao_place_id)
    );
  };

  return (
    <section className="course-create-workspace">
      {step === 1 && (
        <PlaceStep onNext={gotoNextStep} places={places}
        addPlace={addPlace} modifyPlace={modifyPlace} removePlace={removePlace} 
        selectedPlace={selectedPlace} setSelectedPlace={setSelectedPlace} />
      )}

      {step === 2 && (
        <LoadingStep onNext={gotoNextStep} onPrev={gotoPrevStep}
        places={places} setCourse={setCourse} />
      )}

      {step === 3 && (
        <ResultStep onPrev={() => setStep(1)} course={course}
        setSelectedPlace={setSelectedPlace} />
      )}
    </section>
  )
}