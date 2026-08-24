# Architecture

## 책임 분리

1. `ctf-harness`가 CTFd 또는 로컬 파일을 `TaskEnvelope`로 정규화합니다.
2. router가 분야별 profile을 병렬 specialist와 독립 검증자로 배치합니다.
3. Orca는 Codex specialist마다 별도 run task/worker를 생성하고 상태를 추적합니다.
4. API adapter는 명시적 `--with-api-workers`에서만 OpenAI-compatible provider를 Docker 도구 루프에 연결합니다.
5. 모든 워커는 finding과 flag candidate만 control plane에 게시합니다.
6. verifier가 CTFd 토큰을 보유하고 후보를 단일 제출합니다.

Codex launch 실패는 dispatch가 즉시 fallback route로 넘깁니다. 실행 후 `worker_done: failed`는 `ctf-harness supervise`가 처리하며, 실패한 worker의 category에 맞춰 Kimi/DeepSeek/Ollama 중 준비된 첫 provider를 실행합니다. Provider API key와 Docker image가 없으면 failover를 성공으로 가장하지 않고 unavailable receipt를 반환합니다.

## 상태 계약

- `tasks`: 입력, 범위, 아티팩트, 엔드포인트와 작업 상태
- `findings`: 요약, 구체적 증거, confidence
- `candidates`: 플래그 값과 pending/correct/incorrect/error 상태
- `events`: claim, 상태 변경, finding/candidate 발행의 감사 로그

작업 결과를 대화문으로만 넘기지 않고 SQLite와 작업공간 파일로 남겨, 다른 분야 워커가 그대로 이어받을 수 있게 했습니다. 예를 들어 Web 워커가 얻은 바이너리를 `artifacts/`에 저장하고 finding을 발행하면 Reverse 워커는 동일 task workspace를 읽습니다. 같은 분야의 병렬 워커는 `notes/<worker>/`에만 작업물을 기록해 서로의 초안 파일을 덮어쓰지 않습니다.

## 역할별 도구

Pwn은 동적 분석이 필요하므로 컨테이너에 `SYS_PTRACE`만 추가합니다. Reverse 역시 같은 디버그 경계를 사용합니다. Web은 기본적으로 네트워크가 꺼져 있으므로 원격 CTF 인스턴스가 필요할 때 전용 Docker network를 만들어 `runtime.worker_network`에 설정합니다. 호스트 네트워크는 사용하지 않습니다.

IDA Pro는 라이선스와 GUI 세션 때문에 worker image에 포함하지 않습니다. IDA MCP를 추가할 때는 별도 서버로 연결하고 task workspace 밖 파일에 접근하지 못하도록 경로 allowlist를 둡니다. 자동화 경로는 Ghidra headless, radare2, angr로 유지합니다.

## 확장 지점

- 새 provider: `profiles`에 `openai_compatible` profile 추가
- 새 분야: `contracts.CATEGORIES`, router 키워드, `skills/<role>/SKILL.md`, route 추가
- 새 도구: API worker tool schema와 `_execute_tool` 양쪽에 추가
- CTF 플랫폼: CTFdClient와 같은 verifier adapter 구현

외부 provider 자체를 Orca가 직접 지원하면 API worker 대신 `adapter: orca` profile을 사용할 수 있습니다. 그 경우에도 candidate 제출 권한은 MCP verifier에만 둡니다.
