from django.core.files.storage import FileSystemStorage, storages
from storages.backends.s3 import S3Storage


ATTACHMENT_STORAGE_ALIAS = "attachments"


class _ProtectedUrlMixin:
    def url(self, name):
        raise ValueError("Private attachment images do not have public storage URLs.")

    def get_available_name(self, name, max_length=None):
        """Refuse collisions instead of silently renaming an audited key."""
        if max_length is not None and len(name) > max_length:
            raise ValueError("Private attachment storage key is too long.")
        if self.exists(name):
            raise FileExistsError(f"Private attachment already exists: {name}")
        return name


class PrivateFirstAidFileSystemStorage(_ProtectedUrlMixin, FileSystemStorage):
    pass


class PrivateFirstAidS3Storage(_ProtectedUrlMixin, S3Storage):
    pass


def attachment_storage():
    """Return the private storage shared by note and first-aid images."""
    return storages[ATTACHMENT_STORAGE_ALIAS]
