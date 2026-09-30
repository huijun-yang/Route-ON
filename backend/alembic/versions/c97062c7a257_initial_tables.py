"""initial tables

Revision ID: c97062c7a257
Revises: 
Create Date: 2026-09-30 13:39:45.441212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c97062c7a257'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('places',
    sa.Column('kakao_place_id', sa.String(length=50), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('address', sa.String(length=200), nullable=False),
    sa.Column('lat', sa.Float(), nullable=False),
    sa.Column('lng', sa.Float(), nullable=False),
    sa.Column('category', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('kakao_place_id')
    )
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('kakao_id', sa.String(length=50), nullable=False),
    sa.Column('nickname', sa.String(length=50), nullable=False),
    sa.Column('email', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('kakao_id')
    )
    op.create_table('business_hours',
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('place_id', sa.String(length=50), nullable=False),
    sa.Column('weekday', sa.Integer(), nullable=False),
    sa.Column('open_time', sa.Time(), nullable=False),
    sa.Column('close_time', sa.Time(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.kakao_place_id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'place_id', 'weekday')
    )
    op.create_table('courses',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('owner_user_id', sa.String(length=36), nullable=False),
    sa.Column('group_id', sa.String(length=36), nullable=False),
    sa.Column('priority_type', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('share_uuid', sa.String(length=36), nullable=False),
    sa.Column('course_date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('share_uuid')
    )
    op.create_table('course_stops',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('course_id', sa.String(length=36), nullable=False),
    sa.Column('place_id', sa.String(length=50), nullable=False),
    sa.Column('visit_order', sa.Integer(), nullable=False),
    sa.Column('arrival_time', sa.Time(), nullable=True),
    sa.Column('stay_duration', sa.Integer(), nullable=True),
    sa.Column('estimated_cost', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.kakao_place_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('group_sessions',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('course_id', sa.String(length=36), nullable=False),
    sa.Column('invite_code', sa.String(length=20), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('course_id'),
    sa.UniqueConstraint('invite_code')
    )
    op.create_table('group_candidate_places',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('group_session_id', sa.String(length=36), nullable=False),
    sa.Column('place_id', sa.String(length=50), nullable=False),
    sa.Column('added_by_user_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['added_by_user_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['group_session_id'], ['group_sessions.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.kakao_place_id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('votes',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('candidate_place_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['candidate_place_id'], ['group_candidate_places.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('votes')
    op.drop_table('group_candidate_places')
    op.drop_table('group_sessions')
    op.drop_table('course_stops')
    op.drop_table('courses')
    op.drop_table('business_hours')
    op.drop_table('users')
    op.drop_table('places')