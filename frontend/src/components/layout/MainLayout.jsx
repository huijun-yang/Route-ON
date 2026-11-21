import { useState } from "react";
import { Outlet } from "react-router";

import Header from "./Header";
import Sidebar from "./Sidebar";
import Footer from "./Footer";

import "../../styles/layout.css";

export default function MainLayout({
  isLoggedIn = false,
  onLogout,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const toggleSidebar = () => {
    setCollapsed((prev) => !prev);
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <div className="app-layout">
      {/* 상단 헤더 */}
      <Header
        isLoggedIn={isLoggedIn}
        onLogout={onLogout}
        onMenuClick={() => setMobileMenuOpen(true)}
      />

      <div className="app-body">
        {/* 사이드바 */}
        <div
          className={`sidebar-wrapper ${
            collapsed ? "sidebar-collapsed" : ""
          } ${mobileMenuOpen ? "mobile-open" : ""}`}
        >
          <Sidebar
            collapsed={collapsed}
            onToggle={toggleSidebar}
            onNavigate={closeMobileMenu}
          />
        </div>

        {/* 모바일 사이드바 배경 */}
        {mobileMenuOpen && (
          <div
            className="sidebar-overlay"
            onClick={closeMobileMenu}
          />
        )}

        {/* 페이지 콘텐츠 */}
        <main className="main-content">
          <div className="content-container">
            <Outlet />
          </div>
        </main>
      </div>
      {/* 하단 푸터 */}
      <Footer />
    </div>
  );
}
