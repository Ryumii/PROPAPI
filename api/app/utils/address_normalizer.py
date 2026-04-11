"""Japanese address normalizer.

Flow:
  1. Unicode NFKC normalization
  2. Full-width → half-width digits/hyphens
  3. Kanji numeral → arabic for 丁目/番/号
  4. Hyphen-separated lot parsing  (2-24-12 → 二丁目24番12号)
  5. Build canonical form: 都道府県 + 市区町村 + 町名 + 丁目番号
"""

from __future__ import annotations

import re
import unicodedata

# ---------- lookup tables --------------------------------------------------

_KANJI_DIGITS: dict[str, int] = {
    "〇": 0, "一": 1, "二": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
    "十": 10,
}

_ARABIC_TO_KANJI: dict[int, str] = {
    1: "一", 2: "二", 3: "三", 4: "四", 5: "五",
    6: "六", 7: "七", 8: "八", 9: "九", 10: "十",
    11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五",
    16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十",
}

# Prefectures (47)
_PREFECTURES = [
    "北海道",
    "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県",
    "岐阜県", "静岡県", "愛知県", "三重県",
    "滋賀県", "京都府", "大阪府", "兵庫県", "奈良県", "和歌山県",
    "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県",
    "福岡県", "佐賀県", "長崎県", "熊本県", "大分県", "宮崎県", "鹿児島県",
    "沖縄県",
]

# ---------- helpers --------------------------------------------------------


def _nfkc(text: str) -> str:
    """Unicode NFKC normalization (full→half width, etc.)."""
    return unicodedata.normalize("NFKC", text)


def _fullwidth_to_halfwidth(text: str) -> str:
    """Replace remaining full-width digits & all hyphen-like chars."""
    table = str.maketrans(
        "０１２３４５６７８９",
        "0123456789",
    )
    text = text.translate(table)
    # Normalize all dash / hyphen variants to ASCII hyphen-minus
    text = re.sub(r"[ー－—–‐‑−\u2212\uFF0D\u2013\u2014\u2010\u2011\u30FC]", "-", text)
    return text


def _kanji_number_to_int(s: str) -> int | None:
    """Convert kanji numeral string to int.  e.g. '十二' → 12, '三' → 3."""
    if not s:
        return None
    # simple single-digit or known compound
    if s in _KANJI_DIGITS:
        return _KANJI_DIGITS[s]
    # pattern: X十Y
    m = re.match(r"([一二三四五六七八九]?)十([一二三四五六七八九]?)", s)
    if m:
        tens = _KANJI_DIGITS.get(m.group(1), 1) if m.group(1) else 1
        ones = _KANJI_DIGITS.get(m.group(2), 0) if m.group(2) else 0
        return tens * 10 + ones
    # single kanji digit
    if len(s) == 1 and s in _KANJI_DIGITS:
        return _KANJI_DIGITS[s]
    return None


def _int_to_kanji(n: int) -> str:
    """Convert small int to kanji.  e.g. 12 → '十二'."""
    if n in _ARABIC_TO_KANJI:
        return _ARABIC_TO_KANJI[n]
    if 1 <= n <= 99:
        tens, ones = divmod(n, 10)
        parts: list[str] = []
        if tens >= 2:
            parts.append(_ARABIC_TO_KANJI.get(tens, str(tens)))
        if tens >= 1:
            parts.append("十")
        if ones:
            parts.append(_ARABIC_TO_KANJI.get(ones, str(ones)))
        return "".join(parts)
    return str(n)


# ---------- public ---------------------------------------------------------


class NormalizedAddress:
    """Result of address normalization."""

    def __init__(
        self,
        *,
        prefecture: str = "",
        city: str = "",
        town: str = "",
        block: str = "",
        lot: str = "",
        building: str = "",
        raw: str = "",
    ) -> None:
        self.prefecture = prefecture
        self.city = city
        self.town = town
        self.block = block
        self.lot = lot
        self.building = building
        self.raw = raw

    @property
    def normalized(self) -> str:
        """Canonical address string."""
        parts = [self.prefecture, self.city, self.town]
        if self.block:
            parts.append(self.block)
        if self.lot:
            parts.append(self.lot)
        if self.building:
            parts.append(self.building)
        return "".join(parts)

    def __repr__(self) -> str:
        return f"NormalizedAddress({self.normalized!r})"


def normalize_address(raw: str) -> NormalizedAddress:
    """Normalize a Japanese address string.

    Handles:
    - full-width / half-width mixing
    - kanji numerals in 丁目
    - hyphen-separated block/lot (2-24-12)
    - 「丁目」「番」「号」suffixed numbers
    """
    text = _nfkc(raw.strip())
    text = _fullwidth_to_halfwidth(text)

    result = NormalizedAddress(raw=raw)

    # --- extract prefecture ---
    for pref in _PREFECTURES:
        if text.startswith(pref):
            result.prefecture = pref
            text = text[len(pref):]
            break

    # --- extract city (市区町村) ---
    # Handle 政令指定都市+区  e.g. "大阪市北区", "横浜市中区"  first
    designated_city = re.match(r"^(.+市.+?区)", text)
    if designated_city:
        result.city = designated_city.group(1)
        text = text[designated_city.end():]
    else:
        city_pattern = re.compile(
            r"^(.+?[市区町村])"  # greedy-minimal up to 市区町村
        )
        m = city_pattern.match(text)
        if m:
            result.city = m.group(1)
            text = text[m.end():]

    # --- parse remaining: town + ( 丁目 / block / lot / building ) ---
    # Try explicit 丁目番号 pattern first
    #   e.g. "渋谷二丁目24番12号", "渋谷2丁目24番12号"
    explicit = re.match(
        r"^(.+?)"                                     # town name
        r"([一二三四五六七八九十\d]+)丁目"             # chome
        r"(\d+)番"                                      # block
        r"(\d+)号?"                                     # lot
        r"(.*)",                                        # rest (building)
        text,
    )
    if explicit:
        result.town = _format_town(explicit.group(1), explicit.group(2))
        result.block = f"{explicit.group(3)}番"
        result.lot = f"{explicit.group(4)}号"
        rest = explicit.group(5).strip()
        if rest:
            result.building = rest
        return result

    # Try hyphen pattern:  "渋谷2-24-12"
    hyphen = re.match(
        r"^(.+?)"                    # town name
        r"(\d+)"                     # chome (numeric)
        r"[-ノの]"
        r"(\d+)"                     # block
        r"(?:[-ノの](\d+))?"         # lot (optional)
        r"(.*)",
        text,
    )
    if hyphen:
        chome_num = int(hyphen.group(2))
        result.town = _format_town(hyphen.group(1), str(chome_num))
        result.block = f"{hyphen.group(3)}番"
        if hyphen.group(4):
            result.lot = f"{hyphen.group(4)}号"
        rest = hyphen.group(5).strip()
        if rest:
            result.building = rest
        return result

    # Fallback: just keep the rest as town
    result.town = text
    return result


def _format_town(town_base: str, chome_val: str) -> str:
    """Build e.g. '渋谷二丁目' from town_base='渋谷' and chome_val='2'."""
    # If chome_val is already kanji, keep it
    kanji_num = _kanji_number_to_int(chome_val)
    if kanji_num is not None:
        kanji = _int_to_kanji(kanji_num)
    else:
        try:
            kanji = _int_to_kanji(int(chome_val))
        except ValueError:
            kanji = chome_val
    return f"{town_base}{kanji}丁目"
