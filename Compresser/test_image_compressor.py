import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_compressor import CompressionOptions, compress_image


class ImageCompressorTests(unittest.TestCase):
    def test_jpeg_resize_and_compress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "large.jpg"
            output = Path(directory) / "small.jpg"
            Image.new("RGB", (400, 200), "tomato").save(source, quality=100)

            compress_image(source, output, CompressionOptions(quality=60, max_width=100))

            with Image.open(output) as result:
                self.assertEqual(result.size, (100, 50))
                self.assertEqual(result.format, "JPEG")

    def test_animated_gif_keeps_animation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "animation.gif"
            output = Path(directory) / "animation_compressed.gif"
            frames = [
                Image.new("RGBA", (80, 60), (0, 0, 0, 0)),
                Image.new("RGBA", (80, 60), (0, 0, 0, 0)),
            ]
            for x in range(10, 30):
                for y in range(10, 30):
                    frames[0].putpixel((x, y), (255, 0, 0, 255))
                    frames[1].putpixel((x + 30, y), (0, 0, 255, 255))
            frames[0].save(
                source,
                save_all=True,
                append_images=frames[1:],
                duration=[120, 240],
                loop=3,
                disposal=2,
                transparency=0,
            )

            compress_image(
                source,
                output,
                CompressionOptions(max_width=40, gif_colors=32),
            )

            with Image.open(output) as result:
                self.assertTrue(result.is_animated)
                self.assertEqual(result.n_frames, 2)
                self.assertEqual(result.size, (40, 30))
                self.assertEqual(result.info.get("loop"), 3)
                self.assertEqual(result.convert("RGBA").getpixel((0, 0))[3], 0)
                result.seek(1)
                self.assertEqual(result.convert("RGBA").getpixel((0, 0))[3], 0)

    def test_gif_preserves_transparent_pixels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "transparent.gif"
            output = Path(directory) / "transparent_compressed.gif"
            image = Image.new("RGBA", (40, 40), (0, 0, 0, 0))
            for x in range(10, 30):
                for y in range(10, 30):
                    image.putpixel((x, y), (255, 0, 0, 255))
            image.save(source, format="GIF", transparency=0)

            compress_image(source, output, CompressionOptions(gif_colors=32))

            with Image.open(output) as result:
                rgba = result.convert("RGBA")
                self.assertEqual(rgba.getpixel((0, 0))[3], 0)
                self.assertEqual(rgba.getpixel((20, 20))[3], 255)


if __name__ == "__main__":
    unittest.main()
