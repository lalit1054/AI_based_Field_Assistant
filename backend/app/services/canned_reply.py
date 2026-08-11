"""Keyword-matched placeholder assistant reply. Milestone 7 (bounded scope).

No LangGraph agent, no LLM call, no streaming — just enough of a server-side
reply so the chat session/message persistence can be built and the frontend's
Ask panel can be wired to a real endpoint. Mirrors the keyword list the
frontend previously used client-side (mockAssistant.ts) so behavior doesn't
regress when the frontend switches to calling this endpoint.
"""

_RESPONSES: list[tuple[list[str], str]] = [
    (
        ["camera", "image", "blank", "frozen", "blurry"],
        "Try power-cycling the camera at the junction box first. If the feed is still frozen "
        "after 30 seconds, check the ethernet cable for looseness — that's the most common "
        "cause on VI units.",
    ),
    (
        ["network", "connectivity", "offline", "wifi", "internet"],
        "Check the status LED on the switch nearest this machine — solid amber usually means "
        "a link-negotiation issue. Power-cycling the switch resolves most of these.",
    ),
    (
        ["crash", "restart", "freeze", "hang"],
        "App crashes on startup are often a corrupted config cache. Try clearing it from the "
        "device settings menu, then restart the app.",
    ),
    (
        ["power", "shutdown", "ups"],
        "If the UPS battery light is red, the unit needs replacement — flag it in the ticket "
        "as a hardware issue.",
    ),
]

_FALLBACK = (
    "I don't have a specific fix for that yet — I'll open a ticket so a technician can take a look."
)


def get_reply(user_message: str) -> str:
    lower = user_message.lower()
    for keywords, reply in _RESPONSES:
        if any(keyword in lower for keyword in keywords):
            return reply
    return _FALLBACK
