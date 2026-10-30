import React from 'react';

// 9. API 로딩, 에러, 빈 결과 상태 전용 UI 컴포넌트
const StatusHandler = ({ isLoading, isError, errorMessage, isEmpty, emptyMessage, children }) => {
  // 1. 로딩 중인 경우
  if (isLoading) {
    return (
      <div style={{ padding: '24px', textAlign: 'center', backgroundColor: '#f9f9f9', borderRadius: '8px', margin: '12px 0' }}>
        <div style={{ display: 'inline-block', width: '24px', height: '24px', border: '3px solid #f3f3f3', borderTop: '3px solid #2196F3', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
        <p style={{ marginTop: '8px', color: '#666', fontSize: '14px' }}>데이터를 불러오는 중입니다...</p>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // 2. API 에러가 발생한 경우
  if (isError) {
    return (
      <div style={{ padding: '16px', backgroundColor: '#fff2f0', border: '1px solid #ffccc7', borderRadius: '8px', margin: '12px 0', color: '#ff4d4f' }}>
        ⚠️ <strong>오류가 발생했습니다:</strong> {errorMessage || '요청 처리 중 문제가 발생했습니다.'}
      </div>
    );
  }

  // 3. 검색 결과나 코스가 비어있는 경우
  if (isEmpty) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', backgroundColor: '#fafafa', border: '1px dashed #ccc', borderRadius: '8px', margin: '12px 0', color: '#888', fontSize: '14px' }}>
        ℹ️ {emptyMessage || '표시할 데이터가 존재하지 않습니다.'}
      </div>
    );
  }

  // 정상 상태일 때 자식 컴포넌트 렌더링
  return <>{children}</>;
};

export default StatusHandler;