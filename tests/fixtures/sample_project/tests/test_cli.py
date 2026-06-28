from sample_project.cli import render_greeting


def test_render_greeting() -> None:
    assert render_greeting("Ada") == "Hello, Ada!"
