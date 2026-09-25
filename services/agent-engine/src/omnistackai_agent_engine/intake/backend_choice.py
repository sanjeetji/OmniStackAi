"""Which backend language a prompt asked for (R-565).

`surface_to_ir` hardcoded `BackendStrategy.PYTHON`, so an ecosystem build ignored the language the
user named: "a logistics platform with drivers and dispatchers and the backend should be in Go
language" produced a Python backend and said nothing about it. The single-app path honours the
request — `nl_to_ir` tells the model to choose Go when asked — so the same sentence got a different
answer depending on how many apps the prompt happened to imply.

Deterministic on purpose. The ecosystem planner runs without a model, and a plan that changes
between two runs of the same prompt is one nobody can reason about.

The matching is deliberately narrow. "Go" is an ordinary English word and "node" is a thing in a
graph, so a bare mention is not a request: the language has to appear where someone is saying what
to build with. A prompt about a delivery platform that happens to use the word *go* must not change
anybody's backend.
"""

from __future__ import annotations

import re

from ..application_ir import BackendStrategy

#: The default when a prompt says nothing, and the one documented in the stack policy.
DEFAULT_BACKEND = BackendStrategy.PYTHON

#: Each language, with the words that name it unambiguously. `go` is excluded here and handled
#: below: on its own it is a verb, and "customers go to the restaurant" is not a stack decision.
_UNAMBIGUOUS = {
    BackendStrategy.GO: ("golang",),
    BackendStrategy.NODE: ("node.js", "nodejs", "node js", "express.js"),
    BackendStrategy.PYTHON: ("python", "fastapi", "django", "flask"),
}

#: Words that mean the sentence is about what to build the backend with, rather than about the
#: product. A language name only counts when one of these is near it.
_BACKEND_CONTEXT = (
    "backend",
    "back-end",
    "back end",
    "api",
    "server",
    "service",
    "written in",
    "build it in",
    "use",
)

#: The ambiguous ones, which need the context above: `go` the language versus `go` the verb, and
#: `node` the runtime versus a node in a graph.
_NEEDS_CONTEXT = {
    BackendStrategy.GO: ("go",),
    BackendStrategy.NODE: ("node",),
}

_CONTEXT_WINDOW = 60


def _mentions(text: str, word: str) -> list[int]:
    return [m.start() for m in re.finditer(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text)]


def _near_backend_context(text: str, position: int) -> bool:
    """Whether a language name sits close to a word about building the backend."""
    start = max(0, position - _CONTEXT_WINDOW)
    window = text[start : position + _CONTEXT_WINDOW]
    return any(marker in window for marker in _BACKEND_CONTEXT)


def backend_for_prompt(prompt: str, default: BackendStrategy = DEFAULT_BACKEND) -> BackendStrategy:
    """The backend language this prompt asked for, or `default` when it did not ask.

    Ties go to the first match in a stable order, so the same prompt always gives the same answer.
    """
    text = (prompt or "").lower()
    if not text.strip():
        return default

    for strategy in (BackendStrategy.GO, BackendStrategy.NODE, BackendStrategy.PYTHON):
        for word in _UNAMBIGUOUS.get(strategy, ()):
            if word in text:
                return strategy

    for strategy in (BackendStrategy.GO, BackendStrategy.NODE):
        for word in _NEEDS_CONTEXT.get(strategy, ()):
            if any(_near_backend_context(text, at) for at in _mentions(text, word)):
                return strategy

    return default
