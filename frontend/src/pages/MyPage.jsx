import { useState } from "react";
import { updateMyInfo } from "../api/authApi";
import { useAuth } from "../contexts/AuthContext";

export default function MyPage() {
  const { user, checkAuth, logout } = useAuth();
  const [nickname, setNickname] = useState(user?.nickname ?? "");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!nickname.trim()) {
      alert("닉네임을 입력하세요.");
      return;
    }
    setSaving(true);
    try {
      await updateMyInfo(nickname.trim());
      await checkAuth(); // 화면에 표시되는 내 정보를 새로 읽습니다
      alert("닉네임을 변경했습니다.");
    } catch (error) {
      alert(error.message);
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div className="page">
      <h2 className="page-title">마이페이지</h2>
      <p className="page-subtitle">내 정보를 확인하고 닉네임을 바꿀 수 있어요.</p>

      <div className="card stack" style={{ maxWidth: "480px" }}>
        <div className="row-between">
          <span className="muted">이메일</span>
          <span>{user.email ?? "제공되지 않음"}</span>
        </div>
        <div className="row-between">
          <span className="muted">가입일</span>
          <span>{user.created_at?.slice(0, 10)}</span>
        </div>
        <label className="field">
          <span>닉네임</span>
          <div className="search-box">
            <input className="input" value={nickname} maxLength={50} onChange={(e) => setNickname(e.target.value)} />
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "저장 중..." : "변경"}
            </button>
          </div>
        </label>
        <button className="btn btn-danger" onClick={logout}>
          로그아웃
        </button>
      </div>
    </div>
  );
}
