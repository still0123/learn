import importlib.util
import unittest
from pathlib import Path

from PIL import Image


SCRIPT = Path(__file__).resolve().parents[1] / "methods" / "av_evidence" / "focus_context.py"
SPEC = importlib.util.spec_from_file_location("focus_context", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FocusContextTest(unittest.TestCase):
    def test_preserves_canvas_and_shows_both_sources(self):
        context = Image.new("RGB", (120, 60), (255, 0, 0))
        focus = Image.new("RGB", (60, 30), (0, 255, 0))
        output = MODULE.compose_focus_context(context, focus, context_fraction=0.5, divider_px=4)
        self.assertEqual(output.size, context.size)
        self.assertEqual(output.getpixel((10, 10)), (255, 0, 0))
        self.assertEqual(output.getpixel((110, 50)), (0, 255, 0))
        self.assertEqual(output.getpixel((60, 29)), (18, 18, 18))

    def test_rejects_extreme_context_fraction(self):
        image = Image.new("RGB", (20, 20), "white")
        with self.assertRaises(ValueError):
            MODULE.compose_focus_context(image, image, context_fraction=0.2)


if __name__ == "__main__":
    unittest.main()
