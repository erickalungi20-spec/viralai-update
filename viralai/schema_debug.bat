@echo off
cd /d %~dp0
.venv\Scripts\python.exe tmp_schema_check.py
