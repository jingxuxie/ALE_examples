# ALE examples

Task-design and screening artifacts shared for review, organized by collection.
The folders preserve participant instructions where a task was built, authoring
decisions, source artifacts, known-good solutions, evaluators, and fresh-agent
attempts where available.

## Collections

| Collection | Task folders | Review status |
| --- | --- | --- |
| [task_v2](task_v2/README.md) | 11 | Earlier screening archives, including localized statistics decoding; all rejected during screening. |
| [task_v3](task_v3/README.md) | 10 | Newer review snapshots; some tournaments were still in progress during capture. |
| [task_v4](task_v4/README.md) | 10 | Uniform random sample: 5 hard-open, 3 verified-achievable, 1 rejected, and 1 without a final status at draw time. |
| [task_v4_verified](task_v4_verified/README.md) | 18 | Remaining verified-achievable v4 tasks; its index also links the 3 already in the random sample, covering all 21. |

Open a collection's index to browse its task reports and screening records.
Folder names correspond to the author's `tasks_v2`, `tasks_v3`, and `tasks_v4`
source collections. The v4 folder is one unfiltered random sample from all 210
source task folders, not a verified-only selection or an outcome-quota sample.
Its [sampling record](task_v4/SAMPLE.json) preserves the seed and full population.
The verified-achievable supplement is separate and outcome-selected; it does
not change the random sample and should not be pooled with it when estimating
the source population's status distribution.
Inclusion here is not independent acceptance as a hard benchmark.

## Before reviewing or running

These are **author/reviewer bundles** and include solutions, hidden evaluation
data, and attempt transcripts. Do not expose an entire bundle to a blind task
participant.

These are review-oriented exports, not complete offline runtime images. The
[task_v2 publication notes](task_v2/PUBLICATION.md) describe its runtime
exclusions and oversized frozen-snapshot omission. The
[task_v3 publication notes](task_v3/PUBLICATION_V3.md) describe its runtime
exclusions and restoration of losslessly packaged large scientific data.
The [task_v4 publication notes](task_v4/PUBLICATION_V4.md) document its random draw,
runtime exclusions, integrity records, and large-artifact restoration.
The [verified supplement notes](task_v4_verified/PUBLICATION.md) document the
18-plus-3 coverage, preserved link declarations, and artifact restoration.
