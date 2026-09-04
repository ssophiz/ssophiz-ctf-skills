# SSophiz CTF Skills and Harness

Reusable, evidence-driven agent skills and a local orchestration harness for
authorized CTF competitions. The public repository deliberately excludes
flags, credentials, pairing codes, live event workspaces, and raw challenge
artifacts.

## GuardLens Variant Hunter

GuardLens is an evidence-gated missing-guard variant hunter for authorized
binary and source review. It compares sibling functions, derives repeated guard
invariants, and ranks only inconsistencies that also reach a sensitive operation.
Each result includes a guard matrix, peer support, confidence, and reproducible
match evidence.

```powershell
python -m pip install -e ".[dev]"
guardlens examples/guardlens/sample_handlers.json -o guardlens-report.json
python -m unittest tests.test_guardlens -v
```

The current MVP is deterministic and reviewable; it does not claim that a
candidate is a confirmed vulnerability. See [docs/GUARDLENS.md](docs/GUARDLENS.md)
for the input contract, IDA workflow, limitations, and extension path.

## Agent skills

The `skills/` directory follows the `SKILL.md` frontmatter convention used by
Codex and other compatible agents. It contains category workers for Crypto,
Forensics, Malware, Misc, Pwn, Reverse, Web, and latency-sensitive browser
games, plus orchestration and post-event distillation skills.

Install a skill by copying or linking its directory into your agent's skill
discovery path. For example, on Windows:

```powershell
Copy-Item -Recurse .\skills\reverse "$env:USERPROFILE\.codex\skills\ssophiz-ctf-reverse"
Copy-Item -Recurse .\skills\reverse "$env:USERPROFILE\.agents\skills\ssophiz-ctf-reverse"
```

The sanitized [CCE 2026 retrospective](docs/CCE2026_POSTMORTEM.md) records the
operational lessons used to strengthen these skills without publishing any
challenge answers. The separate
[post-event recovery audit](docs/CCE2026_RECOVERY_AUDIT.md) records the bounded
Lease Journal, nsprobe, PiEEE, GRID, and mail-server follow-up without flags or
raw event artifacts.

## Optional context-efficiency tools

Ponytail, Graphify, Semble, ast-grep, Headroom, CodeBurn, Caveman, and
Impeccable can be installed reproducibly for Codex, Claude Code, and this
project:

```powershell
.\scripts\install-agent-efficiency-tools.ps1
```

Headroom remains opt-in through the supplied launch scripts; the installer does
not rewrite an active Codex or Claude session. CodeBurn measures usage. Caveman
is installed as a skill without its proxy hooks, and Impeccable is reserved for
UI work. See [docs/AGENT_EFFICIENCY.md](docs/AGENT_EFFICIENCY.md) for routing,
privacy, and token-measurement guidance. Pinned source versions are recorded in
[config/agent-tools.lock.json](config/agent-tools.lock.json).

This repository also ships project-scoped Codex defaults in
`.codex/config.toml`: medium reasoning, low verbosity, bounded tool history,
disabled Apps/web search, and two nested subagents at most. Explicit Orca wave
settings still override reasoning effort when escalation is required.

### Low-context Pi worker

Install the pinned Pi CLI and checksum-verified Hypa binary, then authenticate
the isolated CTF profile once:

```powershell
.\scripts\install-pi-ctf.ps1
.\scripts\start-pi-ctf.ps1 -Category web -Login
```

Use Pi for bounded triage or one concrete analysis path. The launcher loads one
category skill, disables unrelated extensions and project context, exposes only
four built-in tools, and uses an ephemeral session by default:

```powershell
.\scripts\start-pi-ctf.ps1 `
  -Category realtime-web-game `
  -Workspace .\work\current-game `
  -Thinking medium
