"""What every config file loader shares."""


class ConfigError(ValueError):
    """A config file is malformed: a missing, unknown or mistyped field, or a value out of range."""
