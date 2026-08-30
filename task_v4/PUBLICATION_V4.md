# task_v4 random-sample publication

## Unfiltered sampling

The previous curated verified-achievable collection is replaced by one uniform
random sample of ten distinct directories from all 210 immediate task folders
in the author's `tasks_v4` collection. Sampling does not filter on status,
report availability, topic, archive size, or previous inclusion. Incomplete and
rejected tasks remain eligible. The original task folders are not modified.

The draw uses a newly generated 128-bit system-random seed with Python's
`random.Random(seed).sample(sorted_population, 10)`. The seed, Python version,
full sorted population, population-name hash, selected draw order, and statuses
observed at sampling are recorded in [SAMPLE.json](SAMPLE.json). There is no
redraw or substitution to force a desired outcome mix. This is not stratified
sampling: a ten-task sample need not match population proportions exactly.

The frozen draw contains five `hard_open_candidate`, three
`hard_verified_achievable`, one `rejected`, and one task without a readable
top-level final status. The population has 21 verified-achievable tasks out of
210, so the expected count in a sample of ten is one, not a required count.
The [index](README.md) includes the full population-versus-sample table.

Replay the recorded draw from the repository root with Python's standard library:

```bash
python task_v4/verify_sample.py
```

Use the Python version recorded in `SAMPLE.json` for exact algorithm replay.
The checker verifies the seed replay, population hash, and status tallies; it
does not recertify scientific outcomes or prove population completeness without
access to the original source collection.

## Snapshot scope

All saved concepts, generations, source evidence, evaluators, witnesses, and
attempt records within the sampled folders are retained subject to the explicit
export rules below. Outcomes come from saved records; no scientific evaluation
is rerun or rescored for publication. A recorded status does not independently
certify a scientific claim or apply to every concept inside its task archive.

The sampled kdotpy folder has no top-level final report or status file at draw
time. It is retained rather than replaced. Its generated `REVIEW_SNAPSHOT.md`
points to existing concept and authoring directories; it is not an author final
report or an invented screening decision.

The manifest records capture times, original file modification times, lengths,
SHA-256 hashes, Git object identities, and explicit transformations. Capture is
per-file stable, not atomic across concurrent work. It distinguishes status at
sampling from status at capture and flags changes to the original status file.
All manifest paths are relative to its containing `task_v4/` directory.

The earlier curated bundle remains in Git history at commit `7cf6509`; history
is not rewritten. The current `task_v4/` contains exactly the sampled folders.
`task_v2/` and `task_v3/` are unchanged.

## Runtime and metadata treatment

- Dedicated installed Python dependency trees are replaced with
  `REVIEW_RUNTIME_REQUIREMENTS.txt`, with package versions recorded in the
  manifest. This applies to the Honeycomb authoring dependencies, two Sparse
  Blossom runtime directories, and the Stim vendor environment.
- The Honeycomb participant workspace mixes task code and installed packages.
  It is preserved rather than dropping scientific code with its dependencies.
- pyGSTi's disposable `authoring/runtimes/` tree is replaced with
  `REVIEW_RUNTIME_OMISSION.md`. Runner snapshots and task-attempt records outside
  that runtime tree remain included.
- Nested Git histories, agent marker directories, bytecode, and standard caches
  are omitted. Upstream `.gitattributes` files, if present, are preserved as
  inert `.gitattributes.upstream` files, with original names recorded.
- Existing symbolic-link declarations are preserved without following them
  during copying. Internal source-absolute links are made relative. Missing
  targets and the intentional self-referential NLO parser-audit fixture are
  explicitly recorded, not repaired. The self-link is test data, not a file to
  open recursively.

This is a review archive, not a complete offline runtime image. Version pins do
not guarantee compatible wheels, native toolchains, external services, or a
byte-identical environment. Machine-specific paths and original requirements
are retained, not silently rewritten.

## Large artifacts

Scientific inputs and results are not discarded for size. Files larger than
100 MiB are losslessly gzip-compressed into parts of at most 64 MiB in their
task's `REVIEW_LARGE_FILES/` directory. The manifest records original paths,
sizes, hashes, and ordered part lists. No Git LFS storage is required.

With Python 3.10+ and the standard library, run from the repository root:

```bash
python task_v4/restore_v4_artifacts.py --list
python task_v4/restore_v4_artifacts.py --verify
python task_v4/restore_v4_artifacts.py
```

Original oversized files are absent until restored. Verification checks parts
and fully decompressed originals without installing the originals. Restoration
uses the same checks and refuses to overwrite a differing local file. Use
`--only PATH_PREFIX` relative to `task_v4/`, without including that prefix in
the argument. Restored large files and rebuilt excluded runtimes are ignored
by Git. Allow temporary space for the compressed stream and restored file.

## Review and publication

Artifact hashes, staged Git objects, sampling replay, navigation, omission
rules, and large-data restoration are checked before publication. Credential
patterns are scanned, but this is not a general security audit of code or
nested archives. Preserve upstream licenses and review executable material in
an isolated environment before running it.

Solutions, hidden inputs, private witnesses, and attempts are reviewer-only
material. A blind participant must receive only its chosen participant assets,
not the entire task or collection archive.

On the author's prepared clone, publish the replacement from the repository root:

```bash
bash task_v4/push_tasks_v4.sh --dry-run
bash task_v4/push_tasks_v4.sh
```

The helper checks the destination, refuses divergent remote work, and resumes
bounded ordinary fast-forward push batches. It does not force-push or rewrite
the previous curated release. Intermediate batches may be partial; the final
catalog commit completes the replacement.

If needed, enter a `jingxuxie` GitHub token at the terminal password prompt.
Credentials are cached only in memory for the upload and cleared afterward.
The global credential helper is unchanged. Never put a token in a command line,
a committed file, or a chat message.
