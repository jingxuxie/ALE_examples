# task_v3 review snapshot

## Scope and status

Ten additional folders from the author's `tasks_v3` directory are included under
their original names inside the repository's `task_v3/` folder. Their source
folders are not modified. The earlier task folders and their original
publication manifest are grouped separately in `task_v2/`. Start with the
[collection index](README.md) to browse the newer reports.

This is a **review snapshot**, not a finalized benchmark release. Some reports
explicitly describe ongoing work. Files are captured individually while stable,
but the collection is not an atomic snapshot of all running tournaments. The
manifest records capture timestamps and source-file modification times. Consult
the copied reports, selection records, and run metadata rather than assuming
every pilot is complete or accepted.

Participant material, authoring and source evidence, references, evaluators,
saved results, and available attempt records are preserved. No scientific
evaluation is rerun or rescored for publication. Solutions and hidden inputs
are privileged review material, not inputs for a blind participant.

## Large scientific files

Files too large for ordinary GitHub blobs are **not discarded**. They are
losslessly gzip-compressed and stored as numbered parts of at most 64 MiB under
the corresponding task's `REVIEW_LARGE_FILES/` directory. Identical large
payloads within a task share the same packaged data. Original paths, sizes,
SHA-256 hashes, and the ordered part list are in
`PUBLICATION_MANIFEST_V3.json`. All paths in this manifest are relative to
`task_v3/`, the directory containing the manifest and restoration helper.

The original oversized file paths are absent until restored. With Python 3.10+
and only its standard library, run from the repository root:

```bash
python task_v3/restore_v3_artifacts.py --list
python task_v3/restore_v3_artifacts.py --verify
python task_v3/restore_v3_artifacts.py
```

Use `--only PATH_PREFIX` to select one task or one original path relative to
`task_v3/` (without adding the `task_v3/` prefix). Verification
checks the stored parts and the fully decompressed content. Restoration checks
the same hashes and refuses to overwrite an existing file with different
contents. Restored oversized files are ignored by Git so they are not
accidentally committed as oversized blobs. Allow enough temporary disk space
for the packaged stream and the restored file.

No Git LFS account storage is provisioned or required for these packaged files.
GitHub's file and push limits are documented at
<https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits>.

## Runtime and metadata exclusions

- Installed numerical dependency trees and bundled interpreter environments
  are omitted. Each is replaced by `REVIEW_RUNTIME_REQUIREMENTS.txt`; package
  versions and available Python layout information are also in the manifest.
- Nested `.git` histories, agent-runtime marker directories, Python bytecode,
  and standard caches are omitted.
- Upstream `.gitattributes` files are preserved byte-for-byte under the inert
  name `.gitattributes.upstream`. Their original paths are recorded. This avoids
  inherited LFS, notebook filters, or line-ending rules changing the copied
  source artifacts when this review repository is committed.

The pinned package lists are a starting point for rebuilding dependencies, not
a guarantee of a byte-identical runtime. Bundled Python interpreters, native
libraries, source-local modifications, and external toolchains may require the
original environment. Do not treat a directory containing only a pin file as
a working runtime or as satisfying an original offline-task contract.

Source licenses, original reports, and existing relative symbolic links are
preserved. Any already-broken source link is recorded as such; the exporter does
not silently repair it or copy material from outside `tasks_v3`. Original
machine-specific paths are not generally rewritten.

## Integrity and publication

The manifest distinguishes unchanged regular files, symbolic links, renamed
Git metadata, generated dependency pins, and packaged large data. Preserved
file bytes and staged Git objects are checked before committing. Large payloads
are checked through decompression against their recorded original hashes.
Credential-pattern scanning is performed, but is not a security audit of all
the executable code or nested archive contents.

The collection was initially committed one task at a time, followed by the
catalog and publication tools, then moved into `task_v3/` without changing the
task artifacts. This keeps each upload batch manageable and preserves the
published history. On the author's prepared local clone, run the following from
the repository root to publish the snapshot and its folder reorganization using
ordinary fast-forward pushes:

```bash
bash task_v3/push_tasks_v3.sh --dry-run
bash task_v3/push_tasks_v3.sh
```

The helper checks the repository destination, refuses divergent remote work,
and resumes a partially completed upload. It asks for a `jingxuxie` token at the
terminal password prompt and keeps it only in a temporary, private, in-memory
Git credential cache for this upload. It does not change the global credential
helper. Never put a token in a command line, a committed file, or a chat message.
