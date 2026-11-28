import { useState } from 'react';
import { Search } from 'lucide-react';
import StatusHandler from '../common/StatusHandler';
import { searchPlaces } from '../../api/placesApi';

// 백엔드(/places/search)를 통해 카카오 장소를 검색합니다. REST 키가 브라우저에 노출되지 않습니다.
// 결과를 고르면 onAddPlace 로 넘기고, 그 함수가 false 를 돌려주면(추가 실패) 결과 목록을 그대로 둡니다.
const PlaceSearch = ({ onAddPlace, placeholder = '장소 검색', near }) => {
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async () => {
    if (!keyword.trim()) {
      setErrorMessage('검색어를 입력해 주세요.');
      return;
    }

    setIsLoading(true);
    setErrorMessage('');
    setHasSearched(true);

    try {
      const data = await searchPlaces(keyword.trim(), near ? { lat: near.lat, lng: near.lng, radius: 20000 } : {});
      setResults(data ?? []);
    } catch (error) {
      setErrorMessage(error.message);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePick = async (place) => {
    const added = await onAddPlace(place);
    if (added === false) return;
    setResults([]);
    setKeyword('');
    setHasSearched(false);
  };

  return (
    <div>
      <div className="search-box">
        <input
          className="input"
          type="text"
          placeholder={placeholder}
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button className="btn btn-primary" onClick={handleSearch} aria-label="검색">
          <Search size={16} />
        </button>
      </div>

      <StatusHandler
        isLoading={isLoading}
        isError={Boolean(errorMessage)}
        errorMessage={errorMessage}
        isEmpty={hasSearched && !errorMessage && results.length === 0}
        emptyMessage="검색 결과가 없습니다. 다른 검색어로 검색해 보세요."
      >
        {results.length > 0 && (
          <ul className="search-results">
            {results.map((item) => (
              <li key={item.kakao_place_id} className="search-result" onClick={() => handlePick(item)}>
                <strong>{item.name}</strong>
                <span>
                  {item.address} {item.category ? `· ${item.category}` : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </StatusHandler>
    </div>
  );
};

export default PlaceSearch;
