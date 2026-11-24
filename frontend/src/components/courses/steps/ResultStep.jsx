import StepNavigation from "./StepNavigation";

export default function ResultStep({onPrev, course, setSelectedPlace}) {
  // 장소 리스트에서 장소 선택
  const handleSelectPlace = (place) => {
    if (place.kakao_place_id === selectedPlace?.kakao_place_id) {
      setSelectedPlace(null);
      return;
    }
    setSelectedPlace(place);
  }

  // 이전 단계 이동
  const handlePrev = () => {
    onPrev();
  }

  // 코스 저장
  const handleNext = () => {
    // 백엔드 코스 저장 코드
    
    alert("코스가 저장되었습니다");
    onPrev();
  }

  return (
    <div className="step-workspace">
      <div className="places-list">
        {course.map((place, index) => (
          <div key={place.kakao_place_id} className="place-item">
            <p className="place-title" onClick={() => {
              setSelectedPlace(place);
            }}>{place.name}</p>
          </div>
        ))}
      </div>
      <StepNavigation onPrev={handlePrev} onNext={handleNext} nextText="저장" />
    </div>
  );
}