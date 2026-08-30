#!/usr/bin/env bash
# Start a separate Codex session that can read and write TASK_DIR and OUTPUT_DIR
# (plus Codex's own runtime files). Other directories, such as benchmark
# answers, are not mounted into commands run by the child.
#
# Usage:
#   ./run_allowlisted_codex.sh /absolute/path/to/task /absolute/path/to/output \
#     "Solve the task and write the result into OUTPUT_DIR."
#   ./run_allowlisted_codex.sh --model gpt-5.6-luna --effort low \
#     /absolute/path/to/task /absolute/path/to/output \
#     "Solve the task and write the result into OUTPUT_DIR."
#
# TASK_DIR and OUTPUT_DIR must already exist. TASK_DIR is the child's working
# directory; include the OUTPUT_DIR path in the prompt so the child knows where
# to place its results.
#
# The child inherits model and effort from CODEX_HOME unless --model and/or
# --effort are supplied. Provider and authentication always come from CODEX_HOME.
# Approval escalation is disabled so it cannot request broader filesystem access.
set -euo pipefail

usage() {
  printf '%s\n' \
    "usage: $0 [--model MODEL] [--effort EFFORT] [--task-read-only] TASK_DIR OUTPUT_DIR PROMPT" \
    "" \
    "If omitted, MODEL and EFFORT inherit from CODEX_HOME/config.toml."
}

child_model=
child_effort=
task_access=write

while (($#)); do
  case $1 in
    --task-read-only)
      task_access=read
      shift
      ;;
    --model)
      if (($# < 2)) || [[ -z $2 ]]; then
        echo "--model requires a non-empty value" >&2
        exit 2
      fi
      child_model=$2
      shift 2
      ;;
    --model=*)
      child_model=${1#*=}
      if [[ -z $child_model ]]; then
        echo "--model requires a non-empty value" >&2
        exit 2
      fi
      shift
      ;;
    --effort|--reasoning-effort)
      if (($# < 2)) || [[ -z $2 ]]; then
        echo "$1 requires a non-empty value" >&2
        exit 2
      fi
      child_effort=$2
      shift 2
      ;;
    --effort=*|--reasoning-effort=*)
      child_effort=${1#*=}
      if [[ -z $child_effort ]]; then
        echo "--effort requires a non-empty value" >&2
        exit 2
      fi
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if (($# < 3)); then
  usage >&2
  exit 2
fi

task_dir_input=$1
output_dir_input=$2
shift 2
child_prompt=$*

task_dir=$(realpath -e -- "$task_dir_input")
if [[ ! -d "$task_dir" ]]; then
  echo "task directory does not exist: $task_dir" >&2
  exit 2
fi

output_dir=$(realpath -e -- "$output_dir_input")
if [[ ! -d "$output_dir" ]]; then
  echo "output directory does not exist: $output_dir" >&2
  exit 2
fi

codex_command=$(command -v codex)
codex_bin=$(realpath -e -- "$codex_command")
codex_home_input=${CODEX_HOME:-${HOME}/.codex}
codex_home_dir=$(realpath -e -- "$codex_home_input")
codex_packages_dir="$codex_home_dir/packages"
codex_helpers_dir="$codex_home_dir/tmp/arg0"

for runtime_dir in "$codex_packages_dir" "$codex_helpers_dir"; do
  if [[ ! -d "$runtime_dir" ]]; then
    echo "required Codex runtime directory does not exist: $runtime_dir" >&2
    exit 2
  fi
done

toml_escape() {
  local value=$1
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  printf '%s' "$value"
}

task_toml=$(toml_escape "$task_dir")
output_toml=$(toml_escape "$output_dir")
packages_toml=$(toml_escape "$codex_packages_dir")
helpers_toml=$(toml_escape "$codex_helpers_dir")
binary_toml=$(toml_escape "$codex_bin")

model_overrides=()
if [[ -n $child_model ]]; then
  model_overrides+=(--model "$child_model")
fi
if [[ -n $child_effort ]]; then
  effort_toml=$(toml_escape "$child_effort")
  model_overrides+=(-c "model_reasoning_effort=\"$effort_toml\"")
fi

# Only the task, output, and Codex runtime are mounted into generated commands.
# In particular, sibling benchmark-answer directories are not mounted.
permissions_override="permissions.benchmark.filesystem={\":minimal\"=\"read\",\"$task_toml\"=\"$task_access\",\"$output_toml\"=\"write\",\"$packages_toml\"=\"read\",\"$helpers_toml\"=\"read\",\"$binary_toml\"=\"read\"}"

# Remove permission restrictions inherited from the parent session, then apply
# the narrower benchmark profile to this child process.
exec env \
  -u CODEX_PERMISSION_PROFILE \
  -u CODEX_SANDBOX_NETWORK_DISABLED \
  CODEX_HOME="$codex_home_dir" \
  "$codex_bin" \
  --strict-config \
  "${model_overrides[@]}" \
  -c "$permissions_override" \
  -c 'default_permissions="benchmark"' \
  -c 'approval_policy="never"' \
  -c 'web_search="disabled"' \
  exec \
  --ephemeral \
  --skip-git-repo-check \
  -C "$task_dir" \
  "$child_prompt"
