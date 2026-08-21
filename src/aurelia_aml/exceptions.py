"""Project-specific exceptions."""


class ConfigurationError(ValueError):
    """Raised when governed configuration is missing or invalid."""


class DataQualityError(ValueError):
    """Raised when an analytical input violates a required control."""
