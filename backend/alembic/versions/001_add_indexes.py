NEW_FILE_CODE
"""添加索引优化

Revision ID: 001_add_indexes
Revises: 
Create Date: 2026-05-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_add_indexes'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加索引优化查询性能"""
    # 为 tasks 表添加索引
    op.create_index('idx_user_status', 'tasks', ['user_id', 'status'])
    op.create_index('idx_deadline', 'tasks', ['deadline'])
    op.create_index('idx_start_time', 'tasks', ['start_time'])
    op.create_index('idx_user_created', 'tasks', ['user_id'])


def downgrade() -> None:
    """回退索引"""
    op.drop_index('idx_user_created', table_name='tasks')
    op.drop_index('idx_start_time', table_name='tasks')
    op.drop_index('idx_deadline', table_name='tasks')
    op.drop_index('idx_user_status', table_name='tasks')
