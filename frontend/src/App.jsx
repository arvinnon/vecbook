import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Splash from "./Splash";
import SessionLogin from "./SessionLogin";
import Dashboard from "./Dashboard";
import Teachers from "./Teachers";
import Records from "./Records";
import Enroll from "./Enroll";
import FaceUpload from "./FaceUpload";
import AttendanceCam from "./AttendanceCam";
import TeacherDTR from "./DTRTeacher";
export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/login" element={<SessionLogin />} />
        <Route path="/home" element={<Dashboard />} />
        <Route path="/teachers" element={<Teachers />} />
        <Route path="/records" element={<Records />} />
        <Route path="/enroll" element={<Enroll />} />
        <Route path="/teachers/:id/faces" element={<FaceUpload />} />
        <Route path="/camera" element={<AttendanceCam />} />
        <Route path="/splash" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
        <Route path="/teachers/:id/dtr" element={<TeacherDTR />} />
        
      </Routes>
    </BrowserRouter>
  );
}
