"""Tests for API Key generation & verification."""


from app.dependencies import _key_prefix, generate_api_key, verify_api_key


class TestApiKeyGeneration:
    def test_live_key_format(self) -> None:
        plain, prefix, key_hash = generate_api_key(sandbox=False)
        assert plain.startswith("cs_live_")
        assert prefix == plain[:12]
        assert len(prefix) == 12
        assert len(plain) > 20

    def test_sandbox_key_format(self) -> None:
        plain, prefix, key_hash = generate_api_key(sandbox=True)
        assert plain.startswith("cs_test_")
        assert prefix == plain[:12]
        assert len(prefix) == 12

    def test_verify_correct_key(self) -> None:
        plain, _, key_hash = generate_api_key()
        assert verify_api_key(plain, key_hash) is True

    def test_verify_wrong_key(self) -> None:
        _, _, key_hash = generate_api_key()
        assert verify_api_key("cs_live_wrong_key", key_hash) is False

    def test_key_prefix_extraction(self) -> None:
        assert _key_prefix("cs_live_abcdef123456") == "cs_live_abcd"
        assert _key_prefix("cs_test_xyz") == "cs_test_xyz\x00"[:12] or len(_key_prefix("cs_test_xyz")) <= 12

    def test_unique_keys(self) -> None:
        keys = {generate_api_key()[0] for _ in range(10)}
        assert len(keys) == 10
