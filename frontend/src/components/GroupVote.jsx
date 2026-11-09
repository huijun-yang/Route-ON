import React, { useState } from 'react';

const GroupVote = ({ onConfirmPlaces }) => {
  // 그룹 후보 장소 목록 상태
  const [candidates, setCandidates] = useState([
    { id: 1, name: '성수 맛집 A', category: '음식점', votes: 3, votedByMe: false },
    { id: 2, name: '성수 카페 B', category: '카페', votes: 5, votedByMe: true },
    { id: 3, name: '서울숲 전시관 C', category: '전시/관광', votes: 2, votedByMe: false },
  ]);

  // 새로운 후보 장소 입력 상태
  const [newPlaceName, setNewPlaceName] = useState('');
  const [newCategory, setNewCategory] = useState('카페');

  // 1. 후보 장소 추가
  const handleAddCandidate = () => {
    if (!newPlaceName.trim()) {
      alert('후보 장소명을 입력해주세요.');
      return;
    }

    const newCandidate = {
      id: Date.now(),
      name: newPlaceName,
      category: newCategory,
      votes: 0,
      votedByMe: false,
    };

    setCandidates([...candidates, newCandidate]);
    setNewPlaceName('');
  };

  // 2. 투표 토글 (좋아요 / 취소)
  const handleToggleVote = (id) => {
    setCandidates((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          const isVoted = item.votedByMe;
          return {
            ...item,
            votes: isVoted ? item.votes - 1 : item.votes + 1,
            votedByMe: !isVoted,
          };
        }
        return item;
      })
    );
  };

  // 3. 득표수 높은순으로 확정된 코스에 반영
  const handleFinalizeCourse = () => {
    // 최소 1표 이상 얻은 장소를 득표순 정렬
    const selected = [...candidates]
      .filter((item) => item.votes > 0)
      .sort((a, b) => b.votes - a.votes);

    if (selected.length === 0) {
      alert('투표를 받은 후보 장소가 없습니다.');
      return;
    }

    if (onConfirmPlaces) {
      onConfirmPlaces(selected);
      alert(`${selected.length}개의 장소가 그룹 코스로 최종 확정되었습니다!`);
    }
  };

  return (
    <div style={{ padding: '16px', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#fff', marginBottom: '16px' }}>
      <h3 style={{ marginTop: 0, marginBottom: '12px' }}>7. 그룹 코스 후보 및 투표</h3>

      {/* 후보 장소 추가 입력 폼 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
        <input
          type="text"
          placeholder="그룹 후보 장소 입력"
          value={newPlaceName}
          onChange={(e) => setNewPlaceName(e.target.value)}
          style={{ flex: 2, padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        />
        <select
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
          style={{ flex: 1, padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
        >
          <option value="음식점">음식점</option>
          <option value="카페">카페</option>
          <option value="전시/관광">전시/관광</option>
          <option value="기타">기타</option>
        </select>
        <button
          onClick={handleAddCandidate}
          style={{ padding: '8px 12px', backgroundColor: '#2196F3', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}
        >
          후보 추가
        </button>
      </div>

      {/* 후보 장소 리스트 및 투표 버튼 */}
      <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 16px 0' }}>
        {candidates.map((item) => (
          <li
            key={item.id}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '10px 12px',
              marginBottom: '8px',
              border: '1px solid #eee',
              borderRadius: '6px',
              backgroundColor: item.votedByMe ? '#e8f4ff' : '#fafafa',
            }}
          >
            <div>
              <strong style={{ fontSize: '15px' }}>{item.name}</strong>
              <span style={{ fontSize: '12px', color: '#666', marginLeft: '8px' }}>({item.category})</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontWeight: 'bold', color: '#1976D2' }}>👍 {item.votes}표</span>
              <button
                onClick={() => handleToggleVote(item.id)}
                style={{
                  padding: '6px 12px',
                  backgroundColor: item.votedByMe ? '#ff4d4f' : '#e6f7ff',
                  color: item.votedByMe ? '#fff' : '#1890ff',
                  border: item.votedByMe ? 'none' : '1px solid #91d5ff',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontWeight: 'bold',
                }}
              >
                {item.votedByMe ? '투표 취소' : '투표하기'}
              </button>
            </div>
          </li>
        ))}
      </ul>

      {/* 최종 코스 확정 버튼 */}
      <button
        onClick={handleFinalizeCourse}
        style={{
          width: '100%',
          padding: '10px',
          backgroundColor: '#4CAF50',
          color: '#fff',
          border: 'none',
          borderRadius: '4px',
          fontWeight: 'bold',
          fontSize: '14px',
          cursor: 'pointer',
        }}
      >
        ✅ 투표 결과 반영 및 코스 확정
      </button>
    </div>
  );
};

export default GroupVote;