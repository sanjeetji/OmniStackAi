"""R-521: the generated Next.js web app must compile, and sign-up must be wired correctly.

Commit 1fe1015 shipped four defects that `tsc` on a live generated app found at once:
a syntax error in components/toast.tsx (every page 500'd), a mistyped useToast fallback, Python's
`ir.roles` leaking into app/register/page.tsx (ReferenceError on the sign-up page) and a
register() call that did not match `RegisterData` (sign-up always failed). These checks are
offline: a delimiter-balance scan where it is reliable (the toast component and all non-JSX `.ts`
files), a scan of every generated file for leaked Python identifiers, and the exact call shapes.
"""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir.examples import EXAMPLES, example_ir
from omnistackai_agent_engine.codegen import NextjsWebAdapter, render_toast_component

_CLOSERS = {")": "(", "]": "[", "}": "{"}


def unbalanced(source: str) -> str | None:
    """First delimiter problem in TypeScript source, or None.

    Understands '…', "…", template literals (with nested `${…}`) and comments. It does not model
    regex literals or JSX text, so it is only applied to code that has neither.
    """

    stack: list[str] = []
    modes: list[str | None] = [None]  # None = code, else the open quote character
    i, n = 0, len(source)
    while i < n:
        char, mode = source[i], modes[-1]
        if mode in ("'", '"'):
            if char == "\\":
                i += 2
                continue
            if char == mode or char == "\n":
                modes.pop()
            i += 1
            continue
        if mode == "`":
            if char == "\\":
                i += 2
                continue
            if char == "`":
                modes.pop()
            elif source.startswith("${", i):
                stack.append("${")
                modes.append(None)
                i += 2
                continue
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = n if end < 0 else end
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
            continue
        if char in "'\"`":
            modes.append(char)
        elif char in "([{":
            stack.append(char)
        elif char in ")]}":
            line = source.count("\n", 0, i) + 1
            if not stack:
                return f"unexpected {char!r} on line {line}"
            top = stack.pop()
            if top == "${":
                if char != "}":
                    return f"{char!r} closes a template expression on line {line}"
                modes.pop()
            elif top != _CLOSERS[char]:
                return f"{char!r} closes {top!r} on line {line}"
        i += 1
    return f"unclosed {stack[-1]!r}" if stack else None


class DelimiterCheckerTests(unittest.TestCase):
    def test_checker_catches_the_1fe1015_toast_bug_shape(self) -> None:
        self.assertIsNotNone(unbalanced("const t = Object.assign(fn, {\n  a: 1,\n};\n"))
        self.assertIsNone(unbalanced("const t = Object.assign(fn, {\n  a: 1,\n});\n"))
        self.assertIsNone(unbalanced("const s = `a ${fn({ x: '(' })} b`; // ) ]\n/* { */"))


class GeneratedWebAppIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.projects = {name: NextjsWebAdapter().generate(example_ir(name)) for name in EXAMPLES}

    def test_toast_component_delimiters_balance(self) -> None:
        self.assertIsNone(unbalanced(render_toast_component()))

    def test_toast_is_callable_with_variants_including_the_fallback(self) -> None:
        toast = render_toast_component()
        self.assertIn("const toast = Object.assign(toastFn, {", toast)
        self.assertNotRegex(toast, r"Object\.assign\(toastFn, \{[^;]*?\n  \};\n")
        # The fallback outside a provider must also be a callable ToastFn, not a plain object.
        fallback = toast[toast.index("export function useToast"):]
        self.assertIn("toast: Object.assign(() => {}, {", fallback)

    def test_every_generated_ts_file_balances(self) -> None:
        for name, project in self.projects.items():
            for path in project.paths():
                if path.endswith(".ts"):
                    with self.subTest(example=name, path=path):
                        self.assertIsNone(unbalanced(project.get(path).content))

    def test_no_python_identifiers_leak_into_generated_code(self) -> None:
        leak = re.compile(r"\{\s*ir\.|\bir\.(roles|entities|screens|apis|name|brand)\b")
        for name, project in self.projects.items():
            for path in project.paths():
                if path.endswith((".ts", ".tsx", ".js", ".jsx")):
                    with self.subTest(example=name, path=path):
                        self.assertIsNone(leak.search(project.get(path).content))

    def test_register_page_calls_register_with_register_data(self) -> None:
        for name, project in self.projects.items():
            page = project.get("app/register/page.tsx").content
            provider = project.get("components/auth-provider.tsx").content
            with self.subTest(example=name):
                self.assertIn("register: (data: RegisterData) => Promise<void>;", provider)
                self.assertIn("await register({ full_name: fullName, email, password });", page)
                self.assertNotIn("register(fullName", page)

    def test_sign_up_form_offers_no_role_choice(self) -> None:
        # The server assigns the default role, so the form must not pretend the user can pick one.
        for name, project in self.projects.items():
            page = project.get("app/register/page.tsx").content
            with self.subTest(example=name):
                self.assertNotIn("register-role", page)
                self.assertNotIn("setRole", page)


class GeneratedPythonAuthRouterTests(unittest.TestCase):
    """R-521: the generated FastAPI auth router must run on the app's own psycopg helper and must not
    open privilege escalation or account takeover once it works."""

    @classmethod
    def setUpClass(cls) -> None:
        from omnistackai_agent_engine.codegen.auth_guard import python_auth_router_file

        cls.source = python_auth_router_file(example_ir("minimal-blog"))

    def test_router_is_valid_python_using_the_app_db_helper(self) -> None:
        import ast

        tree = ast.parse(self.source)
        self.assertNotIn("get_db_pool", self.source)
        self.assertNotIn("pool.acquire", self.source)
        self.assertIn("from app.db import connect", self.source)
        self.assertNotRegex(self.source, r"\$[0-9]")  # psycopg uses %s placeholders
        assigned = {t.id for n in ast.walk(tree) if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        self.assertIn("DEFAULT_ROLE", assigned)

    def test_self_registration_cannot_choose_a_role(self) -> None:
        register = self.source[self.source.index("async def register"):self.source.index("async def login")]
        self.assertNotIn("body.role", register)
        self.assertIn("DEFAULT_ROLE", register)

    def test_password_reset_by_email_alone_is_refused(self) -> None:
        # R-521 refused every reset until emailed links existed; R-591 added them. The property is
        # unchanged: a reset redeems the one-time token from the link and never trusts an email.
        reset = self.source[self.source.index("async def reset_password"):]
        self.assertIn("WHERE reset_token_hash = %s AND reset_token_expires_at > NOW()", reset)
        self.assertNotIn("email", reset)


if __name__ == "__main__":
    unittest.main()
