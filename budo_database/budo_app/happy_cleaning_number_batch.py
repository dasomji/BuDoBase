"""Shared policy for unlocking and proposing Happy Cleaning child numbers."""

from budo_app.models import HappyCleaning, HappyCleaningAssignment


BATCH_NUMBER_ACTION = "happy_cleaning.child_number.batch_assign"


def _kid_full_name(child):
    return f"{child.kid_vorname or ''} {child.kid_nachname or ''}".strip()


def first_happy_cleaning_complete(turnus_id, children):
    """Return whether every currently present child is assigned in HC1."""
    first_event_id = (
        HappyCleaning.objects.filter(turnus_id=turnus_id, display_number=1)
        .values_list("id", flat=True)
        .first()
    )
    if first_event_id is None:
        return False
    present_ids = {child.id for child in children if child.anwesend is True}
    assigned_ids = set(
        HappyCleaningAssignment.objects.filter(
            happy_cleaning_id=first_event_id,
            child_id__in=present_ids,
            child__turnus_id=turnus_id,
        ).values_list("child_id", flat=True)
    )
    return present_ids.issubset(assigned_ids)


def number_batch_projection(children, *, unlocked):
    """Suggest deterministic free numbers, extending above present N if needed."""
    if not unlocked:
        return {"available": False, "children": []}

    present = [child for child in children if child.anwesend is True]
    numberless = sorted(
        (child for child in present if child.happy_cleaning_number is None),
        key=lambda child: (
            _kid_full_name(child).casefold(),
            child.id,
        ),
    )
    occupied = {
        child.happy_cleaning_number
        for child in children
        if child.happy_cleaning_number is not None
    }
    proposals = []
    candidate = 1
    for child in numberless:
        while candidate in occupied:
            candidate += 1
        proposals.append({
            "id": child.id,
            "full_name": _kid_full_name(child),
            "number": candidate,
            "expected_version": child.happy_cleaning_number_version,
        })
        occupied.add(candidate)
        candidate += 1

    return {
        "available": bool(proposals),
        "children": proposals,
    }
