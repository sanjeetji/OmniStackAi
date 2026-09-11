"""
R-389: Accessible Futuristic Reusable Audio Player & Frequency Equalizer Suite
Unit tests for render_audio_player_component and the generated components/audio-player.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_audio_player_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _AUDIO_PLAYER_COMPONENT


class TestAudioPlayerComponent(unittest.TestCase):
    """Test suite for components/audio-player.tsx codegen (R-389)."""

    def setUp(self) -> None:
        self.code = render_audio_player_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/audio-player.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/audio-player.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/audio-player.tsx", paths)

    # ------------------------------------------------------------------
    # 2. Zero external npm dependencies (only 'react' imports allowed)
    # ------------------------------------------------------------------
    def test_zero_runtime_dependencies(self):
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.code)
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
            "AudioPlayerVariant",
            "AudioPlayerSize",
            "AudioTrack",
            "AudioEqualizerBand",
            "AudioEqualizerPreset",
            "AudioPlayerHandle",
            "AudioPlaylistProps",
            "AudioEqualizerProps",
            "AudioPlayerProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. All 4 visual variants present
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """All four visual variants must be implemented: default, card, glass, neon."""
        for variant in ("default", "card", "glass", "neon"):
            self.assertIn(f"'{variant}'", self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. All 3 size scales present
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """All three size scales must be configured: sm, md, lg."""
        for size in ("sm", "md", "lg"):
            self.assertIn(f"'{size}'", self.code, f"Missing size: {size}")

    # ------------------------------------------------------------------
    # 6. Compound and semantic alias exports present
    # ------------------------------------------------------------------
    def test_compound_exports(self):
        """All compound and semantic alias exports must be present."""
        exports = [
            "export const AudioPlayer",
            "export const MusicPlayer",
            "export const SoundPlayer",
            "export const AudioPlaylist",
            "export const AudioEqualizer",
        ]
        for exp in exports:
            self.assertIn(exp, self.code, f"Missing export: {exp}")

    # ------------------------------------------------------------------
    # 7. Default export present
    # ------------------------------------------------------------------
    def test_default_export(self):
        """A default export must be present."""
        self.assertIn("export default AudioPlayerComponent", self.code)

    # ------------------------------------------------------------------
    # 8. WAI-ARIA 1.2 semantics present
    # ------------------------------------------------------------------
    def test_aria_semantics(self):
        """WAI-ARIA 1.2 media & region semantics must be present."""
        for attr in ('role="region"', 'aria-label="Audio Player"'):
            self.assertIn(attr, self.code, f"Missing ARIA attribute: {attr}")

    # ------------------------------------------------------------------
    # 9. forwardRef and useImperativeHandle present
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """forwardRef and useImperativeHandle must be used for the imperative handle API."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)

    # ------------------------------------------------------------------
    # 10. Equalizer bands supported
    # ------------------------------------------------------------------
    def test_equalizer_bands(self):
        """5-band frequencies (60Hz, 250Hz, 1kHz, 4kHz, 16kHz) must be supported."""
        for band in ("'60Hz'", "'250Hz'", "'1kHz'", "'4kHz'", "'16kHz'"):
            self.assertIn(band, self.code, f"Missing frequency band: {band}")

    # ------------------------------------------------------------------
    # 11. Equalizer presets supported
    # ------------------------------------------------------------------
    def test_equalizer_presets(self):
        """Equalizer presets flat, bass_boost, vocal, electronic, rock must be supported."""
        for preset in ("'flat'", "'bass_boost'", "'vocal'", "'electronic'", "'rock'"):
            self.assertIn(preset, self.code, f"Missing equalizer preset: {preset}")

    # ------------------------------------------------------------------
    # 12. Imperative handle methods present
    # ------------------------------------------------------------------
    def test_imperative_handle_methods(self):
        """Imperative handle must expose play, pause, togglePlay, nextTrack, prevTrack, seekTo, setVolume, setSpeed, setEqualizerBand."""
        methods = [
            "play",
            "pause",
            "togglePlay",
            "nextTrack",
            "prevTrack",
            "seekTo",
            "setVolume",
            "setSpeed",
            "setEqualizerBand",
            "getCurrentTrack",
            "isPlaying",
        ]
        for m in methods:
            self.assertIn(m, self.code, f"Missing imperative handle method: {m}")

    # ------------------------------------------------------------------
    # 13. 'use client' directive present
    # ------------------------------------------------------------------
    def test_use_client_directive(self):
        """'use client' must be the first statement for Next.js App Router."""
        self.assertTrue(
            self.code.strip().startswith("'use client'") or self.code.strip().startswith('"use client"'),
            "Missing 'use client' directive",
        )

    # ------------------------------------------------------------------
    # 14. Explicit displayName on compound exports
    # ------------------------------------------------------------------
    def test_display_names(self):
        """All compound exports must have explicit displayName properties."""
        names = [
            'AudioPlayer.displayName = "AudioPlayer"',
            'MusicPlayer.displayName = "MusicPlayer"',
            'SoundPlayer.displayName = "SoundPlayer"',
            'AudioPlaylist.displayName = "AudioPlaylist"',
            'AudioEqualizer.displayName = "AudioEqualizer"',
        ]
        for name in names:
            single_quote = name.replace('"', "'")
            self.assertTrue(
                name in self.code or single_quote in self.code,
                f"Missing displayName: {name}",
            )

    # ------------------------------------------------------------------
    # 15. Diff invariance across ir.description
    # ------------------------------------------------------------------
    def test_diff_invariance_across_description(self):
        """Generated audio player content must be identical regardless of ir.description."""
        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")
        proj1 = NextjsWebAdapter().generate(ir1)
        proj2 = NextjsWebAdapter().generate(ir2)
        self.assertEqual(
            proj1.get("components/audio-player.tsx").content,
            proj2.get("components/audio-player.tsx").content,
        )

    # ------------------------------------------------------------------
    # 16. Package codegen exports render_audio_player_component
    # ------------------------------------------------------------------
    def test_package_codegen_exports(self):
        """omnistackai_agent_engine.codegen exposes render_audio_player_component."""
        self.assertTrue(hasattr(cg, "render_audio_player_component"))
        self.assertIn("render_audio_player_component", cg.__all__)
        self.assertEqual(cg.render_audio_player_component(), _AUDIO_PLAYER_COMPONENT)

    # ------------------------------------------------------------------
    # 17. Time formatting and scrubber logic
    # ------------------------------------------------------------------
    def test_time_formatting_and_scrubber(self):
        """formatTime and scrubber progress calculations must be present."""
        self.assertIn("formatTime", self.code)
        self.assertIn("progressPercent", self.code)
        self.assertIn("currentTime", self.code)
