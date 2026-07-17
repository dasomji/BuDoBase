import logging

from django.db import transaction

logger = logging.getLogger(__name__)


def delete_storage_object_on_commit(storage, name):
    """Delete a stored object only after the surrounding DB transaction commits."""
    if not name:
        return

    def delete_object():
        try:
            storage.delete(name)
        except Exception:
            logger.exception("Failed to delete stored media object")

    transaction.on_commit(delete_object)


def delete_field_file_on_commit(field_file):
    if field_file and field_file.name:
        delete_storage_object_on_commit(field_file.storage, field_file.name)
