from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from app.database import Base


class Schedule(Base):
    __tablename__ = "schedules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="anonymous")
    name = Column(String(128), nullable=False)
    day_of_week = Column(Integer, default=0)  # 0=Mon, 6=Sun
    start_slot = Column(Integer, default=1)
    end_slot = Column(Integer, default=1)
    location = Column(String(128), default="")
    teacher = Column(String(64), default="")
    term = Column(String(32), default="2024-2025-2")
    weeks = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class DDL(Base):
    __tablename__ = "ddls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(64), default="anonymous")
    name = Column(String(256), nullable=False)
    course = Column(String(128), default="")
    deadline = Column(String(32), default="")
    countdown = Column(String(32), default="")
    urgent_level = Column(String(16), default="normal")


class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_name = Column(String(128), nullable=False)
    teacher = Column(String(64), default="")
    avg_score = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    tags = Column(JSON, default=list)
    latest_comment = Column(String(512), default="")
    user_id = Column(String(64), default="anonymous")


class Resource(Base):
    __tablename__ = "resources"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(256), nullable=False)
    course_name = Column(String(128), default="")
    size = Column(String(16), default="")
    upload_time = Column(String(32), default="")
    type_icon = Column(String(8), default="")
    download_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    user_id = Column(String(64), default="anonymous")
