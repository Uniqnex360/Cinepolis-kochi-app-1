"""add genre to movies

Revision ID: d16e0bf0a372
Revises: 14076618f793
Create Date: 2026-09-18 15:54:32.337036
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd16e0bf0a372'
down_revision: Union[str, None] = '14076618f793'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("movies", sa.Column("genre", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "genre")