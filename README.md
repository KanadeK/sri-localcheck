# sri-localcheck

Verify existing HTML `integrity` declarations against the actual files in a
local build. Catch stale hashes before deploying; never regenerate them to hide
a mismatch. Python 3.11+, standard library only. [中文说明](README.zh-CN.md).

SRI metadata can survive an asset revision and make browsers block the new file.
This CLI checks a stable build directory without running a server, executing
JavaScript or contacting a CDN. Remote URLs are explicit failures because they
cannot be verified from local files.

## Install and run the proof

```sh
git clone https://github.com/KanadeK/sri-localcheck.git
cd sri-localcheck
python -m venv .venv
# POSIX: . .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install .
sri-localcheck examples/site valid.html --json
sri-localcheck examples/site broken.html --json
```

The first exits 0 for matching JS/CSS. The second exits 1: its correct SHA-256
cannot rescue a wrong SHA-512. `examples/site/remote.html` fails without making a
network request. All assets are original synthetic fixtures, reproduced by
`python scripts/make_examples.py` (a separate fixture generator).

Alternatively, download the wheel and `SHA256SUMS` from the
[v0.1.0 release](https://github.com/KanadeK/sri-localcheck/releases/tag/v0.1.0),
verify SHA-256 and install with
`python -m pip install sri_localcheck-0.1.0-py3-none-any.whl`.
The publication channel is GitHub Releases; this does not imply a PyPI upload.

## Check your build

```sh
python -m sri_localcheck dist pages/index.html --json
sri-localcheck dist pages/index.html --require-integrity --json
```

The HTML path is **relative to the build root**, not your working directory.
Default mode checks existing declarations on external `script[src]` and
`link[rel~=stylesheet]` elements. `--require-integrity` also fails those elements
when the attribute is absent. Unsupported elements carrying integrity metadata
(including preload/modulepreload links and inline scripts) are reported as
unsupported; their integrity behavior is not inferred.

Exit **0**: at least one declaration was checked and all passed. Exit **1**:
per-element mismatch, missing metadata in required mode, unavailable/unsafe asset,
ambiguous HTML attribute/base, unsupported declaration or unverified remote URL.
Exit **2**: root/document/encoding error, HTML/element limit, or no applicable
declarations. Empty HTML and a page with no integrity declarations cannot silently
pass default mode. Findings retain their HTML line and element type.

## Hash and URL contract

- SHA-256, SHA-384 and SHA-512 are supported. Only the strongest algorithm present
  determines a match; any matching digest among alternatives at that strength is
  sufficient. Algorithms and metadata syntax are case sensitive.
- Standard and URL-safe base64 are accepted, with canonical padding or no padding.
  Wrong lengths, nonzero pad bits, redundant padding, malformed/unknown algorithms
  and `?option` tokens fail. This deliberately strict audit policy differs from
  browsers that may ignore unsupported or malformed tokens. It is not a complete
  browser SRI conformance implementation.
- Relative/root-relative asset URLs and one local `<base href>` are supported.
  Query and fragment are discarded for filesystem lookup. The model assumes
  query strings do not select transformed representations. HTML entities and
  UTF-8 `%HH` escapes are decoded once; scripts are never executed.
- Every explicit scheme or protocol-relative URL is unverified, including
  absolute URLs for your own production hostname. External, empty, duplicate or
  ambiguous bases fail. The first local base is applied to static references;
  browser parsing/execution order is outside this checker.
- All files must remain beneath the real build root. Symlinks, Windows reparse
  entries, encoded traversal, backslashes, device/ADS names, invalid percent
  escapes and ambiguous repeated slashes are rejected. Windows-reserved names
  and trailing-dot/space components are rejected on every OS for consistent use.
  Regular relative `../assets/app.js` is allowed when URL resolution stays inside
  the root; encoded `..` is rejected conservatively.

Limits: **2 MiB UTF-8 HTML** (optional BOM), **1,000 candidate elements**,
**64 metadata tokens per declaration**, **16 MiB per asset** and **64 MiB total
asset bytes read**, including failed reads. Bounded stream probes may read one
extra byte to detect overflow. Successful asset hashes are cached once per
resolved relative URL path, but each declaration keeps its own expected hashes.
Missing-integrity elements also count toward the candidate-element bound.

Use a closed/stable build tree. Metadata is checked before and after each asset
read, but there is no atomic filesystem snapshot or hostile concurrent-writer
sandbox. A complete build should not change during the scan or after cached
hashes are reused. The checker reads local bytes, so it does not prove HTTP
encoding, server rewrites, CORS/CSP, MIME type, dynamic DOM, deployment correctness
or browser execution. It does not authenticate files when HTML and assets are
both replaced together.

## Reports, rationale and maintenance

JSON schema `sri-localcheck/v1` includes status, HTML SHA-256, counts, bytes read,
cached asset count and per-element line/type/code/selected algorithm/size. It emits
no source bodies, expected digests, resource URLs, query values or filesystem
paths. The HTML fingerprint can still identify a known page; redaction is not
anonymization. Standard argparse usage errors follow normal CLI behavior.

[Magento's SRI mismatch report](https://github.com/magento/magento2/issues/40807)
illustrates the failure; that product issue was closed after an upstream fix.
Hash selection follows the core rules in the
[W3C SRI Recommendation](https://www.w3.org/TR/2016/REC-SRI-20160623/).
[jkittner/sri-checker](https://github.com/jkittner/sri-checker) is an adjacent
HTML linter with a documented network requirement for public CDNs. Build plugins
generate metadata; this tool checks existing declarations offline. The owner's
assetwire verifies deployed HTTP bytes/MIME against a manifest, sidecar-verify
checks compressed sidecars, and AssetMatrix checks image variants/dimensions.
Those workflows do not establish this declaration-to-local-byte contract.

```sh
python -m pip install -e ".[dev]"
python scripts/verify.py
```

The gate runs Ruff, branch-aware coverage >=90%, meaningful regression cases,
sdist/wheel builds and a fresh installed-wheel CLI flow outside the checkout.
CI repeats it on Ubuntu Python 3.11/3.13, Windows 3.13 and macOS 3.13. Actions have
read-only permissions; complete commit history must match the maintainer's
Author/Committer policy. No runtime dependency or copied implementation is bundled.
See [validation](VALIDATION.md), [provenance](THIRD_PARTY.md),
[contribution policy](CONTRIBUTING.md) and [security reporting](SECURITY.md).

Uninstall using `python -m pip uninstall sri-localcheck`; delete the virtual
environment and checkout as needed. The checker creates no cache/config files
or remote state. MIT license. Future URL/HTML coverage should be driven by real
fixtures and a clear browser-independent contract, not by silent heuristic fixes.
