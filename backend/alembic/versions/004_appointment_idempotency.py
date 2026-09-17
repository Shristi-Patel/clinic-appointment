"""add appointment booking idempotency keys"""
from alembic import op
import sqlalchemy as sa

revision = '004_appointment_idempotency'
down_revision = '003_appointment_history'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'appointment_idempotency',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('key', sa.String(255), nullable=False, unique=True),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

def downgrade():
    op.drop_table('appointment_idempotency')