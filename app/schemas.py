from pydantic import BaseModel
from typing import Optional, List


class CourseItem(BaseModel):
    name: str
    dayOfWeek: int
    startSlot: int
    endSlot: int
    location: str = ""
    teacher: str = ""
    weeks: List[int] = []

    class Config:
        from_attributes = True


class ImportScheduleRequest(BaseModel):
    term: str
    courses: List[CourseItem]


class ReviewItem(BaseModel):
    courseName: str
    teacher: str = ""
    avgScore: float = 0.0
    tags: List[str] = []
    comment: str = ""

    class Config:
        from_attributes = True
