class SunverseException(Exception):
    """Base exception class that other Sunverse exceptions inherit from."""


class LoginError(SunverseException):
    """An Exception raised when the login fails."""

    def __init__(self, code: int, reason: str):
        message = f"Login to Weverse has failed.\nCode: {code}\nReason: {reason}"
        super().__init__(message)


class RequestFailed(SunverseException):
    """An Exception raised when the response returned by the API is not 200."""

    def __init__(self, url: str, code: int, reason: str):
        message = f"Request to {url} has failed.\nCode: {code}\nReason: {reason}"
        super().__init__(message)


class NotFound(SunverseException):
    """An Exception raised when the response returned by the API is 404."""

    def __init__(self, url: str):
        message = (
            f"Request to {url} has failed.\nCode: 404\n"
            "Reason: The requested resource cannot be found or does not exist."
        )
        super().__init__(message)


class InternalServerError(SunverseException):
    """An Exception raised when the response returned by the API is 500."""

    def __init__(self, url: str):
        message = (
            f"Request to {url} has failed.\nCode: 500\n\n"
            "Reason: The Weverse API encountered an Internal Server Error."
        )
        super().__init__(message)
