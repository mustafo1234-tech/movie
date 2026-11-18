from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("language", sa.String(length=8), nullable=False, server_default="uz"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_active", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("telegram_id", name="uq_users_telegram_id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)

    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=8), nullable=False, server_default="movie"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "movie_id", "media_type", name="uq_favorite_user_movie"),
    )
    op.create_index("ix_favorites_user_created", "favorites", ["user_id", "created_at"])

    op.create_table(
        "watched",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("movie_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=8), nullable=False, server_default="movie"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "movie_id", "media_type", name="uq_watched_user_movie"),
    )
    op.create_index("ix_watched_user_created", "watched", ["user_id", "created_at"])

    op.create_table(
        "search_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("search_query", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_search_user_created", "search_history", ["user_id", "created_at"])

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("favorite_genres", sa.Text(), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_index("ix_search_user_created", table_name="search_history")
    op.drop_table("search_history")
    op.drop_index("ix_watched_user_created", table_name="watched")
    op.drop_table("watched")
    op.drop_index("ix_favorites_user_created", table_name="favorites")
    op.drop_table("favorites")
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")
    op.drop_table("users")
