"""Tests for Japanese address normalizer — 20+ test cases."""


from app.utils.address_normalizer import normalize_address


class TestNormalizeAddress:
    """Acceptance: 20+ cases, ≥90% pass rate."""

    def test_standard_kanji_chome(self) -> None:
        r = normalize_address("東京都渋谷区渋谷二丁目24番12号")
        assert r.prefecture == "東京都"
        assert r.city == "渋谷区"
        assert r.town == "渋谷二丁目"
        assert r.block == "24番"
        assert r.lot == "12号"

    def test_arabic_chome_explicit(self) -> None:
        r = normalize_address("東京都渋谷区渋谷2丁目24番12号")
        assert r.town == "渋谷二丁目"
        assert r.block == "24番"

    def test_hyphen_separated(self) -> None:
        r = normalize_address("東京都渋谷区渋谷2-24-12")
        assert r.prefecture == "東京都"
        assert r.city == "渋谷区"
        assert r.town == "渋谷二丁目"
        assert r.block == "24番"
        assert r.lot == "12号"

    def test_fullwidth_hyphen(self) -> None:
        r = normalize_address("東京都渋谷区渋谷２−２４−１２")
        assert r.town == "渋谷二丁目"
        assert r.block == "24番"
        assert r.lot == "12号"

    def test_fullwidth_digits(self) -> None:
        r = normalize_address("東京都新宿区西新宿２丁目８番１号")
        assert r.prefecture == "東京都"
        assert r.city == "新宿区"
        assert r.town == "西新宿二丁目"
        assert r.block == "8番"
        assert r.lot == "1号"

    def test_no_lot(self) -> None:
        r = normalize_address("東京都千代田区丸の内1-9")
        assert r.town == "丸の内一丁目"
        assert r.block == "9番"
        assert r.lot == ""

    def test_chiyoda(self) -> None:
        r = normalize_address("東京都千代田区霞が関1-3-1")
        assert r.prefecture == "東京都"
        assert r.city == "千代田区"
        assert r.town == "霞が関一丁目"
        assert r.block == "3番"
        assert r.lot == "1号"

    def test_minato_ku(self) -> None:
        r = normalize_address("東京都港区六本木6-10-1")
        assert r.town == "六本木六丁目"
        assert r.block == "10番"
        assert r.lot == "1号"

    def test_large_chome(self) -> None:
        r = normalize_address("東京都練馬区大泉学園町8-24-25")
        assert r.town == "大泉学園町八丁目"

    def test_kanji_ten_chome(self) -> None:
        r = normalize_address("東京都江東区豊洲10-2-3")
        assert "十丁目" in r.town

    def test_osaka(self) -> None:
        r = normalize_address("大阪府大阪市北区梅田1-1-3")
        assert r.prefecture == "大阪府"
        assert r.city == "大阪市北区"  # city may grab 大阪市北区 as one unit
        assert "梅田" in r.town

    def test_kanagawa(self) -> None:
        r = normalize_address("神奈川県横浜市中区山下町1-2")
        assert r.prefecture == "神奈川県"

    def test_hokkaido(self) -> None:
        r = normalize_address("北海道札幌市中央区北1条西2-1-1")
        assert r.prefecture == "北海道"

    def test_kyoto_prefix(self) -> None:
        r = normalize_address("京都府京都市中京区河原町通三条1-2-3")
        assert r.prefecture == "京都府"

    def test_normalized_round_trip(self) -> None:
        r = normalize_address("東京都渋谷区渋谷2-24-12")
        assert r.normalized == "東京都渋谷区渋谷二丁目24番12号"

    def test_nfkc_normalization(self) -> None:
        # full-width katakana / spaces
        r = normalize_address("　東京都渋谷区渋谷2-24-12　")
        assert r.prefecture == "東京都"
        assert r.lot == "12号"

    def test_prefecture_detection_all(self) -> None:
        for pref in [
            "東京都", "大阪府", "京都府", "北海道",
            "沖縄県", "愛知県", "福岡県",
        ]:
            r = normalize_address(f"{pref}テスト")
            assert r.prefecture == pref, f"Failed for {pref}"

    def test_empty_input(self) -> None:
        r = normalize_address("")
        assert r.normalized == ""

    def test_no_prefecture(self) -> None:
        r = normalize_address("渋谷区渋谷2-24-12")
        assert r.prefecture == ""
        assert r.city == "渋谷区"
        assert r.town == "渋谷二丁目"

    def test_building_suffix(self) -> None:
        r = normalize_address("東京都渋谷区渋谷2丁目24番12号渋谷ヒカリエ")
        assert r.building == "渋谷ヒカリエ"

    def test_with_no_suffix(self) -> None:
        r = normalize_address("東京都千代田区千代田1-1")
        assert r.town == "千代田一丁目"

    def test_result_repr(self) -> None:
        r = normalize_address("東京都渋谷区渋谷2-24-12")
        assert "NormalizedAddress" in repr(r)
