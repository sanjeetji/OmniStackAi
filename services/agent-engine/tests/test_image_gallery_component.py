"""Tests for the Accessible Futuristic Image Gallery & Masonry Lightbox Suite (components/image-gallery.tsx)."""

from __future__ import annotations

import re
import unittest
from omnistackai_agent_engine.application_ir import example_ir
from omnistackai_agent_engine.codegen import (
    NextjsWebAdapter,
    render_image_gallery_component,
)


class TestImageGalleryComponent(unittest.TestCase):
    """Unit tests for Accessible Futuristic Image Gallery & Masonry Lightbox Suite (R-394)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_image_gallery_component()

    def test_file_generated(self) -> None:
        """components/image-gallery.tsx must be emitted by NextjsWebAdapter."""
        adapter = NextjsWebAdapter()
        ir = example_ir("minimal-blog")
        project = adapter.generate(ir)
        f = project.get("components/image-gallery.tsx")
        self.assertIsNotNone(f)

    def test_diff_invariance_and_codegen_export(self) -> None:
        """render_image_gallery_component must be exported and output diff-invariant."""
        src1 = render_image_gallery_component()
        adapter = NextjsWebAdapter()
        proj1 = adapter.generate(example_ir("minimal-blog"))
        proj2 = adapter.generate(example_ir("rideshare-favourites"))

        f1 = proj1.get("components/image-gallery.tsx")
        f2 = proj2.get("components/image-gallery.tsx")

        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.content, f2.content)
        self.assertEqual(f1.content, src1)

    def test_zero_runtime_dependencies(self) -> None:
        """Only imports from 'react' are allowed — 0 external npm dependencies."""
        imports = re.findall(r'from\s+[\'"]([^\'"]+)[\'"]', self.source)
        for pkg in imports:
            self.assertTrue(
                pkg.startswith("react") or pkg.startswith("next") or pkg.startswith("."),
                f"Unexpected non-react import found: {pkg}",
            )

    def test_forward_ref_and_imperative_handle(self) -> None:
        """Must wrap component in forwardRef and expose useImperativeHandle with ImageGalleryHandle."""
        self.assertIn("forwardRef<ImageGalleryHandle, ImageGalleryProps>", self.source)
        self.assertIn("useImperativeHandle(", self.source)
        self.assertIn("openLightbox,", self.source)
        self.assertIn("closeLightbox,", self.source)
        self.assertIn("nextImage,", self.source)
        self.assertIn("prevImage,", self.source)
        self.assertIn("startSlideshow,", self.source)
        self.assertIn("stopSlideshow,", self.source)
        self.assertIn("downloadCurrentImage,", self.source)

    def test_typescript_types_present(self) -> None:
        """All required TypeScript type exports must be present."""
        expected_types = [
            "export type ImageGalleryVariant",
            "export type ImageGallerySize",
            "export type GalleryLayout",
            "export interface GalleryItem",
            "export interface ImageGalleryHandle",
            "export interface ImageGalleryToolbarProps",
            "export interface LightboxModalProps",
            "export interface ImageGalleryProps",
        ]
        for t in expected_types:
            self.assertIn(t, self.source, f"Missing TypeScript type export: {t}")

    def test_compound_and_alias_exports(self) -> None:
        """Must export ImageGallery, PhotoGallery, MediaGallery, MasonryGallery, Lightbox, and default export."""
        self.assertIn("export const ImageGallery =", self.source)
        self.assertIn("export const PhotoGallery =", self.source)
        self.assertIn("export const MediaGallery =", self.source)
        self.assertIn("export const MasonryGallery =", self.source)
        self.assertIn("export const Lightbox", self.source)
        self.assertIn("export const ImageGalleryToolbar", self.source)
        self.assertIn("export default ImageGalleryComponent", self.source)

    def test_display_names_defined(self) -> None:
        """Must define explicit displayName on all compound and alias exports."""
        self.assertIn("ImageGalleryToolbar.displayName = 'ImageGalleryToolbar'", self.source)
        self.assertIn("Lightbox.displayName = 'Lightbox'", self.source)
        self.assertIn("ImageGalleryComponent.displayName = 'ImageGallery'", self.source)
        self.assertIn("ImageGallery.displayName = 'ImageGallery'", self.source)
        self.assertIn("PhotoGallery.displayName = 'PhotoGallery'", self.source)
        self.assertIn("MediaGallery.displayName = 'MediaGallery'", self.source)
        self.assertIn("MasonryGallery.displayName = 'MasonryGallery'", self.source)

    def test_variants_present(self) -> None:
        """Must define all 4 required visual styling variants: default, card, glass, neon."""
        self.assertIn("'default' | 'card' | 'glass' | 'neon'", self.source)
        self.assertIn("default: {", self.source)
        self.assertIn("card: {", self.source)
        self.assertIn("glass: {", self.source)
        self.assertIn("neon: {", self.source)

    def test_sizes_present(self) -> None:
        """Must define sm, md, lg size scales."""
        self.assertIn("'sm' | 'md' | 'lg'", self.source)
        self.assertIn("sm: {", self.source)
        self.assertIn("md: {", self.source)
        self.assertIn("lg: {", self.source)

    def test_layouts_present(self) -> None:
        """Must support grid and masonry layouts with dedicated SVG icons."""
        self.assertIn("'grid' | 'masonry'", self.source)
        self.assertIn("GridIcon", self.source)
        self.assertIn("MasonryIcon", self.source)

    def test_lightbox_modal_controls(self) -> None:
        """Must implement full-screen interactive lightbox modal with navigation and zoom."""
        self.assertIn("export const Lightbox", self.source)
        self.assertIn("onClose", self.source)
        self.assertIn("onNext", self.source)
        self.assertIn("onPrev", self.source)
        self.assertIn("isSlideshow", self.source)
        self.assertIn("zoomLevel", self.source)
        self.assertIn("rotation", self.source)

    def test_slideshow_timer_logic(self) -> None:
        """Must implement auto-advancing slideshow mode with start/stop/interval controls."""
        self.assertIn("startSlideshow", self.source)
        self.assertIn("stopSlideshow", self.source)
        self.assertIn("slideshowInterval", self.source)
        self.assertIn("setInterval(", self.source)
        self.assertIn("PlayIcon", self.source)
        self.assertIn("PauseIcon", self.source)

    def test_zoom_and_rotation_controls(self) -> None:
        """Must support zoom in, zoom out, reset zoom, and 90-degree image rotation."""
        self.assertIn("ZoomInIcon", self.source)
        self.assertIn("ZoomOutIcon", self.source)
        self.assertIn("RotateIcon", self.source)
        self.assertIn("zoomIn", self.source)
        self.assertIn("zoomOut", self.source)
        self.assertIn("resetZoom", self.source)
        self.assertIn("rotate", self.source)

    def test_category_and_search_filtering(self) -> None:
        """Must filter items by category pill and real-time search query."""
        self.assertIn("selectedCategory", self.source)
        self.assertIn("searchQuery", self.source)
        self.assertIn("filteredItems", self.source)
        self.assertIn("onSelectCategory", self.source)
        self.assertIn("SearchIcon", self.source)

    def test_thumbnail_strip_navigation(self) -> None:
        """Must render clickable miniature thumbnail preview strip at bottom of lightbox."""
        self.assertIn("onSelectIndex", self.source)
        self.assertIn("Thumbnail Strip", self.source)
        self.assertIn("currentIndex", self.source)

    def test_download_and_like_actions(self) -> None:
        """Must support image download and interactive like/favorite counter."""
        self.assertIn("downloadCurrentImage", self.source)
        self.assertIn("DownloadIcon", self.source)
        self.assertIn("HeartIcon", self.source)
        self.assertIn("toggleLike", self.source)
        self.assertIn("likedMap", self.source)

    def test_wai_aria_accessibility(self) -> None:
        """Must include appropriate WAI-ARIA region, dialog, grid, and toolbar roles."""
        self.assertIn('role="region"', self.source)
        self.assertIn('role="grid"', self.source)
        self.assertIn('role="gridcell"', self.source)
        self.assertIn('role="dialog"', self.source)
        self.assertIn('aria-modal="true"', self.source)
        self.assertIn('role="toolbar"', self.source)


if __name__ == "__main__":
    unittest.main()
