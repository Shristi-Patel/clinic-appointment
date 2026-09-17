"""add patient merge target"""
from alembic import op
import sqlalchemy as sa

revision = '005_patient_merge'
down_revision = '004_appointment_idempotency'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('patients', sa.Column('merged_into_patient_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_patients_merged_into_patient_id', 'patients', 'patients', ['merged_into_patient_id'], ['id'])
    op.create_index('ix_patients_merged_into_patient_id', 'patients', ['merged_into_patient_id'])

def downgrade():
    op.drop_index('ix_patients_merged_into_patient_id', table_name='patients')
    op.drop_constraint('fk_patients_merged_into_patient_id', 'patients', type_='foreignkey')
    op.drop_column('patients', 'merged_into_patient_id')