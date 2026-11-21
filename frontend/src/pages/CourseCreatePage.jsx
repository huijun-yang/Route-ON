import RouteMap from "../components/map/RouteMap";
import CourseCreateWorkspace from "../components/courses/CourseCreateWorkspace";
import "./CourseCreatePage.css";
import { useState } from "react";

export default function CourseCreatePage() {
  // 현재 진행 단계
  const [step, setStep] = useState(1);
  // 장소 데이터
  const [places, setPlaces] = useState([]);
  // 생성된 코스
  const [course, setCourse] = useState([]);

  return (
    <div className="course-create-wrapper">
      <section className="course-create-workspace">
        <CourseCreateWorkspace step={step} setStep={setStep}
        places={places} setPlaces={setPlaces}
        course={course} setCourse={setCourse} />
      </section>
      <RouteMap places={places} course={course} step={step} />
    </div>
  )
}