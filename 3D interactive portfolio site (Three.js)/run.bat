@echo off
title Skill Atlas - 3D Interactive Portfolio
echo Starting Skill Atlas server...
cd /d "%~dp0"
start "" http://127.0.0.1:8631/index.html
python -m http.server 8631 --bind 127.0.0.1
pause