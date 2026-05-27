DEFAULT_EMPTY_VALUES = frozenset({"nein", "nan", "none", "-"})
EXTENDED_EMPTY_VALUES = DEFAULT_EMPTY_VALUES | frozenset({"0", "/"})
REQUEST_EMPTY_VALUES = EXTENDED_EMPTY_VALUES | frozenset({"bein"})
FOOD_EMPTY_VALUES = frozenset({"nein", "keine", "keinr", "nan", "ja"})


def clean_optional_text(value, empty_values=DEFAULT_EMPTY_VALUES):
    if value is None:
        return ""

    normalized = str(value).lower().strip()
    if normalized in empty_values:
        return ""

    return value
