"""Small CLI fixture."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class Greeting(BaseModel):
    """Validated greeting input."""

    name: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name cannot be blank")
        return value


def render_greeting(name: str) -> str:
    """Render a greeting with predictable error handling."""

    try:
        greeting = Greeting(name=name)
    except ValueError as exc:
        raise ValueError("invalid greeting name") from exc
    return f"Hello, {greeting.name}!"


def main() -> None:
    """Print a sample greeting."""

    print(render_greeting("Ada"))
