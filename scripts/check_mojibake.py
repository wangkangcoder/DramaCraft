from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".vue",
    ".css",
    ".html",
    ".json",
    ".md",
    ".bat",
    ".cmd",
    ".ps1",
}
SKIP_PARTS = {
    ".git",
    ".venv",
    ".venv_broken",
    "__pycache__",
    "node_modules",
    ".localtools",
    ".localruntime",
    "run_logs",
    "logs",
    "dist",
}
NON_ASCII_SEGMENT = re.compile(r"[^\x00-\x7f]{4,}")
SUSPICIOUS_MARKERS = set("鍓褰妯璁缁闂鐢娴鎿宸銆锛鈥€")


def should_scan(path: Path) -> bool:
    if not path.is_file():
        return False
    if path.suffix.lower() not in TEXT_SUFFIXES:
        return False
    return not any(part in SKIP_PARTS for part in path.parts)


def likely_mojibake_segment(segment: str) -> tuple[bool, str]:
    if "\ufffd" in segment or any("\ue000" <= ch <= "\uf8ff" for ch in segment):
        return True, "contains replacement/private-use characters"

    if sum(ch in SUSPICIOUS_MARKERS for ch in segment) < 2:
        return False, ""

    try:
        repaired = segment.encode("gb18030").decode("utf-8")
    except Exception:
        return False, ""

    if repaired == segment:
        return False, ""

    han_src = sum("\u4e00" <= ch <= "\u9fff" for ch in segment)
    han_dst = sum("\u4e00" <= ch <= "\u9fff" for ch in repaired)
    bad_dst = repaired.count("\ufffd") + sum("\ue000" <= ch <= "\uf8ff" for ch in repaired)

    if han_dst > han_src and bad_dst == 0:
        return True, f"repair candidate: {repaired[:60]!r}"

    return False, ""


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [(0, "", f"not valid UTF-8: {exc}")]

    findings: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in NON_ASCII_SEGMENT.finditer(line):
            segment = match.group(0)
            bad, reason = likely_mojibake_segment(segment)
            if bad:
                findings.append((line_no, line.strip()[:140], reason))
                break
    return findings


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Detect likely mojibake / wrong-encoding text in source files.")
    parser.add_argument("paths", nargs="*", default=["."], help="Paths to scan.")
    args = parser.parse_args()

    targets = [ROOT / path for path in args.paths]
    files: list[Path] = []
    for target in targets:
        if target.is_file():
            if should_scan(target):
                files.append(target)
            continue
        for path in target.rglob("*"):
            if should_scan(path):
                files.append(path)

    findings_found = False
    for path in sorted(set(files)):
        findings = scan_file(path)
        if not findings:
            continue
        findings_found = True
        print(f"[encoding-check] {path.relative_to(ROOT)}")
        for line_no, preview, reason in findings[:8]:
            print(f"  line {line_no}: {reason}")
            if preview:
                print(f"    {preview}")

    if findings_found:
        print("\n[encoding-check] Likely mojibake detected. Please fix the file in UTF-8 before rebuilding.")
        return 1

    print("[encoding-check] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
