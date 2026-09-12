"""Tests for the Accessible Futuristic Reusable Audio Waveform & Spectrum Visualizer Suite (components/audio-visualizer.tsx)."""

from __future__ import annotations

import re
import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_audio_visualizer_component,
)


class TestAudioVisualizerComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Reusable Audio Waveform & Spectrum Visualizer Suite (R-398)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_audio_visualizer_component()

    def test_file_generated(self) -> None:
        """components/audio-visualizer.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/audio-visualizer.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_audio_visualizer_component must be exported and output diff-invariant."""
        src1 = render_audio_visualizer_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/audio-visualizer.tsx")
        f2 = proj2.get("components/audio-visualizer.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_use_client_directive(self) -> None:
        """Must have 'use client' as first statement for Next.js App Router."""
        self.assertTrue(self.source.startswith("'use client';"))

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with AudioVisualizerHandle."""
        self.assertIn("forwardRef<AudioVisualizerHandle, AudioVisualizerProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("play: handlePlay", self.source)
        self.assertIn("pause: handlePause", self.source)
        self.assertIn("togglePlay: handleTogglePlay", self.source)
        self.assertIn("seek: handleSeek", self.source)
        self.assertIn("setVolume: handleVolumeChange", self.source)
        self.assertIn("setMode: setMode", self.source)
        self.assertIn("getCurrentTime:", self.source)
        self.assertIn("getDuration:", self.source)
        self.assertIn("isPlaying:", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type AudioVisualizerVariant",
            "export type AudioVisualizerSize",
            "export type AudioVisualizerMode",
            "export interface AudioVisualizerHandle",
            "export interface AudioVisualizerControlsProps",
            "export interface AudioVisualizerCanvasProps",
            "export interface AudioVisualizerProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export AudioVisualizer, WaveformVisualizer, SpectrumAnalyzer, Oscilloscope, AudioVisualizerControls, AudioVisualizerCanvas, and default export."""
        self.assertIn("export const AudioVisualizer =", self.source)
        self.assertIn("export const WaveformVisualizer =", self.source)
        self.assertIn("export const SpectrumAnalyzer =", self.source)
        self.assertIn("export const Oscilloscope =", self.source)
        self.assertIn("export const AudioVisualizerControls =", self.source)
        self.assertIn("export const AudioVisualizerCanvas =", self.source)
        self.assertIn("export default AudioVisualizerComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("AudioVisualizerCanvas.displayName = 'AudioVisualizerCanvas'", self.source)
        self.assertIn("AudioVisualizerControls.displayName = 'AudioVisualizerControls'", self.source)
        self.assertIn("AudioVisualizer.displayName = 'AudioVisualizer'", self.source)
        self.assertIn("WaveformVisualizer.displayName = 'WaveformVisualizer'", self.source)
        self.assertIn("SpectrumAnalyzer.displayName = 'SpectrumAnalyzer'", self.source)
        self.assertIn("Oscilloscope.displayName = 'Oscilloscope'", self.source)

    def test_variants_present(self) -> None:
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        self.assertIn("isNeon", self.source)
        self.assertIn("isGlass", self.source)
        self.assertIn("isCard", self.source)

    def test_sizes_present(self) -> None:
        """Must define sm, md, lg size scales."""
        self.assertIn("'sm' | 'md' | 'lg'", self.source)

    def test_visualization_modes_present(self) -> None:
        """Must define bars, wave, spectrum, and circular visualizer modes."""
        self.assertIn("'bars' | 'wave' | 'spectrum' | 'circular'", self.source)
        self.assertIn("mode === 'bars'", self.source)
        self.assertIn("mode === 'wave'", self.source)
        self.assertIn("mode === 'spectrum'", self.source)
        self.assertIn("mode === 'circular'", self.source)

    def test_wai_aria_accessibility(self) -> None:
        """Must include appropriate WAI-ARIA roles, labels, and slider attributes."""
        self.assertIn('role="region"', self.source)
        self.assertIn('aria-label="Audio Visualizer"', self.source)
        self.assertIn('role="toolbar"', self.source)
        self.assertIn('role="slider"', self.source)
        self.assertIn('aria-valuemin={0}', self.source)
        self.assertIn('aria-valuemax={duration || 100}', self.source)
        self.assertIn('aria-valuenow={currentTime}', self.source)

    def test_canvas_rendering_logic(self) -> None:
        """Must implement HTML5 canvas rendering and animation loop."""
        self.assertIn("requestAnimationFrame", self.source)
        self.assertIn("cancelAnimationFrame", self.source)
        self.assertIn("clearRect", self.source)
        self.assertIn("createLinearGradient", self.source)
        self.assertIn("peaksRef", self.source)

    def test_timeline_scrubber_and_time_formatting(self) -> None:
        """Must implement timeline scrubber and MM:SS time formatting helper."""
        self.assertIn("formatAudioTime", self.source)
        self.assertIn("onSeek", self.source)
        self.assertIn("currentTime", self.source)
        self.assertIn("duration", self.source)

    def test_volume_and_mute_controls(self) -> None:
        """Must implement volume slider and mute/unmute toggling."""
        self.assertIn("handleVolumeChange", self.source)
        self.assertIn("handleToggleMute", self.source)
        self.assertIn("VolumeMuteIcon", self.source)
        self.assertIn("VolumeHighIcon", self.source)

    def test_playback_rate_and_keyboard_shortcuts(self) -> None:
        """Must implement playback rate selection and keyboard shortcuts."""
        self.assertIn("playbackRate", self.source)
        self.assertIn("handlePlaybackRateChange", self.source)
        self.assertIn("e.code === 'Space'", self.source)
        self.assertIn("e.code === 'KeyM'", self.source)
        self.assertIn("e.code === 'ArrowRight'", self.source)
        self.assertIn("e.code === 'ArrowLeft'", self.source)

    def test_package_codegen_exports_render_audio_visualizer_component(self) -> None:
        """omnistackai_agent_engine.codegen exposes render_audio_visualizer_component."""
        import omnistackai_agent_engine.codegen as cg

        self.assertTrue(hasattr(cg, "render_audio_visualizer_component"))
        self.assertTrue(callable(cg.render_audio_visualizer_component))
        self.assertIn("render_audio_visualizer_component", cg.__all__)
