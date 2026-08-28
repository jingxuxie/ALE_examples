# task_v2 review export notes

## Scope

Eleven task folders from the author's `tasks_v2` directory are grouped under
the repository's `task_v2/` folder. This combines the original
`localized_statistics_decoding` bundle with the ten subsequently exported
folders. Original folder names and concept/version subdirectories are
preserved. The source folders on the author's machine were not modified.
Start with the [collection index](README.md) to browse the task records.

This is a review archive, **not a claim that the tasks passed hardness screening**.
The original status files, task specifications, scientific inputs, solutions,
evaluators, saved results, and attempt evidence remain as recorded. Bodge and
many-body localization contain authoring/rejection records but no built
participant task.

## Exclusions

The additional-task export omits:

- Installed Python dependency trees detected by distribution metadata: ten
  directories across block2, filter functions, Hamiltonian truncation,
  SuperScreen, and vortex-lattice authoring tools. Their package names and
  versions are recorded in `PUBLICATION_MANIFEST.json`; each omitted tree
  contains a new `REVIEW_RUNTIME_REQUIREMENTS.txt` convenience file instead.
- The filter-function archive
  `concept_01/screening/participant_v_01_frozen.tar.gz` (152,732,652 bytes).
  It exceeds GitHub's regular-file limit and contains a frozen participant
  snapshot. Its SHA-256 is recorded in the manifest. The unpacked participant
  version is included subject to the exclusions listed here; no claim is made
  that it substitutes byte-for-byte for that historical archive.
- Nested `.git` histories, empty `.agents`/`.codex` runtime directories,
  Python bytecode, and standard interpreter/test/notebook caches.

No large scientific input or result was excluded just to reduce upload size.
Upstream source files and their license files remain with the copied sources.
No Git LFS storage or external artifact hosting is set up by this export.

Two Package-X upstream `.gitattributes` files are preserved byte-for-byte as
`.gitattributes.upstream`, with their original paths recorded in the manifest.
This makes their inherited Git LFS rules inactive: the small source libraries,
archives, and PDFs are stored directly in this repository rather than being
silently replaced by pointers to a separate LFS service. No scientific file is
changed by this metadata-only rename.

GitHub documents its regular-file size limits at
<https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>.

## Running tasks from this copy

**The original task instructions assume their original offline environment.**
This reduced review export does not satisfy that assumption until the omitted
dependencies have been restored. In particular, a small runtime directory
containing only `REVIEW_RUNTIME_REQUIREMENTS.txt` is not a working runtime.

For an appropriate Python/platform environment, a reviewer can attempt to
recreate an omitted dependency tree with:

```bash
python -m pip install --no-deps --target PATH_TO_RUNTIME \
  -r PATH_TO_RUNTIME/REVIEW_RUNTIME_REQUIREMENTS.txt
```

Replace `PATH_TO_RUNTIME` with the corresponding directory in this repository.
The package pins describe the original installed distributions; they do not
guarantee wheel availability, compatibility on another platform, or preservation
of local binary/library modifications. For a faithful offline replay, obtain
the original runtime and frozen artifacts from the author. Original absolute
paths and external Codex/Mathematica/toolchain requirements are not rewritten.

No scientific evaluations were rerun or rescored for publication.

## Integrity and review boundaries

`PUBLICATION_MANIFEST.json` lists every preserved file from the ten additional
folders with its size and SHA-256, the original screening status, dependency
pins, and the explicit large-artifact omission. New publication documentation
and generated pin files are distinguished from the preserved task artifacts.
The localized-statistics-decoding folder is outside this manifest. All manifest
paths are relative to `task_v2/`, the directory containing the manifest. The
folder reorganization preserves all eleven task directories byte-for-byte and
does not rewrite their published history.

Copied files are checked against their local originals. Credential-pattern
checks are performed before staging, but are not a general security audit of
the submitted code. These folders contain executable author and agent code;
review it before running it, and use an appropriately isolated environment.

Only the selected `participant` version should be exposed in any future blind
attempt, after restoring its declared dependencies. Authoring, solution,
evaluator, screening, and attempt directories are privileged review material.

## Publishing the folder reorganization

On the author's prepared local clone, run from the repository root:

```bash
bash task_v2/push_tasks_v2.sh --dry-run
bash task_v2/push_tasks_v2.sh
```

The helper uses ordinary fast-forward pushes, verifies the destination, and
refuses divergent remote work. If authentication is needed, enter a `jingxuxie`
GitHub token at the terminal password prompt. Credentials are cached only in
memory for this upload and cleared afterward; the global credential helper is
unchanged. Never put a token in a command line, committed file, or chat message.
