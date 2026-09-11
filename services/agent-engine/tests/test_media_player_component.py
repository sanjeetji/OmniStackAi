"""Tests for the Accessible Futuristic Reusable Media Player Suite codegen (R-376).

Verifies:
1. Zero runtime dependencies (pure React + HTML5 media elements).
2. "use client" directive present.
3. React forwardRef and explicit displayName across compound exports.
4. Exported canonical TypeScript types & interfaces.
5. Compound and semantic alias exports (MediaPlayer, VideoPlayer, AudioPlayer, MediaControls, MediaScrubber, VolumeSlider, default).
6. 4 visual styling variants ("default", "card", "glass", "neon").
7. 3 size presets ("sm", "md", "lg").
8. Dual media modes (video and audio).
9. Interactive scrubber bar with played and buffered progress.
10. Volume slider and mute toggle logic.
11. Playback rate control options (0.5x to 2x).
12. Fullscreen and Picture-in-Picture API handlers.
13. Keyboard navigation shortcuts (Space/K, Arrow keys, M, F, P).
14. WAI-ARIA media semantics (role="region", role="slider", aria-valuenow).
15. Imperative handle methods (play, pause, togglePlay, seek, setVolume, toggleMute, toggleFullscreen, togglePiP, getElement).
16. NextjsWebAdapter emits components/media-player.tsx and codegen package exports render_media_player_component.
17. 100% diff-invariance across ir.description changes.
"""

from __future__ import annotations

import dataclasses
import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_media_player_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter


