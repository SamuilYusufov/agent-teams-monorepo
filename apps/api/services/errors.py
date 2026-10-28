"""Domain errors raised by the services. The API maps them to 404 and 409 responses."""


class NotFoundError(LookupError):
    """A referenced entity does not exist."""


class ConflictError(ValueError):
    """The operation would violate a business rule (e.g. deleting a project that still has agents)."""
