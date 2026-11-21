import { useEffect, useState } from "react";

export default function LoadingStep({gotoNextStep, gotoPrevStep, places, setCourse}) {
  useEffect(() => {
    let canceled = false;

    async function createCourse() {
      try {
        // 백엔드 코스 생성 API 호출 필요(아직 구현 안 됨)
        // await 코스생성API함수();

        setCourse(places);
    
        // 테스트용 시간 지연 함수
        const sleep = async (ms) => {
          return new Promise(resolve => setTimeout(resolve, ms));
        }

        await sleep(3000);

        if (canceled) return;

        setCourse(places);
        gotoNextStep();

      } catch(error) {
        if (canceled) return;

        alert(error.message);
        gotoPrevStep();
      }
    }

    createCourse();
    return () => {
      canceled = true;
    }
  }, []);

  return (
    <div>
      코스 생성 중
    </div>
  );
}