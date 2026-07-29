# Happy Cleaning todo contract migration

Migration `0081_remove_happy_cleaning_todo` permanently removes the normalized
todo table after validating that every station has a canonical
`content_document`.

Before deploying it, take and verify a database backup that can restore both
schema and data. Rollback means restoring that backup (or restoring the
pre-migration database snapshot); reversing the Django migration cannot
reconstruct the retired normalized rows. The canonical station documents are
not modified by the migration.
