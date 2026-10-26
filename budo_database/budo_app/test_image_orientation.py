"""Regression coverage for final JPEG bytes, without a second lossy encode."""

from io import BytesIO
import random
import struct
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models.fields.files import ImageFieldFile
from django.test import SimpleTestCase, TestCase, override_settings
from django_resized.forms import ResizedImageFieldFile
from PIL import Image, ImageOps

from .fields import (
    ExifOrientationResetMixin,
    OrientedResizedImageFieldFile,
    reset_jpeg_exif_orientation,
)
from .models import Auslagerorte, AuslagerorteImage


def jpeg_with_exif(orientation=6, endian="<", *, tag=0x0112, kind=3, count=1):
    # Independent, minimal TIFF fixture: header, IFD0, one inline SHORT, next IFD.
    tiff = (b"II" if endian == "<" else b"MM") + struct.pack(endian + "HI", 42, 8)
    tiff += struct.pack(endian + "H", 1)
    tiff += struct.pack(endian + "HHI", tag, kind, count)
    tiff += struct.pack(endian + "H", orientation) + b"\xab\xcd"
    tiff += b"\0" * 4
    app1 = b"Exif\0\0" + tiff
    # Include unrelated APP1/XMP, APP2/ICC and opaque image bytes to detect edits.
    return (
        b"\xff\xd8\xff\xe1\x00\x05xmp"
        + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
        + b"\xff\xe2\x00\x05icc\xff\xda\x00\x02pixels\xff\xd9"
    )


class JpegExifOrientationTest(SimpleTestCase):
    def test_resets_orientations_in_both_byte_orders_changing_only_value(self):
        for endian in ("<", ">"):
            for orientation in range(2, 9):
                with self.subTest(endian=endian, orientation=orientation):
                    original = jpeg_with_exif(orientation, endian)
                    patched = reset_jpeg_exif_orientation(original)
                    self.assertEqual(patched, jpeg_with_exif(1, endian))
                    self.assertEqual(len(patched), len(original))

    def test_unneeded_or_unsupported_patches_return_original_object(self):
        png = BytesIO()
        Image.new("RGB", (3, 2)).save(png, format="PNG")
        for original in (
            jpeg_with_exif(1), jpeg_with_exif(tag=0x010F),
            jpeg_with_exif(kind=4), jpeg_with_exif(count=2),
            b"\xff\xd8\xff\xd9", b"not a jpeg", png.getvalue(), b"",
        ):
            with self.subTest(original=original):
                self.assertIs(reset_jpeg_exif_orientation(original), original)

    def test_truncated_or_malformed_app1_and_tiff_are_unchanged(self):
        valid = jpeg_with_exif()
        # Every truncation before the complete IFD (including its next pointer).
        samples = [valid[:length] for length in range(45)]
        samples += [
            b"\xff\xd8\xff\xe1\x00\x01",  # Invalid segment length.
            b"\xff\xd8\xff\xe1\xff\xffExif\0\0II",  # Beyond file.
            valid.replace(b"II\x2a\x00", b"ZZ\x2a\x00"),
            valid.replace(b"II\x2a\x00", b"II\x2b\x00"),
            valid.replace(b"\x08\x00\x00\x00", b"\xff\xff\xff\xff", 1),
            valid.replace(b"\x08\x00\x00\x00", b"\x00\x00\x00\x00", 1),
            valid.replace(b"\x01\x00\x12\x01", b"\xff\xff\x12\x01", 1),
            b"\xff\xd8" + b"\xff" * (1024 * 1024),
        ]
        for original in samples:
            with self.subTest(original=original[:50]):
                self.assertIs(reset_jpeg_exif_orientation(original), original)

    def test_fuzz_inputs_never_raise(self):
        rng = random.Random(206)
        for length in range(1024):
            raw = rng.randbytes(length)
            for original in (raw, b"\xff\xd8" + raw, b"\xff\xd8\xff\xe1" + raw):
                self.assertIsInstance(reset_jpeg_exif_orientation(original), bytes)

    def test_mro_places_reset_between_resizer_and_django_save(self):
        self.assertEqual(
            OrientedResizedImageFieldFile.__mro__[:4],
            (OrientedResizedImageFieldFile, ResizedImageFieldFile,
             ExifOrientationResetMixin, ImageFieldFile),
        )
        self.assertIs(
            AuslagerorteImage._meta.get_field("image").attr_class,
            OrientedResizedImageFieldFile,
        )


class MirroredLocationImageTest(TestCase):
    def test_mirrored_orientation_is_applied_once(self):
        # Asymmetric quadrants detect the mirror as well as width/height changes.
        source = Image.new("RGB", (1200, 600), "red")
        source.paste("blue", (600, 0, 1200, 300))
        source.paste("green", (0, 300, 600, 600))
        source.paste("yellow", (600, 300, 1200, 600))
        exif = Image.Exif()
        exif[0x0112] = 5
        encoded = BytesIO()
        source.save(encoded, format="JPEG", exif=exif)
        with Image.open(BytesIO(encoded.getvalue())) as original:
            expected = ImageOps.exif_transpose(original)
            expected.thumbnail((1080, 1080), Image.Resampling.LANCZOS)
        with TemporaryDirectory() as root, override_settings(
            MEDIA_ROOT=root,
            STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}},
        ):
            photo = AuslagerorteImage(auslagerort=Auslagerorte.objects.create(name="Mirror"))
            photo.image.save("mirror.jpg", SimpleUploadedFile("mirror.jpg", encoded.getvalue()))
            with photo.image.open("rb") as content, Image.open(content) as stored:
                self.assertEqual(stored.size, (540, 1080))
                self.assertEqual(stored.getexif()[0x0112], 1)
                displayed = ImageOps.exif_transpose(stored)
                self.assertEqual(displayed.size, expected.size)
                for point in ((100, 100), (400, 100), (100, 900), (400, 900)):
                    for actual, wanted in zip(displayed.getpixel(point), expected.getpixel(point)):
                        self.assertLess(abs(actual - wanted), 8)
