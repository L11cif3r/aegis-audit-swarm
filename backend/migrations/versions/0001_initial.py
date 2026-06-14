"""initial Trust Layer schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-06-14

Creates the full Trust Layer schema (audit_logs, control_library,
adversary_findings, evidence_ledger, review_queue) from the shared metadata.
"""
from alembic import op

# Register all tables on the shared metadata.
import agents.librarian.controls   # noqa: F401
import agents.adversary.store       # noqa: F401
import agents.notary.ledger         # noqa: F401
import gateway.review               # noqa: F401
from database import metadata

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    metadata.create_all(bind)


def downgrade() -> None:
    bind = op.get_bind()
    metadata.drop_all(bind)
