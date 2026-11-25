import { createPlace, upsertBusinessHours } from "../../../api/placesApi";
import PlaceSearch from "../../places/PlaceSearch";
import { useState } from "react";
import StepNavigation from "./StepNavigation";

import "./PlaceStep.css";

export default function PlaceStep({
  onNext, places, addPlace, modifyPlace, removePlace, selectedPlace, setSelectedPlace
}) {
  // 세부 입력 정보
  const [weekday, setWeekday] = useState(0);
  const [openTime, setOpenTime] = useState("10:00");
  const [closeTime, setCloseTime] = useState("22:00");
  const [breakStart, setBreakStart] = useState("12:00");
  const [breakEnd, setBreakEnd] = useState("13:00");

  const convertTime = (time) => {
    if (!time) return "00:00:00.000Z";

    return `${time}:00.000Z`;
  }

  // 장소 리스트에서 장소 선택
  const handleSelectPlace = (place) => {
    if (place.kakao_place_id === selectedPlace?.kakao_place_id) {
      setSelectedPlace(null);
      return;
    }
    setSelectedPlace(place);

    setWeekday(0);
    setOpenTime("10:00");
    setCloseTime("22:00");
    setBreakStart("12:00");
    setBreakEnd("13:00");
  }

  // 장소 리스트에서 장소 정보 입력 후 저장
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

  // 생성 버튼 클릭 동작
  const handleNext = () => {
    setSelectedPlace(null);
    onNext();
  }
  
  return (
    <div className="step-workspace">
      <PlaceSearch onAddPlace={addPlace}/>
      <div className="places-list">
        {places.map((place, index) => (
          <div key={place.kakao_place_id} className="place-item">
            <p className="place-title" onClick={() => {
              handleSelectPlace(place);
            }}>
              {index + 1}. {place.name}
              <button onClick={() => {
                removePlace(place)
              }}>삭제</button>
            </p>
            {selectedPlace?.kakao_place_id === place.kakao_place_id && (
              <div className="place-info-input">
                <table className="place-info-table">
                  <tbody>
                  <tr>
                    <th>요일: </th>
                    <td>
                      <select value={weekday} onChange={(e) => setWeekday(Number(e.target.value))}>
                        <option value={0}>일요일</option>
                        <option value={1}>월요일</option>
                        <option value={2}>화요일</option>
                        <option value={3}>수요일</option>
                        <option value={4}>목요일</option>
                        <option value={5}>금요일</option>
                        <option value={6}>토요일</option>
                      </select>
                    </td>
                  </tr>
                  <tr>
                    <th>영업 시작</th>
                    <th>영업 종료</th>
                  </tr>
                  <tr>
                    <td>
                      <input type="time" value={openTime} onChange={(e) => setOpenTime(e.target.value)} />
                    </td>
                    <td>
                      <input type="time" value={closeTime} onChange={(e) => setCloseTime(e.target.value)} />
                    </td>                
                  </tr>
                  <tr>
                    <th>휴식 시작</th>
                    <th>휴식 종료</th>
                  </tr>
                  <tr>
                    <td>
                      <input type="time" value={breakStart} onChange={(e) => setBreakStart(e.target.value)} />
                    </td>
                    <td>
                      <input type="time" value={breakEnd} onChange={(e) => setBreakEnd(e.target.value)} />
                    </td>
                  </tr>
                  </tbody>
                </table>
                <button className="place-info-save"
                onClick={handleSavePlaceInfo}>저장</button>
              </div>
            )}
          </div>
        ))}
      </div>
      <StepNavigation onNext={handleNext} showPrev={false} nextText="생성" />
    </div>
  )
}