import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router'
import App from './App.jsx'
import { AuthProvider } from './contexts/AuthContext.jsx';

import './styles/global.css'
import './styles/ui.css' // 공용 컴포넌트 스타일. 다른 CSS 보다 마지막에 적용되도록 맨 끝에 둡니다.

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
