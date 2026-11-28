import { Link } from "react-router";
import { CalendarClock, Route, Users } from "lucide-react";

const FEATURES = [
  {
    icon: CalendarClock,
    title: "영업시간을 지켜요",
    text: "휴무일과 브레이크타임을 반영해, 도착했는데 문 닫은 일이 없는 순서를 찾아요.",
  },
  {
    icon: Route,
    title: "3가지 코스를 비교해요",
    text: "최단 시간, 최소 도보, 최저 비용 중 내게 맞는 코스를 골라요.",
  },
  {
    icon: Users,
    title: "함께 정해요",
    text: "그룹에서 후보 장소에 투표하고, 득표순으로 코스를 확정해요.",
  },
];

export default function MainPage() {
  return (
    <div className="page">
      <div className="hero">
        <h1>가고 싶은 곳만 고르세요.</h1>
        <p>영업시간·휴식시간·대중교통 이동시간을 반영해, 실제로 갈 수 있는 방문 순서를 계산해 드려요.</p>
        <Link to="/course/create" className="btn btn-primary">
          새 코스 만들기
        </Link>
      </div>

      <div className="feature-grid">
        {FEATURES.map(({ icon: Icon, title, text }) => (
          <div key={title} className="card feature">
            <span className="feature-icon">
              <Icon size={20} />
            </span>
            <h3>{title}</h3>
            <p>{text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
