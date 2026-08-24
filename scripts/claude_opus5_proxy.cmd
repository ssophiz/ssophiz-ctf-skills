@echo off
setlocal

if "%CCE_PROXY_URL%"=="" set "CCE_PROXY_URL=http://192.168.49.1:8282"
set "HTTP_PROXY=%CCE_PROXY_URL%"
set "HTTPS_PROXY=%CCE_PROXY_URL%"
set "http_proxy=%CCE_PROXY_URL%"
set "https_proxy=%CCE_PROXY_URL%"

claude --model opus --effort max %*
exit /b %ERRORLEVEL%
