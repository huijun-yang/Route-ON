import { useEffect, useRef, useState } from "react";
import { Crosshair, MapPin, X } from "lucide-react";
import {
  getBusinessHours,
  getBusinessHoursExceptions,
  upsertBusinessHours,
  upsertBusinessHoursException,
} from "../../../api/placesApi";
import { hoursFromServer, hoursToBody, defaultHoursFor, validateHours } from "../../../utils/placeDefaults";
import { backendWeekday, WEEKDAY_LABEL } from "../../../utils/time";
import PlaceSearch from "../../places/PlaceSearch";
import StepNavigation from "./StepNavigation";

// 방문일에 적용되는 저장값을 서버에서 읽어옵니다. 날짜별 예외가 있으면 요일 값보다 우선합니다.
async function fetchAppliedHours(placeId, weekday, date, signal) {
  const [rows, exceptions] = await Promise.all([
    getBusinessHours(placeId, signal),
    getBusinessHoursExceptions(placeId, date, signal),
  ]);
  const weekdayRow = (rows ?? []).find((r) => r.weekday === weekday) ?? null;
  const dateRow = (exceptions ?? []).find((e) => e.date === date) ?? null;
  return { dateRow, applied: dateRow ?? weekdayRow };
}

const SOURCE_BADGE = {
  default: { className: "badge badge-warning", text: "기본값 · 확인해 주세요" },
  saved: { className: "badge badge-success", text: "저장된 값" },
  edited: { className: "badge badge-accent", text: "수정함" },
};

