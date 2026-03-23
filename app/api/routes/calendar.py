from fastapi import APIRouter
from sqlalchemy import select

from app.api.dependencies import CurrentUser, DBSession
from app.models.content import Topic
from app.models.project import Project
from app.schemas.content import TopicOut


class CalendarTopicOut(TopicOut):
    project_name: str


router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("", response_model=list[CalendarTopicOut])
async def get_calendar_topics(current_user: CurrentUser, db: DBSession) -> list[CalendarTopicOut]:
    """
    Returns all topics that have a scheduled_date across all projects owned by the user.
    """
    stmt = (
        select(Topic, Project.name.label("project_name"))
        .join(Project, Project.id == Topic.project_id)
        .where(Project.owner_id == current_user.id)
        .where(Topic.scheduled_date.is_not(None))
        .order_by(Topic.scheduled_date.asc())
    )
    results = await db.execute(stmt)

    output = []
    for topic, project_name in results:
        # Pydantic v2: use model_dump() instead of dict()
        data = TopicOut.model_validate(topic).model_dump()
        data["project_name"] = project_name
        output.append(CalendarTopicOut(**data))

    return output
