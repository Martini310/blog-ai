"""
Central API router – mounts all route modules.

Add new route modules here; never import them individually in main.py.
"""
from fastapi import APIRouter

from app.api.routes import articles, auth, calendar, health, projects, schedules, topics

api_router = APIRouter()

# Health – no prefix, available at root
api_router.include_router(health.router)

# Versioned API routes
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(topics.router)
api_router.include_router(articles.router)
api_router.include_router(schedules.router)
api_router.include_router(calendar.router)
