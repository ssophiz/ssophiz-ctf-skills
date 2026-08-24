@echo off
setlocal
set "SSOPHIZ_REPO_ROOT=%~dp0.."
set "SSOPHIZ_PROJECT_PYTHON=%SSOPHIZ_REPO_ROOT%\.venv\Scripts\python.exe"
if not exist "%SSOPHIZ_PROJECT_PYTHON%" (
  echo Project virtual environment not found: "%SSOPHIZ_PROJECT_PYTHON%" 1>&2
  exit /b 2
)
pushd "%SSOPHIZ_REPO_ROOT%" || exit /b 2
"%SSOPHIZ_PROJECT_PYTHON%" %*
set "SSOPHIZ_EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %SSOPHIZ_EXIT_CODE%
