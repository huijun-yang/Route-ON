export default function ResultStep({gotoFirstStep, course, setSelectedPlace}) {
  

  return (
    <div>
      {course.map((place, index) => (
        <p key={place.kakao_place_id} onClick={() => {
          setSelectedPlace(place);
        }}>{place.name}</p>
      ))}
    </div>
  );
}