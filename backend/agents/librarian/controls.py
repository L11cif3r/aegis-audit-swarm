# backend/agents/librarian/controls.py
"""Control library schema: regulation clause -> testable technical control."""
from __future__ import annotations

import sqlalchemy

from database import metadata

# Live, versioned control library. Each row maps a regulatory clause to a
# concrete, testable control consumed by the Adversary and the Notary.
control_library = sqlalchemy.Table(
    "control_library", metadata,
    sqlalchemy.Column("control_id",   sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("version",      sqlalchemy.Integer, default=1),
    sqlalchemy.Column("framework",    sqlalchemy.String, index=True),  # NIST_AI_RMF | ISO_27001 | EU_AI_ACT
    sqlalchemy.Column("function",     sqlalchemy.String),              # GOVERN/MAP/MEASURE/MANAGE or Annex domain
    sqlalchemy.Column("clause",       sqlalchemy.String),              # source clause reference
    sqlalchemy.Column("title",        sqlalchemy.String),
    sqlalchemy.Column("description",  sqlalchemy.Text),
    sqlalchemy.Column("risk_tier",    sqlalchemy.String),              # low | medium | high
    sqlalchemy.Column("vertical",     sqlalchemy.String),              # all | logistics | manufacturing | banking
    sqlalchemy.Column("test_types",   sqlalchemy.Text),                # CSV of adversary probe categories
    sqlalchemy.Column("updated_at",   sqlalchemy.String),
)
