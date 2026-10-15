import os

_providers = {}
_closed_sessions = set()


class SessionClosedError(RuntimeError):
    """A late request for an explicitly stopped environment, not missing PI."""
    status_code = 410


def enabled():
    return os.environ.get("PI_ENABLE", "0").lower() in {"1", "true", "yes"}


def register(session_id, provider):
    if session_id in _providers:
        raise RuntimeError(f"PI provider already registered: {session_id}")
    _providers[session_id] = provider
    _closed_sessions.discard(session_id)


def unregister(session_id):
    if _providers.pop(session_id, None) is not None:
        _closed_sessions.add(session_id)


async def capture(session_id):
    if session_id in _closed_sessions:
        raise SessionClosedError(f"PI environment already stopped: {session_id}")
    provider = _providers.get(session_id)
    if provider is None:
        raise RuntimeError(f"No pre-action PI provider for session: {session_id}")
    snapshot = await provider()
    if session_id in _closed_sessions:
        raise SessionClosedError(f"PI environment stopped during capture: {session_id}")
    return snapshot
