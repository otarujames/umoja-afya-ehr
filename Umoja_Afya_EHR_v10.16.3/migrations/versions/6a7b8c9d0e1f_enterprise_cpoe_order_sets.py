"""enterprise CPOE order sets and structured order details

Revision ID: 6a7b8c9d0e1f
Revises: 5f6a7b8c9d0e
"""
from datetime import datetime, timezone
import json

from alembic import op
import sqlalchemy as sa


revision = "6a7b8c9d0e1f"
down_revision = "5f6a7b8c9d0e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("clinical_order", sa.Column("orderable_code", sa.String(length=100), nullable=True))
    op.add_column("clinical_order", sa.Column("instructions", sa.Text(), nullable=True))
    op.add_column("clinical_order", sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"))
    op.create_index("ix_clinical_order_orderable_code", "clinical_order", ["orderable_code"])

    op.create_table(
        "order_set",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("set_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("specialty", sa.String(length=120), nullable=True),
        sa.Column("encounter_types_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("source", sa.String(length=80), nullable=False, server_default="LOCAL_APPROVED"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(length=160), nullable=False),
        sa.Column("approved_by", sa.String(length=160), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_set_set_code", "order_set", ["set_code"], unique=True)
    op.create_index("ix_order_set_name", "order_set", ["name"])
    op.create_index("ix_order_set_specialty", "order_set", ["specialty"])
    op.create_index("ix_order_set_active", "order_set", ["active"])

    op.create_table(
        "order_set_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_set_id", sa.Integer(), nullable=False),
        sa.Column("orderable_code", sa.String(length=100), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("selected_by_default", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("default_priority", sa.String(length=40), nullable=True),
        sa.Column("default_indication", sa.Text(), nullable=True),
        sa.Column("default_instructions", sa.Text(), nullable=True),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.ForeignKeyConstraint(["order_set_id"], ["order_set.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["orderable_code"], ["order_catalog_item.orderable_code"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_set_id", "orderable_code", name="uq_order_set_orderable"),
    )
    op.create_index("ix_order_set_item_order_set_id", "order_set_item", ["order_set_id"])
    op.create_index("ix_order_set_item_orderable_code", "order_set_item", ["orderable_code"])

    # Existing production installations already have the governed order catalog.
    # Seed curated starter sets during upgrade; new review installs seed them after
    # the catalog is populated by the normal idempotent reference-data routine.
    bind = op.get_bind()
    available = {row[0] for row in bind.execute(sa.text("SELECT orderable_code FROM order_catalog_item WHERE active = true"))}
    if available:
        from backend.app.catalog_seed import build_starter_order_sets

        now = datetime.now(timezone.utc)
        for payload in build_starter_order_sets():
            exists = bind.execute(sa.text("SELECT id FROM order_set WHERE set_code = :code"), {"code": payload["set_code"]}).first()
            if exists:
                continue
            items = [item for item in payload["items"] if item["orderable_code"] in available]
            if not items:
                continue
            result = bind.execute(
                sa.text(
                    "INSERT INTO order_set (set_code,name,description,specialty,encounter_types_json,version,source,active,created_by,approved_by,approved_at,created_at,updated_at) "
                    "VALUES (:set_code,:name,:description,:specialty,:encounter_types,1,'UMOJA_STARTER',true,:created_by,:approved_by,:approved_at,:created_at,:updated_at)"
                ),
                {
                    "set_code": payload["set_code"],
                    "name": payload["name"],
                    "description": payload["description"],
                    "specialty": payload["specialty"],
                    "encounter_types": json.dumps(payload["encounter_types"]),
                    "created_by": "Umoja Clinical Content Team",
                    "approved_by": "Umoja Clinical Governance",
                    "approved_at": now,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            order_set_id = bind.execute(
                sa.text(
                    "SELECT id FROM order_set WHERE set_code = :code"
                ),
                {"code": payload["set_code"]},
            ).scalar_one()
            for sequence, item in enumerate(items):
                bind.execute(
                    sa.text(
                        "INSERT INTO order_set_item (order_set_id,orderable_code,sequence,selected_by_default,required,default_priority,default_indication,default_instructions,details_json) "
                        "VALUES (:order_set_id,:orderable_code,:sequence,true,:required,:priority,:indication,:instructions,:details)"
                    ),
                    {
                        "order_set_id": order_set_id,
                        "orderable_code": item["orderable_code"],
                        "sequence": sequence,
                        "required": item["required"],
                        "priority": item["default_priority"],
                        "indication": item["default_indication"],
                        "instructions": item["default_instructions"],
                        "details": json.dumps(item["details"]),
                    },
                )


def downgrade():
    op.drop_index("ix_order_set_item_orderable_code", table_name="order_set_item")
    op.drop_index("ix_order_set_item_order_set_id", table_name="order_set_item")
    op.drop_table("order_set_item")
    op.drop_index("ix_order_set_active", table_name="order_set")
    op.drop_index("ix_order_set_specialty", table_name="order_set")
    op.drop_index("ix_order_set_name", table_name="order_set")
    op.drop_index("ix_order_set_set_code", table_name="order_set")
    op.drop_table("order_set")
    op.drop_index("ix_clinical_order_orderable_code", table_name="clinical_order")
    op.drop_column("clinical_order", "details_json")
    op.drop_column("clinical_order", "instructions")
    op.drop_column("clinical_order", "orderable_code")
