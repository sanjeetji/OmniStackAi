"""PC-104: rich text in generated apps.

A rich_text field is edited with tiptap, stored as HTML cleaned on every write by an allowlist
sanitizer (Python nh3, Go bluemonday, Node sanitize-html), and cleaned again (DOMPurify) before the
web and admin apps render it; tables and the mobile app show the words only. The live proof
(CHANGELOG) sent a script, an event handler, a javascript: link, a style, an iframe and an SVG
straight to each generated API; every one was removed while headings, lists, emphasis and links
survived. These tests keep the generated code in that shape.
"""

import json
from dataclasses import replace
from pathlib import Path
from unittest import TestCase

from omnistackai_agent_engine.application_ir import ApplicationIR, example_ir
from omnistackai_agent_engine.application_ir.ir import FieldType
from omnistackai_agent_engine.codegen.assembler import assemble_project
from omnistackai_agent_engine.codegen.rich_text import TAGS

_HUB = Path(__file__).parent / "fixtures" / "ir" / "content_hub.json"


def _hub(backend: str = "python"):
    ir = ApplicationIR.from_dict(json.loads(_HUB.read_text(encoding="utf-8")))
    return assemble_project(replace(ir, project_strategy=replace(ir.project_strategy, backend_strategy=backend)))


def _file(project, suffix: str) -> str:
    return next(f.content for f in project.files() if f.path.endswith(suffix))


class ARichTextFieldIsAType(TestCase):
    def test_the_plan_can_hold_it_and_the_database_stores_text(self) -> None:
        self.assertEqual(FieldType("rich_text"), FieldType.RICH_TEXT)
        project = _hub()
        self.assertIn('"body" TEXT', _file(project, "migrations/0001_init.sql"))
        openapi = json.loads(project.get("contracts/openapi.json").content)
        post = openapi["components"]["schemas"]["Post"]["properties"]["body"]
        self.assertEqual(post.get("contentMediaType"), "text/html")

    def test_the_allowlist_has_formatting_and_nothing_that_runs(self) -> None:
        for tag in ("h2", "strong", "ul", "li", "a", "blockquote"):
            self.assertIn(tag, TAGS)
        for tag in ("script", "iframe", "img", "svg", "style", "object", "form"):
            self.assertNotIn(tag, TAGS)


class EveryBackendCleansItOnWrite(TestCase):
    def test_python_cleans_it_in_the_model(self) -> None:
        project = _hub("python")
        models = _file(project, "app/models.py")
        self.assertIn("@field_validator('body', 'summary', mode=\"before\")", models)
        self.assertIn("return clean_html(value)", models)
        self.assertIn("nh3.clean(", _file(project, "app/rich_text.py"))
        self.assertIn("nh3==", _file(project, "services/api/requirements.txt"))
        compile(models, "models.py", "exec")

    def test_go_cleans_it_after_decoding(self) -> None:
        project = _hub("go")
        models = _file(project, "models/models.go")
        self.assertIn("func (m *Post) SanitizeRichText()", models)
        self.assertIn("richTextPolicy.Sanitize(m.Body)", models)
        self.assertIn("p.RequireNoReferrerOnLinks(true)", models)
        self.assertLess(models.index('"github.com/microcosm-cc/bluemonday"'), models.index('"time"'),
                        "one import block, sorted as gofmt sorts it")
        self.assertEqual(_file(project, "handlers/posts.go").count("m.SanitizeRichText() // PC-104"), 1)
        self.assertIn("github.com/microcosm-cc/bluemonday", _file(project, "go.mod"))

    def test_node_cleans_it_in_validation(self) -> None:
        project = _hub("node")
        validation = _file(project, "validation.ts")
        self.assertIn("import sanitizeHtml from 'sanitize-html';", validation)
        self.assertIn("body: z.string().transform(cleanRichText),", validation)
        self.assertIn('allowedAttributes: { a: ["href", "title", "target", "rel"] }', validation)
        self.assertIn("sanitize-html", json.loads(_file(project, "services/api/package.json"))["dependencies"])

    def test_apps_without_rich_text_are_unchanged(self) -> None:
        blog = assemble_project(example_ir("minimal-blog"))
        self.assertNotIn("field_validator", blog.get("services/api/app/models.py").content)
        self.assertNotIn("nh3", blog.get("services/api/requirements.txt").content)


