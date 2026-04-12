"""PropAPI exceptions."""


class PropAPIError(Exception):
    """Base exception for PropAPI errors."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[{status_code}] {code}: {message}")


class AuthenticationError(PropAPIError):
    """Raised for 401/403 responses."""


class RateLimitError(PropAPIError):
    """Raised for 429 responses."""

    def __init__(
        self, status_code: int, code: str, message: str, retry_after: int | None = None
    ) -> None:
        super().__init__(status_code, code, message)
        self.retry_after = retry_after
