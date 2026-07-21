"""Validation limits shared by text entries and their image attachments."""

FIRST_AID_DESCRIPTION_MAX_LENGTH = 10_000
FIRST_AID_MAX_PHOTOS = 5

SHA256_PATTERN = r"\A[0-9a-f]{64}\Z"
OPAQUE_WEBP_KEY_PATTERN = (
    r"\A[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{12}\.webp\Z"
)
