# Verified-achievable v4 supplement

## Scope and selection

This folder contains the 18 remaining source tasks marked
`hard_verified_achievable` at selection time. The source `tasks_v4` collection
contained 210 task folders, of which 21 had that recorded final status. Three
are already present in the unchanged random `task_v4/` sample and are linked
from this supplement's [index](README.md) rather than duplicated.

The selection is the complete remainder of that status class, not another
random sample. Do not combine its outcome counts with the random sample when
estimating the source population's status distribution. `task_v2/`, `task_v3/`,
and the entire existing `task_v4/` collection remain unchanged.

[SELECTION.json](SELECTION.json) records the selection time, rule, all 21 task
names, original status-file hashes, and the partition between these 18 folders
and the three already in the random sample. Classification uses `final_status`
when present, otherwise `status`.

Reports, status records, all saved concepts and generations, participant assets,
source evidence, evaluators, private witnesses, and attempt records are
preserved subject to the explicit export rules below. No scientific evaluation
is rerun or rescored for publication. A recorded verified-achievable outcome
is an author claim about the retained task, not independent certification of
every concept, scientific conclusion, or environment in the archive.

Capture is stable per file, not an atomic snapshot of concurrent work. The
manifest records capture times, source modification times, lengths, SHA-256
hashes, Git object identities, and transformations. Changes to a task's status
file between selection and capture are flagged. Manifest paths are relative to
the directory containing it (`task_v4_verified/`).

## Runtime and link treatment

- Qualtran's disposable `authoring/infrastructure/runtimes/` tree is replaced
  with an omission note. Repeated agent installations, plugins, and temporary
  execution roots are excluded; runner snapshots and task records remain.
- The O(N) bootstrap task's diagnostic `clean_home/` and
  `launcher_validation/runtime/` directories are replaced with omission notes.
  Launcher diagnostic inputs, results, and logs outside these directories are
  preserved. No scientific archive is omitted merely for size.
- Nested Git histories, agent marker directories, Python bytecode, and standard
  caches are omitted. Any upstream `.gitattributes` files are preserved as inert
  `.gitattributes.upstream` files so Git filters cannot alter artifact bytes.
- Internal link declarations are preserved without following them during
  copying. Source-absolute links inside the selected collection become relative.
- The p†q archive contains 56 already-dangling sandbox-specific links to
  `/runtime/champion/beam`, `beam2`, `beam3`, or `model.so`. Their exact link
  declarations are preserved and marked external in the manifest. Their
  external targets are not read, copied, or supplied. They require the original
  sandbox layout to resolve; do not treat them as bundled executable files.

This is a review archive, not a complete portable or offline runtime image.
Machine-specific paths, native-library requirements, and external toolchains
are retained rather than silently rewritten. Included dependency installations
may require the original Python version and platform.

## Large scientific artifacts

Files larger than 100 MiB are preserved losslessly as gzip-compressed parts of
at most 64 MiB under their task's `REVIEW_LARGE_FILES/` directory. Original paths,
lengths, hashes, and ordered part lists are in the manifest. Identical large
payloads within a task share packaged parts. No Git LFS account is required.

From the repository root, with Python 3.10+ and the standard library:

```bash
python task_v4_verified/restore_artifacts.py --list
python task_v4_verified/restore_artifacts.py --verify
python task_v4_verified/restore_artifacts.py
```

Oversized originals are absent until restored. Verification checks both parts
and the fully decompressed originals without installing them. Restoration uses
the same checks and refuses to overwrite a differing local file. Use
`--only PATH_PREFIX` relative to `task_v4_verified/`, without that prefix in the
argument. Restored oversized paths and omitted runtimes are ignored by Git.
Allow temporary space for a packaged stream and its restored file.

## Integrity and review boundaries

Publication checks cover artifact hashes, committed Git objects, roster
completeness, navigation, link declarations, and large-data restoration.
Credential-pattern scans are performed, but are not general security audits of
executable source or nested archives. Upstream licenses remain with the copied
sources. Review code before running it in an isolated environment.

Check the 18-plus-3 roster from the repository root with:

```bash
python task_v4_verified/verify_collection.py
```

This checker verifies the saved collection records, not scientific hardness.
Solutions, hidden inputs, private witnesses, and attempts are reviewer-only
material. A blind participant should see only its chosen participant assets.

## Publishing

On the author's prepared local clone, run from the repository root:

```bash
bash task_v4_verified/push_tasks_v4_verified.sh --dry-run
bash task_v4_verified/push_tasks_v4_verified.sh
```

The helper checks the destination, refuses divergent work, and resumes bounded
ordinary fast-forward push batches. The final catalog commit completes the
supplement; intermediate batches can be partial. Previous history is preserved.

If prompted, enter a `jingxuxie` GitHub token at the terminal password prompt.
It is cached only in memory for the upload and cleared afterward. The global
credential helper is unchanged. Never put tokens in command lines, committed
files, or chat messages.