class TheAppsEditAndShowItSafely(TestCase):
    def setUp(self) -> None:
        self.project = _hub()

    def test_web_forms_use_the_editor_and_tables_show_the_words(self) -> None:
        editor = self.project.get("apps/web/app/post_editor/page.tsx").content
        self.assertIn("<RichTextEditor", editor)
        self.assertIn('import { RichTextEditor } from "@/components/rich-text-editor";', editor)
        # PC-108: the web app's list shows the words as a card's summary; the admin table as a cell.
        listing = self.project.get("apps/web/app/post_list/page.tsx").content
        self.assertIn("plainText(item.summary, 160)", listing, "a plan's summary field is the card's teaser")
        self.assertIn('import { plainText } from "@/components/rich-text";', listing)
        table = self.project.get("apps/admin/app/post_list/page.tsx").content
        self.assertIn("plainText((item as any).body, 60)", table)

    def test_the_view_sanitizes_again_and_never_renders_raw_html_first(self) -> None:
        view = self.project.get("apps/web/components/rich-text.tsx").content
        self.assertIn("DOMPurify.sanitize(", view)
        self.assertIn("if (clean === null) return", view, "until the sanitizer loads, only the words show")
        self.assertIn("ALLOWED_URI_REGEXP: /^(?:https?:|mailto:)/i", view)

    def test_the_admin_console_edits_it_and_requires_words_not_empty_formatting(self) -> None:
        manager = self.project.get("apps/admin/components/admin/entity-manager.tsx").content
        self.assertIn('case "rich_text":', manager)
        self.assertIn("plainText(v).length > 0", manager)
        posts = self.project.get("apps/admin/app/manage/posts/page.tsx").content
        self.assertIn('{ name: "body", label: "Body", kind: "rich_text", required: true, editable: true, inTable: false }', posts)

    def test_the_mobile_app_edits_paragraphs_never_raw_html(self) -> None:
        ir = ApplicationIR.from_dict(json.loads(_HUB.read_text(encoding="utf-8")))
        with_mobile = replace(ir, project_strategy=replace(ir.project_strategy, mobile_profile="react_native"))
        mobile = [f.content for f in assemble_project(with_mobile).files()
                  if f.path.endswith("PostDetailScreen.tsx")]
        self.assertTrue(mobile, "the plan with a mobile app has a post screen")
        self.assertIn(".replace(/<[^>]*>/g, '')", mobile[0])
        self.assertIn("'<p>' + part.trim().replace(/&/g, '&amp;')", mobile[0])

    def test_typography_ships_with_the_app(self) -> None:
        self.assertIn(".rich-text ul { list-style: disc;", self.project.get("apps/web/app/globals.css").content)


class ThePlannerAndThePageWriterKnowIt(TestCase):
    def test_the_prompts_say_when_and_how(self) -> None:
        source = Path(__file__).parents[1].joinpath("src/omnistackai_agent_engine/intake/nl_to_ir.py").read_text()
        self.assertIn('use \\"rich_text\\"', source)
        from omnistackai_agent_engine.codegen.llm_ui import build_ui_synthesis_prompt

        self.assertIn("<RichText html={x}/>", build_ui_synthesis_prompt(example_ir("minimal-blog"), "a blog"))


class TheEditorKeepsWhatIsTyped(TestCase):
    """Found live in the admin console: text typed after a toolbar click vanished."""

    def setUp(self) -> None:
        from omnistackai_agent_engine.codegen.rich_text import RICH_TEXT_EDITOR

        self.editor = RICH_TEXT_EDITOR

    def test_the_extensions_are_created_once(self) -> None:
        # A new StarterKit on every render made tiptap rebuild the editor.
        self.assertIn("const EXTENSIONS = [StarterKit.configure(", self.editor)
        self.assertIn("extensions: EXTENSIONS,", self.editor)
        self.assertIn("}, []);", self.editor)

    def test_a_toolbar_click_does_not_take_focus(self) -> None:
        self.assertIn("onMouseDown={(event) => event.preventDefault()}", self.editor)

    def test_only_a_value_the_editor_never_produced_is_loaded(self) -> None:
        self.assertIn("produced.current.has(value)", self.editor)
        self.assertIn('.replace(/(<p><\\/p>)+$/, "")', self.editor, "the trailing typing line is not saved")


class FormattingAskedForReachesThePlan(TestCase):
    def test_the_prompts_cues_turn_content_fields_into_rich_text(self) -> None:
        from omnistackai_agent_engine.codegen.rich_text import with_rich_text

        blog = example_ir("minimal-blog")
        plain = with_rich_text(blog, "a blog")
        self.assertEqual(plain, blog, "no cue, no change")
        formatted = with_rich_text(blog, "a blog whose posts have a formatted body with headings and lists")
        types = {(e.name, f.name): f.type for e in formatted.entities for f in e.fields}
        self.assertIs(types[("Post", "body")], FieldType.RICH_TEXT)
        self.assertIs(types[("Comment", "body")], FieldType.TEXT, "comments stay plain")

    def test_the_publication_template_writes_articles_in_rich_text(self) -> None:
        from omnistackai_agent_engine.intake import ecosystem

        source = Path(ecosystem.__file__).read_text()
        self.assertIn('Field("body", FieldType.RICH_TEXT), Field("published", FieldType.BOOL)', source)
