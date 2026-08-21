"""v3: MarketObservation 价格体系 + 副本动态化 + recipe_type

Revision ID: a1b2c3d4e5f6
Revises: 073eab95c26b
Create Date: 2026-08-21

将价格从 Item 属性迁移到 market_observations（不丢数据），
并删除副本估值快照（利润动态计算）。
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = 'a1b2c3d4e5f6'
down_revision = '073eab95c26b'
branch_labels = None
depends_on = None


# price_type -> observation_type 映射
_PTYPE_MAP = {"vendor": "NPC_PRICE", "market": "SELL_OFFER", "manual": "MANUAL_ESTIMATE"}


def upgrade() -> None:
    # 1. 新建 market_observations 表
    op.create_table(
        'market_observations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('observation_type', sa.String(length=32), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('price_item_id', sa.Integer(), nullable=True),
        sa.Column('price_quantity', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('seller_name', sa.String(length=128), nullable=True),
        sa.Column('location', sa.String(length=128), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['price_item_id'], ['items.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_market_observations_item_id'), 'market_observations', ['item_id'], unique=False)
    op.create_index(op.f('ix_market_observations_observation_type'), 'market_observations', ['observation_type'], unique=False)
    op.create_index(op.f('ix_market_observations_observed_at'), 'market_observations', ['observed_at'], unique=False)

    # 2. 数据迁移：items 三价格字段 -> market_observations
    conn = op.get_bind()
    base_id = conn.execute(
        sa.text("SELECT base_currency_item_id FROM currency_systems WHERE is_active = true LIMIT 1")
    ).scalar()

    def _insert_obs(item_id, otype, price_qty, observed_at, source, quantity=1):
        conn.execute(
            sa.text(
                "INSERT INTO market_observations "
                "(item_id, observation_type, quantity, price_item_id, price_quantity, observed_at, source) "
                "VALUES (:i, :t, :q, :p, :pq, :o, :s)"
            ),
            {
                "i": item_id, "t": otype, "q": quantity, "p": base_id,
                "pq": price_qty, "o": observed_at, "s": source,
            },
        )

    # items.vendor_buy_price -> NPC_PRICE, market_price -> SELL_OFFER, manual_price -> MANUAL_ESTIMATE
    item_rows = conn.execute(
        sa.text("SELECT id, vendor_buy_price, market_price, manual_price, updated_at FROM items")
    ).fetchall()
    for item_id, vendor, market, manual, updated_at in item_rows:
        obs_at = updated_at if updated_at else datetime.now(timezone.utc)
        if vendor is not None:
            _insert_obs(item_id, "NPC_PRICE", vendor, obs_at, "migration")
        if market is not None:
            _insert_obs(item_id, "SELL_OFFER", market, obs_at, "migration")
        if manual is not None:
            _insert_obs(item_id, "MANUAL_ESTIMATE", manual, obs_at, "migration")

    # item_price_history -> market_observations
    hist_rows = conn.execute(
        sa.text("SELECT item_id, price_type, price, quantity, observed_at, source FROM item_price_history")
    ).fetchall()
    for item_id, ptype, price, qty, obs_at, source in hist_rows:
        otype = _PTYPE_MAP.get(ptype)
        if otype is not None and price is not None:
            _insert_obs(item_id, otype, price, obs_at, source or "migration", quantity=(qty or 1))

    # 3. 删除 items 三价格字段
    op.drop_column('items', 'vendor_buy_price')
    op.drop_column('items', 'market_price')
    op.drop_column('items', 'manual_price')

    # 4. 删除 item_price_history 表
    op.drop_table('item_price_history')

    # 5. 删除副本估值快照
    op.drop_column('dungeon_runs', 'total_duration_minutes')
    op.drop_column('dungeon_runs', 'gross_value')
    op.drop_column('dungeon_runs', 'repair_cost')
    op.drop_column('dungeon_runs', 'consumable_cost')
    op.drop_column('dungeon_runs', 'other_cost')
    op.drop_column('dungeon_runs', 'total_cost')
    op.drop_column('dungeon_runs', 'net_profit')
    op.drop_column('dungeon_runs', 'profit_per_hour')
    op.drop_column('dungeon_runs', 'gross_value_fiat')
    op.drop_column('dungeon_runs', 'net_profit_fiat')
    op.drop_column('dungeon_runs', 'profit_per_hour_fiat')

    for tbl in ('dungeon_loots', 'dungeon_consumptions'):
        op.drop_column(tbl, 'valuation_unit_price')
        op.drop_column(tbl, 'valuation_total')
        op.drop_column(tbl, 'valuation_source')
        op.drop_column(tbl, 'valuation_currency_item_id')
        op.drop_column(tbl, 'base_currency_value')
        op.drop_column(tbl, 'fiat_value')
        op.drop_column(tbl, 'valuation_time')

    op.drop_column('dungeon_repairs', 'valuation_unit_price')
    op.drop_column('dungeon_repairs', 'material_cost')
    op.drop_column('dungeon_repairs', 'valuation_source')
    op.drop_column('dungeon_repairs', 'valuation_currency_item_id')
    op.drop_column('dungeon_repairs', 'base_currency_value')
    op.drop_column('dungeon_repairs', 'fiat_value')

    # 6. 新增 recipes.recipe_type
    op.add_column('recipes', sa.Column('recipe_type', sa.String(length=32), nullable=False, server_default='ALCHEMY'))
    op.create_index(op.f('ix_recipes_recipe_type'), 'recipes', ['recipe_type'], unique=False)
    # 根据 category 迁移 recipe_type
    conn.execute(sa.text("UPDATE recipes SET recipe_type = 'CRAFT' WHERE category = '制造'"))


def downgrade() -> None:
    # 回退：重建旧字段/表（价格数据不回迁，仅结构）
    op.add_column('items', sa.Column('manual_price', sa.Numeric(precision=20, scale=8), nullable=True))
    op.add_column('items', sa.Column('market_price', sa.Numeric(precision=20, scale=8), nullable=True))
    op.add_column('items', sa.Column('vendor_buy_price', sa.Numeric(precision=20, scale=8), nullable=True))

    op.create_table(
        'item_price_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('price_type', sa.String(length=32), nullable=False),
        sa.Column('price', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('currency_item_id', sa.Integer(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column('source', sa.String(length=64), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
        sa.ForeignKeyConstraint(['currency_item_id'], ['items.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )

    op.drop_index(op.f('ix_recipes_recipe_type'), table_name='recipes')
    op.drop_column('recipes', 'recipe_type')
    op.drop_index(op.f('ix_market_observations_observed_at'), table_name='market_observations')
    op.drop_index(op.f('ix_market_observations_observation_type'), table_name='market_observations')
    op.drop_index(op.f('ix_market_observations_item_id'), table_name='market_observations')
    op.drop_table('market_observations')
