import asyncio
from sqlalchemy import select
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate
from app.services.project_service import ProjectService
from app.tasks.content_tasks import generate_topics, generate_article

async def main():
    async with get_db() as db:
        users = await db.scalars(select(User).limit(1))
        user = users.first()
        if not user:
            print("No users found in database.")
            return

        print(f"Using user: {user.email} (id: {user.id})")
        
        # 1. Create project
        project_svc = ProjectService(db)
        project_create = ProjectCreate(
            name="Demo AI Project",
            description="Testing AI content generation engine",
            domain="technology",
            language="en"
        )
        project = await project_svc.create(user.id, project_create)
        project_id = project.id
        print(f"Project created: {project_id}")
        
    # Waiting for celery to do analysis
    print("Waiting 15s for project analysis Celery task...")
    await asyncio.sleep(15)
        
    print("Triggering topic generation manually...")
    # Celery delay
    result = generate_topics.delay(str(project_id), str(user.id), None)
    result.get(timeout=30)
    print("Topics generated.")
        
    async with get_db() as db:
        from app.models.content import Topic
        topics = list(await db.scalars(select(Topic).where(Topic.project_id == project_id)))
        if not topics:
            print("No topics generated.")
            return
            
        topic = topics[0]
        print(f"Selected topic {topic.id} ({topic.title})")
        topic_id = topic.id
        
    print("Triggering article generation...")
    art_result = generate_article.delay(str(topic_id), str(project_id), str(user.id), None)
    art_result.get(timeout=60)
    print("Article generated.")
        
    async with get_db() as db:
        from app.models.content import Article
        articles = list(await db.scalars(select(Article).where(Article.topic_id == topic_id)))
        if articles:
            article = articles[0]
            print(f"SUCCESS! Article ID: {article.id}")
            print(f"Title: {article.title}")
        else:
            print("Article was not saved.")

if __name__ == "__main__":
    asyncio.run(main())
