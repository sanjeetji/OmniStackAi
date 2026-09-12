"""Tests for the Accessible Futuristic Particle Network & Interactive Constellation Canvas Suite (components/particle-network.tsx)."""

from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine import codegen as cg
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_particle_network_component,
)


class TestParticleNetworkComponent(unittest.TestCase):
    """Unit tests for the Accessible Futuristic Particle Network Suite (R-399)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_particle_network_component()

    def test_file_generated(self) -> None:
        """components/particle-network.tsx must be emitted by NextjsWebAdapter."""
        project = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        self.assertIsNotNone(project.get("components/particle-network.tsx"))

    def test_diff_invariance_and_codegen_export(self) -> None:
        """Output must be byte-identical across ir.description and equal to the accessor."""
        proj1 = NextjsWebAdapter().generate(example_ir("minimal-blog"))
        proj2 = NextjsWebAdapter().generate(example_ir("rideshare-favourites"))
        f1 = proj1.get("components/particle-network.tsx")
        f2 = proj2.get("components/particle-network.tsx")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, render_particle_network_component())

    def test_use_client_directive(self) -> None:
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        """Only react / next / relative imports are allowed."""
        for pkg in re.findall(r"from\s+['\"]([^'\"]+)['\"]", self.source):
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected import: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        self.assertIn("forwardRef<ParticleNetworkHandle, ParticleNetworkProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        for method in ("pause:", "resume:", "toggle:", "restart:", "isPaused:", "getCanvas:"):
            self.assertIn(method, self.source)

    def test_typescript_types_present(self) -> None:
        for decl in (
            "export type ParticleNetworkVariant",
            "export type ParticleNetworkSize",
            "export interface ParticleNetworkHandle",
            "export interface ParticleNetworkProps",
        ):
            self.assertIn(decl, self.source)

    def test_compound_and_alias_exports(self) -> None:
        for decl in (
            "export const ParticleNetwork =",
            "export const ConstellationCanvas =",
            "export const ParticleField =",
            "export const StarfieldBackground =",
            "export default ParticleNetworkComponent",
        ):
            self.assertIn(decl, self.source)

    def test_display_names_defined(self) -> None:
        for line in (
            "ParticleNetworkComponent.displayName = 'ParticleNetwork'",
            "ConstellationCanvas.displayName = 'ConstellationCanvas'",
            "ParticleField.displayName = 'ParticleField'",
            "StarfieldBackground.displayName = 'StarfieldBackground'",
        ):
            self.assertIn(line, self.source)

    def test_variants_present(self) -> None:
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        for key in ("default: {", "card: {", "glass: {", "neon: {"):
            self.assertIn(key, self.source)

    def test_sizes_present(self) -> None:
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        for key in ("sm: {", "md: {", "lg: {"):
            self.assertIn(key, self.source)

    def test_canvas_animation_loop(self) -> None:
        for token in (
            "requestAnimationFrame",
            "cancelAnimationFrame",
            "getContext('2d')",
            "clearRect",
            ".arc(",
        ):
            self.assertIn(token, self.source)

    def test_prefers_reduced_motion(self) -> None:
        self.assertIn("matchMedia('(prefers-reduced-motion: reduce)')", self.source)
        self.assertIn("reducedMotionRef", self.source)
        self.assertIn("addEventListener('change'", self.source)
        self.assertIn(".matches", self.source)

    def test_pointer_interaction(self) -> None:
        for token in ("pointermove", "pointerleave", "interactionRadius", "pointerRef"):
            self.assertIn(token, self.source)

    def test_link_lines(self) -> None:
        for token in ("linkDistance", "globalAlpha", "moveTo", "lineTo", "Math.hypot"):
            self.assertIn(token, self.source)

    def test_dpr_and_resize(self) -> None:
        self.assertIn("devicePixelRatio", self.source)
        self.assertIn("ctx.scale(", self.source)
        self.assertIn("addEventListener('resize'", self.source)

    def test_wai_aria_semantics(self) -> None:
        self.assertIn('role="img"', self.source)
        self.assertIn('aria-hidden="true"', self.source)
        self.assertIn("aria-label", self.source)

    def test_ambient_no_required_data_props(self) -> None:
        """Particles are generated internally; there is no required data prop."""
        self.assertIn("particlesRef", self.source)
        self.assertIn("density", self.source)
        self.assertIn("count", self.source)
        self.assertNotIn("nodes:", self.source)
        self.assertNotIn("edges:", self.source)

    def test_package_codegen_export(self) -> None:
        self.assertTrue(hasattr(cg, "render_particle_network_component"))
        self.assertTrue(callable(cg.render_particle_network_component))
        self.assertIn("render_particle_network_component", cg.__all__)


if __name__ == "__main__":
    unittest.main()
