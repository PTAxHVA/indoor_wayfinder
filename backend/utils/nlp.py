import re
from typing import Optional, Tuple

# Các mẫu phổ biến: "từ A đến B", "A -> B", "đi từ A tới B", "đến B từ A", "đi tới B"
PATTERNS = [
    r"(?:tu|từ)\s+(?P<a>.+?)\s+(?:den|đến|toi|tới)\s+(?P<b>.+)$",
    r"^(?P<a>.+?)\s*->\s*(?P<b>.+)$",
    r"(?:den|đến|toi|tới)\s+(?P<b>.+)\s+(?:tu|từ)\s+(?P<a>.+)$",
]


def extract_a_b(q: str) -> Tuple[Optional[str], Optional[str]]:
    s = q.strip()
    for pat in PATTERNS:
        m = re.search(pat, s, flags=re.IGNORECASE)
        if m:
            return (m.groupdict().get("a"), m.groupdict().get("b"))
    # Trường hợp chỉ có "đến B" hoặc "tới B": coi A = None
    m2 = re.search(r"(?:den|đến|toi|tới)\s+(?P<b>.+)$", s, flags=re.IGNORECASE)
    if m2:
        return (None, m2.group("b"))
    # Không tách được
    return (None, None)
