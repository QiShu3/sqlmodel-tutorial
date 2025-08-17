#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示使用字段生成器创建的模型
这个文件展示了如何使用 GUI 工具生成的 SQLModel 代码
"""

from datetime import datetime, date, time
from decimal import Decimal
from sqlmodel import SQLModel, Field, create_engine, Session
from typing import Optional, List, Dict, Any
import uuid
from enum import Enum

# 状态枚举（示例）
class UserStatus(str, Enum):
    """用户状态枚举"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    DELETED = "deleted"

# 使用字段生成器生成的用户模型示例
class User(SQLModel, table=True):
    """用户模型 - 使用字段生成器创建"""
    
    # 主键字段
    id: Optional[int] = Field(default=None, primary_key=True, description="用户ID")
    
    # 基本信息字段
    username: str = Field(max_length=50, min_length=3, description="用户名")
    email: str = Field(max_length=100, description="邮箱地址")
    full_name: Optional[str] = Field(default=None, max_length=100, description="全名")
    
    # 数值字段
    age: Optional[int] = Field(default=None, ge=0, le=150, description="年龄")
    balance: Decimal = Field(
        default=Decimal('0.00'), 
        max_digits=10, 
        decimal_places=2, 
        description="账户余额"
    )
    
    # 布尔字段
    is_active: bool = Field(default=True, description="是否激活")
    is_verified: Optional[bool] = Field(default=False, description="是否已验证")
    is_premium: bool = Field(default=False, description="是否为高级用户")
    
    # 日期时间字段
    created_at: datetime = Field(default_factory=datetime.utcnow, description="创建时间")
    updated_at: Optional[datetime] = Field(default=None, description="更新时间")
    birth_date: Optional[date] = Field(default=None, description="出生日期")
    last_login_time: Optional[time] = Field(default=None, description="最后登录时间")
    
    # 特殊类型字段
    uuid_field: uuid.UUID = Field(default_factory=uuid.uuid4, description="唯一标识符")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="用户状态")
    
    # JSON 字段
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="用户偏好设置")
    tags: Optional[List[str]] = Field(default=None, description="用户标签")
    
    # 文本字段
    bio: Optional[str] = Field(default=None, max_length=500, description="个人简介")
    notes: Optional[str] = Field(default=None, description="备注信息")

# 产品模型示例
class Product(SQLModel, table=True):
    """产品模型 - 展示不同字段类型的使用"""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, description="产品名称")
    sku: str = Field(max_length=50, description="产品编码")
    price: Decimal = Field(max_digits=8, decimal_places=2, description="价格")
    cost: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=2, description="成本")
    weight: Optional[float] = Field(default=None, ge=0, description="重量(kg)")
    is_available: bool = Field(default=True, description="是否可用")
    stock_quantity: int = Field(default=0, ge=0, description="库存数量")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
def create_demo_data():
    """创建演示数据"""
    
    # 创建内存数据库
    engine = create_engine("sqlite:///:memory:", echo=True)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # 创建用户数据
        user1 = User(
            username="john_doe",
            email="john@example.com",
            full_name="John Doe",
            age=30,
            balance=Decimal('1500.50'),
            is_verified=True,
            birth_date=date(1993, 5, 15),
            preferences={"theme": "dark", "language": "en"},
            tags=["developer", "python", "sqlmodel"],
            bio="Software developer with 5+ years experience"
        )
        
        user2 = User(
            username="jane_smith",
            email="jane@example.com",
            full_name="Jane Smith",
            age=28,
            balance=Decimal('2300.75'),
            is_premium=True,
            status=UserStatus.ACTIVE,
            preferences={"theme": "light", "notifications": True},
            tags=["designer", "ui/ux"]
        )
        
        # 创建产品数据
        product1 = Product(
            name="Python编程指南",
            sku="BOOK-PY-001",
            price=Decimal('59.99'),
            cost=Decimal('25.00'),
            weight=0.5,
            stock_quantity=100
        )
        
        product2 = Product(
            name="SQLModel实战教程",
            sku="BOOK-SQL-002",
            price=Decimal('79.99'),
            cost=Decimal('35.00'),
            weight=0.6,
            stock_quantity=50,
            is_available=True
        )
        
        # 添加到数据库
        session.add_all([user1, user2, product1, product2])
        session.commit()
        
        # 查询数据
        print("\n=== 用户数据 ===")
        users = session.query(User).all()
        for user in users:
            print(f"用户: {user.username} ({user.email})")
            print(f"  年龄: {user.age}, 余额: {user.balance}")
            print(f"  状态: {user.status}, 激活: {user.is_active}")
            print(f"  创建时间: {user.created_at}")
            print(f"  标签: {user.tags}")
            print()
        
        print("\n=== 产品数据 ===")
        products = session.query(Product).all()
        for product in products:
            print(f"产品: {product.name} (SKU: {product.sku})")
            print(f"  价格: {product.price}, 库存: {product.stock_quantity}")
            print(f"  可用: {product.is_available}")
            print()
        
        # 演示字段验证
        print("\n=== 字段验证演示 ===")
        try:
            # 尝试创建无效用户（用户名太短）
            invalid_user = User(
                username="ab",  # 少于最小长度 3
                email="test@example.com"
            )
            session.add(invalid_user)
            session.commit()
        except Exception as e:
            print(f"验证错误（预期）: {e}")
        
        try:
            # 尝试创建无效年龄的用户
            invalid_user2 = User(
                username="test_user",
                email="test2@example.com",
                age=-5  # 小于最小值 0
            )
            session.add(invalid_user2)
            session.commit()
        except Exception as e:
            print(f"年龄验证错误（预期）: {e}")

def demonstrate_field_features():
    """演示字段特性"""
    print("\n=== SQLModel 字段特性演示 ===")
    
    # 展示字段信息
    print("\n用户模型字段信息:")
    for field_name, field_info in User.__fields__.items():
        print(f"  {field_name}: {field_info.type_}")
        if hasattr(field_info, 'field_info') and field_info.field_info:
            constraints = []
            if hasattr(field_info.field_info, 'max_length') and field_info.field_info.max_length:
                constraints.append(f"max_length={field_info.field_info.max_length}")
            if hasattr(field_info.field_info, 'ge') and field_info.field_info.ge is not None:
                constraints.append(f"ge={field_info.field_info.ge}")
            if hasattr(field_info.field_info, 'le') and field_info.field_info.le is not None:
                constraints.append(f"le={field_info.field_info.le}")
            if constraints:
                print(f"    约束: {', '.join(constraints)}")
    
    # 展示默认值
    print("\n默认值演示:")
    user = User(username="demo_user", email="demo@example.com")
    print(f"  新用户默认激活状态: {user.is_active}")
    print(f"  新用户默认余额: {user.balance}")
    print(f"  新用户UUID: {user.uuid_field}")
    print(f"  新用户状态: {user.status}")
    print(f"  创建时间: {user.created_at}")

if __name__ == "__main__":
    print("SQLModel 字段生成器演示")
    print("=" * 50)
    
    # 演示字段特性
    demonstrate_field_features()
    
    # 创建和操作演示数据
    create_demo_data()
    
    print("\n演示完成！")
    print("\n提示: 这些模型是使用字段生成器 GUI 工具创建的")
    print("你可以运行 'python practice/field_generator_gui.py' 来使用图形界面工具")