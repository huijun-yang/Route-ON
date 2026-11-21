import { Link, useLocation } from "react-router";
import {
  Map,
  Menu,
  LogIn,
  UserCircle,
  LogOut,
  Bell,
} from "lucide-react";

export default function Header({
  isLoggedIn = false,
  onLogout,
  onMenuClick,
}) {
  const location = useLocation();

  const pageTitles = {
    "/": "홈",
    "/course/create": "코스 만들기",
    "/groups": "그룹 코스",
    "/history": "코스 히스토리",
    "/mypage": "마이페이지",
  };

  const title = pageTitles[location.pathname] || "Route-ON";

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          className="mobile-menu-button"
          onClick={onMenuClick}
          aria-label="메뉴 열기"
        >
          <Menu size={22} />
        </button>

        <Link to="/" className="header-logo">
          <Map size={27} strokeWidth={2.5} />
          <span>Route-ON</span>
        </Link>

        <div className="header-divider" />

        <h1 className="header-page-title">{title}</h1>
      </div>

      <div className="header-right">
        <button
          className="header-icon-button"
          aria-label="알림"
        >
          <Bell size={20} />
        </button>

        {isLoggedIn ? (
          <div className="header-user">
            <Link to="/mypage" className="header-user-link">
              <UserCircle size={20} />
              <span>마이페이지</span>
            </Link>

            <button
              className="header-logout-button"
              onClick={onLogout}
            >
              <LogOut size={18} />
              <span>로그아웃</span>
            </button>
          </div>
        ) : (
          <Link to="/login" className="header-login-button">
            <LogIn size={18} />
            <span>로그인</span>
          </Link>
        )}
      </div>
    </header>
  );
}
