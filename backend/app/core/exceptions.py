"""Application errors mapped to standardized API responses."""


class AppError(Exception):
    """Expected failure that should be returned to the client."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: dict | list | None = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(message)
