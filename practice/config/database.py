from sqlmodel import create_engine,SQLModel,Session
from typing import Generator
import os


# 数据库 URL（默认使用 SQLite）
DATABASE_URL = "sqlite:///./tutorial.db"

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 开发时显示 SQL 语句
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def create_db_and_tables():
    """创建数据库表"""
    SQLModel.metadata.create_all(engine)
    print("数据库表创建成功")

def get_session() -> Generator[Session,None,None]:
    """获取数据库会话"""
    with Session(engine) as session:
        yield session