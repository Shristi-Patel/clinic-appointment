"""add reschedule audit history"""
from alembic import op
import sqlalchemy as sa

revision = '003_appointment_history'
down_revision = '002_simulated_clock_outbox'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'appointment_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id'), nullable=False),
        sa.Column('old_start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('old_end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_appointment_history_appointment_id', 'appointment_history', ['appointment_id'])

def downgrade():
    op.drop_index('ix_appointment_history_appointment_id', table_name='appointment_history')
    op.drop_table('appointment_history')