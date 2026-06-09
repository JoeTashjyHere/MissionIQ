"""Knowledge Graph models — MissionIQ's institutional memory.

Two tables back the graph:

- ``graph_entity`` — deduplicated nodes (Agency, Program, Opportunity,
  Contract, Competitor, Technology, Capability, Risk, Win Theme,
  Discriminator, Contract Vehicle, Past Performance), unique per workspace by
  ``(entity_type, normalized_key)``. Entities accumulate ``mention_count`` and
  ``attributes`` over time so the graph gets richer with every opportunity.
- ``graph_edge`` — typed, provenance-stamped relationships between entities.
  Each edge records the ``opportunity_id`` and ``module_id`` that produced it,
  so a module re-run can idempotently replace only its own contributions.

The graph is workspace-scoped: it is the tenant's private institutional
intelligence, never shared across workspaces.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPkMixin

ENTITY_TYPES = (
    "agency",
    "program",
    "opportunity",
    "contract",
    "competitor",
    "technology",
    "capability",
    "risk",
    "win_theme",
    "discriminator",
    "contract_vehicle",
    "past_performance",
)

RELATION_TYPES = (
    "opportunity_for_agency",
    "opportunity_under_program",
    "opportunity_uses_vehicle",
    "opportunity_has_incumbent",
    "opportunity_has_competitor",
    "opportunity_has_risk",
    "opportunity_has_win_theme",
    "opportunity_has_discriminator",
    "opportunity_requires_capability",
    "opportunity_involves_technology",
    "company_has_capability",
    "company_has_past_performance",
)


class GraphEntity(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "graph_entity"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "entity_type",
            "normalized_key",
            name="uq_graph_entity_ws_type_key",
        ),
        CheckConstraint(
            f"entity_type IN {ENTITY_TYPES!r}", name="ck_graph_entity_type"
        ),
        Index("ix_graph_entity_ws_type", "workspace_id", "entity_type"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(400), nullable=False)
    normalized_key: Mapped[str] = mapped_column(String(400), nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    outgoing_edges = relationship(
        "GraphEdge",
        foreign_keys="GraphEdge.source_entity_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class GraphEdge(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "graph_edge"
    __table_args__ = (
        CheckConstraint(
            f"relation IN {RELATION_TYPES!r}", name="ck_graph_edge_relation"
        ),
        Index("ix_graph_edge_ws_relation", "workspace_id", "relation"),
        Index("ix_graph_edge_opportunity", "opportunity_id"),
        Index("ix_graph_edge_provenance", "opportunity_id", "module_id"),
        Index("ix_graph_edge_source", "source_entity_id"),
        Index("ix_graph_edge_target", "target_entity_id"),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("workspace.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("graph_entity.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("graph_entity.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation: Mapped[str] = mapped_column(String(60), nullable=False)
    # Provenance: which opportunity + module produced this fact. Lets a module
    # re-run replace exactly its own edges (idempotent ingestion).
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("opportunity.id", ondelete="CASCADE"),
        nullable=True,
    )
    module_id: Mapped[str | None] = mapped_column(String(80))
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    attributes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    source = relationship(
        "GraphEntity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_edges",
    )
    target = relationship("GraphEntity", foreign_keys=[target_entity_id])
