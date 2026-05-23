@echo off
echo Starting Elevator App...

if not exist "files" (
  echo Creating link to DriveFiles...
  mklink /J "files" "C:\Users\danih\Documents\DriveFiles"
)

echo App: http://localhost:8080
start "App Server" cmd /c "cd /d C:\Users\danih\Documents\elevator-poc-recovered && python -m http.server 8080"
timeout /t 2
start http://localhost:8080
