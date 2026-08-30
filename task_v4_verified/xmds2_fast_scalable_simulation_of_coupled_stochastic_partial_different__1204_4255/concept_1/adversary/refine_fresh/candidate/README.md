# Generic transform-planner portfolio

Run `python3 solve.py` with one supplied instance per JSON input line. The
planner emits one `{"actions": [...]}` answer per line. Under the official
runner it imports only the public checker from `/task/workspace/model.py`;
the public baseline implementation is bundled as `baseline.py`.

Copy this directory alone for submission. Its configuration contains only
generic search parameters, not case IDs, cases, costs, or saved schedules.
The enclosing `refine_fresh` directory contains privileged experiment data
and is **not** a submission bundle.

The wrapper independently runs each configured C++ search, verifies its
answer with the public exact checker, and retains the cheapest valid answer
including the public baseline. Processes run sequentially. A shared
109-second wall deadline reserves time for fallback and serialization.
The official one-CPU and aggregate-address-space limits remain applicable;
the wrapper does not change CPU affinity or resource limits.

The bundled binary was rebuilt from the reviewed source in this directory.
Rebuild with `g++ -O3 -DNDEBUG -std=c++17 -pipe planner_v2guide.cpp -o planner_v2guide`.
Runtime dependencies are Python 3 standard library and the C++ runtime; no
NumPy/SciPy version-specific functionality is used. The original source and
the exact experimental changes are retained outside this submission under
`sources/` for privileged review.

See the enclosing `REPORT.md` and `bundle_manifest.json` for measured scores,
resource caveats, and content hashes. Presence of this portable bundle is not
a claim that the fixed 20% target has been achieved.
