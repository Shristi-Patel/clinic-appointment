"""initial clinicdesk schema"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS btree_gist')
    op.create_table('users', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('email', sa.String(255), nullable=False, unique=True), sa.Column('hashed_password', sa.Text, nullable=False), sa.Column('role', sa.String(30), nullable=False, server_default='staff'), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('doctors', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('specialty', sa.String(120), nullable=False), sa.Column('active', sa.Boolean, nullable=False, server_default=sa.true()))
    op.create_table('patients', sa.Column('id', sa.Integer, primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('phone', sa.String(40)), sa.Column('email', sa.String(255)), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table('appointments', sa.Column('id', sa.Integer, primary_key=True), sa.Column('doctor_id', sa.Integer, sa.ForeignKey('doctors.id'), nullable=False), sa.Column('patient_id', sa.Integer, sa.ForeignKey('patients.id'), nullable=False), sa.Column('start_time', sa.DateTime(timezone=True), nullable=False), sa.Column('end_time', sa.DateTime(timezone=True), nullable=False), sa.Column('status', sa.String(20), nullable=False, server_default='booked'), sa.Column('created_by_user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False), sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column('cancelled_at', sa.DateTime(timezone=True)), sa.Column('late_fee_charged', sa.Boolean, nullable=False, server_default=sa.false()), sa.Column('late_fee_amount', sa.Numeric(10, 2), nullable=False, server_default='0'))
    op.create_index('ix_users_email', 'users', ['email'], unique=True); op.create_index('ix_doctors_name', 'doctors', ['name']); op.create_index('ix_patients_name', 'patients', ['name']); op.create_index('ix_appointments_start_time', 'appointments', ['start_time']); op.create_index('ix_appointments_status', 'appointments', ['status'])
    op.execute("""ALTER TABLE appointments ADD CONSTRAINT no_overlapping_active_appointments
        EXCLUDE USING gist (doctor_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&)
        WHERE (status != 'cancelled')""")
    op.execute("""INSERT INTO doctors (name, specialty) VALUES
        ('Maya Chen', 'Family Medicine'), ('Elias Romero', 'Cardiology'), ('Priya Shah', 'Pediatrics')""")

def downgrade():
    op.drop_table('appointments'); op.drop_table('patients'); op.drop_table('doctors'); op.drop_table('users')
