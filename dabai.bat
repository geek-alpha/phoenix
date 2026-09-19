@echo off
rem 旧名兼容：dabai.bat 已改名为 phoenix.bat，这里只做转发。
rem 保留的原因：已部署实例的快捷方式 / 计划任务 / 旧文档里写死了 dabai.bat。
call "%~dp0phoenix.bat" %*
exit /b %errorlevel%
