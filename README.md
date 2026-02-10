📘 Vecbook
Facial Recognition Attendance System
Vecbook is a full-stack facial recognition attendance system built with FastAPI, React, and OpenCV (LBPH).
It allows administrators to register teachers, train facial data, and log attendance automatically using a webcam.

🚀 Features
👤 Teacher Management
Register teachers with name, department, and employee ID
Upload face images (required for enrollment)
Auto-training after face upload
View teacher list with search and reset options

📷 Facial Recognition Attendance
Webcam-based face scanning
Real-time recognition (1 frame/sec)
Confidence scoring (LBPH distance)
Prevents unenrolled/ghost identities
Duplicate attendance protection (once per day)

📊 Attendance Records
View daily and all-time logs
Date filtering
Summary (Total / On-time / Late)
Print-friendly attendance reports
Reset attendance logs (with confirmation)

🎨 UI / UX
Light & Dark mode
Splash screen on startup
Responsive dashboard
Print-safe layout
Poppins font + clean modern design

🧠 Technology Stack
Backend
FastAPI – REST API framework
SQLite – Lightweight database
OpenCV (LBPH) – Face recognition
Haar Cascade – Face detection
Python 3.10+

Frontend
React (Vite)
React Router
Context API (ThemeProvider)
HTML5 Webcam API
CSS (Print + Dark Mode support)

⚙️ Installation & Setup
1️⃣ Backend Setup
cd vecbook
python -m venv venv
venv\Scripts\activate  

Run the API:
uvicorn backend.main:app --reload --port 8000

2️⃣ Frontend Setup
cd frontend
npm install
npm run dev