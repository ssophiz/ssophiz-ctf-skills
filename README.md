# SSophiz CTF Skills and Harness

Reusable, evidence-driven agent skills and a local orchestration harness for
authorized CTF competitions. The public repository deliberately excludes
flags, credentials, pairing codes, live event workspaces, and raw challenge
artifacts.

## Agent skills

The `skills/` directory follows the `SKILL.md` frontmatter convention used by
Codex and other compatible agents. It contains category workers for Crypto,
Forensics, Malware, Misc, Pwn, Reverse, and Web, plus orchestration and
post-event distillation skills.

Install a skill by copying or linking its directory into your agent's skill
discovery path. For example, on Windows:

```powershell
Copy-Item -Recurse .\skills\reverse "$env:USERPROFILE\.codex\skills\ssophiz-ctf-reverse"
Copy-Item -Recurse .\skills\reverse "$env:USERPROFILE\.agents\skills\ssophiz-ctf-reverse"
```

The sanitized [CCE 2026 retrospective](docs/CCE2026_POSTMORTEM.md) records the
operational lessons used to strengthen these skills without publishing any
challenge answers.

## Optional context-efficiency tools

Ponytail and Graphify can be installed reproducibly for Codex and this project:

```powershell
.\scripts\install-agent-efficiency-tools.ps1
```

Ponytail discourages unnecessary implementation and Graphify provides a local
AST-backed project graph that can be queried before reading many files. See
[docs/AGENT_EFFICIENCY.md](docs/AGENT_EFFICIENCY.md) for activation, privacy,
and token-measurement guidance. Pinned source versions are recorded in
[config/agent-tools.lock.json](config/agent-tools.lock.json).

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
  TaskEnvelope ──► category router ──► Orca wave 0 (Codex)
       │                                  │
       │                                  ├─ pwn / reverse / web skill
       │                                  └─ evidence + candidate
       │
       └────────────────────────────► wave 1 API worker
                                          DeepSeek / Kimi / Grok
                                                  │
                                                  ▼
                                     Docker isolated tool loop

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
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply --with-api-workers
```

Codex worker가 시작하지 못하면 설정된 중국계 fallback 순서에서 첫 번째 사용 가능한 provider를 자동 실행합니다. 실행 이후의 실패까지 감시하려면 Orca를 시작한 coordinator 터미널에서 supervisor를 계속 호출합니다.

```powershell
while ($true) { .\scripts\ctf-harness.ps1 supervise --timeout-seconds 60 }
```

현재 fallback 우선순위는 Kimi K3 → DeepSeek → 로컬 Ollama입니다. 이 선택은 2026-08 시점 독립 벤치마크의 중국계 모델군 순위를 기준으로 하되, 실제 Kimi API model ID와 reasoning tier는 사용하는 계정의 최신 문서에 맞춰야 합니다. API key와 Docker worker image가 실제로 준비된 provider만 선택됩니다. 수동 전환은 `.\scripts\ctf-harness.ps1 rescue <task_id>`입니다.

`dispatch --apply`는 분야별 Codex 전문 워커를 각각 별도 Orca task로 동시에 시작합니다. API/Ollama 독립 검증자도 함께 시작하려면 비용·키 사용을 명시하는 `--with-api-workers`를 붙입니다.

```powershell
.\scripts\ctf-harness.ps1 dispatch <task_id> --apply --with-api-workers
```

```powershell
$env:DEEPSEEK_API_KEY = "..."
.\scripts\ctf-harness.ps1 provider-run <task_id> --profile deepseek_exploit
```

Ollama는 선택적인 로컬 검산 worker입니다. `ollama pull qwen3:14b` 후 API key 없이 실행할 수 있습니다.

```powershell
.\scripts\ctf-harness.ps1 provider-run <task_id> --profile ollama_local
```

기본 route에서는 Misc 2차 검산에만 넣었습니다. 16GB VRAM 환경에서는 Pwn 주력 모델로 과신하지 말고, 디컴파일 요약·구조체 가설 검산·로그 교차검증처럼 병렬 가치가 큰 작업에 쓰는 편이 낫습니다.

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

기본값은 강한 Codex 워커를 wave 0에 두고, 서로 다른 계열 모델을 wave 1 독립 검증자로 둡니다.

| 분야 | wave 0 | wave 1 | 핵심 도구 |
|---|---|---|---|
| Pwn | Codex Sol | DeepSeek | pwntools, gdb, checksec, ROPgadget |
| Reverse | Codex Sol | Kimi | Ghidra headless, radare2, gdb, angr |
| Web | Codex Terra | Grok | curl, Chromium, mitmproxy, nuclei templates |

모델·API 이름은 공급자 변경이 잦으므로 [config/harness.example.json](config/harness.example.json)에서 실제 계정에 맞게 수정해야 합니다. 외부 모델에 보내면 안 되는 문제는 해당 profile을 route에서 제거하십시오.

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
