"""Use the installed CLI outside the checkout against temporary fixture copies."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    python = Path(sys.argv[1])
    console = python.parent / ("sri-localcheck.exe" if os.name == "nt" else "sri-localcheck")
    subprocess.run([str(console), "--version"], check=True)
    examples = Path(__file__).resolve().parents[1] / "examples/site"
    with tempfile.TemporaryDirectory(prefix="sri-localcheck-demo-") as temp:
        root = Path(temp) / "site"
        shutil.copytree(examples, root)
        (root / "empty.html").write_bytes(b"")
        original = {p.name: p.read_bytes() for p in root.iterdir()}
        for name, status in (("valid", 0), ("broken", 1), ("remote", 1), ("empty", 2)):
            command = [str(python), "-m", "sri_localcheck", str(root), name + ".html", "--json"]
            result = subprocess.run(command, text=True, capture_output=True, check=False)
            report = json.loads(result.stdout)
            if result.returncode != status:
                raise RuntimeError("Installed CLI returned an unexpected status")
            print(name, status, report["status"])
        if original != {p.name: p.read_bytes() for p in root.iterdir()}:
            raise RuntimeError("Checker changed its input")


if __name__ == "__main__":
    main()
