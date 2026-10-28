"""API schemas shared between routers."""
from typing import Any

from anthropic.types.beta import BetaManagedAgentsSession
from pydantic import BaseModel, Field

ERROR_DESCRIPTIONS = {
    404: "A referenced entity does not exist.",
    409: "The request conflicts with existing data or a business rule.",
}


class ErrorResponse(BaseModel):
    """Body of 404 and 409 responses."""

    detail: str = Field(description="What went wrong.")


class SessionInfo(BaseModel):
    """A Managed Agents session running an agent."""

    id: str = Field(description="ID of the session in the Managed Agents API.")
    status: str = Field(description="Session status, e.g. `idle` or `running`.")
    title: str | None

    @classmethod
    def from_session(cls, session: BetaManagedAgentsSession) -> SessionInfo:
        return cls(id=session.id, status=session.status, title=session.title)


def errors(*status_codes: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses` documenting the given error status codes."""
    return {code: {"model": ErrorResponse, "description": ERROR_DESCRIPTIONS[code]} for code in status_codes}
