"""First-run seeding of a default experiment type and example vocab terms.

Called from :func:`core.db.connect` (lazily, to avoid an import cycle). Only
seeds when the relevant tables are empty, so it never overwrites user edits.
"""

from __future__ import annotations

from . import exp_types, vocab
from .db import Connection

# A few molecular-biology examples to make the dropdowns immediately useful.
# The user manages these freely under Experiments → Types & Lists.
_EXAMPLE_TERMS = {
    "vector": ["Lentiviral", "AAV", "Plasmid", "Retroviral", "Adenoviral"],
    "cell": ["HEK293T", "iPSC", "Jurkat", "HeLa", "Primary T cells"],
    "reagent": ["DMEM", "RPMI 1640", "FBS", "Polybrene", "Puromycin", "PEI", "Lipofectamine"],
}


def seed_defaults(conn: Connection) -> None:
    if conn.execute("SELECT count(*) FROM experiment_types").fetchone()[0] == 0:
        exp_types.create_type(conn, "Generic", exp_types.default_field_template())

    if conn.execute("SELECT count(*) FROM vocab_terms").fetchone()[0] == 0:
        for category, values in _EXAMPLE_TERMS.items():
            vocab.add_terms(conn, category, values)
