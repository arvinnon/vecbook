# Changelog

All notable changes to this project will be documented in this file.

## 2026-02-10
### Added
- Live camera capture for teacher enrollment (auto and manual capture).
- Circular face guide overlay in enrollment and recognition views.
- Optional API key protection for write/admin endpoints.
- Per-record deletion for attendance logs.
- Backend/Frontend test suites (pytest and Vitest).

### Changed
- Attendance records now include PM entries and show Time Out.
- Shift rules updated to AM 07:30-12:00, lunch 12:00-13:00, PM 13:00-17:00.
- Backend refactored into routers and training service module.
- Centralized configuration for paths and shift times.

### Fixed
- DTR endpoint alignment between frontend and backend.
- Training single-flight protection to prevent concurrent model writes.
- Encoding/mojibake issues in UI and README.

### Removed
- Legacy unused `face_embeddings` table.
- Stale `face_recognition/recognizer.py`.
