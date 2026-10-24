"""Reproduce original static fixtures; this is separate from the read-only checker."""

import base64
import hashlib
from pathlib import Path


def token(data, algorithm):
    return algorithm + "-" + base64.b64encode(hashlib.new(algorithm, data).digest()).decode()


def main():
    root = Path(__file__).resolve().parents[1] / "examples/site"
    root.mkdir(parents=True, exist_ok=True)
    js = b"document.documentElement.dataset.demo = 'original';\n"
    css = b"body { color: #2468ac; }\n"
    (root / "app.js").write_bytes(js)
    (root / "style.css").write_bytes(css)
    good = (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">\n'
        f'<link rel="stylesheet" href="style.css" integrity="{token(css, "sha384")}">\n'
        "</head><body><p>Original synthetic fixture</p>\n"
        f'<script src="app.js" integrity="{token(js, "sha384")}"></script>\n'
        "</body></html>\n"
    )
    wrong = token(js, "sha256") + " " + token(b"another revision", "sha512")
    broken = f'<script src="app.js" integrity="{wrong}"></script>\n'
    js_token = token(js, "sha384")
    remote = f'<script src="https://example.test/app.js" integrity="{js_token}"></script>\n'
    for name, markup in (("valid", good), ("broken", broken), ("remote", remote)):
        (root / f"{name}.html").write_text(markup, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
