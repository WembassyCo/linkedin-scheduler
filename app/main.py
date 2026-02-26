import os
import logging
from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
from dotenv import load_dotenv

load_dotenv()

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///linkedin_scheduler.db', echo=False)
SessionLocal = sessionmaker(bind=engine)

class ScheduledPost(Base):
    __tablename__ = 'scheduled_posts'
    
    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False)
    schedule_time = Column(DateTime, nullable=False)
    visibility = Column(String, default='PUBLIC')
    recurring = Column(Boolean, default=False)
    recurrence_pattern = Column(String, nullable=True)
    status = Column(String, default='scheduled')
    linkedin_post_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)

Base.metadata.create_all(engine)

# LinkedIn API configuration
LI_CLIENT_ID = os.getenv('LI_CLIENT_ID')
LI_CLIENT_SECRET = os.getenv('LI_CLIENT_SECRET')
LI_ACCESS_TOKEN = os.getenv('LI_ACCESS_TOKEN')
LI_PERSON_URN = os.getenv('LI_PERSON_URN')

# Scheduler
scheduler = BackgroundScheduler()

def post_to_linkedin(post_id: int):
    """Post content to LinkedIn API"""
    db = SessionLocal()
    try:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if not post:
            logger.error(f"Post {post_id} not found")
            return
        
        if post.status == 'published':
            logger.info(f"Post {post_id} already published")
            return
        
        if not LI_ACCESS_TOKEN or not LI_PERSON_URN:
            logger.error("LinkedIn credentials not configured")
            post.status = 'failed'
            post.error_message = 'LinkedIn credentials not configured'
            db.commit()
            return
        
        # LinkedIn API endpoint
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {LI_ACCESS_TOKEN}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        payload = {
            "author": f"urn:li:person:{LI_PERSON_URN}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": post.content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": post.visibility
            }
        }
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            post.linkedin_post_id = response.headers.get('X-LinkedIn-Id', 'unknown')
            post.status = 'published'
            logger.info(f"Successfully posted to LinkedIn: {post.linkedin_post_id}")
            
            # Handle recurring posts
            if post.recurring:
                create_recurring_post(db, post)
        else:
            post.retry_count += 1
            if post.retry_count >= 3:
                post.status = 'failed'
                post.error_message = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"Post {post_id} failed after 3 retries: {post.error_message}")
            else:
                logger.warning(f"Post {post_id} failed (attempt {post.retry_count}), will retry")
        
        db.commit()
        
    except Exception as e:
        logger.exception(f"Error posting to LinkedIn: {e}")
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if post:
            post.retry_count += 1
            if post.retry_count >= 3:
                post.status = 'failed'
                post.error_message = str(e)
            db.commit()
    finally:
        db.close()

def create_recurring_post(db, original_post):
    """Create next occurrence of a recurring post"""
    from datetime import timedelta
    
    if original_post.recurrence_pattern == 'daily':
        next_time = original_post.schedule_time + timedelta(days=1)
    elif original_post.recurrence_pattern == 'weekly':
        next_time = original_post.schedule_time + timedelta(weeks=1)
    else:
        return
    
    new_post = ScheduledPost(
        content=original_post.content,
        schedule_time=next_time,
        visibility=original_post.visibility,
        recurring=original_post.recurring,
        recurrence_pattern=original_post.recurrence_pattern,
        status='scheduled'
    )
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    # Schedule the new post
    scheduler.add_job(
        post_to_linkedin,
        'date',
        run_date=next_time,
        args=[new_post.id],
        id=f'linkedin_post_{new_post.id}'
    )
    logger.info(f"Created recurring post {new_post.id} for {next_time}")

def load_scheduled_jobs():
    """Load existing scheduled posts from database on startup"""
    db = SessionLocal()
    try:
        posts = db.query(ScheduledPost).filter(ScheduledPost.status == 'scheduled').all()
        for post in posts:
            if post.schedule_time > datetime.utcnow():
                scheduler.add_job(
                    post_to_linkedin,
                    'date',
                    run_date=post.schedule_time,
                    args=[post.id],
                    id=f'linkedin_post_{post.id}',
                    replace_existing=True
                )
                logger.info(f"Loaded scheduled post {post.id} for {post.schedule_time}")
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()
    load_scheduled_jobs()
    logger.info("LinkedIn Scheduler started")
    yield
    # Shutdown
    scheduler.shutdown()
    logger.info("LinkedIn Scheduler stopped")

app = FastAPI(title="LinkedIn Content Scheduler", lifespan=lifespan)

# Pydantic models
class SchedulePostRequest(BaseModel):
    content: str
    schedule_time: datetime
    visibility: str = "PUBLIC"
    recurring: bool = False
    recurrence_pattern: Optional[str] = None

class SchedulePostResponse(BaseModel):
    id: int
    status: str
    message: str

class ScheduledPostItem(BaseModel):
    id: int
    content: str
    schedule_time: datetime
    visibility: str
    recurring: bool
    recurrence_pattern: Optional[str]
    status: str
    created_at: datetime
    retry_count: int

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/api/v1/schedule", response_model=SchedulePostResponse)
def schedule_post(request: SchedulePostRequest):
    db = SessionLocal()
    try:
        if request.schedule_time <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="Schedule time must be in the future")
        
        if request.recurring and request.recurrence_pattern not in ['daily', 'weekly']:
            raise HTTPException(status_code=400, detail="Recurrence pattern must be 'daily' or 'weekly'")
        
        post = ScheduledPost(
            content=request.content,
            schedule_time=request.schedule_time,
            visibility=request.visibility,
            recurring=request.recurring,
            recurrence_pattern=request.recurrence_pattern,
            status='scheduled'
        )
        db.add(post)
        db.commit()
        db.refresh(post)
        
        # Schedule the job
        scheduler.add_job(
            post_to_linkedin,
            'date',
            run_date=request.schedule_time,
            args=[post.id],
            id=f'linkedin_post_{post.id}'
        )
        
        logger.info(f"Scheduled post {post.id} for {request.schedule_time}")
        return SchedulePostResponse(
            id=post.id,
            status="scheduled",
            message=f"Post scheduled for {request.schedule_time}"
        )
    finally:
        db.close()

@app.get("/api/v1/scheduled", response_model=List[ScheduledPostItem])
def list_scheduled():
    db = SessionLocal()
    try:
        posts = db.query(ScheduledPost).order_by(ScheduledPost.schedule_time.desc()).all()
        return [
            ScheduledPostItem(
                id=p.id,
                content=p.content[:100] + "..." if len(p.content) > 100 else p.content,
                schedule_time=p.schedule_time,
                visibility=p.visibility,
                recurring=p.recurring,
                recurrence_pattern=p.recurrence_pattern,
                status=p.status,
                created_at=p.created_at,
                retry_count=p.retry_count
            ) for p in posts
        ]
    finally:
        db.close()

@app.delete("/api/v1/scheduled/{post_id}")
def cancel_scheduled(post_id: int):
    db = SessionLocal()
    try:
        post = db.query(ScheduledPost).filter(ScheduledPost.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        if post.status != 'scheduled':
            raise HTTPException(status_code=400, detail=f"Post is already {post.status}")
        
        # Remove from scheduler
        job_id = f'linkedin_post_{post_id}'
        try:
            scheduler.remove_job(job_id)
        except:
            pass
        
        post.status = 'cancelled'
        db.commit()
        
        logger.info(f"Cancelled scheduled post {post_id}")
        return {"status": "cancelled", "id": post_id}
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
