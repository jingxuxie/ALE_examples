import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

from isolation import bubblewrap_command, clean_environment, landlock_status, run_bounded, submission_command, validate_pair


AUTHORING = Path(__file__).resolve().parent
RUNNER = Path("/home/xuandong/mnt/jingxu/ALE/run_allowlisted_codex.sh")
RUNNER_SHA256 = "06f4693741de6587283d2cf78d91895e5a74c1230c9960b5457f8cc536cf0394"
INSTALLED_CODEX = Path("/home/xuandong/.local/bin/codex")
MODEL = "ultima-alpha"
DISABLED_FEATURES = (
    "apps", "browser_use", "browser_use_external", "browser_use_full_cdp_access",
    "chronicle", "code_mode", "code_mode_host", "computer_use", "goals", "hooks",
    "image_generation", "js_repl", "memories", "multi_agent", "multi_agent_v2",
    "plugins", "plugin_sharing", "recommended_plugins", "remote_plugin", "shell_snapshot",
    "shell_snapshot_v2", "skill_search", "skill_mcp_dependency_install", "standalone_web_search",
    "tool_suggest", "workspace_dependencies",
)
GUARDRAIL = "You are a fresh independent coding agent. Use only the supplied participant files and local computation. Do not access prior sessions, memories, evaluator material, other agents, or the internet. Write deliverables only to the supplied output directory."


def digest(path):
    with open(path, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else digest_stream(stream)


def digest_stream(stream):
    hasher = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        hasher.update(block)
    return hasher.hexdigest()


def write_json(path, value):
    with open(path, "x") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def toml_value(value):
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, list):
        return "[" + ",".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(key) + "=" + toml_value(item) for key, item in value.items()) + "}"
    raise ValueError("Unsupported configuration value")


def new_root(label):
    os.umask(0o077)
    if digest(RUNNER) != RUNNER_SHA256:
        raise ValueError("The provided runner changed; re-audit it instead of silently proceeding")
    return Path(tempfile.mkdtemp(prefix=f"isolation_{label}_", dir=AUTHORING)).resolve()


def build_runtime(root):
    source_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).resolve(strict=True)
    with (source_home / "config.toml").open("rb") as stream:
        source = tomllib.load(stream)
    if source.get("model_provider", "openai") != "openai" or source.get("model_providers"):
        raise ValueError("Custom providers require a separate credential/configuration audit")
    home = root / "codex-home"
    package = home / "packages" / "standalone" / "current"
    (home / "tmp" / "arg0" / "pinned").mkdir(parents=True, mode=0o700)
    originals = INSTALLED_CODEX.resolve(strict=True).parent.parent
    hashes = {}
    for relative in ("bin/codex", "codex-resources/bwrap", "codex-path/rg"):
        original = originals / relative
        with original.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ValueError(f"Expected a native runtime executable: {relative}")
        target = package / ("codex-resources/bwrap.real" if relative == "codex-resources/bwrap" else relative)
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        subprocess.run(["/bin/cp", "--reflink=auto", "--", str(original), str(target)], check=True, timeout=90)
        target.chmod(0o500)
        hashes[relative] = digest(target)
    adapter = package / "codex-resources" / "bwrap"
    shutil.copyfile(AUTHORING / "isolation_bwrap.py", adapter)
    adapter.chmod(0o500)
    hashes["codex-resources/bwrap-adapter"] = digest(adapter)
    (home / "tmp" / "arg0" / "pinned" / "bwrap").symlink_to(adapter)
    binary = package / "bin" / "codex"
    for name in ("apply_patch", "codex-linux-sandbox"):
        (home / "tmp" / "arg0" / "pinned" / name).symlink_to(binary)
    with (source_home / "auth.json").open() as stream:
        original_auth = json.load(stream)
    authentication = {key: original_auth[key] for key in ("auth_mode", "OPENAI_API_KEY", "last_refresh") if key in original_auth}
    if isinstance(original_auth.get("tokens"), dict):
        authentication["tokens"] = {key: value for key, value in original_auth["tokens"].items() if key in {"id_token", "access_token", "refresh_token", "account_id"}}
    if not authentication.get("OPENAI_API_KEY") and not authentication.get("tokens", {}).get("access_token"):
        raise ValueError("No supported file-based credentials; no parent environment fallback is permitted")
    write_json(home / "auth.json", authentication)
    environment = clean_environment()
    environment.update({
        "HOME": str(home), "CODEX_HOME": str(home),
        "PATH": f"{home / 'tmp' / 'arg0' / 'pinned'}:{package / 'bin'}:{package / 'codex-path'}:/usr/bin:/bin",
    })
    shell_environment = clean_environment()
    shell_environment["PATH"] = environment["PATH"]
    shell_environment["CODEX_HOME"] = str(home)
    config = {
        "model": MODEL, "approval_policy": "never", "web_search": "disabled",
        "default_permissions": "benchmark", "allow_login_shell": False,
        "project_doc_max_bytes": 0, "cli_auth_credentials_store": "file",
        "check_for_update_on_startup": False, "history": {"persistence": "none"},
        "memories": {"generate_memories": False, "use_memories": False},
        "features": {name: False for name in DISABLED_FEATURES},
        "mcp_servers": {}, "plugins": {},
        "shell_environment_policy": {"inherit": "none", "set": shell_environment},
        "permissions": {"benchmark": {"network": {"enabled": False}}},
    }
    if source.get("model_reasoning_effort"):
        config["model_reasoning_effort"] = source["model_reasoning_effort"]
    catalog_path = Path(source["model_catalog_json"])
    if not catalog_path.is_absolute():
        catalog_path = source_home / catalog_path
    catalog = json.loads(catalog_path.read_text())
    matching = [entry for entry in catalog["models"] if entry.get("slug") == MODEL]
    if len(matching) != 1:
        raise ValueError("Expected exactly one ultima-alpha metadata entry")
    keys = {
        "slug", "display_name", "default_reasoning_level", "supported_reasoning_levels",
        "shell_type", "visibility", "supported_in_api", "priority", "support_verbosity",
        "context_window", "truncation_policy", "effective_context_window_percent",
    }
    model = {key: value for key, value in matching[0].items() if key in keys}
    model.update({"description": "Fresh isolated local participant", "base_instructions": GUARDRAIL, "experimental_supported_tools": []})
    write_json(home / "model-catalog.json", {"models": [model]})
    config["model_catalog_json"] = str(home / "model-catalog.json")
    with (home / "config.toml").open("x") as stream:
        stream.write("\n".join(f"{key} = {toml_value(value)}" for key, value in config.items()) + "\n")
    write_json(root / "runtime-audit.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(), "model": MODEL,
        "runner_sha256": digest(RUNNER), "runtime_sha256": hashes,
        "source_state_copied": ["allowlisted authentication fields", "sanitized single-model metadata", "three native ELF runtime files", "reasoning effort scalar"],
        "sessions_memories_logs_skills_plugins_copied": False,
        "credential_values_recorded": False, "landlock": landlock_status(),
        "network_adapter": "Explicit seccomp-denied networking instead of network namespace setup; all bubblewrap filesystem arguments and native filters retained",
        "initial_home_entries": sorted(str(path.relative_to(home)) for path in home.rglob("*")),
    })
    return {"home": home, "binary": binary, "environment": environment}


