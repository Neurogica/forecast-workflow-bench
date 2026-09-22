"""Check the Git publication candidate without printing potentially sensitive text."""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "non-English CJK text": r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]",
    "credential pattern": (
        r"sk-proj-[A-Za-z0-9_-]{15,}|hf_[A-Za-z0-9]{20,}|AKIA[A-Z0-9]{16}|"
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "private workstation path": r"/home/" r"ubuntu/|/var/" r"folders/|/Users" r"/",
}
DATA_SUFFIXES = {".csv", ".parquet", ".arrow", ".safetensors", ".pt", ".pth", ".bin"}


def main():
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT
    ).decode().split("\0")
    failures = []
    count = 0
    for name in sorted(set(filter(None, names))):
        path = ROOT / name
        if not path.exists():  # Files removed from a previously committed tree.
            continue
        count += 1
        if path.is_symlink():
            failures.append((name, "symlink requires manual review"))
            continue
        if path.suffix.lower() in DATA_SUFFIXES or path.parts[-1].startswith(".env"):
            if name != ".env.example":
                failures.append((name, "data, weights, or environment file"))
        try:
            contents = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in PATTERNS.items():
            if re.search(pattern, contents):
                failures.append((name, label))
    for name, reason in failures:
        print(f"FAIL {name}: {reason}")
    if failures:
        raise SystemExit(1)
    print(f"Release audit passed for {count} files (known patterns; manual review still required).")


if __name__ == "__main__":
    main()
