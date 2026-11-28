import { createContext, useContext, useEffect, useState } from "react";
import { getMyInfo } from "../api/authApi";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authStatus, setAuthStatus] = useState("loading");

  const checkAuth = async (signal) => {
    // 토큰을 이용해 로그인 여부 확인
    const token = localStorage.getItem("accessToken");

    if (!token) {
      setUser(null);
      setAuthStatus("anonymous");
      return;
    }

    try {
      const result = await getMyInfo(signal);
      setUser(result);
      setAuthStatus("authenticated");
    } catch(error) {
      // 요청 취소는 인증 실패로 처리하지 않음
      if (signal?.aborted || error.name === "AbortError" || error.code === "ERR_CANCELED")
        return;

      setUser(null);
      setAuthStatus("anonymous");
    }
  }

  // 앱 최초 실행 시 인증 확인
  useEffect(() => {
    const controller = new AbortController();

    checkAuth(controller.signal);

    return () => {
      controller.abort();
    }
  }, []);

  // 로그인 처리
  const login = async (accessToken) => {
    localStorage.setItem("accessToken", accessToken);
    setAuthStatus("loading");
    await checkAuth();
  };

  // 로그아웃 처리
  const logout = async () => {
    localStorage.removeItem("accessToken");
    setUser(null);
    setAuthStatus("anonymous");
  };

  const value = {
    user,
    authStatus,
    isLoggedIn: authStatus === "authenticated",
    isLoading: authStatus === "loading",
    login,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// 다른 컴포넌트에서 AuthContext 사용
export function useAuth() {
  const context = useContext(AuthContext);

  if(!context) {
    throw new Error(
      "useAuth must be used within AuthProvider"
    );
  }

  return context;
}