import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router';
import { Trash2 } from 'lucide-react';
import { deleteCourse, getMyCourses } from '../../api/coursesApi';
import StatusHandler from '../common/StatusHandler';
import { formatDuration } from '../../utils/time';

const STATUS_BADGE = {
  PARTIAL: { className: 'badge badge-warning', text: '일부 장소 제외' },
  NO_FEASIBLE: { className: 'badge badge-danger', text: '방문 불가' },
};

// 내가 만든 코스 목록 (백엔드에 저장된 히스토리)
const CourseHistory = () => {
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getMyCourses({ onlyActive: true }, controller.signal)
      .then((data) => setCourses(data ?? []))
      .catch((error) => {
        if (error.name !== 'AbortError') setErrorMessage(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setIsLoading(false);
      });
    return () => controller.abort();
  }, []);

  const handleDelete = async (course) => {
    if (!window.confirm(`'${course.title}' 코스를 삭제할까요? (3개 버전이 모두 삭제됩니다)`)) return;
    try {
      await deleteCourse(course.id);
      setCourses((prev) => prev.filter((c) => c.group_id !== course.group_id));
    } catch (error) {
      alert(`삭제하지 못했습니다: ${error.message}`);
    }
  };

  return (
    <div className="page">
      <h2 className="page-title">코스 히스토리</h2>
      <p className="page-subtitle">지금까지 만든 코스예요. 눌러서 일정과 지도를 다시 볼 수 있어요.</p>

      <StatusHandler
        isLoading={isLoading}
        isError={Boolean(errorMessage)}
        errorMessage={errorMessage}
        isEmpty={courses.length === 0}
        emptyMessage="아직 만든 코스가 없어요. '코스 만들기'에서 첫 코스를 만들어 보세요."
      >
        <div className="stack">
          {courses.map((course) => {
            const badge = STATUS_BADGE[course.status];
            return (
              <div
                key={course.id}
                className="list-item clickable"
                onClick={() => navigate(`/course/view/${course.id}`)}
              >
                <div className="row-between">
                  <strong style={{ color: 'var(--color-primary)' }}>{course.title}</strong>
                  <button
                    className="icon-btn"
                    aria-label="코스 삭제"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDelete(course);
                    }}
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
                <div className="row-wrap" style={{ margin: '8px 0 6px' }}>
                  <span className="badge">{course.course_date}</span>
                  <span className="badge">{formatDuration(course.total_time)}</span>
                  <span className="badge">{course.total_cost.toLocaleString()}원</span>
                  <span className="badge">{course.stop_count}곳</span>
                  {badge && <span className={badge.className}>{badge.text}</span>}
                </div>
                <div className="muted">{course.place_names.join(' → ')}</div>
              </div>
            );
          })}
        </div>
      </StatusHandler>
    </div>
  );
};

export default CourseHistory;
