@echo off
echo Starting Elevator App...
echo App:   http://localhost:8080
echo Files: http://localhost:8081
start "App Server"    cmd /c "cd /d C:\Users\danih\Documents\elevator-poc-recovered && python -m http.server 8080"
start "Files Server"  cmd /c "cd /d C:\Users\danih\Documents\DriveFiles && python -m http.server 8081"
timeout /t 2
start http://localhost:8080
