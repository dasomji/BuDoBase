"""Bounded-memory immutable snapshots for streamed sensitive exports."""

from tempfile import SpooledTemporaryFile


EXPORT_SNAPSHOT_MEMORY_LIMIT = 1024 * 1024
EXPORT_STREAM_CHUNK_SIZE = 64 * 1024


def create_export_snapshot():
    return SpooledTemporaryFile(max_size=EXPORT_SNAPSHOT_MEMORY_LIMIT, mode="w+b")


def stream_snapshot(snapshot):
    try:
        while chunk := snapshot.read(EXPORT_STREAM_CHUNK_SIZE):
            yield chunk
    finally:
        snapshot.close()


def close_snapshot_with_response(response, snapshot):
    """Ensure abandoned/unconsumed responses release their backing snapshot."""
    original_close = response.close

    def close():
        try:
            original_close()
        finally:
            snapshot.close()

    response.close = close
    return response
