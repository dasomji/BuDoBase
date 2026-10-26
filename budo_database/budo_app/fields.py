"""Location image fields: preserve metadata without applying orientation twice."""

import struct

from django.core.files.base import ContentFile
from django.db.models.fields.files import ImageFieldFile
from django_resized import ResizedImageField as DjangoResizedImageField
from django_resized.forms import ResizedImageFieldFile


def reset_jpeg_exif_orientation(data: bytes) -> bytes:
    """Reset the inline IFD0 SHORT in a JPEG's EXIF, without re-encoding pixels.

    Inspect only the pre-scan JPEG header (at most 1 MiB / 4096 markers).
    TIFF reads stay inside APP1's 16-bit length; cap IFD0 at 4096 entries.
    Unsupported or malformed headers are deliberately left untouched.
    """
    if not data.startswith(b"\xff\xd8"):
        return data
    limit = min(len(data), 1024 * 1024)
    position = 2
    for _ in range(4096):
        if position >= limit or data[position] != 0xFF:
            return data
        while position < limit and data[position] == 0xFF:
            position += 1
        if position >= limit:
            return data
        marker = data[position]
        position += 1
        if marker in (0x00, 0xD8, 0xD9, 0xDA):
            return data
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue  # Standalone markers carry no length.
        if position + 2 > limit:
            return data
        length = struct.unpack_from(">H", data, position)[0]
        end = position + length
        if length < 2 or end > limit:
            return data
        start = position + 2
        position = end
        if marker != 0xE1 or data[start:start + 6] != b"Exif\0\0":
            continue
        tiff = start + 6
        if tiff + 8 > end:
            return data
        byte_order = data[tiff:tiff + 2]
        if byte_order not in (b"II", b"MM"):
            return data
        endian = "<" if byte_order == b"II" else ">"
        magic, offset = struct.unpack_from(endian + "HI", data, tiff + 2)
        if magic != 42 or offset < 8:
            return data
        ifd = tiff + offset
        if ifd + 2 > end:
            return data
        count = struct.unpack_from(endian + "H", data, ifd)[0]
        if count > 4096 or ifd + 2 + count * 12 + 4 > end:
            return data
        for entry in range(ifd + 2, ifd + 2 + count * 12, 12):
            tag, kind, values = struct.unpack_from(endian + "HHI", data, entry)
            if tag != 0x0112:
                continue
            if kind != 3 or values != 1:
                return data
            value = entry + 8
            if struct.unpack_from(endian + "H", data, value)[0] == 1:
                return data
            return data[:value] + struct.pack(endian + "H", 1) + data[value + 2:]
        return data
    return data


class ExifOrientationResetMixin(ImageFieldFile):
    """Receive django-resized's final encoded bytes through cooperative super()."""

    def save(self, name, content, save=True):
        content.seek(0)
        original = content.read()
        patched = reset_jpeg_exif_orientation(original)
        if patched is not original:
            content = ContentFile(patched)
        else:
            content.seek(0)
        return super().save(name, content, save)


class OrientedResizedImageFieldFile(ResizedImageFieldFile, ExifOrientationResetMixin):
    pass


class ResizedImageField(DjangoResizedImageField):
    attr_class = OrientedResizedImageFieldFile
