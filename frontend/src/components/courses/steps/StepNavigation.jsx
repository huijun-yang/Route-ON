export default function StepNavigation({
  onPrev,
  onNext,
  prevText = "이전",
  nextText = "다음",
  showPrev = true,
  showNext = true,
  prevDisabled = false,
  nextDisabled = false,
}) {
  return (
    <div className="step-navigation">
      <div>
        {showPrev && (
          <button className="btn" onClick={onPrev} disabled={prevDisabled}>
            {prevText}
          </button>
        )}
      </div>

      <div>
        {showNext && (
          <button className="btn btn-primary btn-block" onClick={onNext} disabled={nextDisabled}>
            {nextText}
          </button>
        )}
      </div>
    </div>
  );
}
