import { useEffect, useState } from "react";
import { ChevronLeft } from "lucide-react";
import { createGroup, getGroup, getMyGroups, joinGroup } from "../api/groupsApi";
import StatusHandler from "../components/common/StatusHandler";
import GroupVote from "../components/groups/GroupVote";

// 그룹 목록, 만들기/참여, 선택한 그룹의 후보·투표·확정
export default function GroupCoursesPage() {
  const [groups, setGroups] = useState([]);
  const [current, setCurrent] = useState(null); // 선택한 그룹 상세(GroupRead)
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState("");
  const [title, setTitle] = useState("");
  const [inviteCode, setInviteCode] = useState("");

  const loadGroups = async (signal) => {
    try {
      setGroups((await getMyGroups(signal)) ?? []);
      setErrorMessage("");
    } catch (error) {
      if (error.name !== "AbortError") setErrorMessage(error.message);
    } finally {
      if (!signal?.aborted) setIsLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    loadGroups(controller.signal);
    return () => controller.abort();
  }, []);

  // 그룹 상세 열기
  const openGroup = async (groupId) => {
    try {
      setCurrent(await getGroup(groupId));
    } catch (error) {
      alert(error.message);
    }
  };

  const handleCreate = async () => {
    try {
      const created = await createGroup(title.trim() || null);
      setTitle("");
      setCurrent(created);
      loadGroups();
    } catch (error) {
      alert(error.message);
    }
  };

  const handleJoin = async () => {
    if (!inviteCode.trim()) {
      alert("초대코드를 입력하세요.");
      return;
    }
    try {
      const joined = await joinGroup(inviteCode.trim());
      setInviteCode("");
      setCurrent(joined);
      loadGroups();
    } catch (error) {
      alert(error.message);
    }
  };

  // 상세 화면: 목록으로 돌아가기 + 그룹 화면
  if (current) {
    return (
      <div className="page">
        <button
          className="btn btn-ghost btn-sm"
          style={{ marginBottom: "12px" }}
          onClick={() => {
            setCurrent(null);
            loadGroups();
          }}
        >
          <ChevronLeft size={16} /> 그룹 목록
        </button>
        <GroupVote
          group={current}
          onChange={setCurrent}
          onLeft={() => {
            setCurrent(null);
            loadGroups();
          }}
        />
      </div>
    );
  }

  return (
    <div className="page">
      <h2 className="page-title">그룹 코스</h2>
      <p className="page-subtitle">친구들과 후보 장소에 투표하고, 득표순으로 코스를 확정해요.</p>

      <div className="feature-grid" style={{ marginTop: 0, marginBottom: "20px" }}>
        <div className="card stack">
          <h3 className="card-title" style={{ margin: 0 }}>새 그룹 만들기</h3>
          <div className="search-box">
            <input
              className="input"
              placeholder="그룹 이름 (선택)"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <button className="btn btn-primary" onClick={handleCreate}>
              만들기
            </button>
          </div>
        </div>
        <div className="card stack">
          <h3 className="card-title" style={{ margin: 0 }}>초대코드로 참여</h3>
          <div className="search-box">
            <input
              className="input"
              placeholder="초대코드"
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleJoin()}
            />
            <button className="btn btn-primary" onClick={handleJoin}>
              참여
            </button>
          </div>
        </div>
      </div>

      <StatusHandler
        isLoading={isLoading}
        isError={Boolean(errorMessage)}
        errorMessage={errorMessage}
        isEmpty={groups.length === 0}
        emptyMessage="참여 중인 그룹이 없어요. 그룹을 만들거나 초대코드로 참여해 보세요."
      >
        <div className="stack">
          {groups.map((g) => (
            <div key={g.id} className="list-item clickable" onClick={() => openGroup(g.id)}>
              <div className="row-between">
                <strong style={{ color: "var(--color-primary)" }}>{g.title || "이름 없는 그룹"}</strong>
                <span className={`badge ${g.status === "open" ? "badge-success" : ""}`}>
                  {g.status === "open" ? "투표 중" : "확정됨"}
                </span>
              </div>
              <div className="muted" style={{ marginTop: "4px" }}>
                멤버 {g.member_count}명 · 후보 {g.candidate_count}곳
              </div>
            </div>
          ))}
        </div>
      </StatusHandler>
    </div>
  );
}
