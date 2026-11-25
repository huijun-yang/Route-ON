import { useLocation, useNavigate } from "react-router";
import { loginWithKakao } from "../api/authApi";
import kakaoIcon from "../assets/kakao-icon.svg";
import { useAuth } from "../contexts/AuthContext";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const from = location.state?.from?.pathname || "/";

  // 카카오 로그인
  const handleLogin = () => {
    if (!window.Kakao) {
      alert('카카오 SDK가 로드되지 않았습니다.');
      return;
    }

    if (!window.Kakao.isInitialized()) {
      window.Kakao.init(import.meta.env.VITE_KAKAO_JAVASCRIPT_KEY);
    }

    window.Kakao.Auth.login({
      success: async (authObj) => {
        try {
          // 로그인 성공 후 Access Token 가져오기
          const accessToken = authObj.access_token;

          // 백엔드에 토큰 전달
          const result = await loginWithKakao(accessToken);

          login(result.access_token);

          // 원래 페이지로 이동
          navigate(from, { replace: true });
        } catch (error) {
          console.error("백엔드 로그인 실패:", error);
          alert("로그인 처리에 실패했습니다.");
        }
      },

      fail: (error) => {
        console.error("카카오 로그인 실패:", error);
        alert("카카오 로그인에 실패했습니다.");
      }
    });
  };

  return (
    <div style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "100vh"}}>
      <button onClick={ handleLogin } style={{border: "0px"}}>
        <img src={kakaoIcon} />
      </button>
    </div>
  );
}