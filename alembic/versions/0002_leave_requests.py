"""add leave_requests table"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0002"
down_revision = "0001"

UUID_PK = lambda: sa.Column(  # noqa: E731
    "id", UUID(as_uuid=True), primary_key=True,
    server_default=sa.text("uuid_generate_v4()"),
)
TS = lambda name: sa.Column(  # noqa: E731
    name, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()"),
)


def upgrade() -> None:
    op.create_table(
        "leave_requests",
        UUID_PK(),
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        TS("created_at"),
    )
    op.create_index("idx_leave_requests_family_id", "leave_requests", ["family_id"])


def downgrade() -> None:
    op.drop_table("leave_requests")
