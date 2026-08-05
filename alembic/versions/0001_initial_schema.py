"""initial schema — espelha app/models.py"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0001"
down_revision = None

UUID_PK = lambda: sa.Column(  # noqa: E731
    "id", UUID(as_uuid=True), primary_key=True,
    server_default=sa.text("uuid_generate_v4()"),
)
TS = lambda name: sa.Column(  # noqa: E731
    name, sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()"),
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "users",
        UUID_PK(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.Text()),
        sa.Column("fcm_token", sa.Text()),
        TS("created_at"), TS("updated_at"),
    )

    op.create_table(
        "families",
        UUID_PK(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("invite_code", sa.String(12), nullable=False, unique=True),
        TS("created_at"),
    )

    op.create_table(
        "family_members",
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        TS("joined_at"),
    )

    op.create_table(
        "locations",
        UUID_PK(),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("latitude", sa.Float(precision=53), nullable=False),
        sa.Column("longitude", sa.Float(precision=53), nullable=False),
        sa.Column("accuracy", sa.Float(precision=53), nullable=False,
                  server_default="0"),
        sa.Column("address", sa.Text()),
        TS("created_at"),
    )
    op.create_index("idx_locations_user_id", "locations", ["user_id"])
    op.execute("CREATE INDEX idx_locations_created_at ON locations(created_at DESC)")

    op.create_table(
        "wifi_status",
        UUID_PK(),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ssid", sa.String(255), nullable=False),
        sa.Column("bssid", sa.String(50), nullable=False),
        sa.Column("is_trusted", sa.Boolean(), nullable=False, server_default="false"),
        TS("updated_at"),
        sa.UniqueConstraint("user_id", "family_id"),
    )

    op.create_table(
        "trusted_networks",
        UUID_PK(),
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ssid", sa.String(255), nullable=False),
        sa.Column("bssid", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False, server_default=""),
        sa.UniqueConstraint("family_id", "bssid"),
    )

    op.create_table(
        "geofences",
        UUID_PK(),
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("latitude", sa.Float(precision=53), nullable=False),
        sa.Column("longitude", sa.Float(precision=53), nullable=False),
        sa.Column("radius", sa.Float(precision=53), nullable=False,
                  server_default="200"),
        TS("created_at"),
    )

    op.create_table(
        "alerts",
        UUID_PK(),
        sa.Column("family_id", UUID(as_uuid=True),
                  sa.ForeignKey("families.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        TS("created_at"),
    )
    op.create_index("idx_alerts_family_id", "alerts", ["family_id"])
    op.execute("CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC)")


def downgrade() -> None:
    for t in ("alerts", "geofences", "trusted_networks", "wifi_status",
              "locations", "family_members", "families", "users"):
        op.drop_table(t)
