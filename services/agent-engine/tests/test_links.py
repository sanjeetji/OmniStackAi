"""PC-125 (with PC-116): every link in a generated app goes to a page that exists in it.

Found by the PC-122 benchmark, in model-designed pages that type-checked: a clinic home page linking to
/privacy and /terms (no such pages) and a services page to /appointment_list (the records are
bookings); a blog linking a post to /posts/${post.id} - a data route that answers JSON.
"""

import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

from omnistackai_agent_engine.verify import links

PAGES = ["/", "/booking_detail", "/booking_list", "/login", "/post_detail", "/post_list", "/service_list"]


def _app(root: Path, pages: list[str], data: list[str] = (), files: dict[str, str] | None = None) -> Path:
    web = root / "apps" / "web"
    for route in pages:
        folder = web / "app" / route.strip("/")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "page.tsx").write_text("export default function P() { return null }\n")
    for route in data:
        folder = web / "app" / route.strip("/")
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "route.ts").write_text("export async function GET() {}\n")
    for path, text in (files or {}).items():
        (web / path).parent.mkdir(parents=True, exist_ok=True)
        (web / path).write_text(text)
    return web


class FindingLinks(TestCase):
    def test_every_way_a_page_navigates(self) -> None:
        text = ('<Link href="/a">x</Link>\n<a href={\'/b\'}>y</a>\n<Link href={`/c?id=${item.id}`}/>\n'
                'router.push("/d"); router.replace(`/e/${id}`); redirect("/f")\n'
                '<a href="https://example.com">x</a> <a href="#top"/> <a href="//cdn.example.com/x"/>\n'
                'text.replace("/not-a-link", "")')
        found = [(l.target, l.route) for l in links.find_links(text)]
        self.assertEqual(found, [("/a", "/a"), ("/b", "/b"), ("/c?id=${item.id}", "/c"), ("/d", "/d"),
                                 ("/e/${id}", "/e/__any__"), ("/f", "/f")])
        self.assertEqual(links.find_links("x\n  <Link href=\"/a\"/>")[0].line, 2)

    def test_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = _app(Path(tmp), ["/", "/(shop)/cart", "/orders/[orderId]", "/docs/[...slug]"], data=["/orders"])
            self.assertEqual(links.page_routes(web), ["/", "/cart", "/docs/[...slug]", "/orders/[orderId]"])
            self.assertEqual(links.data_routes(web), ["/orders"])
        pages = ["/", "/cart", "/docs/[...slug]", "/orders/[orderId]"]
        for route, ok in (("/cart", True), ("/orders/42", True), ("/orders/__any__", True), ("/docs/a/b", True),
                          ("/orders", False), ("/docs", False), ("/carts", False)):
            with self.subTest(route=route):
                self.assertEqual(links.is_page(route, pages), ok)


