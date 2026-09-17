"""add simulated clock and notification outbox"""
from alembic import op
import sqlalchemy as sa

revision = '002_simulated_clock_outbox'
down_revision = '001_initial'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('clock_state',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('current_time', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table('outbox',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recipient', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('appointment_id', sa.Integer(), sa.ForeignKey('appointments.id')),
        sa.Column('reminder_date', sa.Date(), nullable=True),
        sa.UniqueConstraint('appointment_id', 'reminder_date', name='uq_outbox_appointment_reminder_day'),
    )
    op.create_index('ix_outbox_appointment_id', 'outbox', ['appointment_id'])
    op.execute('ALTER TABLE appointments DROP CONSTRAINT no_overlapping_active_appointments')
    op.execute("""ALTER TABLE appointments ADD CONSTRAINT no_overlapping_active_appointments
        EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
        WHERE (status NOT IN ('cancelled', 'no_show'))""")

def downgrade():
    op.execute('ALTER TABLE appointments DROP CONSTRAINT no_overlapping_active_appointments')
    op.execute("""ALTER TABLE appointments ADD CONSTRAINT no_overlapping_active_appointments
        EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
        WHERE (status != 'cancelled')""")
    op.drop_index('ix_outbox_appointment_id', table_name='outbox')
    op.drop_table('outbox')
    op.drop_table('clock_state')
