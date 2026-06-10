"""v1 API router assembly."""
from fastapi import APIRouter

from app.api.v1 import (
    auth,
    automation,
    chat,
    company_profile,
    connectors,
    documents,
    exports,
    governance,
    health,
    market_intel,
    memory,
    modules,
    opportunities,
    outcomes,
    users,
    workspaces,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(workspaces.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(
    company_profile.router, prefix="/workspaces", tags=["company-profile"]
)
api_router.include_router(opportunities.router, tags=["opportunities"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(market_intel.router, prefix="/market-intel", tags=["market-intel"])
api_router.include_router(market_intel.links_router, tags=["market-intel"])
api_router.include_router(modules.router, tags=["modules"])
api_router.include_router(memory.router, tags=["memory"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(exports.router, tags=["exports"])
api_router.include_router(connectors.router, tags=["connectors"])
api_router.include_router(automation.router, tags=["automation"])
api_router.include_router(outcomes.router, tags=["outcomes"])
api_router.include_router(governance.router, tags=["governance"])
