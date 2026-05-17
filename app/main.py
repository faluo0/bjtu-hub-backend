from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database import engine, get_db, Base
from app.models import Schedule, DDL, Review, Resource
from pydantic import BaseModel
from typing import List, Any

from app.schemas import ImportScheduleRequest, ReviewItem

app = FastAPI(title="BJTU Hub API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 节次→时间映射（北交大 7 节制）
SLOT_TIME = {
    1: {"start": "08:00", "end": "09:50"},
    2: {"start": "10:10", "end": "12:00"},
    3: {"start": "12:10", "end": "14:00"},
    4: {"start": "14:10", "end": "16:00"},
    5: {"start": "16:20", "end": "18:10"},
    6: {"start": "19:00", "end": "20:50"},
    7: {"start": "21:00", "end": "21:50"},
}

USER_ID = "anonymous"

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _seed_if_empty()


def _seed_if_empty():
    db = next(get_db())
    try:
        if db.query(Review).count() == 0:
            db.add_all([
                Review(course_name="操作系统", teacher="张迪", avg_score=4.5, review_count=128,
                       tags=["给分好", "硬核"], latest_comment="老师讲课逻辑清晰，但实验比较硬核。"),
                Review(course_name="Linux操作系统与网络编程", teacher="张健", avg_score=4.3, review_count=67,
                       tags=["实用", "编程量大"], latest_comment="内容很硬，但收获很大。"),
            ])
        if db.query(Resource).count() == 0:
            db.add_all([
                Resource(name="操作系统-期末试卷.pdf", course_name="操作系统", size="1.2MB",
                         upload_time="3天前", type_icon="📄", download_count=234, like_count=45),
                Resource(name="数据库原理-笔记.pdf", course_name="数据库原理", size="3.5MB",
                         upload_time="1周前", type_icon="📝", download_count=187, like_count=32),
            ])
        if db.query(DDL).count() == 0:
            db.add_all([
                DDL(name="操作系统实验三", course="操作系统", deadline="2026-05-12 23:59",
                    countdown="剩 2 天", urgent_level="urgent"),
                DDL(name="数据库 ER 图作业", course="数据库原理", deadline="2026-05-15 23:59",
                    countdown="剩 5 天", urgent_level="warning"),
            ])
        db.commit()
    finally:
        db.close()


def _today_dow():
    d = datetime.now().weekday()  # 0=Mon, 6=Sun
    return d  # Python weekday() already matches our convention


# ─── 课程相关 ──────────────────────────────────────

@app.get("/api/courses/today")
def get_today_courses(db: Session = Depends(get_db)):
    dow = _today_dow()
    rows = db.query(Schedule).filter(
        Schedule.user_id == USER_ID,
        Schedule.day_of_week == dow,
    ).order_by(Schedule.start_slot).all()

    if not rows:
        rows = db.query(Schedule).filter(Schedule.user_id == USER_ID).all()
        if not rows:
            # 完全没数据 → 返回种子数据
            return {"courses": [
                {"id": "seed-1", "name": "【示例】请先导入课表", "startTime": "10:10", "endTime": "12:00", "location": ""},
            ], "source": "demo-empty"}
        return {"courses": [], "source": "database-empty-today"}

    return {
        "courses": [
            {
                "id": r.id,
                "name": r.name,
                "startTime": SLOT_TIME.get(r.start_slot, {}).get("start", ""),
                "endTime": SLOT_TIME.get(r.end_slot, {}).get("end", ""),
                "location": r.location,
            }
            for r in rows
        ],
        "source": "database",
    }


@app.get("/api/courses")
def get_week_courses(week: int = 1, term: str = "2024-2025-2", db: Session = Depends(get_db)):
    rows = db.query(Schedule).filter(
        Schedule.user_id == USER_ID,
        Schedule.term == term,
    ).order_by(Schedule.day_of_week, Schedule.start_slot).all()

    if not rows:
        return {
            "courses": [
                {"id": "seed-w1", "name": "【示例】请先导入课表", "dayOfWeek": 0, "startSlot": 2, "endSlot": 2,
                 "location": "", "teacher": "", "timeText": "先导入课表"},
            ],
            "term": term, "week": week, "source": "demo-empty",
        }

    return {
        "courses": [
            {
                "id": r.id,
                "name": r.name,
                "dayOfWeek": r.day_of_week,
                "startSlot": r.start_slot,
                "endSlot": r.end_slot,
                "location": r.location,
                "teacher": r.teacher,
                "timeText": r.name,
            }
            for r in rows
        ],
        "term": term, "week": week, "source": "database",
    }


# ─── 课表导入 ──────────────────────────────────────

@app.post("/api/schedules")
def import_schedule(req: ImportScheduleRequest, db: Session = Depends(get_db)):
    if not req.courses:
        raise HTTPException(status_code=400, detail="courses 不能为空")

    db.query(Schedule).filter(Schedule.user_id == USER_ID, Schedule.term == req.term).delete()

    count = 0
    for c in req.courses:
        db.add(Schedule(
            user_id=USER_ID,
            name=c.name,
            day_of_week=c.dayOfWeek,
            start_slot=c.startSlot,
            end_slot=c.endSlot,
            location=c.location,
            teacher=c.teacher,
            term=req.term,
            weeks=c.weeks,
        ))
        count += 1

    db.commit()
    return {"success": True, "total": len(req.courses), "imported": count}


# ─── DDL ───────────────────────────────────────────

@app.get("/api/ddls")
def get_ddls(db: Session = Depends(get_db)):
    rows = db.query(DDL).filter(DDL.user_id == USER_ID).all()
    return {
        "ddls": [
            {"id": r.id, "name": r.name, "course": r.course,
             "deadline": r.deadline, "countdown": r.countdown, "urgentLevel": r.urgent_level}
            for r in rows
        ],
    }


@app.post("/api/ddls")
def add_ddl(req: dict, db: Session = Depends(get_db)):
    d = DDL(
        user_id=USER_ID,
        name=req.get("name", ""),
        course=req.get("course", ""),
        deadline=req.get("deadline", ""),
        countdown=req.get("countdown", ""),
        urgent_level=req.get("urgentLevel", "normal"),
    )
    db.add(d)
    db.commit()
    return {"success": True, "id": d.id}


class DeleteItem(BaseModel):
    id: int


@app.delete("/api/ddls/{ddl_id}")
def delete_ddl(ddl_id: int, db: Session = Depends(get_db)):
    db.query(DDL).filter(DDL.id == ddl_id, DDL.user_id == USER_ID).delete()
    db.commit()
    return {"success": True}


# ─── 评价 ──────────────────────────────────────────

@app.get("/api/reviews")
def get_reviews(db: Session = Depends(get_db)):
    rows = db.query(Review).all()
    return {
        "list": [
            {"id": r.id, "courseName": r.course_name, "teacher": r.teacher,
             "avgScore": r.avg_score, "reviewCount": r.review_count,
             "tags": r.tags, "latestComment": r.latest_comment}
            for r in rows
        ],
    }


@app.get("/api/reviews/{review_id}")
def get_review_detail(review_id: int, db: Session = Depends(get_db)):
    r = db.query(Review).filter(Review.id == review_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="评价不存在")
    return {
        "id": r.id,
        "courseName": r.course_name,
        "teacher": r.teacher,
        "avgScore": r.avg_score,
        "reviewCount": r.review_count,
        "tags": r.tags,
        "latestComment": r.latest_comment,
        "scoreDistribution": [
            {"star": 5, "count": int(r.review_count * 0.45), "percent": 45},
            {"star": 4, "count": int(r.review_count * 0.30), "percent": 30},
            {"star": 3, "count": int(r.review_count * 0.15), "percent": 15},
            {"star": 2, "count": int(r.review_count * 0.07), "percent": 7},
            {"star": 1, "count": int(r.review_count * 0.03), "percent": 3},
        ],
        "reviews": [
            {"id": 1, "user": "匿名同学", "score": r.avg_score, "time": "最近",
             "content": r.latest_comment},
        ],
    }


@app.post("/api/reviews")
def add_review(req: ReviewItem, db: Session = Depends(get_db)):
    r = Review(
        course_name=req.courseName,
        teacher=req.teacher,
        avg_score=req.avgScore,
        review_count=1,
        tags=req.tags,
        latest_comment=req.comment,
        user_id=USER_ID,
    )
    db.add(r)
    db.commit()
    return {"success": True, "id": r.id}


# ─── 资料 ──────────────────────────────────────────

@app.get("/api/resources")
def get_resources(db: Session = Depends(get_db)):
    rows = db.query(Resource).all()
    return {
        "list": [
            {"id": r.id, "name": r.name, "courseName": r.course_name,
             "size": r.size, "uploadTime": r.upload_time,
             "typeIcon": r.type_icon, "downloadCount": r.download_count,
             "likeCount": r.like_count, "liked": False}
            for r in rows
        ],
    }


# ─── 用户统计 ──────────────────────────────────────

@app.get("/api/user/stats")
def get_user_stats(db: Session = Depends(get_db)):
    review_count = db.query(Review).filter(Review.user_id == USER_ID).count()
    resource_count = db.query(Resource).filter(Resource.user_id == USER_ID).count()
    return {"reviewCount": review_count, "uploadCount": resource_count, "helpCount": 0}


# ─── 用户资料 ──────────────────────────────────────

_profile = {"nickName": "同学", "studentId": ""}


@app.get("/api/user/profile")
def get_profile():
    return _profile


class ProfileUpdate(BaseModel):
    nickName: str = ""
    studentId: str = ""


@app.put("/api/user/profile")
def update_profile(req: ProfileUpdate):
    if req.nickName:
        _profile["nickName"] = req.nickName
    _profile["studentId"] = req.studentId
    return {"success": True, "profile": _profile}
