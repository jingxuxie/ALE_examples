#!/usr/bin/env bash
set -euo pipefail

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repository=$(git -C "$script_directory" rev-parse --show-toplevel)
cd -- "$repository"
baseline=a4073b69e0fc3b93daf9cc12d0bd82d01335657d
expected_remote=https://github.com/jingxuxie/ALE_examples.git
if [[ $(git remote get-url origin) != "$expected_remote" ]]; then
    printf '%s\n' 'Refusing to push: origin is not the expected ALE_examples repository.' >&2
    exit 1
fi
if [[ $# -gt 1 || ( $# -eq 1 && ${1:-} != --dry-run ) ]]; then
    printf '%s\n' 'Usage: bash task_v4_verified/push_tasks_v4_verified.sh [--dry-run]' >&2
    exit 2
fi
tip=$(git log -1 --format=%H -- task_v4_verified/push_tasks_v4_verified.sh)
if [[ -z $tip ]] || ! git merge-base --is-ancestor "$baseline" "$tip"; then
    printf '%s\n' 'The publication commit is missing or does not descend from the expected baseline.' >&2
    exit 1
fi
if [[ ${1:-} == --dry-run ]]; then
    git log --reverse --format='%h %s' "$baseline..$tip"
    exit 0
fi
remote_head=$(git ls-remote origin refs/heads/main | awk '{print $1}')
if [[ -z $remote_head ]] || ! git cat-file -e "$remote_head^{commit}" 2>/dev/null; then
    printf '%s\n' 'Remote main is unknown locally. Fetch and review it before publishing.' >&2
    exit 1
fi
if git merge-base --is-ancestor "$tip" "$remote_head"; then
    printf '%s\n' 'This task_v4_verified supplement is already published.'
    exit 0
fi
if ! git merge-base --is-ancestor "$remote_head" "$tip"; then
    printf '%s\n' 'Remote main has diverged. Refusing to overwrite other work.' >&2
    exit 1
fi
cache_directory=$(mktemp -d "${TMPDIR:-/tmp}/ale-github-auth.XXXXXXXX")
cache_socket=$cache_directory/socket
cleanup() {
    git credential-cache --socket "$cache_socket" exit >/dev/null 2>&1 || true
    rmdir -- "$cache_directory" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
mapfile -t commits < <(git rev-list --reverse "$remote_head..$tip")
printf '%s\n' 'Use a jingxuxie GitHub token at the password prompt. It is cached only in memory for this upload.'
previous_start=-12
for commit in "${commits[@]}"; do
    elapsed=$((SECONDS - previous_start))
    if ((elapsed < 12)); then
        sleep "$((12 - elapsed))"
    fi
    previous_start=$SECONDS
    git show -s --format='Publishing %h: %s' "$commit"
    git -c credential.helper= \
        -c "credential.helper=cache --timeout=3600 --socket=$cache_socket" \
        -c credential.username=jingxuxie \
        push origin "$commit:refs/heads/main"
done
remote_head=$(git ls-remote origin refs/heads/main | awk '{print $1}')
if [[ $remote_head != "$tip" ]]; then
    printf '%s\n' 'Remote changed after the upload; inspect GitHub before claiming exact-tip verification.' >&2
    exit 1
fi
printf 'Published and verified task_v4_verified supplement: %s\n' "$tip"
