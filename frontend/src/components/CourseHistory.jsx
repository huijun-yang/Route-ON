import React, { useState, useEffect } from 'react';

const CourseHistory = ({ currentPlaces, onLoadCourse }) => {
  const [savedCourses, setSavedCourses] = useState([]);
  const [courseName, setCourseName] = useState('');

  // LocalStorage에서 저장된 코스 목록 불러오기
  useEffect(() => {
    const history = localStorage.getItem('routeon_course_history');
    if (history) {
      setSavedCourses(JSON.parse(history));
    }
  }, []);

  // 현재 코스 저장 핸들러
  const handleSaveCourse = () => {
    if (!currentPlaces || currentPlaces.length === 0) {
      alert('저장할 코스 장소가 없습니다.');
      return;
    }
    if (!courseName.trim()) {
      alert('코스 이름을 입력해 주세요.');
      return;
    }

    const newCourse = {
      id: Date.now(),
      name: courseName,
      date: new Date().toLocaleDateString('ko-KR'),
      places: currentPlaces,
    };

    const updated = [newCourse, ...savedCourses];
    setSavedCourses(updated);
    localStorage.setItem('routeon_course_history', JSON.stringify(updated));
    setCourseName('');
    alert('코스가 히스토리에 저장되었습니다!');
  };

  // 저장된 코스 삭제
  const handleDeleteCourse = (id) => {
    const updated = savedCourses.filter((course) => course.id !== id);
    setSavedCourses(updated);
    localStorage.setItem('routeon_course_history', JSON.stringify(updated));
  };

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff', marginBottom: '16px' }}>
      <h3 style={{ marginTop: 0, marginBottom: '12px' }}>8. 코스 히스토리 (저장 / 불러오기)</h3>

      {/* 코스 저장 입력창 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="저장할 코스 이름 (예: 성수동 데이트 코스)"
          value={courseName}
          onChange={(e) => setCourseName(e.target.value)}
          style={{ flex: '1 1 200px', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <button
          onClick={handleSaveCourse}
          style={{ padding: '8px 16px', backgroundColor: '#FF9800', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          💾 현재 코스 저장
        </button>
      </div>

      {/* 저장된 코스 히스토리 리스트 */}
      {savedCourses.length === 0 ? (
        <p style={{ color: '#888', fontSize: '14px', margin: 0 }}>저장된 코스 히스토리가 없습니다.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {savedCourses.map((course) => (
            <div
              key={course.id}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '10px 12px',
                border: '1px solid #eee',
                borderRadius: '6px',
                backgroundColor: '#fdfdfd',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div>
                <strong style={{ fontSize: '15px' }}>{course.name}</strong>
                <span style={{ fontSize: '12px', color: '#888', marginLeft: '8px' }}>({course.date})</span>
                <div style={{ fontSize: '13px', color: '#555', marginTop: '4px' }}>
                  📍 {course.places.map((p) => p.name).join(' ➔ ')}
                </div>
              </div>

              <div style={{ display: 'flex', gap: '6px' }}>
                <button
                  onClick={() => onLoadCourse(course.places)}
                  style={{ padding: '6px 12px', backgroundColor: '#2196F3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
                >
                  불러오기
                </button>
                <button
                  onClick={() => handleDeleteCourse(course.id)}
                  style={{ padding: '6px 10px', backgroundColor: '#f44336', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '13px' }}
                >
                  삭제
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default CourseHistory;