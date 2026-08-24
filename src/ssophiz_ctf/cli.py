from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .archives import ArchiveLimits, prepare_archive
from .api_worker import APIWorker
from .config import HarnessConfig, load_config
from .contracts import TaskEnvelope, classify_flag_candidate
from .ctfd import CTFdClient
from .evidence_report import build_evidence_pdf
from .hwpx import extract_hwpx_text
from .orca_runtime import OrcaRuntime, build_orca_plan
from .router import infer_category, route_task
from .state import StateStore


def _json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _config(args: argparse.Namespace) -> HarnessConfig:
    return load_config(args.config)


def _store(config: HarnessConfig) -> StateStore:
    return StateStore(config.resolve_path("state_db"))


def command_init(args: argparse.Namespace) -> int:
    destination = Path(args.config)
    example = Path("config/harness.example.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    created = False
    if not destination.exists():
        shutil.copy2(example, destination)
        created = True
    config = load_config(destination)
    config.resolve_path("workspace_root").mkdir(parents=True, exist_ok=True)
    store = _store(config)
    store.close()
    _json({"config": str(destination), "created": created, "state_db": str(config.resolve_path("state_db"))})
    return 0


def _version(command: str, *args: str) -> dict[str, Any]:
    path = shutil.which(command)
    if not path:
        return {"available": False}
    try:
        completed = subprocess.run(
            [path, *args],
            text=True,
            errors="replace",
            capture_output=True,
            check=False,
            timeout=15,
        )
    except subprocess.TimeoutExpired:
        return {"available": False, "path": path, "error": "version check timed out"}
    output = (completed.stdout or completed.stderr).splitlines()
    return {"available": completed.returncode == 0, "path": path, "version": output[0] if output else ""}


def command_doctor(args: argparse.Namespace) -> int:
    config = _config(args)
    project_root = config.path.parent.parent
    project_venv = (project_root / ".venv").resolve()
    checks = {
        "python": {"available": sys.version_info >= (3, 11), "version": sys.version.split()[0]},
        "project_venv": {
            "available": Path(sys.executable).resolve().is_relative_to(project_venv),
            "python": str(Path(sys.executable).resolve()),
            "expected_root": str(project_venv),
        },
        "docker": _version("docker", "--version"),
        "orca": _version(str(config.data["orca"]["executable"]), "--version"),
        "codex": _version("codex", "--version"),
        "claude": _version("claude", "--version"),
        "ollama": _version("ollama", "--version"),
        "wsl": _version("wsl", "--version"),
        "worker_image": {"available": False, "name": config.runtime["worker_image"]},
    }
    if checks["docker"]["available"]:
        completed = subprocess.run(
            ["docker", "image", "inspect", str(config.runtime["worker_image"])],
            capture_output=True,
            check=False,
            timeout=20,
        )
        checks["worker_image"]["available"] = completed.returncode == 0
    required_ok = all(
        checks[name]["available"]
        for name in ("python", "project_venv", "docker", "orca", "codex", "worker_image")
    )
    _json({"ok": required_ok, "checks": checks})
    return 0 if required_ok else 1


def command_add(args: argparse.Namespace) -> int:
    provisional = _register_task(args)
    _json(provisional.to_dict())
    return 0


def command_prepare_archive(args: argparse.Namespace) -> int:
    destination = Path(args.destination).resolve() if args.destination else None
    result = prepare_archive(
        Path(args.source).resolve(),
        destination,
        limits=ArchiveLimits(max_depth=args.max_depth),
    )
    _json(result)
    return 0


def command_extract_hwpx(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve() if args.output else None
    _json(extract_hwpx_text(Path(args.source).resolve(), output))
    return 0


def command_classify_flag(args: argparse.Namespace) -> int:
    _json(classify_flag_candidate(args.value).to_dict())
    return 0


def _register_task(args: argparse.Namespace) -> TaskEnvelope:
    config = _config(args)
    artifacts = [str(Path(item).resolve()) for item in args.artifact]
    description = args.description
    if args.description_file:
        description = Path(args.description_file).read_text(encoding="utf-8")
    category = infer_category(description, artifacts) if args.category == "auto" else args.category
    root = config.resolve_path("workspace_root")
    provisional = TaskEnvelope.create(
        name=args.name,
        category=category,
        description=description,
        workspace=str(root / "pending"),
        endpoints=args.endpoint,
        platform_challenge_id=args.challenge_id,
        timeout_minutes=args.timeout,
        allow_target_operations=bool(getattr(args, "enable_target_operations", False)),
    )
    workspace = root / provisional.id
    provisional.workspace = str(workspace)
    artifact_dir = workspace / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for source_name in artifacts:
        source = Path(source_name)
        if not source.is_file():
            raise FileNotFoundError(source)
        target = artifact_dir / source.name
        shutil.copy2(source, target)
        copied.append(str(target.relative_to(workspace)))
    provisional.artifacts = copied
    role = category
    provisional.skills = [f"ctf-{category}"]
    configured_roles = config.data.get("mcp_roles", {})
    provisional.allowed_mcp = list(configured_roles.get(role, ["ctf-control", "ctf-artifact", "ctf-sandbox"]))
    store = _store(config)
    try:
        store.add_task(provisional, "ready")
    finally:
        store.close()
    return provisional


def command_ingest_ctfd(args: argparse.Namespace) -> int:
    config = _config(args)
    client = CTFdClient.from_config(config.data["ctfd"])
    challenge = client.get_challenge(args.challenge_id)
    description = str(challenge.get("description") or "No description supplied by CTFd.")
    category = infer_category(description, [str(item) for item in challenge.get("files") or []])
    files = [str(item) for item in challenge.get("files") or [] if isinstance(item, str)]
    connection_info = str(challenge.get("connection_info") or challenge.get("connection") or "").strip()
    namespace = argparse.Namespace(
        config=args.config,
        name=str(challenge.get("name") or f"challenge-{args.challenge_id}"),
        category=category,
        description=description,
        description_file="",
        artifact=[],
        endpoint=[connection_info] if connection_info else [],
        challenge_id=args.challenge_id,
        timeout=args.timeout,
        enable_target_operations=False,
    )
    task = _register_task(namespace)
    downloaded: list[str] = []
    artifact_root = Path(task.workspace) / "artifacts"
    selected_files = files if args.download_attachments else []
    for index, file_url in enumerate(selected_files, start=1):
        parsed = urllib.parse.urlparse(file_url)
        filename = Path(parsed.path).name or f"attachment-{index}"
        safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in filename)
        target = artifact_root / safe_name
        client.download_attachment(file_url, target)
        downloaded.append(str(target.relative_to(task.workspace)))
    if downloaded:
        task.artifacts = downloaded
        store = _store(config)
        try:
            store.add_task(task, "ready")
        finally:
            store.close()
    _json({"task": task.to_dict(), "downloaded": downloaded})
    return 0


def command_list(args: argparse.Namespace) -> int:
    store = _store(_config(args))
    try:
        rows = store.list_tasks(args.status or None)
        for row in rows:
            payload = json.loads(row.pop("payload"))
            row["name"] = payload["name"]
        _json(rows)
    finally:
        store.close()
    return 0


def command_show(args: argparse.Namespace) -> int:
    store = _store(_config(args))
    try:
        _json(
            {
                "task": store.get_task(args.task_id).to_dict(),
                "evidence_ledger": store.list_ledger_entries(args.task_id),
                "findings": store.list_findings(args.task_id),
                "candidates": store.list_candidates(args.task_id),
            }
        )
    finally:
        store.close()
    return 0


def command_evidence_pdf(args: argparse.Namespace) -> int:
    store = _store(_config(args))
    try:
        _json(build_evidence_pdf(store, args.output, task_ids=args.task_id or None))
    finally:
        store.close()
    return 0


def command_plan(args: argparse.Namespace) -> int:
    config = _config(args)
    store = _store(config)
    try:
        task = store.get_task(args.task_id)
    finally:
        store.close()
    assignments = route_task(task, config)
    commands = build_orca_plan(task, assignments, str(config.data["orca"]["executable"]))
    _json(
        {
            "task": task.to_dict(),
            "assignments": assignments,
            "orca_commands": [{"purpose": item.purpose, "argv": item.argv} for item in commands],
            "note": "Each Orca specialist receives a distinct Orca task. API/Ollama reviewers start only with --with-api-workers.",
        }
    )
    return 0


def _find_id(payload: Any, keys: tuple[str, ...]) -> str | None:
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, str):
                return value
        for value in payload.values():
            found = _find_id(value, keys)
            if found:
                return found
    if isinstance(payload, list):
        for value in payload:
            found = _find_id(value, keys)
            if found:
                return found
    return None


