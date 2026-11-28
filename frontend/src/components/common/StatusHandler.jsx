// API 로딩, 에러, 빈 결과 상태 전용 UI 컴포넌트
const StatusHandler = ({ isLoading, isError, errorMessage, isEmpty, emptyMessage, children }) => {
  if (isLoading) {
    return (
      <div className="empty" style={{ border: 0, background: 'transparent' }}>
        <div className="spinner" />
        <p style={{ margin: '8px 0 0' }}>불러오는 중입니다...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="alert alert-danger" style={{ margin: '8px 0' }}>
        <span>
          ⚠️ <strong>오류가 발생했습니다.</strong> {errorMessage || '요청 처리 중 문제가 발생했습니다.'}
        </span>
      </div>
    );
  }

  if (isEmpty) {
    return <div className="empty">{emptyMessage || '표시할 데이터가 없습니다.'}</div>;
  }

  return <>{children}</>;
};

export default StatusHandler;
