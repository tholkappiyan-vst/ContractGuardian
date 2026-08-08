"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSON

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), unique=True, nullable=False, index=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("account_type", sa.String(), server_default="individual"),
        sa.Column("plan", sa.String(), server_default="free"),
        sa.Column("contracts_used", sa.Integer(), server_default="0"),
        sa.Column("contracts_limit", sa.Integer(), server_default="3"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "organizations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), unique=True, nullable=False),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan", sa.String(), server_default="professional"),
        sa.Column("contracts_used", sa.Integer(), server_default="0"),
        sa.Column("contracts_limit", sa.Integer(), server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "org_members",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("org_id", "user_id"),
    )

    op.create_table(
        "contracts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="SET NULL"), index=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("contract_type", sa.String()),
        sa.Column("status", sa.String(), server_default="uploaded", index=True),
        sa.Column("error_message", sa.Text()),
        sa.Column("language", sa.String(), server_default="en"),
        sa.Column("page_count", sa.Integer()),
        sa.Column("word_count", sa.Integer()),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("file_name", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(), nullable=False),
        sa.Column("raw_text", sa.Text()),
        sa.Column("ocr_used", sa.Boolean(), server_default="false"),
        sa.Column("ocr_confidence", sa.Float()),
        sa.Column("page_count", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "clauses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("clause_index", sa.Integer(), nullable=False),
        sa.Column("section_number", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(), nullable=False, index=True),
        sa.Column("subcategory", sa.String()),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("is_standard", sa.Boolean()),
        sa.Column("parent_id", sa.String(), sa.ForeignKey("clauses.id", ondelete="SET NULL")),
        sa.Column("page_number", sa.Integer()),
        sa.Column("start_offset", sa.Integer()),
        sa.Column("end_offset", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("clause_id", sa.String(), sa.ForeignKey("clauses.id", ondelete="SET NULL"), index=True),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("normalized", JSON()),
        sa.Column("confidence", sa.Float(), server_default="0.0"),
        sa.Column("role", sa.String()),
        sa.Column("aliases", ARRAY(sa.String())),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "risk_scores",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("clause_id", sa.String(), sa.ForeignKey("clauses.id", ondelete="CASCADE"), index=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("consequence", sa.Text(), nullable=False),
        sa.Column("affected_party", sa.String()),
        sa.Column("is_standard", sa.Boolean()),
        sa.Column("standard_note", sa.Text()),
        sa.Column("related_clauses", ARRAY(sa.String())),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "analyses",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("executive_summary", sa.Text()),
        sa.Column("contract_type", JSON()),
        sa.Column("parties", JSON()),
        sa.Column("dates", JSON()),
        sa.Column("payment_summary", JSON()),
        sa.Column("obligations", JSON()),
        sa.Column("risk_score", sa.Integer()),
        sa.Column("risk_label", sa.String()),
        sa.Column("risk_summary", sa.Text()),
        sa.Column("top_risks", JSON()),
        sa.Column("action_items", JSON()),
        sa.Column("model_used", sa.String()),
        sa.Column("prompt_version", sa.String()),
        sa.Column("tokens_input", sa.Integer()),
        sa.Column("tokens_output", sa.Integer()),
        sa.Column("cost_usd", sa.Float()),
        sa.Column("processing_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "negotiation_suggestions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("clause_id", sa.String(), sa.ForeignKey("clauses.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("alternative_text", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("talking_points", ARRAY(sa.String())),
        sa.Column("likelihood", sa.String()),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", JSON()),
        sa.Column("tokens_used", sa.Integer()),
        sa.Column("model_used", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id", ondelete="SET NULL"), index=True),
        sa.Column("org_id", sa.String(), sa.ForeignKey("organizations.id", ondelete="SET NULL")),
        sa.Column("contract_id", sa.String(), sa.ForeignKey("contracts.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(), nullable=False, index=True),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.String()),
        sa.Column("details", JSON()),
        sa.Column("ip_address", sa.String()),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("audit_logs")
    op.drop_table("chat_messages")
    op.drop_table("negotiation_suggestions")
    op.drop_table("analyses")
    op.drop_table("risk_scores")
    op.drop_table("entities")
    op.drop_table("clauses")
    op.drop_table("documents")
    op.drop_table("contracts")
    op.drop_table("org_members")
    op.drop_table("organizations")
    op.drop_table("users")
