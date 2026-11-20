import { NavLink } from "react-router";
import {
  Home,
  MapPinPlus,
  MapPinned,
  Users,
  History,
  UserCircle,
  Route,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

const menuItems = [
  {
    label: "홈",
    path: "/",
    icon: Home,
  },
  {
    label: "코스 만들기",
    path: "/course/create",
    icon: MapPinPlus,
  },
  {
    label: "코스 조회하기",
    path: "/course/view",
    icon: MapPinned,
  },
  {
    label: "그룹 코스",
    path: "/groups",
    icon: Users,
  },
  {
    label: "코스 히스토리",
    path: "/history",
    icon: History,
  },
  {
    label: "마이페이지",
    path: "/mypage",
    icon: UserCircle,
  },
];

export default function Sidebar({
  collapsed,
  onToggle,
}) {
  return (
    <aside
      className={`app-sidebar ${
        collapsed ? "collapsed" : ""
      }`}
    >
      <div className="sidebar-top">
        <div className="sidebar-section-title">
          <span>MENU</span>
        </div>
        <button
          className="sidebar-toggle"
          onClick={onToggle}
          aria-label={
            collapsed ? "사이드바 펼치기" : "사이드바 접기"
          }
          title={collapsed ? "펼치기" : "접기"}
        >
          {collapsed ? (
            <PanelLeftOpen size={21} />
          ) : (
            <PanelLeftClose size={21} />
          )}

          {!collapsed && <span>메뉴 접기</span>}
        </button>
      </div>
      
      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;

          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `sidebar-link ${
                  isActive ? "active" : ""
                }`
              }
              title={collapsed ? item.label : ""}
            >
              <Icon size={21} strokeWidth={2} />

              {!collapsed && (
                <span>{item.label}</span>
              )}
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-bottom">
        {!collapsed && (
          <div className="sidebar-brand">
            <Route size={22} />
            <div>
              <strong>Route-ON</strong>
              <small>Smart Route Planner</small>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
