import { MapPin } from "lucide-react";

export default function Footer() {
  return (
    <footer className="app-footer">
      <div className="footer-left">
        <MapPin size={16} />
        <span>
          Route-ON | 스마트 동선 최적화 서비스
        </span>
      </div>

      <span className="footer-copyright">
        © 2026 Route-ON. All rights reserved.
      </span>
    </footer>
  );
}
