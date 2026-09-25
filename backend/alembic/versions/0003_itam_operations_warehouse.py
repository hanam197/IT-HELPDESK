"""Add ITAM operation history and warehouse inventory tables.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('asset_types', sa.Column('track_serial', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('asset_types', sa.Column('allow_station', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'asset_operations',
        sa.Column('number', sa.String(length=40), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('operation_type', sa.String(length=30), nullable=False),
        sa.Column('from_entity_type', sa.String(length=30), nullable=True),
        sa.Column('from_entity_id', sa.Integer(), nullable=True),
        sa.Column('to_entity_type', sa.String(length=30), nullable=True),
        sa.Column('to_entity_id', sa.Integer(), nullable=True),
        sa.Column('operation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('condition_before', sa.Text(), nullable=True),
        sa.Column('condition_after', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.Integer(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number'),
    )
    op.create_table(
        'warehouses',
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'inventory_items',
        sa.Column('code', sa.String(length=40), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('unit', sa.String(length=30), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('minimum_stock', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('bin_shelf', sa.String(length=80), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_table(
        'inventory_transactions',
        sa.Column('number', sa.String(length=40), nullable=False),
        sa.Column('transaction_type', sa.String(length=20), nullable=False),
        sa.Column('warehouse_id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('item_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=False),
        sa.Column('transaction_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_vendor', sa.String(length=150), nullable=True),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('performed_by', sa.Integer(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id']),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['item_id'], ['inventory_items.id']),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number'),
    )


def downgrade():
    op.drop_table('inventory_transactions')
    op.drop_table('inventory_items')
    op.drop_table('warehouses')
    op.drop_table('asset_operations')
    op.drop_column('asset_types', 'allow_station')
    op.drop_column('asset_types', 'track_serial')
