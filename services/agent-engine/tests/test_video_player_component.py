"""
R-390: Accessible Futuristic Reusable Video Player & Streaming Theater Suite
Unit tests for render_video_player_component and the generated components/video-player.tsx.
"""
from __future__ import annotations

import re
import unittest

from omnistackai_agent_engine.application_ir import example_ir
import omnistackai_agent_engine.codegen as cg
from omnistackai_agent_engine.codegen import render_video_player_component
from omnistackai_agent_engine.codegen.nextjs import NextjsWebAdapter, _VIDEO_PLAYER_COMPONENT


class TestVideoPlayerComponent(unittest.TestCase):
    """Test suite for components/video-player.tsx codegen (R-390)."""

    def setUp(self) -> None:
        self.code = render_video_player_component()
        self.ir = example_ir("rideshare-favourites")
        project = NextjsWebAdapter().generate(self.ir)
        self.file = project.get("components/video-player.tsx")

    # ------------------------------------------------------------------
    # 1. File is generated at the correct path
    # ------------------------------------------------------------------
    def test_file_generated(self):
        """components/video-player.tsx must be emitted by NextjsWebAdapter."""
        ir = example_ir("minimal-blog")
        project = NextjsWebAdapter().generate(ir)
        paths = project.paths()
        self.assertIn("components/video-player.tsx", paths)

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
            "VideoPlayerVariant",
            "VideoPlayerSize",
            "VideoQuality",
            "VideoChapter",
            "VideoCaption",
            "VideoSource",
            "VideoPlayerHandle",
            "VideoControlsProps",
            "VideoPlayerProps",
        ]
        for t in required_types:
            self.assertIn(t, self.code, f"Missing TypeScript type: {t}")

    # ------------------------------------------------------------------
    # 4. Visual variants supported
    # ------------------------------------------------------------------
    def test_variants_present(self):
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        for variant in ["default", "card", "glass", "neon"]:
            self.assertIn(f"'{variant}'", self.code, f"Missing variant: {variant}")

    # ------------------------------------------------------------------
    # 5. Size scales supported
    # ------------------------------------------------------------------
    def test_sizes_present(self):
        """Must define sm, md, lg size scales."""
        for size in ["sm", "md", "lg"]:
            self.assertIn(f"'{size}'", self.code, f"Missing size scale: {size}")

    # ------------------------------------------------------------------
    # 6. Video quality options
    # ------------------------------------------------------------------
    def test_qualities_present(self):
        """Must support auto, 1080p, 720p, 480p, 360p video quality options."""
        for quality in ["auto", "1080p", "720p", "480p", "360p"]:
            self.assertIn(quality, self.code, f"Missing video quality option: {quality}")

    # ------------------------------------------------------------------
    # 7. Playback controls present
    # ------------------------------------------------------------------
    def test_playback_controls_present(self):
        """Must implement play/pause, seek rewind/forward, and time display."""
        self.assertIn("onTogglePlay", self.code)
        self.assertIn("formatVideoTime", self.code)
        self.assertIn("Rewind 10 seconds", self.code)
        self.assertIn("Forward 10 seconds", self.code)

    # ------------------------------------------------------------------
    # 8. Scrubber & chapter markers present
    # ------------------------------------------------------------------
    def test_scrubber_and_chapter_markers_present(self):
        """Must implement timeline scrubber slider, buffered progress, and chapter markers."""
        self.assertIn("scrubberRef", self.code)
        self.assertIn("bufferedPct", self.code)
        self.assertIn("progressPct", self.code)
        self.assertIn("ch.title", self.code)

    # ------------------------------------------------------------------
    # 9. Fullscreen and PiP present
    # ------------------------------------------------------------------
    def test_fullscreen_and_pip_present(self):
        """Must implement fullscreen and picture-in-picture toggling."""
        self.assertIn("toggleFullscreen", self.code)
        self.assertIn("requestFullscreen", self.code)
        self.assertIn("togglePiP", self.code)
        self.assertIn("requestPictureInPicture", self.code)

    # ------------------------------------------------------------------
    # 10. Theater mode present
    # ------------------------------------------------------------------
    def test_theater_mode_present(self):
        """Must implement theater mode layout expansion."""
        self.assertIn("toggleTheater", self.code)
        self.assertIn("isTheater", self.code)
        self.assertIn("theaterMode", self.code)

    # ------------------------------------------------------------------
    # 11. Captions & subtitles support
    # ------------------------------------------------------------------
    def test_captions_subtitles_present(self):
        """Must implement closed captions / subtitles overlay and toggle."""
        self.assertIn("showCaptions", self.code)
        self.assertIn("activeCaption", self.code)
        self.assertIn("onToggleCaptions", self.code)

    # ------------------------------------------------------------------
    # 12. forwardRef and VideoPlayerHandle exposed
    # ------------------------------------------------------------------
    def test_forward_ref_and_imperative_handle(self):
        """Must wrap component in forwardRef and expose useImperativeHandle with VideoPlayerHandle."""
        self.assertIn("forwardRef", self.code)
        self.assertIn("useImperativeHandle", self.code)
        self.assertIn("play", self.code)
        self.assertIn("pause", self.code)
        self.assertIn("seekTo", self.code)
        self.assertIn("setVolume", self.code)
        self.assertIn("getVideoElement", self.code)

    # ------------------------------------------------------------------
    # 13. Explicit displayName defined on compound exports
    # ------------------------------------------------------------------
    def test_display_names_defined(self):
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("VideoPlayerComponent.displayName = 'VideoPlayer'", self.code)
        self.assertIn("VideoControls.displayName = 'VideoControls'", self.code)
        self.assertIn("VideoPlayer.displayName = 'VideoPlayer'", self.code)
        self.assertIn("MoviePlayer.displayName = 'MoviePlayer'", self.code)
        self.assertIn("TheaterPlayer.displayName = 'TheaterPlayer'", self.code)
        self.assertIn("StreamPlayer.displayName = 'StreamPlayer'", self.code)

    # ------------------------------------------------------------------
    # 14. Compound and semantic alias exports
    # ------------------------------------------------------------------
    def test_compound_and_alias_exports(self):
        """Must export VideoPlayer, MoviePlayer, TheaterPlayer, StreamPlayer, VideoControls, and default export."""
        self.assertIn("export const VideoPlayer =", self.code)
        self.assertIn("export const MoviePlayer =", self.code)
        self.assertIn("export const TheaterPlayer =", self.code)
        self.assertIn("export const StreamPlayer =", self.code)
        self.assertIn("export const VideoControls", self.code)
        self.assertIn("export default VideoPlayerComponent", self.code)

    # ------------------------------------------------------------------
    # 15. WAI-ARIA accessibility semantics
    # ------------------------------------------------------------------
    def test_wai_aria_accessibility(self):
        """Must include appropriate WAI-ARIA roles, labels, and value attributes."""
        self.assertIn('role="region"', self.code)
        self.assertIn('role="toolbar"', self.code)
        self.assertIn('role="slider"', self.code)
        self.assertIn('aria-label="Video timeline"', self.code)
        self.assertIn('aria-valuemin={0}', self.code)
        self.assertIn('aria-valuemax=', self.code)

    # ------------------------------------------------------------------
    # 16. Codegen helper function exported from codegen package
    # ------------------------------------------------------------------
    def test_codegen_export_callable(self):
        """render_video_player_component must be callable from omnistackai_agent_engine.codegen."""
        self.assertTrue(hasattr(cg, "render_video_player_component"))
        code = cg.render_video_player_component()
        self.assertIsInstance(code, str)
        self.assertGreater(len(code), 2000)
        self.assertIn("'use client'", code)

    # ------------------------------------------------------------------
    # 17. Snapshot diff invariance across IR descriptions
    # ------------------------------------------------------------------
    def test_diff_invariance_across_ir_descriptions(self):
        """Changing ir.description must not alter components/video-player.tsx output."""
        ir1 = example_ir("rideshare-favourites")
        ir2 = example_ir("minimal-blog")

        p1 = NextjsWebAdapter().generate(ir1)
        p2 = NextjsWebAdapter().generate(ir2)

        file1 = p1.get("components/video-player.tsx")
        file2 = p2.get("components/video-player.tsx")

        self.assertIsNotNone(file1)
        self.assertIsNotNone(file2)
        self.assertEqual(file1.content, file2.content)


if __name__ == "__main__":
    unittest.main()
