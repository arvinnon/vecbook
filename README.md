:blue_book: Vecbook
Facial Recognition Attendance System
Vecbook is a full-stack facial recognition attendance system built with FastAPI, React, and OpenCV (LBPH).
It allows administrators to register teachers, train facial data, and log attendance automatically using a webcam.

## Documentation
- User Guide: `docs/USER_GUIDE.md`
- User Guide (Screenshots): `docs/USER_GUIDE_SCREENSHOTS.md`

:rocket: Features
:bust_in_silhouette: Teacher Management
Register teachers with name, department, and employee ID
Live camera face capture for enrollment
Auto-training after face upload
View teacher list with search and reset options

:camera: Facial Recognition Attendance
Webcam-based face scanning
Real-time recognition (1 frame/sec)
Confidence scoring (LBPH distance)
Prevents unenrolled/ghost identities
Duplicate attendance protection (once per day)

:bar_chart: Attendance Records
View daily and all-time logs
Date filtering
Summary (Total / On-time / Late)
Admin scan audit history with review filters
Strict attendance rules (grace period, auto-close, absence cutoff)
Print-friendly attendance reports
Reset attendance logs (with confirmation)
Delete individual log entries

:art: UI / UX
Light & Dark mode
Splash screen on startup
Responsive dashboard
Print-safe layout
Poppins font + clean modern design

:brain: Technology Stack
Backend
FastAPI - REST API framework
SQLite - Lightweight database
OpenCV (LBPH) - Face recognition
Haar Cascade - Face detection
Python 3.10+

Frontend
React (Vite)
React Router
Context API (ThemeProvider)
HTML5 Webcam API
CSS (Print + Dark Mode support)

:gear: Installation & Setup
1. Backend Setup
cd vecbook
python -m venv venv
venv\Scripts\activate  

Run the API:
uvicorn backend.main:app --reload --port 8000

2. Frontend Setup
cd frontend
npm install
npm run dev

:lock: Security (Admin Account + Token Flow)
Write/admin endpoints require a Bearer token from an admin login.
Log in via `POST /auth/login` using:
- `username`
- `password`

On startup, the backend auto-creates the configured admin account if it does not already exist in the database.

Recommended backend env vars:
- `VECBOOK_ADMIN_USERNAME` (default: `admin`)
- `VECBOOK_ADMIN_PASSWORD` (default: `admin123`, change this in real deployments)
- `VECBOOK_SIGNING_KEY` (token signing key)
- `VECBOOK_AUTH_TOKEN_TTL_SECONDS` (default: 43200 / 12h)

Frontend note:
- Use the Admin Login screen (`/login`) to authenticate and store the bearer token locally.

:shield: Debug + CORS Hardening
- `/debug/dbpath` is protected by admin auth and disabled by default.
- Enable it only when needed: `VECBOOK_ENABLE_DEBUG_ENDPOINTS=true`
- CORS is environment-driven:
  - `VECBOOK_CORS_ALLOW_ORIGINS` (comma-separated origins)
  - `VECBOOK_CORS_ALLOW_METHODS` (comma-separated methods)
  - `VECBOOK_CORS_ALLOW_HEADERS` (comma-separated headers)
  - `VECBOOK_CORS_ALLOW_CREDENTIALS` (`true`/`false`)

:wrench: Recognition Tuning (Optional)
- `VECBOOK_MATCH_THRESHOLD` (default: 60)
- `VECBOOK_STRICT_MATCH_THRESHOLD` (default: 85% of match threshold)
- `VECBOOK_MATCH_CONFIRMATIONS` (default: 1 match)
- `VECBOOK_SESSION_TTL_SECONDS` (default: 10)
- `VECBOOK_AM_START` (default: 05:00:00)
- `VECBOOK_AM_END` (default: 12:00:00)
- `VECBOOK_PM_START` (default: 13:00:00)
- `VECBOOK_PM_END` (default: 19:00:00)
- `VECBOOK_ATTENDANCE_GRACE_MINUTES` (default: 10)
- `VECBOOK_ATTENDANCE_AUTO_CLOSE_CUTOFF` (default: 19:00:00)
- `VECBOOK_ATTENDANCE_ABSENCE_CUTOFF` (default: 23:59:00)
- `VECBOOK_ATTENDANCE_DUPLICATE_COOLDOWN_SECONDS` (default: 60)
- `VECBOOK_ATTENDANCE_LOGOUT_MODE` (default: `fixed_two_action`, set to `flexible` for lunch-window/within-day logout flexibility)
- `VECBOOK_MAX_FACES` (default: 1)
- `VECBOOK_MIN_FACE_SIZE` (default: 120 px)
- `VECBOOK_FACE_CENTER_MAX_OFFSET_RATIO` (default: 0.2 of min frame dimension)
- `VECBOOK_BLUR_THRESHOLD` (default: 60, higher is stricter)
- `VECBOOK_BRIGHTNESS_MIN` (default: 60)
- `VECBOOK_BRIGHTNESS_MAX` (default: 200)
