"""HEIF decoding with metadata safe to forward to other Pillow encoders."""

from PIL import Image
from pillow_heif import register_heif_opener as register_pillow_heif_opener
from pillow_heif.as_plugin import HeifImageFile


class _MetadataSafeHeifImageFile(HeifImageFile):
    def _init_from_heif_file(self, img_index):
        super()._init_from_heif_file(img_index)
        # Drop every None-valued info key (e.g. exif, xmp, icc_profile,
        # original_orientation), which pillow-heif uses for absent metadata.
        # django-resized forwards info as encoder kwargs; JPEG rejects exif=None.
        # Normalize each frame without discarding any metadata that is present.
        self.info = {key: value for key, value in self.info.items() if value is not None}


def register_heif_opener():
    if Image.OPEN.get("HEIF", (None,))[0] is _MetadataSafeHeifImageFile:
        return
    register_pillow_heif_opener()
    _, accept = Image.OPEN["HEIF"]
    Image.register_open("HEIF", _MetadataSafeHeifImageFile, accept)
