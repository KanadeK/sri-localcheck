# Validation contract

Run `python scripts/verify.py` for the complete release gate. It includes Ruff,
branch-aware coverage >=90%, meaningful regression tests, sdist-to-wheel build,
clean virtual environment installation, real console/module invocation outside
the checkout and immutable synthetic fixture checks across all exit statuses.

Cases cover independent Node-generated SHA-2 abc vectors; strongest-hash selection;
same-strength alternatives; strict/URL-safe/unpadded metadata; local bases, entities,
Unicode paths, queries and root-relative URLs; remote/unsupported URLs; traversal,
Windows device/ADS/reparse paths; duplicate attributes and bases; required versus
optional integrity; no-applicable-input rejection; actual POSIX symlinks/FIFOs;
HTML/element/token/asset/total bounds; stream growth; changing-file detection;
cache reuse and budgets that retain bytes consumed by failed reads.

Prepublication self-review also compares 39 actual file checks to separately run
Node crypto digests across 13 binary lengths and all three algorithms, including
empty data and a payload larger than a streaming chunk. Node is a development
cross-check, not a runtime or test-suite dependency. Probe receipts are recorded
with the local incubation evidence. This does not establish browser compatibility.

Review found two correctness hazards that were fixed before publication: urllib
can collapse repeated path slashes, and failed reads can accidentally be omitted
from aggregate budgets. Both behaviors now have regression cases.

CI runs the full gate on Ubuntu Python 3.11/3.13, Windows 3.13 and macOS 3.13,
using read-only, SHA-pinned official Actions. Complete history must use the owner's
Author/Committer identity without co-author trailers. Release publication separately
checks GitHub identity mapping, the sole contributor, tag/commit identity, artifact
code equality and anonymous release downloads matching local bytes.

Read the README's stable-tree and URL mapping assumptions. These are bounded
local-build checks, not filesystem snapshots, browser automation, HTTP deployment
verification or an adversarial file-access sandbox. Measured results are in the
verification logs/CI; this document describes the checks rather than claiming a run.
