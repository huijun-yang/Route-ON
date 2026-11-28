import { useState } from 'react';
import { useNavigate } from 'react-router';
import { Crosshair, ThumbsUp, Trash2 } from 'lucide-react';
import { createPlace } from '../../api/placesApi';
import {
  addCandidate,
  deleteGroup,
  finalizeGroup,
  leaveGroup,
  removeCandidate,
  unvoteCandidate,
  voteCandidate,
} from '../../api/groupsApi';
import { DEFAULT_START } from '../../utils/defaults';
import { todayString } from '../../utils/time';
import PlaceSearch from '../places/PlaceSearch';

// 그룹 한 개의 후보 장소 · 투표 · 코스 확정 화면. 서버 상태(group)를 그대로 보여주고, 변경은 서버 응답으로 갱신합니다.
const GroupVote = ({ group, onChange, onLeft }) => {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [finalize, setFinalize] = useState({ courseDate: todayString(), startTime: '10:00', maxPlaces: 5 });
  const [start, setStart] = useState(DEFAULT_START);

  const isOwner = group.my_role === 'owner';
  const isOpen = group.status === 'open';

  // 서버 호출을 감싸 중복 클릭 방지와 오류 안내를 한 곳에서 처리합니다.
  const run = async (action) => {
    setBusy(true);
    try {
      return await action();
    } catch (error) {
      alert(error.message);
      return null;
    } finally {
      setBusy(false);
    }
  };

  const handleAddCandidate = async (place) => {
    const updated = await run(async () => {
      await createPlace(place); // 후보로 넣기 전에 장소를 저장해야 합니다.
      return addCandidate(group.id, place.kakao_place_id);
    });
    if (updated) onChange(updated);
    return Boolean(updated);
  };

  const handleToggleVote = async (candidate) => {
    const updated = await run(() =>
      candidate.voted_by_me ? unvoteCandidate(group.id, candidate.id) : voteCandidate(group.id, candidate.id)
    );
    if (updated) onChange(updated);
  };

  const handleRemove = async (candidate) => {
    const updated = await run(() => removeCandidate(group.id, candidate.id));
    if (updated) onChange(updated);
  };

  const handleFinalize = async () => {
    if (!window.confirm('투표를 마감하고 코스를 확정할까요? 이후에는 후보와 투표를 바꿀 수 없습니다.')) return;
    const result = await run(() =>
      finalizeGroup(group.id, {
        course_date: finalize.courseDate,
        start: { lat: start.lat, lng: start.lng },
        start_time: finalize.startTime,
        max_places: Number(finalize.maxPlaces) || 5,
      })
    );
    if (result) {
      const active = result.courses.find((c) => c.is_active) ?? result.courses[0];
      navigate(`/course/view/${active.id}`);
    }
  };

  // 출발지: 현재 위치 또는 장소 검색
  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      alert('이 브라우저는 위치 조회를 지원하지 않습니다.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => setStart({ lat: pos.coords.latitude, lng: pos.coords.longitude, label: '현재 위치' }),
      () => alert('현재 위치를 가져오지 못했습니다. 브라우저의 위치 권한을 확인하세요.')
    );
  };

  const handleLeave = async () => {
    const message = isOwner ? '그룹을 삭제할까요? 모든 멤버에게서 사라집니다.' : '그룹에서 나갈까요?';
    if (!window.confirm(message)) return;
    const done = await run(async () => {
      await (isOwner ? deleteGroup(group.id) : leaveGroup(group.id));
      return true;
    });
    if (done) onLeft();
  };

  return (
    <div className="stack">
      <div className="card">
        <div className="row-between">
          <h2 className="page-title" style={{ margin: 0, fontSize: '20px' }}>
            {group.title || '이름 없는 그룹'}
          </h2>
          <span className={`badge ${isOpen ? 'badge-success' : ''}`}>{isOpen ? '투표 중' : '확정됨'}</span>
        </div>
        <div className="row-wrap" style={{ marginTop: '10px' }}>
          <span className="badge badge-accent">초대코드 {group.invite_code}</span>
          {group.members.map((m) => (
            <span key={m.user_id} className="badge">
              {m.nickname}
              {m.role === 'owner' && ' 👑'}
            </span>
          ))}
        </div>
        {!isOpen && group.course_id && (
          <button
            className="btn btn-primary"
            style={{ marginTop: '12px' }}
            onClick={() => navigate(`/course/view/${group.course_id}`)}
          >
            확정된 코스 보기
          </button>
        )}
      </div>

      {isOpen && (
        <div className="card">
          <h3 className="card-title">후보 장소 추가</h3>
          <PlaceSearch placeholder="후보로 올릴 장소를 검색하세요" onAddPlace={handleAddCandidate} />
        </div>
      )}

      {group.candidates.length === 0 && <div className="empty">아직 후보 장소가 없어요. 위에서 검색해 추가해 보세요.</div>}

      {group.candidates.map((item) => (
        <div
          key={item.id}
          className="list-item"
          style={item.voted_by_me ? { borderColor: 'var(--color-accent)', background: 'var(--color-accent-light)' } : undefined}
        >
          <div className="row-between">
            <div style={{ minWidth: 0 }}>
              <strong style={{ color: 'var(--color-primary)' }}>{item.place.name}</strong>
              <div className="muted">
                {item.place.category?.split('>').pop()?.trim()} · 추가: {item.added_by_nickname ?? '알 수 없음'}
              </div>
            </div>
            <div className="row">
              <span className="badge badge-accent">👍 {item.vote_count}표</span>
              {isOpen && (
                <>
                  <button
                    className={`btn btn-sm ${item.voted_by_me ? '' : 'btn-primary'}`}
                    disabled={busy}
                    onClick={() => handleToggleVote(item)}
                  >
                    <ThumbsUp size={14} /> {item.voted_by_me ? '취소' : '투표'}
                  </button>
                  <button className="icon-btn" aria-label="후보 삭제" disabled={busy} onClick={() => handleRemove(item)}>
                    <Trash2 size={16} />
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      ))}

      {isOpen && isOwner && (
        <div className="card">
          <h3 className="card-title">코스 확정 (대표만)</h3>
          <div className="stack">
            <div className="field-row">
              <label className="field">
                <span>방문 날짜</span>
                <input
                  className="input"
                  type="date"
                  value={finalize.courseDate}
                  onChange={(e) => setFinalize({ ...finalize, courseDate: e.target.value })}
                />
              </label>
              <label className="field">
                <span>출발 시각</span>
                <input
                  className="input"
                  type="time"
                  value={finalize.startTime}
                  onChange={(e) => setFinalize({ ...finalize, startTime: e.target.value })}
                />
              </label>
            </div>
            <label className="field" style={{ maxWidth: '160px' }}>
              <span>최대 장소 수</span>
              <input
                className="input"
                type="number"
                min={1}
                max={8}
                value={finalize.maxPlaces}
                onChange={(e) => setFinalize({ ...finalize, maxPlaces: e.target.value })}
              />
            </label>
            <div className="row-between">
              <span className="muted">
                출발지: <strong>{start.label}</strong>
              </span>
              <button className="btn btn-sm" onClick={handleUseMyLocation}>
                <Crosshair size={14} /> 현재 위치로
              </button>
            </div>
            <PlaceSearch
              placeholder="출발지를 바꾸려면 검색하세요"
              onAddPlace={(place) => setStart({ lat: place.lat, lng: place.lng, label: place.name })}
            />
            <div className="alert">득표 상위 장소로 코스를 만들어요. 영업시간은 대표가 저장한 값을 사용합니다.</div>
            <button className="btn btn-primary" disabled={busy} onClick={handleFinalize}>
              투표 마감하고 코스 확정
            </button>
          </div>
        </div>
      )}

      <button className="btn btn-danger" disabled={busy} onClick={handleLeave}>
        {isOwner ? '그룹 삭제' : '그룹 나가기'}
      </button>
    </div>
  );
};

export default GroupVote;