def discard_runtime(home):
    if home.name != "codex-home" or home.parent.parent != AUTHORING or not home.parent.name.startswith("isolation_") or home.is_symlink():
        raise ValueError("Refusing cleanup outside a task-local generated runtime")
    if home.exists():
        shutil.rmtree(home)
        write_json(home.parent / "runtime-cleanup.json", {"runtime_home_deleted": True, "credentials_retained": False})


def prepare_runtime(root):
    try:
        return build_runtime(root)
    except BaseException:
        discard_runtime(root / "codex-home")
        raise


def controller_command(runtime, participant, output, command):
    home = runtime["home"]
    return bubblewrap_command([
        (RUNNER.resolve(), RUNNER, False),
        (participant, participant, False), (output, output, True),
        (home, home, True), (home / "packages", home / "packages", False),
    ], participant, command, network=True)


def run_controller(runtime, participant, output, command, seconds, log_path):
    try:
        return run_bounded(controller_command(runtime, participant, output, command), runtime["environment"], seconds, log_path)
    finally:
        discard_runtime(runtime["home"])


def benchmark_options(runtime, participant, output):
    home = runtime["home"]
    filesystem = {
        ":minimal": "read", str(participant): "read", str(output): "write",
        str(home / "packages"): "read", str(home / "tmp" / "arg0"): "read",
        str(runtime["binary"]): "read",
    }
    return [
        "--model", MODEL,
        "-c", "permissions.benchmark.filesystem=" + toml_value(filesystem),
        "-c", 'default_permissions="benchmark"', "-c", 'approval_policy="never"',
        "-c", 'web_search="disabled"',
    ]


def fixture(root, host_port):
    participant = root / "participant"
    output = root / "output"
    participant.mkdir()
    output.mkdir()
    hidden = root / "evaluator" / "hidden"
    sibling = root / "sibling-output"
    hidden.mkdir(parents=True)
    sibling.mkdir()
    (hidden / "canary.txt").write_text("HIDDEN_PREFLIGHT_CANARY\n")
    (sibling / "canary.txt").write_text("SIBLING_PREFLIGHT_CANARY\n")
    (participant / "public.txt").write_text("PUBLIC_PREFLIGHT_ONLY\n")
    shutil.copyfile(AUTHORING / "isolation_probe.py", participant / "isolation_probe.py")
    write_json(participant / "probe-input.json", {
        "host_port": host_port,
        "forbidden_files": [str(hidden / "canary.txt"), str(sibling / "canary.txt")],
        "forbidden_open_files": [
            str(root / "codex-home" / "auth.json"), str(root / "codex-home" / "config.toml"),
            str(root / "runtime-audit.json"), str(root / "agent.log"), str(root / "sandbox.log"),
            str(AUTHORING / "qulacs.pdf"), str(RUNNER),
            "/srv/home/xuandong/.codex/auth.json", "/srv/home/xuandong/.codex/config.toml",
            "/home/xuandong/.codex/auth.json", "/home/xuandong/.codex/config.toml",
        ],
        "forbidden_directories": [str(hidden), str(sibling), "/home/xuandong/.codex/sessions", "/srv/home/xuandong/.codex/sessions"],
    })
    return participant, output


