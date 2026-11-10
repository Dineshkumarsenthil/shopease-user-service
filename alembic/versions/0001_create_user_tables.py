"""create user_profiles and user_addresses tables

Revision ID: 0001
Revises:
Create Date: 2026-11-10
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("auth_user_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(20), nullable=True),
        sa.Column("profile_image", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("auth_user_id", name="uq_user_profiles_auth_user_id"),
    )
    op.create_index("ix_user_profiles_id", "user_profiles", ["id"])

    op.create_table(
        "user_addresses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("address_type", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone_number", sa.String(20), nullable=False),
        sa.Column("address_line_1", sa.String(255), nullable=False),
        sa.Column("address_line_2", sa.String(255), nullable=True),
        sa.Column("city", sa.String(100), nullable=False),
        sa.Column("state", sa.String(100), nullable=False),
        sa.Column("country", sa.String(100), nullable=False),
        sa.Column("postal_code", sa.String(20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE",
                                name="fk_user_addresses_user_id"),
    )
    op.create_index("ix_user_addresses_id", "user_addresses", ["id"])
    op.create_index("ix_user_addresses_user_id", "user_addresses", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_addresses_user_id", table_name="user_addresses")
    op.drop_index("ix_user_addresses_id", table_name="user_addresses")
    op.drop_table("user_addresses")
    op.drop_index("ix_user_profiles_id", table_name="user_profiles")
    op.drop_table("user_profiles")