// 장소 한 곳의 입력 카드. 검색해서 추가하면 체류시간·예상 지출·영업시간 입력칸이 바로 펼쳐져 있습니다.
function PlaceCard({ place, index, weekday, courseDate, selected, onSelect, onChange, onRemove }) {
  const { hours } = place;
  const badge = SOURCE_BADGE[place.hours_source];

  // 영업시간 값을 바꾸면 "직접 수정함" 상태가 되어 이후 날짜를 바꿔도 덮어쓰지 않습니다.
  const editHours = (patch) => onChange({ hours: { ...hours, ...patch }, hours_source: "edited" });

  return (
    <div className={`place-card${selected ? " selected" : ""}${hours.isClosed ? " closed" : ""}`}>
      <div className="place-card-head" onClick={onSelect}>
        <span className="place-index">{index + 1}</span>
        <div className="place-card-title">
          <strong>{place.name}</strong>
          <span>
            {place.category?.split(">").pop()?.trim()} {place.address && `· ${place.address}`}
          </span>
        </div>
        <button
          className="icon-btn"
          aria-label={`${place.name} 삭제`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        >
          <X size={16} />
        </button>
      </div>

      <div className="field-row">
        <label className="field">
          <span>체류시간 (분)</span>
          <input
            className="input"
            type="number"
            min={5}
            max={720}
            value={place.stay_min ?? ""}
            placeholder={`추천 ${place.recommended_stay_min}분`}
            onChange={(e) => onChange({ stay_min: e.target.value === "" ? null : Number(e.target.value) })}
          />
        </label>
        <label className="field">
          <span>예상 지출 (원)</span>
          <input
            className="input"
            type="number"
            min={0}
            step={1000}
            value={place.estimated_cost || ""}
            placeholder="0"
            onChange={(e) => onChange({ estimated_cost: Number(e.target.value) || 0 })}
          />
        </label>
      </div>

      <div className="hours-box">
        <div className="hours-head">
          <span className="hours-title">
            {courseDate && weekday !== null ? `${WEEKDAY_LABEL[weekday]}요일 영업시간` : "영업시간"}
          </span>
          {badge && <span className={badge.className}>{badge.text}</span>}
        </div>

        <label className="checkbox">
          <input type="checkbox" checked={hours.isClosed} onChange={(e) => editHours({ isClosed: e.target.checked })} />
          이날은 쉬는 날이에요
        </label>

        {!hours.isClosed && (
          <>
            <div className="field-row">
              <label className="field">
                <span>영업 시작</span>
                <input
                  className="input input-sm"
                  type="time"
                  value={hours.openTime}
                  onChange={(e) => editHours({ openTime: e.target.value })}
                />
              </label>
              <label className="field">
                <span>영업 종료</span>
                <input
                  className="input input-sm"
                  type="time"
                  value={hours.closeTime}
                  onChange={(e) => editHours({ closeTime: e.target.value })}
                />
              </label>
            </div>

            <label className="checkbox">
              <input type="checkbox" checked={hours.hasBreak} onChange={(e) => editHours({ hasBreak: e.target.checked })} />
              휴식(브레이크) 시간이 있어요
            </label>
            {hours.hasBreak && (
              <div className="field-row">
                <label className="field">
                  <span>휴식 시작</span>
                  <input
                    className="input input-sm"
                    type="time"
                    value={hours.breakStart}
                    onChange={(e) => editHours({ breakStart: e.target.value })}
                  />
                </label>
                <label className="field">
                  <span>휴식 종료</span>
                  <input
                    className="input input-sm"
                    type="time"
                    value={hours.breakEnd}
                    onChange={(e) => editHours({ breakEnd: e.target.value })}
                  />
                </label>
              </div>
            )}
          </>
        )}

        {place.hours_source === "edited" && (
          <div className="hours-footer">
            <label className="checkbox">
              <input
                type="checkbox"
                checked={place.save_hours}
                onChange={(e) => onChange({ save_hours: e.target.checked })}
              />
              다음에도 쓰도록 저장
            </label>
            {place.save_hours && (
              <select
                className="select input-sm"
                style={{ width: "auto" }}
                value={place.scope}
                onChange={(e) => onChange({ scope: e.target.value })}
              >
                <option value="weekday">매주 {weekday !== null ? WEEKDAY_LABEL[weekday] : ""}요일</option>
                <option value="date">{courseDate} 하루만</option>
              </select>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function PlaceStep({
  onNext,
  places,
  settings,
  setSettings,
  addPlace,
  modifyPlace,
  removePlace,
  selectedPlace,
  setSelectedPlace,
}) {
  const [saving, setSaving] = useState(false);

  // 방문일 기준 요일 (백엔드: 0=월 ~ 6=일)
  const weekday = backendWeekday(settings.courseDate);

  // effect 안의 비동기 콜백이 최신 값을 읽도록 ref 로 들고 있습니다. (매 렌더마다 새로 만들어지는 함수 때문에 effect 가 다시 돌지 않게)
  const modifyPlaceRef = useRef(modifyPlace);
  const placesRef = useRef(places);
  useEffect(() => {
    modifyPlaceRef.current = modifyPlace;
    placesRef.current = places;
  });

  // 새로 추가했거나 방문일이 바뀐 장소는, 직접 고치지 않은 한 서버에 저장된 영업시간을 확인해 채웁니다.
  // 저장된 값이 없으면 카테고리별 기본값을 보여줍니다.
  const pendingKey = places
    .filter((p) => p.hours_source !== "edited" && p.hours_checked !== settings.courseDate)
    .map((p) => p.kakao_place_id)
    .join(",");

  useEffect(() => {
    if (!pendingKey || weekday === null || !settings.courseDate) return;
    const controller = new AbortController();
    const date = settings.courseDate;

    pendingKey.split(",").forEach((placeId) => {
      fetchAppliedHours(placeId, weekday, date, controller.signal)
        .then(({ dateRow, applied }) => {
          const category = placesRef.current.find((p) => p.kakao_place_id === placeId)?.category;
          modifyPlaceRef.current(
            placeId,
            applied
              ? {
                  hours: hoursFromServer(applied, category),
                  hours_source: "saved",
                  scope: dateRow ? "date" : "weekday",
                  hours_checked: date,
                }
              : { hours: defaultHoursFor(category), hours_source: "default", hours_checked: date }
          );
        })
        .catch((error) => {
          if (error.name !== "AbortError") console.error("영업시간 조회 실패:", error);
        });
    });

    return () => controller.abort();
  }, [pendingKey, weekday, settings.courseDate]);

  const updateSettings = (patch) => setSettings((prev) => ({ ...prev, ...patch }));

  // 현재 위치를 출발지로
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      alert("이 브라우저는 위치 조회를 지원하지 않습니다.");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) =>
        updateSettings({
          start: { lat: pos.coords.latitude, lng: pos.coords.longitude, label: "현재 위치" },
        }),
      () => alert("현재 위치를 가져오지 못했습니다. 브라우저의 위치 권한을 확인하세요.")
    );
  };

  // 검색한 장소를 출발지로
  const handlePickStart = (place) => {
    updateSettings({ start: { lat: place.lat, lng: place.lng, label: place.name } });
  };

  // 코스 생성: 입력 검사 → 직접 고친 영업시간 저장 → 계산 단계로
  const handleNext = async () => {
    if (!settings.courseDate) {
      alert("방문 날짜를 선택하세요.");
      return;
    }
    if (places.length === 0) {
      alert("방문할 장소를 한 곳 이상 추가하세요.");
      return;
    }
    for (const place of places) {
      const problem = validateHours(place.hours);
      if (problem) {
        alert(`${place.name}: ${problem}`);
        setSelectedPlace(place);
        return;
      }
    }

    setSaving(true);
    // 직접 고친 영업시간은 다음에도 쓸 수 있게 서버에 저장합니다. 저장이 실패해도 이번 계산은 입력한 값으로 진행합니다.
    const edited = places.filter((p) => p.hours_source === "edited" && p.save_hours);
    const results = await Promise.allSettled(
      edited.map((p) =>
        p.scope === "date"
          ? upsertBusinessHoursException(p.kakao_place_id, { ...hoursToBody(p.hours), date: settings.courseDate })
          : upsertBusinessHours(p.kakao_place_id, { ...hoursToBody(p.hours), weekday })
      )
    );
    const failed = results.filter((r) => r.status === "rejected");
    if (failed.length > 0) {
      alert(`영업시간 ${failed.length}건을 저장하지 못했습니다. 이번 코스 계산에는 입력한 값을 그대로 씁니다.`);
    }
    setSaving(false);

    setSelectedPlace(null);
    onNext();
  };

  return (
    <div className="step-workspace">
      <div className="step-scroll">
        {/* 코스 조건 */}
        <div className="card">
          <h3 className="card-title">코스 조건</h3>
          <div className="stack">
            <label className="field">
              <span>코스 이름 (선택)</span>
              <input
                className="input"
                type="text"
                maxLength={80}
                placeholder="비우면 날짜로 자동 설정돼요"
                value={settings.title}
                onChange={(e) => updateSettings({ title: e.target.value })}
              />
            </label>
            <div className="field-row">
              <label className="field">
                <span>방문 날짜{weekday !== null && ` (${WEEKDAY_LABEL[weekday]}요일)`}</span>
                <input
                  className="input"
                  type="date"
                  value={settings.courseDate}
                  onChange={(e) => updateSettings({ courseDate: e.target.value })}
                />
              </label>
              <label className="field">
                <span>출발 시각</span>
                <input
                  className="input"
                  type="time"
                  value={settings.startTime}
                  onChange={(e) => updateSettings({ startTime: e.target.value })}
                />
              </label>
            </div>
            <div className="row-between">
              <span className="muted">
                <MapPin size={14} style={{ verticalAlign: "-2px" }} /> 출발지: <strong>{settings.start.label}</strong>
              </span>
              <button className="btn btn-sm" onClick={handleUseMyLocation}>
                <Crosshair size={14} /> 현재 위치로
              </button>
            </div>
            <PlaceSearch placeholder="출발지를 바꾸려면 검색하세요" onAddPlace={handlePickStart} />
          </div>
        </div>

        {/* 방문 장소 */}
        <div className="card">
          <h3 className="card-title">방문할 장소 ({places.length}/8)</h3>
          <PlaceSearch placeholder="가고 싶은 곳을 검색하세요 (예: 경복궁)" onAddPlace={addPlace} near={settings.start} />
        </div>

        {places.length === 0 && (
          <div className="empty">장소를 검색해서 추가하면 체류시간과 영업시간 입력칸이 바로 나타나요.</div>
        )}

        {places.map((place, index) => (
          <PlaceCard
            key={place.kakao_place_id}
            place={place}
            index={index}
            weekday={weekday}
            courseDate={settings.courseDate}
            selected={selectedPlace?.kakao_place_id === place.kakao_place_id}
            onSelect={() => setSelectedPlace(selectedPlace?.kakao_place_id === place.kakao_place_id ? null : place)}
            onChange={(patch) => modifyPlace(place.kakao_place_id, patch)}
            onRemove={() => removePlace(place)}
          />
        ))}
      </div>

      <StepNavigation
        onNext={handleNext}
        showPrev={false}
        nextText={saving ? "저장 중..." : "코스 만들기"}
        nextDisabled={saving || places.length === 0}
      />
    </div>
  );
}
