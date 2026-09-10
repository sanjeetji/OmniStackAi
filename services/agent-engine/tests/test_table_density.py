"""Tests for Task R-311: Generated Collection Table Display Density Toggle.

Verifies that NextjsWebAdapter emits interactive, accessible table density controls
("compact" | "comfortable" | "spacious") with derived cell padding, font size,
and data-density attributes in generated collection screens.
"""

from __future__ import annotations

import unittest

from omnistackai_agent_engine.application_ir import (
    example_ir,
)
from omnistackai_agent_engine.codegen.nextjs import (
    NextjsWebAdapter,
    render_screen_page,
)


class TableDensityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ir = example_ir("minimal-blog")
        self.screen = next(s for s in self.ir.screens if s.id == "post_list")
        self.page = render_screen_page(self.screen, self.ir)

    def test_collection_screen_declares_density_state(self) -> None:
        self.assertIn(
            'const [density, setDensity] = useState<"compact" | "comfortable" | "spacious">("comfortable");',
            self.page,
        )

    def test_collection_screen_computes_density_padding_and_font_size(self) -> None:
        self.assertIn(
            'const densityPadding = density === "compact" ? "6px 12px" : density === "spacious" ? "16px 20px" : "12px 16px";',
            self.page,
        )
        self.assertIn(
            'const densityFontSize = density === "compact" ? 13 : 14;',
            self.page,
        )

    def test_collection_screen_renders_density_toggle_group(self) -> None:
        self.assertIn('role="group"', self.page)
        self.assertIn('aria-label="Table display density"', self.page)

    def test_collection_screen_renders_compact_button(self) -> None:
        self.assertIn('aria-label="Compact density"', self.page)
        self.assertIn('aria-pressed={density === "compact"}', self.page)
        self.assertIn('setDensity("compact")', self.page)

    def test_collection_screen_renders_comfortable_button(self) -> None:
        self.assertIn('aria-label="Comfortable density"', self.page)
        self.assertIn('aria-pressed={density === "comfortable"}', self.page)
        self.assertIn('setDensity("comfortable")', self.page)

    def test_collection_screen_renders_spacious_button(self) -> None:
        self.assertIn('aria-label="Spacious density"', self.page)
        self.assertIn('aria-pressed={density === "spacious"}', self.page)
        self.assertIn('setDensity("spacious")', self.page)

    def test_collection_screen_table_has_data_density_attribute(self) -> None:
        self.assertIn('data-density={density}', self.page)
        self.assertIn('fontSize: densityFontSize', self.page)

    def test_collection_screen_td_cells_use_density_padding(self) -> None:
        self.assertIn('padding: densityPadding', self.page)

    def test_diff_invariance_across_ir_description_changes(self) -> None:
        import dataclasses
        ir1 = example_ir("minimal-blog")
        ir2 = dataclasses.replace(ir1, description="A completely different description")

        s1 = next(s for s in ir1.screens if s.id == "post_list")
        s2 = next(s for s in ir2.screens if s.id == "post_list")
        p1 = render_screen_page(s1, ir1)
        p2 = render_screen_page(s2, ir2)
        self.assertEqual(p1, p2)

    def test_adapter_generate_includes_density_controls(self) -> None:
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        screen_file = project.get("app/post_list/page.tsx")
        self.assertIsNotNone(screen_file)
        self.assertIn('aria-label="Table display density"', screen_file.content)
        self.assertIn('data-density={density}', screen_file.content)


if __name__ == "__main__":
    unittest.main()
