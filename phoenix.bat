@echo off
rem Phoenix Windows 启动脚本（与 phoenix.sh 等价）
rem
rem 用法：
rem   phoenix.bat              启动 server.py
rem   phoenix.bat --setup      一键：建 venv + 装依赖 + 自检 + 启动（首次用这条）
rem   phoenix.bat --check      只做环境自检，不启动
rem
rem 环境变量：
rem   PHOENIX_PYTHON  指定解释器（默认：venv\Scripts\python.exe -> py -3 -> python）
rem   PHOENIX_PORT    覆盖端口（默认沿用 settings.json 配置）
rem
rem 旧名 DABAI_PYTHON / DABAI_PORT 继续可用（已部署实例的脚本里写死了）。
setlocal enabledelayedexpansion
chcp 65001 >nul
cd /d "%~dp0"
set "ROOT=%CD%"

set "SETUP=0"
set "CHECKONLY=0"
set "DIAG=0"
set "PASS="

:parse
if "%~1"=="" goto parsed
if /i "%~1"=="--setup" goto opt_setup
if /i "%~1"=="--check" goto opt_check
if /i "%~1"=="--diag" goto opt_diag
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

:opt_diag
set "DIAG=1"
shift
goto parse

:parsed
rem ---- 工作目录写权限：装在 Program Files 等受保护目录时，非管理员会在建 venv / 写
rem 证书时一直卡在权限重试，用户只看到黑窗停住。先探一次，把原因说清楚再往下走。
mkdir "%ROOT%\.phoenix_write_test" 2>nul
if not exist "%ROOT%\.phoenix_write_test" (
  echo [X] 当前目录不可写：%ROOT%
  echo     装在 Program Files 等受保护目录时，非管理员会卡在建 venv / 写证书这一步。
  echo     请把 Phoenix 解压到用户目录（如 %%USERPROFILE%%\Phoenix）后重试。
  pause
  exit /b 1
)
rmdir "%ROOT%\.phoenix_write_test" 2>nul


rem ---- 基础解释器：只用来建 venv ----
set "BASEPY="
if defined PHOENIX_PYTHON set "BASEPY=%PHOENIX_PYTHON%"
if not defined BASEPY if defined DABAI_PYTHON set "BASEPY=%DABAI_PYTHON%"
if not defined BASEPY (
  where py >nul 2>nul
  if not errorlevel 1 set "BASEPY=py -3"
)
if not defined BASEPY (
  where python >nul 2>nul
  if not errorlevel 1 set "BASEPY=python"
)
if not defined BASEPY (
  echo [X] 找不到 Python，请安装 Python 3.10+，或设置 PHOENIX_PYTHON 指向解释器
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
    "!VPY!" "%ROOT%\tools\check_deps.py" --gate >nul 2>nul
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
    echo 正在安装依赖（首次下载量较大，可能几分钟无输出，属正常）...
    "!VPY!" -m pip install --no-input --disable-pip-version-check --upgrade pip
    "!VPY!" -m pip install --no-input --disable-pip-version-check -r "%ROOT%\requirements.txt"
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

rem ---- 环境诊断：起不来 / 卡住时先跑 --diag，把输出整段贴出来即可定位 ----
if "%DIAG%"=="1" (
  echo ===== Phoenix 环境诊断 =====
  echo 工作目录 : !ROOT!
  echo 系统     : %OS%  %PROCESSOR_ARCHITECTURE%
  echo.
  echo [解释器]
  echo   BASEPY : !BASEPY!
  where py 2>nul
  where python 2>nul
  if exist "!VPY!" (echo   VENV   : !VPY!  [存在]) else (echo   VENV   : 不存在)
  if exist "!VPY!" "!VPY!" -c "import sys;print('  VENV 版本:', sys.version.split()[0])"
  echo.
  echo [依赖]
  !PYCMD! "!ROOT!\tools\check_deps.py"
  echo.
  echo [端口 8000]
  netstat -ano | findstr ":8000" | findstr LISTENING
  echo   -- Windows 保留端口段（非管理员绑不上的常见原因）--
  netsh interface ipv4 show excludedportrange protocol=tcp
  echo.
  echo [yt-dlp / ffmpeg]
  if exist "!VPY!" "!VPY!" -c "import importlib.util as u;print('  yt-dlp:', 'OK' if u.find_spec('yt_dlp') else '缺失')"
  where ffmpeg 2>nul
  echo.
  echo [是否管理员]
  net session >nul 2>&1
  if errorlevel 1 (echo   否) else (echo   是)
  echo ==============================
  pause
  exit /b 0
)

rem ---- 依赖自检：缺包时给出可执行命令，而不是让 server 崩在 import ----
echo [1/2] 检查依赖...
%PYCMD% "%ROOT%\tools\check_deps.py"
if errorlevel 1 (
  echo     或一键补齐：phoenix.bat --setup
  rem 双击运行时窗口会随 exit 一起关掉，用户什么都看不到——停一下让他读完。
  pause
  exit /b 1
)

rem ---- 启动 ----
rem 失败时不再只 pause 一声不响：把退出码与对应诊断命令打出来。
rem 端口绑不上（Windows 保留端口段 / 已被占用）是「非管理员起不来」的最常见
rem 原因，server.py 会自己打印 netsh 修复命令，这里再补一条兜底提示。
title Phoenix
echo [2/2] 启动服务（首次启动约 10-30 秒，日志停在最后一行属正常）...
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
%PYCMD% "%ROOT%\server.py" %PASS%
set "RC=%errorlevel%"
if not "%RC%"=="0" (
  echo.
  echo [X] 服务未正常启动，退出码 %RC%
  echo     报 WinError 10013（端口被拒）：Windows 保留了该端口段，按上面
  echo     server 输出里的 netsh 命令修复一次即可，不必长期用管理员运行。
  echo     查保留段 : netsh interface ipv4 show excludedportrange protocol=tcp
  echo     查占用者 : netstat -ano ^| findstr :8000
  echo     防火墙   : 若弹出「Windows 安全中心」允许访问，请勾选专用网络并允许
  pause
)
exit /b %RC%

:usage
echo Phoenix Windows 启动脚本
echo.
echo   phoenix.bat              启动 server.py
echo   phoenix.bat --setup      一键：建 venv + 装依赖 + 自检 + 启动
echo   phoenix.bat --check      只做环境自检，不启动
echo   phoenix.bat --diag       打印环境诊断（起不来/卡住时先跑这条）
echo.
echo 环境变量：
echo   PHOENIX_PYTHON  指定解释器
echo   PHOENIX_PORT    覆盖端口
exit /b 0
