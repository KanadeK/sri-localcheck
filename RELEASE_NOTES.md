First public release of the offline local-build SRI checker.

- Verify existing script/stylesheet integrity against confined local file bytes.
- Select the strongest SHA-256/384/512 metadata and accept same-strength alternatives.
- Resolve supported local URLs/bases; fail explicitly on remote or unsafe resources.
- Include bounded reads, strict metadata, required-integrity mode and redacted locations.
- Original fixtures, English/Chinese docs and a clean installed-wheel CLI demonstration.
- Python 3.11+, no runtime dependencies. Browser/HTTP validation remains outside scope.
