"""Per-request current-user context.

Lets deeply-nested LLM/embedding call sites (notably the copilot realtime
subsystem) resolve the right user's provider config without threading a
user_id through every signature. Set once at a request/connection boundary;
provider functions read it as a fallback when no explicit user_id is passed.

Each HTTP request / websocket connection serves exactly one user, and
asyncio.create_task / to_thread copy the context, so there is no cross-user
leakage.
"""

import contextvars

_current_user_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "current_user_id", default=None
)


def set_current_user(user_id: str | None):
    """Bind the current user for this context. Returns the token for reset()."""
    return _current_user_id.set(user_id)

def reset_current_user(token) -> None:
    _current_user_id.reset(token)


def get_current_user_id() -> str | None:
    return _current_user_id.get()
