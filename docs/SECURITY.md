# Security Boundary

이 프로젝트는 소유하거나 명시적으로 허가받은 CTF 문제에만 사용합니다.

## 기본 경계

- 작업 scope는 `Authorized CTF challenge only`로 고정됩니다.
- Docker worker는 `--cap-drop ALL`, `no-new-privileges`, CPU/메모리/PID 제한을 적용합니다.
- Pwn/Reverse에만 `SYS_PTRACE`를 추가합니다.
- 기본 Docker network는 `none`입니다.
- 작업공간 파일 API는 resolved path가 전용 workspace 내부인지 검사합니다.
- CTFd 토큰은 provider prompt, task payload, MCP task 조회 결과에 포함되지 않습니다.
- 실제 제출은 환경 변수로 한 번 더 활성화해야 합니다.

## 외부 모델 사용 전 확인

- 문제 NDA와 데이터 국외 이전 조건
- 바이너리·소스·플래그 후보 전송 허용 여부
- provider의 로그 보관/학습 정책
- 조직 승인된 endpoint와 API key 저장 방식

민감한 사내 문제는 외부 profile을 routes에서 제거하고 Orca의 로컬/승인 모델만 사용하십시오. `.env`, SQLite DB, 작업공간은 Git에서 제외됩니다.

## 의도적 제한

- CTFd attachment 자동 다운로드는 하지 않습니다. 인증 URL/파일을 먼저 검토한 뒤 `--artifact`로 등록합니다.
- 플래그 후보를 발견했다고 자동 제출하지 않습니다.
- 호스트 shell을 모델에 직접 노출하지 않습니다.
- IDA GUI 제어와 브라우저 로그인 세션을 기본 권한으로 제공하지 않습니다.
