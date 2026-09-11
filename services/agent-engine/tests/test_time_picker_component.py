"""Tests for the Accessible Futuristic Time Picker & Time Range Suite codegen (R-371).

Verifies:
1. Zero runtime dependencies (pure React).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound exports (TimePicker, TimeRangePicker, TimeInput, TimeColumn, ClockIcon, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. WAI-ARIA 1.2 accessibility semantics (role="combobox", role="listbox", role="option", role="group").
9. 12h and 24h formatting helpers and AM/PM logic.
10. Scrollable TimeColumn subcomponent.
11. Quick presets support.
12. TimeRangePicker dual inputs and hidden inputs.
13. Inline and popover dropdown modes.
14. Hidden input form submission integration.
15. NextjsWebAdapter emits components/time-picker.tsx.
16. Codegen package export render_time_picker_component in __all__.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_time_picker_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestTimePickerComponent(unittest.TestCase):
    """Test suite for components/time-picker.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_time_picker_component()
        self.ir = example_ir("rideshare-favourites")

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for imp in imports:
            self.assertEqual(imp, "react", f"Forbidden external import: {imp}")

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        lines = [line.strip() for line in self.code.splitlines() if line.strip()]
        self.assertEqual(lines[0], '"use client";')

    def test_forward_ref_and_display_name(self) -> None:
        """Must use React.forwardRef and set explicit displayName across compound exports."""
        self.assertIn("forwardRef", self.code)
        self.assertIn('TimePicker.displayName = "TimePicker"', self.code)
        self.assertIn('TimeRangePicker.displayName = "TimeRangePicker"', self.code)
        self.assertIn('TimeInput.displayName = "TimeInput"', self.code)

    def test_exported_types(self) -> None:
        """Must export canonical TypeScript types and interfaces."""
        expected_types = [
            "TimeFormat",
            "TimePickerVariant",
            "TimePickerSize",
            "TimePreset",
            "TimeRangePreset",
            "TimePickerProps",
            "TimeRangePickerProps",
            "TimeInputProps",
        ]
        for t in expected_types:
            self.assertTrue(
                f"export type {t}" in self.code or f"export interface {t}" in self.code,
                f"Missing exported type/interface: {t}",
            )

    def test_compound_exports_and_default(self) -> None:
        """Must export TimePicker, TimeRangePicker, TimeInput, TimeColumn, ClockIcon, and default."""
        self.assertIn("export const TimePicker", self.code)
        self.assertIn("export const TimeRangePicker", self.code)
        self.assertIn("export const TimeInput", self.code)
        self.assertIn("export function TimeColumn", self.code)
        self.assertIn("export function ClockIcon", self.code)
        self.assertIn("export default TimePicker;", self.code)

    def test_four_visual_variants(self) -> None:
        """Must support 'default', 'card', 'glass', 'neon' visual variants."""
        self.assertIn('"default"', self.code)
        self.assertIn('"card"', self.code)
        self.assertIn('"glass"', self.code)
        self.assertIn('"neon"', self.code)
        # Cyberpunk cyan glow and glassmorphism blur
        self.assertTrue(
            "#06b6d4" in self.code or "rgba(6, 182, 212" in self.code,
            "Missing neon cyan glow styling",
        )
        self.assertIn("backdropFilter", self.code)

    def test_three_size_presets(self) -> None:
        """Must support 'sm', 'md', and 'lg' size scales."""
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)
        self.assertIn("SIZE_STYLES", self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must implement WAI-ARIA 1.2 combobox, listbox, and option semantics."""
        self.assertIn('role="combobox"', self.code)
        self.assertIn('role="listbox"', self.code)
        self.assertIn('role="option"', self.code)
        self.assertIn('role="group"', self.code)
        self.assertIn('aria-haspopup="dialog"', self.code)
        self.assertIn("aria-selected", self.code)

    def test_12h_and_24h_formatting_helpers(self) -> None:
        """Must implement 12h/24h conversion helpers and AM/PM logic."""
        self.assertIn("parseTimeString", self.code)
        self.assertIn("formatTimeString", self.code)
        self.assertIn('"12h"', self.code)
        self.assertIn('"24h"', self.code)
        self.assertIn('"AM"', self.code)
        self.assertIn('"PM"', self.code)

    def test_time_column_component(self) -> None:
        """Must render scrollable columns with auto-scroll into view."""
        self.assertIn("TimeColumn", self.code)
        self.assertIn("scrollIntoView", self.code)

    def test_quick_presets_support(self) -> None:
        """Must support quick-select presets chips."""
        self.assertIn("effectivePresets", self.code)
        self.assertIn("preset-", self.code)

    def test_range_picker_dual_inputs(self) -> None:
        """TimeRangePicker must provide dual start and end controls with hidden fields."""
        self.assertIn("handleStartChange", self.code)
        self.assertIn("handleEndChange", self.code)
        self.assertIn("_start", self.code)
        self.assertIn("_end", self.code)

    def test_inline_and_popover_modes(self) -> None:
        """Must support inline mode alongside popover dropdown."""
        self.assertIn("inline", self.code)
        self.assertIn("timepicker-dropdown", self.code)

    def test_hidden_input_form_integration(self) -> None:
        """Must include hidden inputs for native form submission."""
        self.assertIn('type="hidden"', self.code)
        self.assertIn("name", self.code)

    def test_adapter_emits_time_picker_file(self) -> None:
        """NextjsWebAdapter must generate components/time-picker.tsx."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        f = project.get("components/time-picker.tsx")
        self.assertIsNotNone(f, "components/time-picker.tsx must be emitted")
        self.assertEqual(f.content, self.code)

    def test_package_codegen_exports_render_time_picker_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_time_picker_component."""
        self.assertIn("render_time_picker_component", cg.__all__)
        self.assertTrue(callable(cg.render_time_picker_component))
        self.assertEqual(cg.render_time_picker_component(), self.code)

    def test_diff_invariance_across_description(self) -> None:
        """Component code must be 100% diff-invariant across ir.description changes."""
        ir_mod = dataclasses.replace(self.ir, description="Completely changed description for time picker")
        adapter = NextjsWebAdapter()
        f1 = adapter.generate(self.ir).get("components/time-picker.tsx")
        f2 = adapter.generate(ir_mod).get("components/time-picker.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)


if __name__ == "__main__":
    unittest.main()
