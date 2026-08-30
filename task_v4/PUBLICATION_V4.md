# task_v4 review publication

## Scope and selection

This is a review snapshot of ten selected task folders from `tasks_v4`, grouped
under `task_v4/` in this repository. The source collection contained 210 folders
when inspected; 21 recorded a final `hard_verified_achievable` status. Ten were
selected for topical diversity, completed reports, and reviewable artifacts.
The [index](README.md) lists the exact selection and links the saved evidence.
The selection is not random or a comprehensive ranking.

Each task's original reports, statuses, participant assets, evaluators, private
witnesses, source evidence, and saved attempts are preserved. All concepts and
generations are included, not only the selected winner. No scientific
evaluation is rerun or rescored for publication. A recorded status is not an
independent guarantee that every claim, runtime, or scientific conclusion is
correct. Source task folders and the earlier `task_v2/` and `task_v3/`
collections are not modified.

Capture is per-file stable, not an atomic snapshot of concurrent work. The
manifest records capture times, original modification times, file sizes,
SHA-256 hashes, Git object identities, and explicit export transformations.
Every manifest path is relative to the directory containing it (`task_v4/`).

## Excluded runtime material

- Installed Python dependency environments are replaced with package-version
  pins in `REVIEW_RUNTIME_REQUIREMENTS.txt`. The Stim task's installed vendor
  dependency is excluded this way, not its scientific source or task assets.
- Qualtran's disposable `authoring/infrastructure/runtimes/` tree is replaced
  with `REVIEW_RUNTIME_OMISSION.md`. It contains repeated agent CLI installs,
  plugins, and temporary execution roots. The runner snapshot, preflight
  records, and task-attempt evidence outside that tree are preserved.
- Nested `.git` histories, agent-runtime marker directories, bytecode, and
  standard caches are omitted.
- Any upstream `.gitattributes` files are preserved as inert
  `.gitattributes.upstream` files, with original paths recorded. This prevents
  inherited LFS or other filters from changing the exported artifact bytes.

This is not a complete offline runtime image. Package pins do not preserve
locally modified dependencies, guarantee compatible wheels, or provide external
toolchains or model access. Original machine-specific paths and environment
requirements are retained rather than silently rewritten. Relative symlinks
are preserved; source-absolute links within the selected collection are made
relative to their corresponding copied targets. Already-missing targets are
recorded in the manifest, not silently repaired.

## Large scientific artifacts

Oversized scientific inputs and results are not discarded. Files larger than
100 MiB are losslessly gzip-compressed into parts of at most 64 MiB under the
corresponding task's `REVIEW_LARGE_FILES/` folder. The manifest records original
paths, lengths, hashes, and ordered part lists. Identical payloads within a task
can share the same packaged data. No Git LFS storage is required for these parts.

With Python 3.10+ and its standard library, run from the repository root:

```bash
python task_v4/restore_v4_artifacts.py --list
python task_v4/restore_v4_artifacts.py --verify
python task_v4/restore_v4_artifacts.py
```

The original oversized files are absent until restored. `--verify` checks part
hashes and fully decompressed original content without restoring files.
`--only PATH_PREFIX` selects a path relative to `task_v4/` (omit that prefix in
the argument). Restoration refuses to overwrite a differing local file and
checks the same hashes. Allow temporary space for a compressed stream and the
restored file. Restored oversized paths and rebuilt runtimes are ignored by Git.

## Integrity and review boundaries

Exported artifact hashes, Git objects, relative links, and packaged data are
checked before publication. Credential-pattern scanning is also performed;
it is not a comprehensive security audit of executable code or nested archives.
Preserved upstream licenses and source attribution remain with their artifacts.

Solutions, hidden inputs, private witnesses, and attempt transcripts are
privileged reviewer material. Do not expose the entire archive to a blind
participant. Review code before executing it in an appropriately isolated
environment.

## Publishing the selected examples

On the author's prepared local clone, run from the repository root:

```bash
bash task_v4/push_tasks_v4.sh --dry-run
bash task_v4/push_tasks_v4.sh
```

The helper publishes only this collection's prepared commit series using
ordinary fast-forward pushes. It verifies the destination, refuses divergent
remote work, and resumes partial uploads. Larger task archives are split into
bounded commit batches without changing their final folder structure.

If prompted, enter a `jingxuxie` GitHub token at the terminal password prompt.
Credentials are cached only in memory for this upload and cleared afterward;
the global credential helper is unchanged. Never put a token in a command line,
a committed file, or a chat message.
