import { Routes, Route } from "react-router";

import MainLayout from "./components/layout/MainLayout";
import ProtectedRoute from "./routes/ProtectedRoute";

import MainPage from "./pages/MainPage";
import LoginPage from "./pages/LoginPage";
import CourseCreatePage from "./pages/CourseCreatePage";
import CourseViewPage from "./pages/CourseViewPage";
import GroupCoursesPage from "./pages/GroupCoursesPage";
import HistoryPage from "./pages/HistoryPage";
import MyPage from "./pages/MyPage";
import { useAuth } from "./contexts/AuthContext";

export default function App() {
  const { isLoggedIn } = useAuth(); // 추후 인증 Context 연결

  return (
    <Routes>
      {/* 로그인 없이 접근 가능한 페이지 */}
      <Route element={<MainLayout isLoggedIn={isLoggedIn} />}>
        <Route path="/" element={<MainPage />} />
        <Route
          path="/course/view/:identifier"
          element={<CourseViewPage />}
        />
      </Route>

      {/* 로그인 페이지 */}
      <Route path="/login" element={<LoginPage />} />

      {/* 로그인해야 접근 가능한 페이지 */}
      <Route element={<ProtectedRoute isLoggedIn={isLoggedIn} />}>
        <Route element={<MainLayout isLoggedIn={isLoggedIn} />}>
          <Route path="/course/create" element={<CourseCreatePage />} />
          <Route path="/groups" element={<GroupCoursesPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/mypage" element={<MyPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
