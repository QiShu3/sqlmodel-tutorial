from email.policy import default
from pydoc import describe
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class HeroBase(SQLModel):
    """英雄基础模型（共享字段）"""
    name: str = Field(
        max_length = 50 ,
        description = "英雄名称"
    )
    secret_name: str = Field(
        description="真实名字"
    )
    age: Optional[int] = Field(
        default = None,
        ge=0,le=200,
        description = "年龄"
    )

class Hero(HeroBase, table=True):
    """英雄模型（数据库表）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class HeroCreate(HeroBase):
    """创建英雄的请求模型"""
    pass

class HeroRead(HeroBase):
    """读取英雄的响应模型"""
    id: int
    created_at: datetime

class HeroUpdate(SQLModel):
    """更新英雄的请求模型"""
    name: Optional[str] = Field(default=None, max_length=50)
    secret_name: Optional[str] = None
    age: Optional[int] = Field(default=None, ge=0, le=200)