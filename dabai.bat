@echo off
rem Phoenix Windows 启动脚本（与 dabai.sh 等价）
rem
rem 用法：
rem   dabai.bat              启动 server.py
rem   dabai.bat --setup      一键：建 venv + 装依赖 + 自检 + 启动（首次用这条）
rem   dabai.bat --check      只做环境自检，不启动
rem
rem 环境变量：
rem   DABAI_PYTHON  指定解释器（默认：venv\Scripts\python.exe -> py -3 -> python）
rem   DABAI_PORT    覆盖端口（默认沿用 settings.json 配置）
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
set "ROOT=%CD%"

set "SETUP=0"
set "CHECKONLY=0"
set "PASS="

:parse
if "%~1"=="" goto parsed
if /i "%~1"=="--setup" goto opt_setup
if /i "%~1"=="--check" goto opt_check
if /i "%~1"=="-h" goto usage
if /i "%~1"=="--help" goto usage
set "PASS=%PASS% %~1"
shift
goto parse

:opt_setup
set "SETUP=1"
shift
goto parse

:opt_check
set "CHECKONLY=1"
shift
goto parse

:parsed

rem ---- 基础解释器：只用来建 venv ----
set "BASEPY="
if defined DABAI_PYTHON set "BASEPY=%DABAI_PYTHON%"
if not defined BASEPY (
  where py >nul 2>nul
  if not errorlevel 1 set "BASEPY=py -3"
)
if not defined BASEPY (
  where python >nul 2>nul
  if not errorlevel 1 set "BASEPY=python"
)
if not defined BASEPY (
  echo [X] 找不到 Python，请安装 Python 3.10+，或设置 DABAI_PYTHON 指向解释器
  exit /b 1
)

set "VPY=%ROOT%\venv\Scripts\python.exe"

rem ---- 一键引导：venv 不在、或启动必需依赖不全，都补装（幂等）----
rem 只看 venv\Scripts\python.exe 存在与否不够：上次装到一半（磁盘满 / 断网）会留下一个
rem 半成品 venv，再跑 --setup 会直接跳过，问题拖到启动时才炸。
if "%SETUP%"=="1" (
  set "NEED=0"
  if not exist "!VPY!" (
    set "NEED=1"
  ) else (
    "!VPY!" "%ROOT%\tools\check_deps.py" >nul 2>nul
    if errorlevel 1 set "NEED=1"
  )
  if "!NEED!"=="1" (
    echo == 环境缺失或依赖不全：创建虚拟环境并安装依赖 ==
    if not exist "!VPY!" (
      %BASEPY% -m venv "%ROOT%\venv"
      if errorlevel 1 (
        echo [X] 创建虚拟环境失败
        exit /b 1
      )
    )
    "!VPY!" -m pip install --upgrade pip
    "!VPY!" -m pip install -r "%ROOT%\requirements.txt"
    if errorlevel 1 (
      echo [X] 依赖安装失败，请检查网络或代理后重试
      exit /b 1
    )
  )
)

rem ---- 选解释器：优先项目内 venv ----
set "PYCMD="
if exist "!VPY!" set PYCMD="!VPY!"
if not defined PYCMD set "PYCMD=%BASEPY%"

rem ---- 环境自检（--check 只自检不启动）----
if "%CHECKONLY%"=="1" (
  %PYCMD% "%ROOT%\tools\selfcheck.py"
  exit /b !errorlevel!
)

rem ---- 依赖自检：缺包时给出可执行命令，而不是让 server 崩在 import ----
%PYCMD% "%ROOT%\tools\check_deps.py"
if errorlevel 1 (
  echo     或一键补齐：dabai.bat --setup
  exit /b 1
)

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
%PYCMD% "%ROOT%\server.py" %PASS%
if errorlevel 1 pause
exit /b %errorlevel%

:usage
echo Phoenix Windows 启动脚本
echo.
echo   dabai.bat              启动 server.py
echo   dabai.bat --setup      一键：建 venv + 装依赖 + 自检 + 启动
echo   dabai.bat --check      只做环境自检，不启动
echo.
echo 环境变量：
echo   DABAI_PYTHON  指定解释器
echo   DABAI_PORT    覆盖端口
exit /b 0