```

Add `-Interactive` for a continuing TUI session or `-KeepSession` for a saved
one-shot run. Hypa remains an explicit CLI for large repetitive non-evidence
output; its Pi extension and automatic shell rewriting are deliberately not
installed. Exact flags, credentials, hashes, addresses, offsets, payloads, and
decisive errors must come from raw output.

## Live evidence ledger

Solver workers can preserve decisive commands, PoC paths, key output, flag
candidates, and reproduction steps through the compact `ctf-control`
`record_evidence` tool. Generate the long-form packet only once at event close:

```powershell
.\scripts\ctf-harness.ps1 evidence-pdf --output .\output\pdf\ctf-evidence-ledger.pdf
```

See [docs/EVIDENCE_LEDGER.md](docs/EVIDENCE_LEDGER.md) for the worker payload
and verifier linkage rules.

## CCE2027 preparation helpers

Run the harness through the repository virtual environment so the checked-out code and dependencies are always used:

```powershell
.\scripts\ctf-harness.ps1 doctor
```

Configure an optional private Markdown/Obsidian corpus, then prepare the
first-five-minute packet before dispatch. The corpus stays local and is never
committed:

```powershell
$env:SSOPHIZ_CTF_CORPUS = 'D:\Obsidian\CTF'
.\scripts\ctf-harness.ps1 kickoff <task_id>
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply
```

Small corpora use exact local search. Large corpora use bounded Semble retrieval.
The generated `notes/kickoff.json` also tells the worker which deterministic
runner should own brute force, races, replay, emulation, or other hot loops.

The committed ENKI source manifest contains only allowlisted public references.
Raw pages and repositories stay under the ignored local corpus directory, while
derived retrieval text masks historical flags to prevent accidental submission:

```powershell
.\scripts\ctf-harness.ps1 corpus-sources --collection enki
.\scripts\ctf-harness.ps1 corpus-sync --collection enki
.\scripts\ctf-harness.ps1 recall "WAF cache partial inspection" --collection enki
```

CCE, ENKI, CODEGATE, and FIESTA task names automatically prioritize this local
collection during `kickoff`. RAG-Anything may index the same local raw directory
offline for PDFs and images; it is deliberately not a default dependency or an
always-on MCP server.

## LAN worker in Orca

On a second Windows PC with this repository available, prepare the CTF skills,
project environment, and an Orca worker server:

```powershell
.\scripts\setup-orca-lan-worker.ps1 -Offline -Port 6770
```

If optional local tooling is incomplete immediately before an event, use
`-SkipPythonSetup` to bring the Orca worker online first. Run the harness doctor
after pairing and install the missing Docker/WSL/IDA components separately.

Keep that terminal open. On the coordinator PC, register the printed pairing
code and optionally register the repository path that exists on the worker:

```powershell
.\scripts\connect-orca-lan-worker.ps1 `
  -PairingCode 'orca://pair?code=...' `
  -Name 'cce-laptop-2' `
  -RemoteRepoPath 'C:\path\to\ssophiz-ctf-skills'
```

Allow the Orca server through Windows Firewall on **Private networks only**.
Pairing codes are credentials; do not commit or post them publicly.

The `ctf-artifact` MCP server now inventories and safely extracts nested ZIP/TAR/7z archives with a `provenance.json` manifest, rejects traversal/link entries, and extracts HWPX section text. The configured `ctf-web` server provides cookie-sharing bounded sessions, HS256 JWT and `itsdangerous` helpers, a bounded race runner, and local-only ffmpeg/HLS gate probes against a generated dummy fixture.

Target traffic is off by default. Register the challenge with `--enable-target-operations`, set `SSOPHIZ_ENABLE_TARGETS=1` only for that run, and use `ctf-web`; it rejects URLs outside the task's endpoint allowlist and does not follow redirects. Non-read-only methods additionally require `SSOPHIZ_ENABLE_TARGET_MUTATION=1` plus the tool's explicit `confirm_state_change` argument.

Local corpus preparation is also available without MCP:

```powershell
.\scripts\ctf-harness.ps1 prepare-archive .\challenge.zip --destination .\prepared\challenge
.\scripts\ctf-harness.ps1 extract-hwpx .\writeup.hwpx --output .\prepared\writeup.txt
.\scripts\ctf-harness.ps1 classify-flag "CCE{candidate_value}"
```

ENKI WhiteHat 스타일의 승인된 CTF 문제를 여러 모델이 분석하고, 증거와 플래그 후보를 중앙 검증기로 모으는 로컬 하네스입니다. Orca가 작업 DAG와 워커 수명주기를 맡고, 이 저장소는 CTF 전용 라우팅·격리 도구·MCP 계약·CTFd 검증 경계를 제공합니다.

## 구조

```text
CTFd / 수동 입력
       │
       ▼
  TaskEnvelope ──► category router ──► wave 0: Luna low triage
                                          │
                                          ├─ evidence or candidate ──► stop
                                          └─ concrete blocker
                                                  │
                                                  ▼
                                     wave 1: Sol medium solve
                                                  │
                                                  └─ blocker wave 2: Sol xhigh

findings / candidates ──► SQLite control plane ──► verifier-only CTFd submit
```

설계 원칙은 세 가지입니다.

- 모델은 CTFd 토큰을 받지 않습니다. 제출은 `SSOPHIZ_ENABLE_SUBMIT=1`인 검증기만 수행합니다.
- 워커는 문제별 작업공간과 Docker 컨테이너를 사용합니다. 기본 네트워크는 `none`입니다.
- 첫 모델의 답을 그대로 믿지 않습니다. 증거, 재현 스크립트, 후보 플래그를 분리해 저장합니다.

## 빠른 시작

PowerShell 기준입니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\scripts\ctf-harness.ps1 init
docker build -t ssophiz-ctf-worker:latest docker/worker
.\scripts\ctf-harness.ps1 doctor
```

문제를 등록하고 배치 계획을 확인합니다.

```powershell
.\scripts\ctf-harness.ps1 add --name warmup --category auto `
  --description "64-bit ELF with a buffer overflow" `
  --artifact .\challenge\chall --endpoint example.ctf:31337

