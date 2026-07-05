"""
Order device models inside every category: newest generation first,
and within one generation: Ultra / Pro Max > Pro > Plus/Max > base > Mini/e.

Alphabetical ordering breaks phone names badly (iPhone 8 and iPhone X sort
AFTER iPhone 17). This migration fills the existing Collection.order field
with computed values so Meta.ordering = ["order", "name"] shows a natural
newest-first menu. Re-runnable logic also lives in the sort key below.
"""
import re
from django.db import migrations

# variant rank (higher = shown first within the same generation)
_VARIANTS = [
    (re.compile(r"\bpro\s*max\b", re.I), 6),
    (re.compile(r"\bultra\b", re.I), 6),
    (re.compile(r"\bpro\b", re.I), 5),
    (re.compile(r"\bplus\b|\bmax\b", re.I), 4),
    (re.compile(r"\bmini\b", re.I), 2),
    (re.compile(r"\d+\s*e\b|\be\b$", re.I), 1),   # iPhone 16e / SE-style
]

# iPhone X family has no digits -- map to generation 10.x
_X_FAMILY = [
    (re.compile(r"\bxs\s*max\b", re.I), 10.3),
    (re.compile(r"\bxs\b", re.I), 10.2),
    (re.compile(r"\bxr\b", re.I), 10.1),
    (re.compile(r"\bx\b", re.I), 10.0),
]


def model_sort_key(name):
    """Return a tuple that sorts models newest-first when used ascending."""
    # series rank: S > Z > Note > A > (no letter, e.g. iPhone) -- flagship first
    series = 0
    m = re.search(r"\b([A-Za-z]+)?(\d+)", name)
    gen = 0.0
    if m:
        gen = float(m.group(2))
        prefix = (m.group(1) or "").upper()
        series = {"S": 40, "Z": 30, "NOTE": 20, "A": 10}.get(prefix, 0)
    else:
        for rx, val in _X_FAMILY:
            if rx.search(name):
                gen = val
                break
    if series == 0 and re.search(r"\bnote\b", name, re.I):
        series = 20
    variant = 3  # base model
    for rx, val in _VARIANTS:
        if rx.search(name):
            variant = val
            break
    # negative -> flagship series first, biggest generation first, strongest variant first
    return (-series, -gen, -variant, name.lower())


def assign_order(apps, schema_editor):
    Collection = apps.get_model("store", "Collection")
    parents = (
        Collection.objects.filter(parent__isnull=False)
        .values_list("parent_id", flat=True)
        .distinct()
    )
    for pid in parents:
        siblings = list(Collection.objects.filter(parent_id=pid))
        siblings.sort(key=lambda c: model_sort_key(c.name))
        for i, c in enumerate(siblings):
            new_order = (i + 1) * 10  # gaps of 10 so the admin can insert between
            if c.order != new_order:
                c.order = new_order
                c.save(update_fields=["order"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0007_merge_duplicate_models"),
    ]

    operations = [
        migrations.RunPython(assign_order, noop),
    ]