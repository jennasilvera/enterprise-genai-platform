"""add human review requests

Revision ID: 7b1c0e2f4a91
Revises: 8a0f69a3baf1
Create Date: 2026-09-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "7b1c0e2f4a91"
down_revision: str | Sequence[str] | None = "8a0f69a3baf1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add durable Phase 13 human-review lifecycle state."""

    op.create_table(
        "human_review_requests",
        sa.Column(
            "review_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "contract_version",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "question",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "answer_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "answer_value_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "unit",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "supporting_record_ids_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "citation_ids_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source_fact_ids_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "evidence_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "synthesis_version",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "sufficiency_policy_version",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "decision",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column(
            "reviewer_identity",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "revision",
            sa.Integer(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('awaiting_review', 'approved', 'rejected')",
            name="ck_human_review_requests_status",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('approve', 'reject')",
            name="ck_human_review_requests_decision",
        ),
        sa.CheckConstraint(
            "revision IN (1, 2)",
            name="ck_human_review_requests_revision",
        ),
        sa.CheckConstraint(
            "length(review_id) > 0",
            name="ck_human_review_requests_review_id",
        ),
        sa.CheckConstraint(
            "length(contract_version) > 0",
            name="ck_human_review_requests_contract_version",
        ),
        sa.CheckConstraint(
            "length(question) > 0",
            name="ck_human_review_requests_question",
        ),
        sa.CheckConstraint(
            """
            (
                status = 'awaiting_review'
                AND decision IS NULL
                AND reviewer_identity IS NULL
                AND revision = 1
            )
            OR
            (
                status = 'approved'
                AND decision = 'approve'
                AND reviewer_identity IS NOT NULL
                AND length(reviewer_identity) > 0
                AND revision = 2
            )
            OR
            (
                status = 'rejected'
                AND decision = 'reject'
                AND reviewer_identity IS NOT NULL
                AND length(reviewer_identity) > 0
                AND revision = 2
            )
            """,
            name="ck_human_review_requests_lifecycle",
        ),
        sa.PrimaryKeyConstraint(
            "review_id",
        ),
    )

    op.create_index(
        "ix_human_review_requests_status",
        "human_review_requests",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    """Remove durable Phase 13 human-review lifecycle state."""

    op.drop_index(
        "ix_human_review_requests_status",
        table_name="human_review_requests",
    )

    op.drop_table("human_review_requests")