.\scripts\ctf-harness.ps1 list
.\scripts\ctf-harness.ps1 plan <task_id>
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply
```

CTFd API token이 있는 경우에는 설명·카테고리를 등록합니다. 첨부파일은 검토 후 명시적으로 `--download-attachments`를 붙일 때만 같은 CTFd 호스트에서 내려받습니다.

```powershell
$env:SSOPHIZ_CTFD_URL = "https://ctf.example"
$env:SSOPHIZ_CTFD_TOKEN = "..."
.\scripts\ctf-harness.ps1 ingest-ctfd 42 --download-attachments
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply
```

기본 dispatch는 Luna low 워커 하나로 최대 세 가지 값싼 검사를 수행합니다. 선택된 경로만 wave 1의 Sol medium으로 풀고, 구체적인 blocker가 남았을 때만 wave 2의 Sol xhigh를 실행합니다.

레이스컨디션, TOCTOU, scheduler/workqueue, 실시간 게임, WebSocket, 물리 시뮬레이션 신호가 있는 문제는 fast lane으로 분류합니다. 이 경우 Luna를 생략하고 wave 0에서 Sol medium이 먼저 결정론적 PoC·반복 실행기·게임 봇을 작성하며, 모델이 요청 루프를 직접 운전하지 않습니다.

```powershell
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply --wave 1
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply --wave 2
```

DeepSeek, Kimi, Grok profile과 자동 fallback은 기본 구성에서 제거했습니다. 일반 OpenAI-compatible adapter는 사설 또는 별도 승인 provider를 수동 연결할 수 있도록 확장 지점으로만 남아 있습니다.

Ollama는 선택적인 로컬 검산 worker입니다. `ollama pull qwen3:14b` 후 API key 없이 실행할 수 있습니다.

```powershell
.\scripts\ctf-harness.ps1 provider-run <task_id> --profile ollama_local
```

Ollama는 기본 route에 포함되지 않습니다. 16GB VRAM 환경에서는 Pwn 주력 모델로 과신하지 말고, 디컴파일 요약·구조체 가설 검산·로그 교차검증처럼 병렬 가치가 큰 작업에만 수동 사용합니다.

후보를 검토한 다음에만 CTFd로 제출합니다.

```powershell
$env:SSOPHIZ_CTFD_URL = "https://ctf.example"
$env:SSOPHIZ_CTFD_TOKEN = "..."
$env:SSOPHIZ_ENABLE_SUBMIT = "1"
.\scripts\ctf-harness.ps1 submit <candidate_id>
```

## MCP 연결

MCP는 하나의 과권한 서버가 아니라 역할별 stdio 서버로 분리됩니다.

```powershell
$env:SSOPHIZ_CONFIG = "$PWD\config\harness.json"
ctf-control-mcp
```

Claude Code용 프로젝트 설정 예시는 [.mcp.json](.mcp.json)입니다. Codex에는 다음처럼 등록할 수 있습니다.

```powershell
codex mcp add ctf-control -- ctf-control-mcp
```

`ctf-control`은 작업·증거·후보를, `ctf-artifact`는 작업공간 파일을, `ctf-sandbox`는 Docker 분석 명령을 제공합니다. `ctf-verifier`는 별도 프로세스에만 연결하는 제출 전용 서버입니다. 상세 권한 표는 [docs/MCP.md](docs/MCP.md)에 있습니다.

## 모델 배치

기본값은 한 문제에 한 워커입니다. 증거가 없는 막힘이 확인될 때만 다음 wave를 시작합니다.

| 단계 | 모델 | 시작 조건 | 목적 |
|---|---|---|---|
| wave 0 | Luna, low | 항상 | 최대 세 가지 값싼 검사와 난이도·경로 분류 |
| wave 1 | Sol, medium | QUICK/SOLVE 판정 | 선택된 경로의 최소 PoC와 플래그 회수 |
| wave 2 | Sol, xhigh | 구체적 blocker | exploit 구성, 교차 분야 추론, 난제 해결 |

분야별 SKILL.md는 그대로 사용하므로 Pwn, Reverse, Web 등 전문 지침은 유지됩니다. 후속 wave는 `list_findings`와 기존 작업물을 먼저 읽고 완료된 triage를 반복하지 않습니다.

## 개발 검증

```powershell
python -m unittest discover -s tests -v
python -m compileall -q src
```

## WSL 환경

Ubuntu WSL이 정상 기동되는 PC에서는 다음 명령으로 Pwn·Reverse·Forensics 도구를 설치하고 검증합니다.

```powershell
.\scripts\setup-wsl.ps1
```

WSL 기동 자체가 멈추면 관리자 PowerShell에서 `.\scripts\repair-wsl-admin.ps1`을 실행하고 재부팅한 다음 위 설정 명령을 다시 실행합니다. 이 복구 스크립트는 배포판을 unregister하거나 데이터를 삭제하지 않습니다.

세부 경계와 운영 방식은 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md)를 참고하십시오.