class TestMediaPlayerComponent(unittest.TestCase):
    """Test suite for components/media-player.tsx codegen."""

    def setUp(self) -> None:
        self.code = render_media_player_component()
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
        self.assertIn('MediaPlayer.displayName = "MediaPlayer"', self.code)
        self.assertIn('VideoPlayer.displayName = "VideoPlayer"', self.code)
        self.assertIn('AudioPlayer.displayName = "AudioPlayer"', self.code)
        self.assertIn('MediaControls.displayName = "MediaControls"', self.code)
        self.assertIn('MediaScrubber.displayName = "MediaScrubber"', self.code)
        self.assertIn('VolumeSlider.displayName = "VolumeSlider"', self.code)

    def test_exported_canonical_types(self) -> None:
        """Canonical TypeScript types must be exported."""
        self.assertIn("export type MediaType =", self.code)
        self.assertIn("export type MediaPlayerVariant =", self.code)
        self.assertIn("export type MediaPlayerSize =", self.code)
        self.assertIn("export type MediaPlaybackRate =", self.code)
        self.assertIn("export interface MediaTrackSource", self.code)
        self.assertIn("export interface MediaSubtitle", self.code)
        self.assertIn("export interface MediaPlayerHandle", self.code)
        self.assertIn("export interface MediaPlayerProps", self.code)
        self.assertIn("export interface MediaScrubberProps", self.code)
        self.assertIn("export interface VolumeSliderProps", self.code)

    def test_compound_and_semantic_exports(self) -> None:
        """Must export MediaPlayer, VideoPlayer, AudioPlayer, MediaControls, MediaScrubber, VolumeSlider, and default export."""
        self.assertIn("export const MediaPlayer =", self.code)
        self.assertIn("export const VideoPlayer =", self.code)
        self.assertIn("export const AudioPlayer =", self.code)
        self.assertIn("export const MediaControls =", self.code)
        self.assertIn("export const MediaScrubber =", self.code)
        self.assertIn("export const VolumeSlider =", self.code)
        self.assertIn("export default MediaPlayer;", self.code)

    def test_visual_variants(self) -> None:
        """Must support 4 visual styling variants."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f'"{variant}"', self.code)
        self.assertIn("backdrop-blur-md", self.code)
        self.assertIn("border-cyan-500", self.code)

    def test_size_presets(self) -> None:
        """Must define sm, md, lg size presets."""
        self.assertIn('"sm"', self.code)
        self.assertIn('"md"', self.code)
        self.assertIn('"lg"', self.code)

    def test_dual_media_modes(self) -> None:
        """Must support both video and audio media modes."""
        self.assertIn('"video"', self.code)
        self.assertIn('"audio"', self.code)
        self.assertIn('type === "video"', self.code)
        self.assertIn("<video", self.code)
        self.assertIn("<audio", self.code)

    def test_interactive_scrubber_and_buffered(self) -> None:
        """Must compute played and buffered progress percentages and handle seek."""
        self.assertIn("playedPercent", self.code)
        self.assertIn("bufferedPercent", self.code)
        self.assertIn("handleSeek", self.code)
        self.assertIn("onSeek", self.code)

    def test_volume_slider_and_mute(self) -> None:
        """Must handle volume change and mute/unmute toggle."""
        self.assertIn("handleVolumeChange", self.code)
        self.assertIn("handleToggleMute", self.code)
        self.assertIn("VolumeSlider", self.code)
        self.assertIn("VolumeMuteIcon", self.code)

    def test_playback_rate_control(self) -> None:
        """Must support configurable playback rates."""
        self.assertIn("handleRateChange", self.code)
        self.assertIn("playbackRate", self.code)
        for rate in ["0.5", "0.75", "1", "1.25", "1.5", "2"]:
            self.assertIn(rate, self.code)

    def test_fullscreen_and_pip(self) -> None:
        """Must support fullscreen and Picture-in-Picture toggling."""
        self.assertIn("requestFullscreen", self.code)
        self.assertIn("requestPictureInPicture", self.code)
        self.assertIn("handleToggleFullscreen", self.code)
        self.assertIn("handleTogglePiP", self.code)

    def test_keyboard_navigation_shortcuts(self) -> None:
        """Must handle keyboard shortcuts for play, seek, volume, mute, fullscreen, and PiP."""
        self.assertIn("handleKeyDown", self.code)
        self.assertIn('"ArrowLeft"', self.code)
        self.assertIn('"ArrowRight"', self.code)
        self.assertIn('"ArrowUp"', self.code)
        self.assertIn('"ArrowDown"', self.code)
        self.assertIn('"m"', self.code)
        self.assertIn('"f"', self.code)
        self.assertIn('"p"', self.code)

    def test_wai_aria_semantics(self) -> None:
        """Must contain WAI-ARIA role and slider attributes for accessibility."""
        self.assertIn('role="region"', self.code)
        self.assertIn('role="slider"', self.code)
        self.assertIn('aria-label="Seek timeline"', self.code)
        self.assertIn('aria-valuenow={currentTime}', self.code)
        self.assertIn('aria-roledescription=', self.code)

    def test_imperative_handle_methods(self) -> None:
        """Must expose imperative control methods via useImperativeHandle."""
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("play:", self.code)
        self.assertIn("pause:", self.code)
        self.assertIn("togglePlay:", self.code)
        self.assertIn("seek:", self.code)
        self.assertIn("setVolume:", self.code)
        self.assertIn("toggleMute:", self.code)
        self.assertIn("toggleFullscreen:", self.code)
        self.assertIn("togglePiP:", self.code)
        self.assertIn("getElement:", self.code)

    def test_nextjs_adapter_and_codegen_exports(self) -> None:
        """NextjsWebAdapter emits components/media-player.tsx and codegen exposes render function."""
        adapter = NextjsWebAdapter()
        project = adapter.generate(self.ir)
        player_file = project.get("components/media-player.tsx")
        self.assertIsNotNone(player_file, "components/media-player.tsx must be generated")
        self.assertEqual(player_file.content, self.code)

        self.assertIn("render_media_player_component", cg.__all__)
        self.assertTrue(callable(cg.render_media_player_component))
        self.assertEqual(cg.render_media_player_component(), self.code)

    def test_diff_invariance(self) -> None:
        """Component code must be 100% diff-invariant across varying IR descriptions."""
        adapter = NextjsWebAdapter()
        ir1 = self.ir
        ir2 = dataclasses.replace(self.ir, description="Modified IR for media player invariance")

        file1 = adapter.generate(ir1).get("components/media-player.tsx")
        file2 = adapter.generate(ir2).get("components/media-player.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
