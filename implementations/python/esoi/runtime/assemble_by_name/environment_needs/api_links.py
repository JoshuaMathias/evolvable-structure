"""Format the signup and docs links of an API requirement for a person to follow."""

from __future__ import annotations

from esoi.runtime.assemble_by_name.environment_needs.declarations import Api


def link(label: str, url: str) -> str:
    return f"{label}: {url}" if url else ""


def api_hint(item: Api) -> str:
    """The sentence naming how to get the key, from the declared links."""
    names = " or ".join(item.key.names) if item.key else ""
    detail = "; ".join(part for part in (("free key: " + item.signup_url) if item.signup_url else "", link("docs", item.docs_url)) if part)
    text = f"set {names}" + (f" ({detail})" if detail else "")
    return text + (", or leave it unset to use the keyless path" if item.keyless else "")
