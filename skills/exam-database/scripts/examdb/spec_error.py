"""Error type for invalid schema or query specs."""


class SpecError(Exception):
    """Raised when a spec file is inconsistent; the message names the offending element."""
