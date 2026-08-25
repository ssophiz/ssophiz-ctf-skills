# Architecture

## 책임 분리

1. `ctf-harness`가 CTFd 또는 로컬 파일을 `TaskEnvelope`로 정규화합니다.
2. router가 분야별 playbook을 유지하면서 worker profile을 세 단계 wave로 배치합니다.
3. Orca는 선택한 wave의 worker 하나만 별도 run task로 생성하고 상태를 추적합니다.
4. wave 0은 Luna low 분류, wave 1은 Sol medium 풀이, wave 2는 blocker용 Sol xhigh입니다.
   레이스컨디션·실시간 게임 신호가 있으면 fast lane이 Luna를 생략하고 Sol medium을 wave 0으로 당깁니다.
5. 모든 워커는 finding과 flag candidate만 control plane에 게시합니다.
6. verifier가 CTFd 토큰을 보유하고 후보를 단일 제출합니다.

DeepSeek, Kimi, Grok 기본 profile과 자동 provider fallback은 제거했습니다. 실패는 명시적으로 기록하고, coordinator가 같은 wave 재시도 또는 다음 wave 실행 중 하나를 선택합니다. 로컬 Ollama와 일반 OpenAI-compatible adapter는 기본 route 밖의 수동 확장 지점으로만 남습니다.

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

- 새 provider: 데이터 경계를 검토한 뒤 `profiles`에 수동 `openai_compatible` profile 추가
- 새 분야: `contracts.CATEGORIES`, router 키워드, `skills/<role>/SKILL.md`, route 추가
- 새 도구: API worker tool schema와 `_execute_tool` 양쪽에 추가
- CTF 플랫폼: CTFdClient와 같은 verifier adapter 구현

외부 provider 자체를 Orca가 직접 지원하면 API worker 대신 `adapter: orca` profile을 사용할 수 있습니다. 그 경우에도 candidate 제출 권한은 MCP verifier에만 둡니다.
