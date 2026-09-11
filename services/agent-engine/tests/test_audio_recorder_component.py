"""
R-385: Accessible Futuristic Reusable Audio & Voice Recorder Suite
Unit tests for render_audio_recorder_component and the generated components/audio-recorder.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_audio_recorder_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _AUDIO_RECORDER_COMPONENT


class TestAudioRecorderComponent(unittest.TestCase):
    """Test suite for components/audio-recorder.tsx codegen (R-385)."""

    def setUp(self) -> None:
        self.code = render_audio_recorder_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/audio-recorder.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/audio-recorder.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/audio-recorder.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+"([^"]+)"', self.code)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Forbidden external import detected: {pkg}",
            )

    # ------------------------------------------------------------------
    # 3. TypeScript type interfaces present
    # ------------------------------------------------------------------
    def test_typescript_types_present(self):
        """All required TypeScript type exports must be present."""
        required_types = [
            "AudioRecorderVariant",
            "AudioRecorderSize",
            "RecordingState",
            "WaveformStyle",
            "AudioRecording",
            "AudioRecorderHandle",
            "WaveformVisualizerProps",
            "AudioPlayerBarProps",
            "AudioRecorderProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f'case "{variant}"', self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f'case "{size}"', self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const AudioRecorder",
            "export const VoiceRecorder",
            "export const SoundRecorder",
            "export const WaveformVisualizer",
            "export const AudioPlayerBar",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default AudioRecorderComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 media semantics present
    # ------------------------------------------------------------------
    def test_aria_media_semantics(self):
        """WAI-ARIA 1.2 media & region semantics must be present."""
        for attr in ('role="region"', 'aria-label="Audio Recorder"', 'aria-live="polite"', 'aria-label'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. Recording lifecycle states present
    # ------------------------------------------------------------------
    def test_recording_lifecycle_states(self):
        """Lifecycle states idle, recording, paused, stopped must be handled."""
        for state in ('"idle"', '"recording"', '"paused"', '"stopped"'):
            self.assertIn(state, self.code, f"Missing recording state: {state}")

    # ------------------------------------------------------------------
    # 11. Waveform styles supported
    # ------------------------------------------------------------------
    def test_waveform_styles(self):
        """Waveform styles bars, wave, and mirror must be supported."""
        for style in ('"bars"', '"wave"', '"mirror"'):
            self.assertIn(style, self.code, f"Missing waveform style: {style}")

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose startRecording, stopRecording, pauseRecording, resumeRecording, reset, getRecording."""
        for method in ("startRecording", "stopRecording", "pauseRecording", "resumeRecording", "reset", "getRecording"):
            self.assertIn(method, self.code, f"Missing imperative handle method: {method}")

    # ------------------------------------------------------------------
    # 13. Timer and playback controls
    # ------------------------------------------------------------------
    def test_timer_and_playback_controls(self):
        """Timer formatting, seek bar, and playback controls must be supported."""
        self.assertIn("formatTime", self.code)
        self.assertIn('type="range"', self.code)
        self.assertIn("maxDuration", self.code)

    # ------------------------------------------------------------------
    # 14. Exported in codegen __all__
    # ------------------------------------------------------------------
    def test_package_codegen_exports(self):
        """omnistackai_agent_engine.codegen exposes render_audio_recorder_component."""
        self.assertTrue(hasattr(cg, "render_audio_recorder_component"))
        self.assertIn("render_audio_recorder_component", cg.__all__)

    # ------------------------------------------------------------------
    # 15. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.startswith('"use client"') or self.code.startswith("'use client'"),
            "Component file must start with 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 16. Display names present on exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        for name in ("AudioRecorder", "VoiceRecorder", "SoundRecorder", "WaveformVisualizer", "AudioPlayerBar"):
            self.assertIn(f'{name}.displayName = "{name}"', self.code, f"Missing displayName for {name}")

    # ------------------------------------------------------------------
    # 17. 100% diff-invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated audio recorder content must be identical regardless of ir.description."""
        ir_a = example_ir("rideshare-favourites")
        ir_b = example_ir("minimal-blog")
        project_a = NextjsWebAdapter().generate(ir_a)
        project_b = NextjsWebAdapter().generate(ir_b)
        content_a = project_a.get("components/audio-recorder.tsx")
        content_b = project_b.get("components/audio-recorder.tsx")
        self.assertIsNotNone(content_a)
        self.assertIsNotNone(content_b)
        self.assertEqual(
            content_a.content,
            content_b.content,
            "components/audio-recorder.tsx must be diff-invariant across ir.description changes",
        )


if __name__ == "__main__":
    unittest.main()
