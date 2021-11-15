"""empty message

Revision ID: a555413424be
Revises: 75542b25251b
Create Date: 2021-11-15 01:21:52.695991

"""
from alembic import op
import sqlalchemy as sa


revision = 'a555413424be'
down_revision = '75542b25251b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('op_dependencies',
    sa.Column('id_op', sa.Integer(), nullable=False),
    sa.Column('id_dependency', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['id_dependency'], ['op.id'], ),
    sa.ForeignKeyConstraint(['id_op'], ['op.id'], ),
    sa.PrimaryKeyConstraint('id_op', 'id_dependency')
    )
    op.drop_constraint('op_id_dependency_fkey', 'op', type_='foreignkey')
    op.drop_column('op', 'id_dependency')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('op', sa.Column('id_dependency', sa.INTEGER(), autoincrement=False, nullable=True))
    op.create_foreign_key('op_id_dependency_fkey', 'op', 'op', ['id_dependency'], ['id'])
    op.drop_table('op_dependencies')
    # ### end Alembic commands ###