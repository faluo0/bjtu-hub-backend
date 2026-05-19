# tests/test_api.py — 后端接口测试
# pytest + FastAPI TestClient + SQLite 内存库

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# 内存 SQLite + StaticPool：确保所有连接看到同一份数据
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ─── 课程 ────────────────────────────────────────────

def test_get_today_courses_empty():
    """未导入课表时返回种子数据"""
    res = client.get("/api/courses/today")
    assert res.status_code == 200
    data = res.json()
    assert "courses" in data
    assert data.get("source") == "demo-empty"


def test_get_week_courses_empty():
    """未导入课表时返回周课提示"""
    res = client.get("/api/courses?week=1&term=2024-2025-2")
    assert res.status_code == 200
    assert res.json()["source"] == "demo-empty"


def test_import_and_query_schedule():
    """导入课表后能查到"""
    courses = [
        {"name": "操作系统", "dayOfWeek": 0, "startSlot": 2, "endSlot": 2,
         "location": "YF207", "teacher": "张迪", "weeks": [1, 2, 3, 4, 5, 6, 7, 8]},
        {"name": "射箭", "dayOfWeek": 1, "startSlot": 2, "endSlot": 2,
         "location": "综合体育馆", "teacher": "鲁大兴", "weeks": [1, 2, 3]},
    ]
    res = client.post("/api/schedules", json={"term": "2024-2025-2", "courses": courses})
    assert res.status_code == 200
    assert res.json()["imported"] == 2

    # 每周课表
    res2 = client.get("/api/courses?week=1&term=2024-2025-2")
    assert res2.json()["source"] == "database"
    assert len(res2.json()["courses"]) == 2


def test_import_empty_courses():
    """空数组应被拒"""
    res = client.post("/api/schedules", json={"term": "2024-2025-2", "courses": []})
    assert res.status_code == 400


# ─── 评价 ────────────────────────────────────────────

def test_get_reviews_seeded():
    """启动时有种子评价数据"""
    res = client.get("/api/reviews")
    assert res.status_code == 200
    assert isinstance(res.json()["list"], list)


def test_add_review():
    """提交一条评价"""
    payload = {"courseName": "测试课程", "teacher": "测试老师",
               "avgScore": 4.0, "tags": [], "comment": "不错"}
    res = client.post("/api/reviews", json=payload)
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 评价列表里应该有它
    res2 = client.get("/api/reviews")
    names = [r["courseName"] for r in res2.json()["list"]]
    assert "测试课程" in names


def test_get_review_detail():
    """评价详情接口"""
    # 先提交一条
    client.post("/api/reviews", json={
        "courseName": "详情测试", "teacher": "T", "avgScore": 3.5,
        "tags": ["测试"], "comment": "还行"})
    # 取第一条
    res = client.get("/api/reviews")
    rid = res.json()["list"][0]["id"]
    res2 = client.get(f"/api/reviews/{rid}")
    assert res2.status_code == 200
    assert res2.json()["courseName"] == "详情测试"


def test_review_detail_404():
    """不存在的评价"""
    res = client.get("/api/reviews/99999")
    assert res.status_code == 404


# ─── DDL ─────────────────────────────────────────────

def test_get_ddls():
    """DDL 列表（可能有种子数据）"""
    res = client.get("/api/ddls")
    assert res.status_code == 200
    assert "ddls" in res.json()


def test_add_and_delete_ddl():
    """添加再删除 DDL"""
    add = client.post("/api/ddls", json={
        "name": "测试任务", "course": "测试课",
        "deadline": "2026-06-01", "countdown": "剩 10 天", "urgentLevel": "normal"})
    assert add.status_code == 200
    ddl_id = add.json()["id"]

    # 列表里出现
    list_res = client.get("/api/ddls")
    names = [d["name"] for d in list_res.json()["ddls"]]
    assert "测试任务" in names

    # 删除
    delete = client.delete(f"/api/ddls/{ddl_id}")
    assert delete.status_code == 200
    assert delete.json()["success"] is True


# ─── 资料 ────────────────────────────────────────────

def test_get_resources():
    """资料列表"""
    res = client.get("/api/resources")
    assert res.status_code == 200
    assert isinstance(res.json()["list"], list)


# ─── 用户 ────────────────────────────────────────────

def test_user_stats():
    res = client.get("/api/user/stats")
    assert res.status_code == 200
    data = res.json()
    assert "reviewCount" in data
    assert "uploadCount" in data


def test_get_and_update_profile():
    """获取和更新资料"""
    # 获取默认
    res = client.get("/api/user/profile")
    assert res.status_code == 200
    assert res.json()["nickName"] == "同学"

    # 更新
    res2 = client.put("/api/user/profile", json={"nickName": "小明", "studentId": "202330724763"})
    assert res2.status_code == 200
    assert res2.json()["profile"]["nickName"] == "小明"
