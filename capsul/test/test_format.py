import unittest

from capsul.format import global_formats


class FormatManagerTests(unittest.TestCase):
    def test_formats(self):
        gf = global_formats()
        gf["Raw image"] = ["raw"]
        pri = gf.new_format_list("Possibly raw image")
        pri.extend(gf.formats("BrainVISA image formats"))
        pri.append(gf["Raw image"])

        brainvisa_formats = [
            "JPEG image",
            "GIF image",
            "PNG image",
            "MNG image",
            "BMP image",
            "PBM image",
            "PGM image",
            "PPM image",
            "XBM image",
            "XPM image",
            "TIFF image",
            "TIFF(.tif) image",
        ]
        self.assertEqual(
            [i.label for i in gf.formats("BrainVisa imagE formAts")], brainvisa_formats
        )
        with self.assertRaises(KeyError):
            gf["rAw imAge"] = ["raw"]
        self.assertEqual(
            [i.label for i in gf.formats("Possibly raw image")],
            brainvisa_formats + ["Raw image"],
        )
