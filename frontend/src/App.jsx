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
import ScanAudit from "./ScanAudit";
import { hasSession } from "./api";

function RequireAuth({ children }) {
  if (!hasSession()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Splash />} />
        <Route path="/login" element={<SessionLogin />} />
        <Route
          path="/home"
          element={
            <RequireAuth>
              <Dashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/teachers"
          element={
            <RequireAuth>
              <Teachers />
            </RequireAuth>
          }
        />
        <Route
          path="/records"
          element={
            <RequireAuth>
              <Records />
            </RequireAuth>
          }
        />
        <Route
          path="/enroll"
          element={
            <RequireAuth>
              <Enroll />
            </RequireAuth>
          }
        />
        <Route
          path="/teachers/:id/faces"
          element={
            <RequireAuth>
              <FaceUpload />
            </RequireAuth>
          }
        />
        <Route
          path="/camera"
          element={
            <RequireAuth>
              <AttendanceCam />
            </RequireAuth>
          }
        />
        <Route path="/splash" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
        <Route
          path="/teachers/:id/dtr"
          element={
            <RequireAuth>
              <TeacherDTR />
            </RequireAuth>
          }
        />
        <Route
          path="/audit"
          element={
            <RequireAuth>
              <ScanAudit />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