class CheckingLinks(TestCase):
    def test_what_the_benchmark_found(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            web = _app(Path(tmp), PAGES, data=["/posts", "/posts/[postId]"], files={
                "app/page.tsx": '<a href="/privacy">Privacy</a>\n<Link href="/booking_list">Book</Link>',
                "app/service_list/page.tsx": '<Link href="/appointment_list">See appointments</Link>',
                "components/PostCard.tsx": '<Link href={`/posts/${post.id}`}>Read</Link>',
            })
            errors = links.check_links(web)
        found = {(e.path, e.line): e.message for e in errors}
        self.assertEqual(set(found), {("app/page.tsx", 1), ("app/service_list/page.tsx", 1), ("components/PostCard.tsx", 1)})
        self.assertIn('link "/privacy" goes to no page in this app. Link only to pages that exist: /, /booking_detail',
                      found[("app/page.tsx", 1)])
        self.assertIn("is a data route (it answers JSON), not a page", found[("components/PostCard.tsx", 1)])
        self.assertTrue(all(e.code == "OSA404" for e in errors))

    def test_an_app_without_pages_is_not_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(links.check_links(Path(tmp)), ())


class FixingLinks(TestCase):
    def test_the_nearest_page_that_exists(self) -> None:
        cases = {
            "/appointment_list": "/booking_list",     # the same thing by another name
            "/servce_list": "/service_list",           # a typo
            "/privacy": "/",                           # nothing like it: home, not a 404
            "/booking_editor": "/booking_list",        # no editor: the record's own list
        }
        for route, expected in cases.items():
            with self.subTest(route=route):
                self.assertEqual(links.nearest_page(route, PAGES), expected)

    def test_a_records_data_route_becomes_its_page(self) -> None:
        text, changes = links.fix_links('<Link href={`/posts/${post.id}`}>Read</Link> <a href="/posts">All</a>', PAGES)
        self.assertEqual(text, '<Link href={`/post_detail?id=${post.id}`}>Read</Link> <a href="/post_list">All</a>')
        self.assertEqual(changes, [("/posts/${post.id}", "/post_detail?id=${post.id}"), ("/posts", "/post_list")])

    def test_good_links_are_left_alone(self) -> None:
        text = '<Link href="/booking_list">x</Link> <Link href={`/booking_detail?id=${b.id}`}>y</Link>'
        self.assertEqual(links.fix_links(text, PAGES), (text, []))


class TheRepairLoopUsesIt(TestCase):
    """A dead link goes to the model with the pages that exist; if it is still there in the last round,
    the link is fixed and the rest of the model's page is kept - not thrown away."""

    def test_links_are_fixed_not_the_page_reverted(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.codegen import MARKER_PREFIX
        from omnistackai_agent_engine.codegen.hybrid_repair import compile_and_repair

        ir = example_ir("minimal-blog")
        page = MARKER_PREFIX + ' (m)\nexport default function Home() { return <a href="/appointment_list">Go</a> }\n'
        calls = []

        def runner(argv, cwd, timeout_seconds):
            calls.append(argv)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        class NoModel:
            provider_id = "none"

            async def generate(self, request):
                raise AssertionError("one round: no model call")

        with tempfile.TemporaryDirectory() as tmp:
            web = _app(Path(tmp), ["/", "/post_list", "/post_detail"], files={"app/page.tsx": page})
            (web / "node_modules" / ".bin").mkdir(parents=True)
            (web / "node_modules" / ".bin" / "tsc").write_text("")
            report = asyncio.run(compile_and_repair(repo_dir=tmp, ir=ir, user_prompt="a blog", provider=NoModel(),
                                                    model_id="m", synthesize_screens=True, runner=runner, max_rounds=1))
            on_disk = (web / "app" / "page.tsx").read_text()
        self.assertTrue(report.final_ok)
        self.assertEqual(report.repaired, ("app/page.tsx",))
        self.assertEqual(report.reverted, ())
        self.assertIn('href="/post_list"', on_disk)
        self.assertIn(MARKER_PREFIX, on_disk, "the model's page is kept")


class InvisibleText(TestCase):
    """Found by the PC-122 benchmark: `text-muted` is the page's own background colour (contrast 1.00:1)."""

    def test_surface_colours_used_as_text(self) -> None:
        from omnistackai_agent_engine.verify.tokens import fix_invisible_text

        text = ('<p className="text-lg text-muted mb-6">a</p> <span className="hover:text-accent text-card/80">b</span>'
                ' <i className="text-muted-foreground text-primary text-background bg-muted">c</i>')
        fixed, count = fix_invisible_text(text)
        self.assertEqual(count, 3)
        self.assertIn('className="text-lg text-muted-foreground mb-6"', fixed)
        self.assertIn('hover:text-accent-foreground text-card-foreground/80', fixed)
        self.assertIn("text-muted-foreground text-primary text-background bg-muted", fixed, "real text colours stay")

    def test_the_repair_loop_fixes_model_pages_only(self) -> None:
        from omnistackai_agent_engine.application_ir import example_ir
        from omnistackai_agent_engine.codegen import MARKER_PREFIX
        from omnistackai_agent_engine.codegen.hybrid_repair import compile_and_repair

        page = MARKER_PREFIX + ' (m)\nexport default function Home() { return <p className="text-muted">Hi</p> }\n'
        template = 'export function Footer() { return <p className="text-muted">kept as written</p> }\n'

        def runner(argv, cwd, timeout_seconds):
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            web = _app(Path(tmp), ["/"], files={"app/page.tsx": page, "components/Footer.tsx": template})
            (web / "node_modules" / ".bin").mkdir(parents=True)
            (web / "node_modules" / ".bin" / "tsc").write_text("")
            report = asyncio.run(compile_and_repair(repo_dir=tmp, ir=example_ir("minimal-blog"), user_prompt="a blog",
                                                    provider=None, model_id="m", synthesize_screens=True, runner=runner))
            self.assertIn('className="text-muted-foreground"', (web / "app" / "page.tsx").read_text())
            self.assertEqual((web / "components" / "Footer.tsx").read_text(), template)
        self.assertEqual(report.repaired, ("app/page.tsx",))
