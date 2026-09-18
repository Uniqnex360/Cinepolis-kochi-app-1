"""add genre to movies

Revision ID: 14076618f793
Revises: dc54f0bd6c44
Create Date: 2026-09-18 15:47:33.386758
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '14076618f793'
down_revision: Union[str, None] = 'dc54f0bd6c44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column("movies", sa.Column("genre", sa.String(120), nullable=True))


def downgrade() -> None:
    op.drop_column("movies", "genre")