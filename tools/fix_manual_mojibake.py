"""Repair cp1252 double-encoding (mojibake) in the source manual.

Some UTF-8 bytes were mis-decoded as Windows-1252 and re-encoded, producing
runs like ``â€”`` for ``—`` or ``5Ã—10â»â´`` for ``5×10⁻⁴``.  This tool
rewrites ONLY runs that begin with a classic mojibake lead character
(Â/Ã/â) followed by cp1252-representable characters; anything else —
including legitimately encoded Unicode — is left byte-for-byte untouched.

Run:  python -m tools.fix_manual_mojibake
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUAL = ROOT / "docs" / "ASTRA_Software_Documentation.md"

LEAD = {"Â", "Ã", "â"}

# Characters the cp1252 codec maps to bytes 0x80-0x9F (plus all Latin-1).
_CP1252_HIGH = {
    "€": 0x80, "‚": 0x82, "ƒ": 0x83, "„": 0x84, "…": 0x85,
    "†": 0x86, "‡": 0x87, "ˆ": 0x88, "‰": 0x89, "Š": 0x8A,
    "‹": 0x8B, "Œ": 0x8C, "Ž": 0x8E, "‘": 0x91, "’": 0x92,
    "“": 0x93, "”": 0x94, "•": 0x95, "–": 0x96, "—": 0x97,
    "˜": 0x98, "™": 0x99, "š": 0x9A, "›": 0x9B, "œ": 0x9C,
    "ž": 0x9E, "Ÿ": 0x9F,
}


def _in_cont(ch: str) -> bool:
    o = ord(ch)
    return 0x80 <= o < 0x100 or ch in _CP1252_HIGH


def _run_bytes(run: str) -> bytes | None:
    out = bytearray()
    for ch in run:
        o = ord(ch)
        if 0x80 <= o < 0x100:
            out.append(o)
        elif ch in _CP1252_HIGH:
            out.append(_CP1252_HIGH[ch])
        else:
            return None
    return bytes(out)


def repair(text: str) -> tuple[str, int]:
    n = len(text)
    i = 0
    fixed = 0
    out: list[str] = []
    while i < n:
        ch = text[i]
        if ch in LEAD and i + 1 < n and _in_cont(text[i + 1]):
            j = i + 1
            while j < n and _in_cont(text[j]):
                j += 1
            run = text[i:j]
            raw = _run_bytes(run)
            try:
                decoded = raw.decode("utf-8") if raw else None
            except UnicodeDecodeError:
                decoded = None
            # Only rewrite when it actually round-trips into valid UTF-8
            # that differs from what a no-op would give.
            if decoded is not None and "�" not in decoded and decoded != run:
                out.append(decoded)
                fixed += 1
                i = j
                continue
        out.append(ch)
        i += 1
    return "".join(out), fixed


def main() -> int:
    src = MANUAL.read_text(encoding="utf-8", newline="")
    fixed_text, count = repair(src)
    MANUAL.write_text(fixed_text, encoding="utf-8", newline="")
    import re
    leftover = len(re.findall(r"[ÂÃâ][\x80-\xff€‚ƒ„…†‡ˆ‰Š‹ŒŽ‘’“”•–—˜™š›œžŸ]", fixed_text))
    print(f"repaired {count} mojibake run(s); suspicious lead-sequences left: {leftover}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