def record_result(root, result, output):
    probe_path = output / "probe-result.json"
    probe = json.loads(probe_path.read_text()) if probe_path.is_file() else None
    passed = result["returncode"] == 0 and not result["remaining_owned_descendants"] and bool(probe and probe.get("passed"))
    result.update({"scientific_attempt": False, "probe_passed": passed, "root": str(root)})
    write_json(root / "result.json", result)
    print(json.dumps(result), flush=True)
    return passed


def preflight(agent_smoke):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(8)
        port = listener.getsockname()[1]
        root = new_root("submission_preflight")
        participant, output = fixture(root, port)
        command = submission_command(participant, output, ["/usr/bin/python3", "-I", participant / "isolation_probe.py", participant, output])
        result = run_bounded(command, clean_environment(), 90, root / "submission.log")
        if not record_result(root, result, output):
            return 1
        root = new_root("runner_preflight")
        participant, output = fixture(root, port)
        runtime = prepare_runtime(root)
        command = [str(runtime["binary"])] + benchmark_options(runtime, participant, output) + [
            "sandbox", "--permission-profile", "benchmark", "--cd", str(participant),
            "--", "/usr/bin/python3", "-I", str(participant / "isolation_probe.py"), str(participant), str(output),
        ]
        write_json(root / "invocation.json", {"command": command, "scientific_attempt": False, "note": "codex sandbox rejects --strict-config; the unchanged runner retains it for codex exec"})
        result = run_controller(runtime, participant, output, command, 90, root / "sandbox.log")
        if not record_result(root, result, output):
            return 1
        if agent_smoke:
            root = new_root("agent_smoke")
            participant, output = fixture(root, port)
            runtime = prepare_runtime(root)
            prompt = (
                "Infrastructure preflight only, NOT a scientific attempt. Execute exactly this command with the shell tool: "
                f"/usr/bin/python3 -I {participant}/isolation_probe.py {participant} {output} . "
                "Do not change it, inspect any other files, or solve any scientific task. "
                "When the command finishes, report PROBE_PASS only if it exited zero; otherwise report PROBE_FAIL."
            )
            command = [str(RUNNER), "--model", MODEL, "--task-read-only", str(participant), str(output), prompt]
            write_json(root / "invocation.json", {"command": command, "limit_seconds": 240, "output_initially_empty": not any(output.iterdir()), "scientific_attempt": False})
            result = run_controller(runtime, participant, output, command, 240, root / "agent.log")
            if not record_result(root, result, output):
                return 1
    return 0


def run_attempt(arguments):
    if not arguments.confirm_concept_attempt:
        raise ValueError("Actual attempts require --confirm-concept-attempt; use preflight first")
    participant, output = validate_pair(arguments.participant, arguments.output)
    if participant.name != "participant":
        raise ValueError("The runner task directory must be named participant")
    prompt = arguments.prompt_file.read_text()
    if preflight(False) != 0:
        raise ValueError("Synthetic isolation gates failed; no concept attempt started")
    participant, output = validate_pair(participant, output)
    root = new_root("fresh")
    runtime = prepare_runtime(root)
    command = [str(RUNNER), "--model", MODEL, "--task-read-only", str(participant), str(output), GUARDRAIL + "\n" + prompt + f"\nOutput directory: {output}"]
    write_json(root / "invocation.json", {"command": command, "limit_seconds": 3600, "output_initially_empty": True, "scientific_attempt": True})
    print(f"Fresh runtime audit: {root}", flush=True)
    result = run_controller(runtime, participant, output, command, 3600, root / "agent.log")
    write_json(root / "result.json", result)
    print(json.dumps(result), flush=True)
    return result["returncode"] or bool(result["remaining_owned_descendants"])


def main():
    parser = argparse.ArgumentParser(description="Unchanged allowlisted runner with fresh state and an additional external filesystem/PID boundary")
    commands = parser.add_subparsers(dest="mode", required=True)
    smoke = commands.add_parser("preflight", help="Synthetic fixtures only; no scientific attempts")
    smoke.add_argument("--agent-smoke", action="store_true", help="After kernel checks, run one synthetic ultima-alpha probe with a separate clean home")
    attempt = commands.add_parser("run", help="Explicitly authorized future concept attempt, 3600-second hard deadline")
    attempt.add_argument("--participant", required=True, type=Path)
    attempt.add_argument("--output", required=True, type=Path)
    attempt.add_argument("--prompt-file", required=True, type=Path)
    attempt.add_argument("--confirm-concept-attempt", action="store_true")
    arguments = parser.parse_args()
    return preflight(arguments.agent_smoke) if arguments.mode == "preflight" else run_attempt(arguments)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"FRESH_LAUNCH_REFUSED: {error}", file=sys.stderr)
        raise SystemExit(2)
