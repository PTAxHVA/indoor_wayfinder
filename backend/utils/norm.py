import re
from unidecode import unidecode


def normalize_name(s: str) -> str:
    s = s.strip().lower()
    s = unidecode(s)
    s = re.sub(r"[^a-z0-9\s\-_/]", " ", s)
    s = re.sub(r"\s+", " ", s)
    # một vài thay thế đồng nghĩa cơ bản
    s = s.replace("toa ", "toa ").replace("toà ", "toa ")
    s = s.replace("nha ", "toa ").replace("khoi ", "khu ")
    return s.strip()
