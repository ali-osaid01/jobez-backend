class AppException(Exception):
    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: dict | None = None,
    ):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


class ValidationError(AppException):
    def __init__(self, message: str = "Invalid input data", details: dict | None = None):
        super().__init__(400, "VALIDATION_ERROR", message, details)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(401, "UNAUTHORIZED", message)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(403, "FORBIDDEN", message)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(404, "NOT_FOUND", f"{resource} not found")


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(409, "CONFLICT", message)


class InvalidTransitionException(AppException):
    def __init__(self, message: str = "Invalid status transition"):
        super().__init__(422, "INVALID_TRANSITION", message)


class LLMException(AppException):
    def __init__(self, message: str = "AI service unavailable"):
        super().__init__(503, "LLM_ERROR", message)
