import { createPlace, upsertBusinessHours } from "../../../api/placesApi";
import PlaceSearch from "../../places/PlaceSearch";
import { useState } from "react";

export default function PlaceStep({
  gotoNextStep, places, addPlace, modifyPlace, removePlace, selectedPlace, setSelectedPlace
}) {
  // 세부 입력 정보
  const [weekday, setWeekday] = useState(0);
  const [openTime, setOpenTime] = useState("10:00");
  const [closeTime, setCloseTime] = useState("22:00");
  const [breakStart, setBreakStart] = useState("11:00");
  const [breakEnd, setBreakEnd] = useState("13:00");

  const convertTime = (time) => {
    if (!time) return "00:00:00.000Z";

    return `${time}:00.000Z`;
  }

  const handleSelectPlace = (place) => {
    if (place.kakao_place_id === selectedPlace?.kakao_place_id) {
      setSelectedPlace(null);
      return;
    }
    setSelectedPlace(place);
  }

  const handleSavePlaceInfo = async () => {
    const businessHours = {
      weekday: weekday,
      open_time: convertTime(openTime),
      close_time: convertTime(closeTime),
      break_start: convertTime(breakStart),
      break_end: convertTime(breakEnd),
    }
    modifyPlace({...selectedPlace, ...businessHours});
    await createPlace(selectedPlace);
    await upsertBusinessHours(selectedPlace.kakao_place_id, businessHours);
    console.log(businessHours);
  }
  
  return (
    <div>
      <PlaceSearch onAddPlace={addPlace}/>
      <div>
        {places.map((place, index) => (
          <div key={place.kakao_place_id}>
            <p onClick={() => {
              handleSelectPlace(place);
            }}>
              {index + 1}. {place.name}
              <button onClick={() => {
                removePlace(place)
              }}>삭제</button>
            </p>
            {selectedPlace?.kakao_place_id === place.kakao_place_id && (
              <div>
                <div>
                  <label>
                    요일: <select value={weekday} onChange={(e) => setWeekday(Number(e.target.value))}>
                      <option value={0}>일요일</option>
                      <option value={1}>월요일</option>
                      <option value={2}>화요일</option>
                      <option value={3}>수요일</option>
                      <option value={4}>목요일</option>
                      <option value={5}>금요일</option>
                      <option value={6}>토요일</option>
                    </select>
                  </label>
                  <label>
                    영업 시작: <input type="time" value={selectedPlace.open_time} onChange={(e) => setOpenTime(e.target.value)} />
                  </label>
                  <label>
                    영업 종료: <input type="time" value={selectedPlace.close_time} onChange={(e) => setCloseTime(e.target.value)} />
                  </label>
                  <label>
                    휴식 시작: <input type="time" value={selectedPlace.break_start} onChange={(e) => setBreakStart(e.target.value)} />
                  </label>
                  <label>
                    휴식 종료: <input type="time" value={selectedPlace.break_end} onChange={(e) => setBreakEnd(e.target.value)} />
                  </label>
                  <button onClick={handleSavePlaceInfo}>저장</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      <button onClick={gotoNextStep}>생성</button>
    </div>
  )
}