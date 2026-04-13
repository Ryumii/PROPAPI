"""Japanese address normalizer.

Flow:
  1. Unicode NFKC normalization
  2. Full-width → half-width digits/hyphens
  3. Strip postal codes (〒106-0031)
  4. English ↔ Japanese place name conversion (Google Maps format)
  5. Kanji numeral → arabic for 丁目/番/号
  6. Hyphen-separated lot parsing  (2-24-12 → 二丁目24番12号)
  7. Build canonical form: 都道府県 + 市区町村 + 町名 + 丁目番号
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

# Postal code pattern:  〒106-0031  /  106-0031  /  1060031
_RE_POSTAL = re.compile(r"〒?\s*\d{3}[-−ー]?\d{4}\s*")

# Google Maps English place names → Japanese
_EN_TO_JA_PREF: dict[str, str] = {
    "hokkaido": "北海道",
    "aomori": "青森県", "iwate": "岩手県", "miyagi": "宮城県",
    "akita": "秋田県", "yamagata": "山形県", "fukushima": "福島県",
    "ibaraki": "茨城県", "tochigi": "栃木県", "gunma": "群馬県",
    "saitama": "埼玉県", "chiba": "千葉県", "tokyo": "東京都",
    "kanagawa": "神奈川県", "niigata": "新潟県", "toyama": "富山県",
    "ishikawa": "石川県", "fukui": "福井県", "yamanashi": "山梨県",
    "nagano": "長野県", "gifu": "岐阜県", "shizuoka": "静岡県",
    "aichi": "愛知県", "mie": "三重県", "shiga": "滋賀県",
    "kyoto": "京都府", "osaka": "大阪府", "hyogo": "兵庫県",
    "nara": "奈良県", "wakayama": "和歌山県", "tottori": "鳥取県",
    "shimane": "島根県", "okayama": "岡山県", "hiroshima": "広島県",
    "yamaguchi": "山口県", "tokushima": "徳島県", "kagawa": "香川県",
    "ehime": "愛媛県", "kochi": "高知県", "fukuoka": "福岡県",
    "saga": "佐賀県", "nagasaki": "長崎県", "kumamoto": "熊本県",
    "oita": "大分県", "miyazaki": "宮崎県", "kagoshima": "鹿児島県",
    "okinawa": "沖縄県",
}

# Major cities / wards  (Google Maps format → Japanese)
_EN_TO_JA_CITY: dict[str, str] = {
    "chiyoda": "千代田区", "chuo": "中央区", "minato": "港区",
    "shinjuku": "新宿区", "bunkyo": "文京区", "taito": "台東区",
    "sumida": "墨田区", "koto": "江東区", "shinagawa": "品川区",
    "meguro": "目黒区", "ota": "大田区", "setagaya": "世田谷区",
    "shibuya": "渋谷区", "nakano": "中野区", "suginami": "杉並区",
    "toshima": "豊島区", "kita": "北区", "arakawa": "荒川区",
    "itabashi": "板橋区", "nerima": "練馬区", "adachi": "足立区",
    "katsushika": "葛飾区", "edogawa": "江戸川区",
    # Common suffixed forms from Google Maps
    "chiyoda city": "千代田区", "chuo city": "中央区", "minato city": "港区",
    "shinjuku city": "新宿区", "bunkyo city": "文京区", "taito city": "台東区",
    "sumida city": "墨田区", "koto city": "江東区", "shinagawa city": "品川区",
    "meguro city": "目黒区", "ota city": "大田区", "setagaya city": "世田谷区",
    "shibuya city": "渋谷区", "nakano city": "中野区", "suginami city": "杉並区",
    "toshima city": "豊島区", "kita city": "北区", "arakawa city": "荒川区",
    "itabashi city": "板橋区", "nerima city": "練馬区", "adachi city": "足立区",
    "katsushika city": "葛飾区", "edogawa city": "江戸川区",
}

# Common town names in Google Maps English
_EN_TO_JA_TOWN: dict[str, str] = {
    "nishiazabu": "西麻布", "higashiazabu": "東麻布", "minamiazabu": "南麻布",
    "motoazabu": "元麻布", "azabudai": "麻布台", "azabujuban": "麻布十番",
    "roppongi": "六本木", "akasaka": "赤坂", "aoyama": "青山",
    "shimbashi": "新橋", "shinbashi": "新橋", "toranomon": "虎ノ門",
    "ginza": "銀座", "nihonbashi": "日本橋", "marunouchi": "丸の内",
    "shibuya": "渋谷", "ebisu": "恵比寿", "daikanyama": "代官山",
    "harajuku": "原宿", "jingumae": "神宮前", "sendagaya": "千駄ヶ谷",
    "shinjuku": "新宿", "kabukicho": "歌舞伎町", "takadanobaba": "高田馬場",
    "ikebukuro": "池袋", "otsuka": "大塚",
    "ueno": "上野", "asakusa": "浅草", "akihabara": "秋葉原",
    "kanda": "神田", "ochanomizu": "御茶ノ水",
    "shinagawa": "品川", "gotanda": "五反田", "osaki": "大崎",
    "meguro": "目黒", "nakameguro": "中目黒",
    "setagaya": "世田谷", "sangenjaya": "三軒茶屋",
    "shimo-kitazawa": "下北沢", "shimokitazawa": "下北沢",
    "nakano": "中野", "koenji": "高円寺", "ogikubo": "荻窪",
}

# Pattern: "X Chome-Y-Z" or "X Chome−Y−Z" (Google Maps English chome format)
_RE_EN_CHOME = re.compile(
    r"(\d+)\s*Chome[−\-](\d+)(?:[−\-](\d+))?",
    re.IGNORECASE,
)


def _strip_postal_code(text: str) -> str:
    """Remove Japanese postal code (〒106-0031, 106-0031, etc.)"""
    return _RE_POSTAL.sub("", text).strip()


def _try_convert_english(text: str) -> str | None:
    """Try to convert Google Maps English format to Japanese.

    Input:  "Minato City, Nishiazabu, 2 Chome-15-12"
    Output: "港区西麻布2-15-12"

    Returns None if the text doesn't look like an English address.
    """
    # Quick check: likely English if it contains ASCII letters
    if not re.search(r"[A-Za-z]", text):
        return None

    # Split by comma, strip each part, reverse order (Google Maps is small→large)
    parts = [p.strip() for p in text.split(",") if p.strip()]

    # Collect translations
    pref_ja = ""
    city_ja = ""
    town_ja = ""
    chome_str = ""
    remaining_parts: list[str] = []

    for part in parts:
        low = part.lower().strip()

        # Check prefecture
        if low in _EN_TO_JA_PREF:
            pref_ja = _EN_TO_JA_PREF[low]
            continue

        # Check town name (before city, so "Shibuya" resolves to town if city is already set)
        if low in _EN_TO_JA_TOWN and (city_ja or not low in _EN_TO_JA_CITY):
            town_ja = _EN_TO_JA_TOWN[low]
            continue

        # Check city (with "City" suffix)
        if low in _EN_TO_JA_CITY:
            city_ja = _EN_TO_JA_CITY[low]
            continue
        # Try without " city" suffix
        bare = re.sub(r"\s+city$", "", low)
        if bare in _EN_TO_JA_CITY:
            city_ja = _EN_TO_JA_CITY[bare]
            continue

        # Check for Chome pattern: "2 Chome-15-12" or "2 Chome−15−12"
        m_chome = _RE_EN_CHOME.search(part)
        if m_chome:
            # Before it, there might be a town name
            before_chome = part[:m_chome.start()].strip().rstrip(",").strip()
            if before_chome:
                t = before_chome.lower()
                town_ja = _EN_TO_JA_TOWN.get(t, before_chome)
            chome_str = m_chome.group(1)
            block = m_chome.group(2)
            lot = m_chome.group(3)
            chome_str = f"{chome_str}-{block}" + (f"-{lot}" if lot else "")
            # After the Chome match, there might be building info
            after_chome = part[m_chome.end():].strip()
            if after_chome:
                remaining_parts.append(after_chome)
            continue

        remaining_parts.append(part)

    # If we matched at least prefecture or city, build Japanese address
    if pref_ja or city_ja:
        result = pref_ja + city_ja + town_ja
        if chome_str:
            result += chome_str
        if remaining_parts:
            result += " " + " ".join(remaining_parts)
        return result

    return None


def _strip_building_name(text: str) -> tuple[str, str]:
    """Separate building name from the address.

    Building patterns (after lot number):
      カルテットビル 1F
      〇〇マンション301
      ABC building

    Returns (address, building_name).
    """
    # If there's a clear address+building split with a known lot pattern,
    # extract building after: 号 / F / 階 or after last number group
    # Match: "...N号<building>" or "...N-N-N<space><building>"
    # Pattern: after 号, anything remaining is building
    m = re.match(
        r"^(.*?\d+号)\s*(.+)$",
        text,
    )
    if m and not re.match(r"^\d", m.group(2)):
        return m.group(1), m.group(2)

    # Pattern: "...N-N-N <building>"  (hyphen lot, then space + non-number)
    m = re.match(
        r"^(.*\d+[-ノの]\d+(?:[-ノの]\d+)?)\s+(\D.+)$",
        text,
    )
    if m:
        return m.group(1), m.group(2)

    return text, ""


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
    - postal codes (〒106-0031, 106-0031)
    - English address format from Google Maps
    - building name separation
    - full-width / half-width mixing
    - kanji numerals in 丁目
    - hyphen-separated block/lot (2-24-12)
    - 「丁目」「番」「号」suffixed numbers
    """
    text = _nfkc(raw.strip())
    text = _fullwidth_to_halfwidth(text)

    # --- strip postal code ---
    text = _strip_postal_code(text)

    # --- try English → Japanese conversion ---
    ja = _try_convert_english(text)
    if ja:
        text = ja

    # --- strip building name early (before address parsing) ---
    text, building_hint = _strip_building_name(text)

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
        result.building = rest or building_hint
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
        result.building = rest or building_hint
        return result

    # Fallback: just keep the rest as town
    result.town = text
    result.building = building_hint
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
