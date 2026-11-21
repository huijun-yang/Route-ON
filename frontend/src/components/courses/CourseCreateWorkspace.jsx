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

  // 첫 단계 이동
  const gotoFirstStep = () => {
    setStep(1);
  }

  // 장소 추가
  const addPlace = (newPlace) => {
    setPlaces((prev) => {
      // 이미 추가된 장소라면 중복 추가 방지
      if (prev.some((place) => place.place_id === newPlace.id)) {
        return prev;
      }

      return [...prev, newPlace];
    });
  };

  // 장소 삭제
  const removePlace = (placeId) => {
    setPlaces((prev) =>
      prev.filter((place) => place.place_id !== placeId)
    );
  };

  return (
    <section>
      {step === 1 && (
        <PlaceStep gotoNextStep={gotoNextStep} places={places}
        addPlace={addPlace} removePlace={removePlace} />
      )}

      {step === 2 && (
        <LoadingStep gotoNextStep={gotoNextStep} gotoPrevStep={gotoPrevStep}
        setCourse={setCourse} />
      )}

      {step === 3 && (
        <ResultStep gotoFirstStep={gotoFirstStep} course={course} />
      )}
    </section>
  )
}