def _created_orca_task_id(receipt: dict[str, Any]) -> str | None:
    """Return the created orchestration task id, not the receipt request id."""
    result = receipt.get("result")
    if isinstance(result, dict):
        task = result.get("task")
        if isinstance(task, dict) and isinstance(task.get("id"), str):
            return str(task["id"])
    return _find_id(receipt, ("taskId", "task_id"))


def _spawn_provider(task: TaskEnvelope, config: HarnessConfig, profile_name: str, reason: str) -> dict[str, Any]:
    profile = config.profiles.get(profile_name)
    if not profile:
        return {"profile": profile_name, "started": False, "reason": "unknown profile"}
    adapter = str(profile.get("adapter", ""))
    if adapter not in {"openai_compatible", "ollama"}:
        return {"profile": profile_name, "started": False, "reason": f"unsupported fallback adapter {adapter}"}
    key_env = str(profile.get("api_key_env", ""))
    if adapter != "ollama" and not os.getenv(key_env):
        return {"profile": profile_name, "started": False, "reason": f"missing {key_env}"}
    if adapter == "ollama":
        models_url = f"{str(profile.get('base_url', '')).rstrip('/')}/models"
        try:
            with urllib.request.urlopen(models_url, timeout=3) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
        except (OSError, RuntimeError, urllib.error.URLError) as exc:
            return {"profile": profile_name, "started": False, "reason": f"Ollama unavailable: {exc}"}
    image = str(config.runtime["worker_image"])
    try:
        image_check = subprocess.run(["docker", "image", "inspect", image], capture_output=True, check=False, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return {"profile": profile_name, "started": False, "reason": f"worker image check failed: {exc}"}
    if image_check.returncode != 0:
        return {"profile": profile_name, "started": False, "reason": f"worker image is not available: {image}"}

    log_root = Path(task.workspace) / "logs"
    log_root.mkdir(parents=True, exist_ok=True)
    stdout_path = log_root / f"{profile_name}.stdout.log"
    stderr_path = log_root / f"{profile_name}.stderr.log"
    command = [
        sys.executable,
        "-m",
        "ssophiz_ctf",
        "--config",
        str(config.path),
        "provider-run",
        task.id,
        "--profile",
        profile_name,
    ]
    popen_options: dict[str, Any] = {"cwd": str(config.path.parent.parent)}
    if os.name == "nt":
        popen_options["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    stdout_handle = stdout_path.open("ab")
    stderr_handle = stderr_path.open("ab")
    try:
        process = subprocess.Popen(command, stdout=stdout_handle, stderr=stderr_handle, **popen_options)
    finally:
        stdout_handle.close()
        stderr_handle.close()
    store = _store(config)
    try:
        store.record_event(
            task.id,
            "external_worker_started",
            {"profile": profile_name, "pid": process.pid, "reason": reason},
        )
        store.connection.commit()
    finally:
        store.close()
    return {
        "profile": profile_name,
        "started": True,
        "pid": process.pid,
        "reason": reason,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def _launch_failover(task: TaskEnvelope, config: HarnessConfig, failed_profile: str, reason: str) -> dict[str, Any]:
    failover = config.data.get("failover", {})
    if not failover.get("enabled", False):
        return {"started": False, "reason": "failover disabled", "attempts": []}
    attempts: list[dict[str, Any]] = []
    for profile_name in failover.get("routes", {}).get(task.category, []):
        if profile_name == failed_profile:
            continue
        receipt = _spawn_provider(task, config, str(profile_name), f"failover from {failed_profile}: {reason}")
        attempts.append(receipt)
        if receipt.get("started"):
            return {"started": True, "selected": profile_name, "attempts": attempts}
    return {"started": False, "reason": "no configured fallback was available", "attempts": attempts}


def _find_orca_task(payload: Any, task_id: str) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        if payload.get("id") == task_id and isinstance(payload.get("spec"), str):
            return payload
        for value in payload.values():
            found = _find_orca_task(value, task_id)
            if found:
                return found
    elif isinstance(payload, list):
        for value in payload:
            found = _find_orca_task(value, task_id)
            if found:
                return found
    return None


def command_dispatch(args: argparse.Namespace) -> int:
    config = _config(args)
    store = _store(config)
    try:
        task = store.get_task(args.task_id)
    finally:
        store.close()
    assignments = route_task(task, config)
    if not args.apply:
        return command_plan(args)
    runtime = OrcaRuntime(str(config.data["orca"]["executable"]))
    run_receipt = runtime.create_run(f"Solve and validate: {task.name}")
    worker_receipts: list[dict[str, Any]] = []
    external_receipts: list[dict[str, Any]] = []
    worker_start_failed = False
    for assignment in assignments:
        if assignment["adapter"] != "orca":
            continue
        task_receipt = runtime.create_worker_task(task, assignment)
        orca_task_id = _created_orca_task_id(task_receipt)
        if not orca_task_id:
            raise RuntimeError(f"Could not find Orca task id in receipt: {task_receipt}")
        try:
            worker_receipt = runtime.start_worker(orca_task_id, assignment)
            worker_receipts.append({"assignment": assignment, "task": task_receipt, "worker": worker_receipt})
        except RuntimeError as exc:
            worker_start_failed = True
            failover = _launch_failover(task, config, str(assignment["profile"]), str(exc))
            worker_receipts.append({"assignment": assignment, "task": task_receipt, "error": str(exc), "failover": failover})
    if args.with_api_workers:
        for assignment in assignments:
            if assignment["adapter"] not in {"openai_compatible", "ollama"}:
                continue
            receipt = _spawn_provider(task, config, str(assignment["profile"]), "explicit parallel reviewer")
            external_receipts.append({"assignment": assignment, **receipt})
    _json({"run": run_receipt, "workers": worker_receipts, "external_workers": external_receipts})
    return 1 if worker_start_failed else 0


def command_rescue(args: argparse.Namespace) -> int:
    config = _config(args)
    store = _store(config)
    try:
        task = store.get_task(args.task_id)
    finally:
        store.close()
    _json(_launch_failover(task, config, args.failed_profile, args.reason))
    return 0


def command_supervise(args: argparse.Namespace) -> int:
    config = _config(args)
    runtime = OrcaRuntime(str(config.data["orca"]["executable"]))
    delivery = runtime.check_wait(args.timeout_seconds * 1000)
    result = delivery.get("result", {})
    messages = list(result.get("messages") or [])
    receipts: list[dict[str, Any]] = []
    requires_attention = False
    task_listing: dict[str, Any] | None = None
    for message in messages:
        message_type = str(message.get("type") or "")
        if message_type in {"question", "escalation"}:
            requires_attention = True
            receipts.append({"message": message, "action": "requires coordinator attention"})
            continue
        raw_payload = message.get("payload") or {}
        payload = raw_payload if isinstance(raw_payload, dict) else json.loads(str(raw_payload))
        dispatch_id = str(payload.get("dispatchId") or "")
        orca_task_id = str(payload.get("taskId") or "")
        outcome = str(payload.get("outcome") or "")
        receipt: dict[str, Any] = {"message": message, "outcome": outcome}
        if outcome == "failed" and orca_task_id:
            task_listing = task_listing or runtime.task_list()
            row = _find_orca_task(task_listing, orca_task_id)
            if row:
                try:
                    spec = json.loads(str(row["spec"]))
                    local_task_id = str(spec["control_task_id"])
                    failed_profile = str(spec.get("worker", {}).get("profile", "codex"))
                    store = _store(config)
                    try:
                        local_task = store.get_task(local_task_id)
                    finally:
                        store.close()
                    receipt["failover"] = _launch_failover(local_task, config, failed_profile, str(message.get("body") or "worker failed"))
                except (KeyError, ValueError, json.JSONDecodeError) as exc:
                    receipt["failover_error"] = f"{type(exc).__name__}: {exc}"
        if dispatch_id:
            receipt["release"] = runtime.release_worker(dispatch_id)
        receipts.append(receipt)
    delivery_id = str(result.get("deliveryId") or "")
    acknowledgement = None
    if delivery_id and not requires_attention:
        acknowledgement = runtime.acknowledge(delivery_id)
    _json({"delivery": delivery, "actions": receipts, "acknowledgement": acknowledgement, "requires_attention": requires_attention})
    return 0


def command_provider_run(args: argparse.Namespace) -> int:
    config = _config(args)
    profile = config.profiles.get(args.profile)
    if not profile:
        raise KeyError(f"Unknown profile: {args.profile}")
    if profile.get("adapter") not in {"openai_compatible", "ollama"}:
        raise ValueError("provider-run requires an openai_compatible or ollama profile")
    store = _store(config)
    try:
        task = store.get_task(args.task_id)
        worker = APIWorker(task, args.profile, profile, store, config.runtime)
        _json(worker.run())
    finally:
        store.close()
    return 0


def command_submit(args: argparse.Namespace) -> int:
    if os.getenv("SSOPHIZ_ENABLE_SUBMIT") != "1":
        raise PermissionError("Set SSOPHIZ_ENABLE_SUBMIT=1 in the verifier environment")
    config = _config(args)
    store = _store(config)
    try:
        candidate = store.get_candidate(args.candidate_id)
        if not store.candidate_has_reproduction(args.candidate_id):
            raise ValueError("Candidate has no attached reproduction evidence")
        classification = classify_flag_candidate(str(candidate["value"]))
        if not classification.submit_eligible:
            raise ValueError(f"Candidate is classified as {classification.kind}; refusing submission")
        task = store.get_task(candidate["task_id"])
        if task.platform_challenge_id is None:
            raise ValueError("Task has no CTFd challenge id")
        result = CTFdClient.from_config(config.data["ctfd"]).submit_flag(task.platform_challenge_id, candidate["value"])
        store.update_candidate(args.candidate_id, result.status, result.message)
        if result.status == "correct":
            store.update_task_status(task.id, "completed")
        _json({"status": result.status, "message": result.message})
    finally:
        store.close()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctf-harness", description="Orca-backed multi-model CTF validation harness")
    parser.add_argument("--config", default="config/harness.json")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Create local config and state database")
    init.set_defaults(func=command_init)

    doctor = sub.add_parser("doctor", help="Check the workstation runtime")
    doctor.set_defaults(func=command_doctor)

    archive = sub.add_parser("prepare-archive", help="Safely inventory or extract a nested archive")
    archive.add_argument("source")
    archive.add_argument("--destination", default="", help="Persist extraction and provenance under a new path")
    archive.add_argument("--max-depth", type=int, default=4)
    archive.set_defaults(func=command_prepare_archive)

    hwpx = sub.add_parser("extract-hwpx", help="Extract text from HWPX section XML")
    hwpx.add_argument("source")
    hwpx.add_argument("--output", default="")
    hwpx.set_defaults(func=command_extract_hwpx)

    classify = sub.add_parser("classify-flag", help="Classify a candidate versus mock/test placeholders")
    classify.add_argument("value")
    classify.set_defaults(func=command_classify_flag)

    add = sub.add_parser("add", help="Register one authorized CTF challenge")
    add.add_argument("--name", required=True)
    add.add_argument("--category", choices=["auto", "pwn", "reverse", "malware", "web", "crypto", "forensics", "misc"], default="auto")
    add.add_argument("--description", default="")
    add.add_argument("--description-file", default="")
    add.add_argument("--artifact", action="append", default=[])
    add.add_argument("--endpoint", action="append", default=[])
    add.add_argument("--challenge-id", type=int)
    add.add_argument("--timeout", type=int, default=12)
    add.add_argument(
        "--enable-target-operations",
        action="store_true",
        help="Explicitly permit scope-checked web target requests for this task",
    )
    add.set_defaults(func=command_add)

    ingest = sub.add_parser("ingest-ctfd", help="Register CTFd challenge metadata")
    ingest.add_argument("challenge_id", type=int)
    ingest.add_argument("--timeout", type=int, default=12)
    ingest.add_argument("--download-attachments", action="store_true", help="Download same-origin challenge attachments after metadata review")
    ingest.set_defaults(func=command_ingest_ctfd)

    task_list = sub.add_parser("list", help="List local tasks")
    task_list.add_argument("--status", default="")
    task_list.set_defaults(func=command_list)

    show = sub.add_parser("show", help="Show task evidence and candidates")
    show.add_argument("task_id")
    show.set_defaults(func=command_show)

    report = sub.add_parser("evidence-pdf", help="Batch-render compact challenge evidence into one final PDF")
    report.add_argument(
        "--output",
        default="output/pdf/ctf-evidence-ledger.pdf",
        help="Destination PDF path",
    )
    report.add_argument(
        "--task-id",
        action="append",
        default=[],
        help="Include only this task (repeatable); default includes every task",
    )
    report.set_defaults(func=command_evidence_pdf)

    plan = sub.add_parser("plan", help="Compile a task into worker assignments")
    plan.add_argument("task_id")
    plan.set_defaults(func=command_plan)

    dispatch = sub.add_parser("dispatch", help="Create an Orca run and start every configured Orca specialist")
    dispatch.add_argument("task_id")
    dispatch.add_argument("--apply", action="store_true", help="Actually create the Orca run and workers")
    dispatch.add_argument("--with-api-workers", action="store_true", help="Also start configured API/Ollama workers; this can consume provider credits")
    dispatch.set_defaults(func=command_dispatch)

    rescue = sub.add_parser("rescue", help="Start the first available configured non-Codex fallback")
    rescue.add_argument("task_id")
    rescue.add_argument("--failed-profile", default="codex")
    rescue.add_argument("--reason", default="manual rescue")
    rescue.set_defaults(func=command_rescue)

    supervise = sub.add_parser("supervise", help="Process one Orca completion batch and fail over failed Codex workers")
    supervise.add_argument("--timeout-seconds", type=int, default=60)
    supervise.set_defaults(func=command_supervise)

    provider = sub.add_parser("provider-run", help="Run an OpenAI-compatible model in the Docker tool loop")
    provider.add_argument("task_id")
    provider.add_argument("--profile", required=True)
    provider.set_defaults(func=command_provider_run)

    submit = sub.add_parser("submit", help="Submit one queued candidate through the verifier")
    submit.add_argument("candidate_id")
    submit.set_defaults(func=command_submit)
    return parser


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.func(args))
    except (FileNotFoundError, KeyError, PermissionError, RuntimeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
