"""SQLAlchemy ORM models for MissionIQ.

Importing this package registers every model on ``Base.metadata`` for
Alembic autogeneration and the test database fixtures.
"""
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.chat import ChatMessage, ChatThread
from app.models.company_profile import Capability, CompanyProfile
from app.models.document import Document, DocumentChunk
from app.models.graph import GraphEdge, GraphEntity
from app.models.intelligence import (
    AIOutput,
    ComplianceRequirement,
    EvaluationCriterion,
    Risk,
)
from app.models.market_intel import (
    MarketIntelRecord,
    MarketIntelSource,
    OpportunityMarketIntelLink,
)
from app.models.opportunity import Opportunity
from app.models.user import RefreshToken, User
from app.models.workspace import TeamMember, Workspace

__all__ = [
    "AIOutput",
    "AuditLog",
    "Base",
    "Capability",
    "ChatMessage",
    "ChatThread",
    "ComplianceRequirement",
    "CompanyProfile",
    "Document",
    "DocumentChunk",
    "EvaluationCriterion",
    "GraphEdge",
    "GraphEntity",
    "MarketIntelRecord",
    "MarketIntelSource",
    "Opportunity",
    "OpportunityMarketIntelLink",
    "RefreshToken",
    "Risk",
    "TeamMember",
    "User",
    "Workspace",
]
