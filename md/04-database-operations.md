# SQLModel 教程系列 - 第四章：数据库操作

## 目录

1. [数据库连接与配置](#1-数据库连接与配置)
2. [会话管理](#2-会话管理)
3. [基础 CRUD 操作](#3-基础-crud-操作)
4. [高级查询操作](#4-高级查询操作)
5. [事务处理](#5-事务处理)
6. [批量操作](#6-批量操作)
7. [性能优化](#7-性能优化)
8. [错误处理与调试](#8-错误处理与调试)
9. [实际应用示例](#9-实际应用示例)
10. [总结与下一步](#10-总结与下一步)

---

## 1. 数据库连接与配置

### 1.1 数据库引擎配置

```python
# database.py
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.pool import StaticPool
from typing import Generator
import os
from urllib.parse import quote_plus

# === 数据库配置类 ===
class DatabaseConfig:
    """数据库配置管理"""
    
    def __init__(self):
        self.database_type = os.getenv("DATABASE_TYPE", "sqlite")
        self.database_url = self._build_database_url()
        
    def _build_database_url(self) -> str:
        """构建数据库连接URL"""
        if self.database_type == "sqlite":
            return self._build_sqlite_url()
        elif self.database_type == "postgresql":
            return self._build_postgresql_url()
        elif self.database_type == "mysql":
            return self._build_mysql_url()
        else:
            raise ValueError(f"不支持的数据库类型: {self.database_type}")
    
    def _build_sqlite_url(self) -> str:
        """构建 SQLite 连接URL"""
        db_path = os.getenv("SQLITE_PATH", "./app.db")
        return f"sqlite:///{db_path}"
    
    def _build_postgresql_url(self) -> str:
        """构建 PostgreSQL 连接URL"""
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        user = os.getenv("POSTGRES_USER", "postgres")
        password = quote_plus(os.getenv("POSTGRES_PASSWORD", ""))
        database = os.getenv("POSTGRES_DB", "myapp")
        
        return f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    def _build_mysql_url(self) -> str:
        """构建 MySQL 连接URL"""
        host = os.getenv("MYSQL_HOST", "localhost")
        port = os.getenv("MYSQL_PORT", "3306")
        user = os.getenv("MYSQL_USER", "root")
        password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
        database = os.getenv("MYSQL_DB", "myapp")
        
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"

# === 引擎配置 ===
def create_database_engine(config: DatabaseConfig):
    """创建数据库引擎"""
    
    # 基础引擎参数
    engine_kwargs = {
        "echo": os.getenv("SQL_ECHO", "false").lower() == "true",  # SQL 日志
        "future": True,  # 使用 SQLAlchemy 2.0 风格
    }
    
    # 根据数据库类型添加特定配置
    if config.database_type == "sqlite":
        engine_kwargs.update({
            "poolclass": StaticPool,
            "connect_args": {
                "check_same_thread": False,  # SQLite 多线程支持
                "timeout": 20,  # 连接超时
            }
        })
    elif config.database_type == "postgresql":
        engine_kwargs.update({
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        })
    elif config.database_type == "mysql":
        engine_kwargs.update({
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
            "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
            "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
            "connect_args": {
                "charset": "utf8mb4",
                "autocommit": False,
            }
        })
    
    return create_engine(config.database_url, **engine_kwargs)

# === 全局引擎实例 ===
config = DatabaseConfig()
engine = create_database_engine(config)

# === 数据库初始化 ===
def create_db_and_tables():
    """创建数据库表"""
    SQLModel.metadata.create_all(engine)

def drop_db_and_tables():
    """删除所有数据库表"""
    SQLModel.metadata.drop_all(engine)

def reset_database():
    """重置数据库（删除并重新创建所有表）"""
    drop_db_and_tables()
    create_db_and_tables()
```

### 1.2 环境配置文件

```bash
# .env 文件示例

# === 数据库配置 ===
DATABASE_TYPE=postgresql  # sqlite, postgresql, mysql
SQL_ECHO=false  # 是否显示 SQL 日志

# === SQLite 配置 ===
SQLITE_PATH=./data/app.db

# === PostgreSQL 配置 ===
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=myuser
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=myapp

# === MySQL 配置 ===
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=mypassword
MYSQL_DB=myapp

# === 连接池配置 ===
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

---

## 2. 会话管理

### 2.1 基础会话操作

```python
# session_management.py
from sqlmodel import Session
from contextlib import contextmanager
from typing import Generator, Optional
from database import engine
import logging

logger = logging.getLogger(__name__)

# === 基础会话函数 ===
def get_session() -> Generator[Session, None, None]:
    """获取数据库会话（生成器模式）"""
    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话错误: {e}")
            raise
        finally:
            session.close()

@contextmanager
def get_session_context() -> Generator[Session, None, None]:
    """获取数据库会话（上下文管理器）"""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"数据库操作失败: {e}")
        raise
    finally:
        session.close()

# === 会话装饰器 ===
def with_session(func):
    """会话装饰器 - 自动管理会话生命周期"""
    def wrapper(*args, **kwargs):
        # 检查是否已经传入了 session
        if 'session' in kwargs and kwargs['session'] is not None:
            return func(*args, **kwargs)
        
        # 创建新会话
        with get_session_context() as session:
            kwargs['session'] = session
            return func(*args, **kwargs)
    
    return wrapper

# === 会话管理类 ===
class SessionManager:
    """会话管理器"""
    
    def __init__(self, engine=None):
        self.engine = engine or globals()['engine']
        self._session: Optional[Session] = None
    
    def __enter__(self) -> Session:
        """进入上下文管理器"""
        self._session = Session(self.engine)
        return self._session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文管理器"""
        if self._session:
            if exc_type is None:
                try:
                    self._session.commit()
                except Exception as e:
                    self._session.rollback()
                    logger.error(f"提交事务失败: {e}")
                    raise
            else:
                self._session.rollback()
                logger.error(f"事务回滚: {exc_val}")
            
            self._session.close()
            self._session = None
    
    def get_session(self) -> Session:
        """获取当前会话"""
        if not self._session:
            raise RuntimeError("会话未初始化，请在上下文管理器中使用")
        return self._session

# === 使用示例 ===
def example_session_usage():
    """会话使用示例"""
    
    # 方式1：使用生成器
    with get_session() as session:
        # 执行数据库操作
        pass
    
    # 方式2：使用上下文管理器
    with get_session_context() as session:
        # 执行数据库操作
        pass
    
    # 方式3：使用会话管理器
    with SessionManager() as session:
        # 执行数据库操作
        pass
    
    # 方式4：使用装饰器
    @with_session
    def some_database_operation(session: Session):
        # 执行数据库操作
        pass
    
    some_database_operation()  # 自动注入 session
```

### 2.2 FastAPI 集成

```python
# fastapi_integration.py
from fastapi import FastAPI, Depends, HTTPException
from sqlmodel import Session
from typing import Generator
from database import engine

app = FastAPI()

# === 依赖注入 ===
def get_db() -> Generator[Session, None, None]:
    """FastAPI 数据库会话依赖"""
    with Session(engine) as session:
        yield session

# === 路由示例 ===
@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    """获取用户信息"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

@app.post("/users/")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    db_user = User.from_orm(user)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# === 高级依赖注入 ===
class DatabaseDependency:
    """数据库依赖类"""
    
    def __init__(self, auto_commit: bool = True):
        self.auto_commit = auto_commit
    
    def __call__(self) -> Generator[Session, None, None]:
        with Session(engine) as session:
            try:
                yield session
                if self.auto_commit:
                    session.commit()
            except Exception:
                session.rollback()
                raise

# 创建不同的依赖实例
get_db_auto_commit = DatabaseDependency(auto_commit=True)
get_db_manual_commit = DatabaseDependency(auto_commit=False)

@app.post("/users/batch")
def create_users_batch(
    users: list[UserCreate], 
    db: Session = Depends(get_db_manual_commit)
):
    """批量创建用户（手动提交）"""
    try:
        db_users = []
        for user_data in users:
            db_user = User.from_orm(user_data)
            db.add(db_user)
            db_users.append(db_user)
        
        db.commit()  # 手动提交
        
        # 刷新所有对象
        for db_user in db_users:
            db.refresh(db_user)
        
        return db_users
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
```

---

## 3. 基础 CRUD 操作

### 3.1 创建操作 (Create)

```python
# crud_create.py
from sqlmodel import Session, select
from typing import List, Optional, Union
from models import User, Product, Order  # 假设已定义的模型
from datetime import datetime

class UserCRUD:
    """用户 CRUD 操作"""
    
    @staticmethod
    def create_user(session: Session, user_data: dict) -> User:
        """创建单个用户"""
        # 方式1：直接创建
        user = User(**user_data)
        session.add(user)
        session.commit()
        session.refresh(user)  # 获取数据库生成的字段（如ID）
        return user
    
    @staticmethod
    def create_user_safe(session: Session, user_data: dict) -> Optional[User]:
        """安全创建用户（处理重复等错误）"""
        try:
            # 检查邮箱是否已存在
            existing_user = session.exec(
                select(User).where(User.email == user_data.get('email'))
            ).first()
            
            if existing_user:
                raise ValueError(f"邮箱 {user_data.get('email')} 已存在")
            
            user = User(**user_data)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
            
        except Exception as e:
            session.rollback()
            print(f"创建用户失败: {e}")
            return None
    
    @staticmethod
    def create_users_batch(session: Session, users_data: List[dict]) -> List[User]:
        """批量创建用户"""
        users = []
        try:
            for user_data in users_data:
                user = User(**user_data)
                session.add(user)
                users.append(user)
            
            session.commit()
            
            # 刷新所有用户以获取生成的ID
            for user in users:
                session.refresh(user)
            
            return users
            
        except Exception as e:
            session.rollback()
            print(f"批量创建用户失败: {e}")
            return []
    
    @staticmethod
    def create_user_with_profile(session: Session, user_data: dict, profile_data: dict) -> User:
        """创建用户及其档案（关联对象）"""
        try:
            # 创建用户
            user = User(**user_data)
            session.add(user)
            session.flush()  # 刷新以获取用户ID，但不提交
            
            # 创建用户档案
            profile_data['user_id'] = user.id
            profile = UserProfile(**profile_data)
            session.add(profile)
            
            session.commit()
            session.refresh(user)
            return user
            
        except Exception as e:
            session.rollback()
            raise e

# === 使用示例 ===
def create_examples():
    """创建操作示例"""
    
    with get_session_context() as session:
        # 1. 创建单个用户
        user_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "first_name": "John",
            "last_name": "Doe"
        }
        user = UserCRUD.create_user(session, user_data)
        print(f"创建用户: {user.id} - {user.username}")
        
        # 2. 批量创建用户
        users_data = [
            {
                "username": "alice",
                "email": "alice@example.com",
                "first_name": "Alice",
                "last_name": "Smith"
            },
            {
                "username": "bob",
                "email": "bob@example.com",
                "first_name": "Bob",
                "last_name": "Johnson"
            }
        ]
        users = UserCRUD.create_users_batch(session, users_data)
        print(f"批量创建 {len(users)} 个用户")
        
        # 3. 创建带关联的对象
        user_data = {
            "username": "jane_doe",
            "email": "jane@example.com",
            "first_name": "Jane",
            "last_name": "Doe"
        }
        profile_data = {
            "bio": "Software Developer",
            "website": "https://jane.dev",
            "location": "San Francisco"
        }
        user_with_profile = UserCRUD.create_user_with_profile(
            session, user_data, profile_data
        )
        print(f"创建用户及档案: {user_with_profile.username}")
```

### 3.2 读取操作 (Read)

```python
# crud_read.py
from sqlmodel import Session, select, and_, or_, func
from typing import List, Optional, Dict, Any
from models import User, Product, Order
from datetime import datetime, timedelta

class UserCRUD:
    """用户读取操作"""
    
    @staticmethod
    def get_user_by_id(session: Session, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return session.get(User, user_id)
    
    @staticmethod
    def get_user_by_email(session: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        statement = select(User).where(User.email == email)
        return session.exec(statement).first()
    
    @staticmethod
    def get_users_by_status(session: Session, is_active: bool = True) -> List[User]:
        """根据状态获取用户列表"""
        statement = select(User).where(User.is_active == is_active)
        return session.exec(statement).all()
    
    @staticmethod
    def get_users_paginated(
        session: Session, 
        page: int = 1, 
        page_size: int = 10
    ) -> Dict[str, Any]:
        """分页获取用户"""
        offset = (page - 1) * page_size
        
        # 获取总数
        count_statement = select(func.count(User.id))
        total = session.exec(count_statement).one()
        
        # 获取分页数据
        statement = (
            select(User)
            .offset(offset)
            .limit(page_size)
            .order_by(User.created_at.desc())
        )
        users = session.exec(statement).all()
        
        return {
            "users": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    
    @staticmethod
    def search_users(
        session: Session, 
        keyword: str, 
        filters: Optional[Dict] = None
    ) -> List[User]:
        """搜索用户"""
        statement = select(User)
        
        # 关键词搜索
        if keyword:
            keyword_filter = or_(
                User.username.contains(keyword),
                User.first_name.contains(keyword),
                User.last_name.contains(keyword),
                User.email.contains(keyword)
            )
            statement = statement.where(keyword_filter)
        
        # 附加过滤条件
        if filters:
            if 'is_active' in filters:
                statement = statement.where(User.is_active == filters['is_active'])
            
            if 'created_after' in filters:
                statement = statement.where(User.created_at >= filters['created_after'])
            
            if 'created_before' in filters:
                statement = statement.where(User.created_at <= filters['created_before'])
        
        return session.exec(statement).all()
    
    @staticmethod
    def get_users_with_relationships(session: Session) -> List[User]:
        """获取用户及其关联数据"""
        from sqlmodel import Relationship
        
        # 使用 joinedload 预加载关联数据
        statement = (
            select(User)
            .options(
                # 预加载用户档案
                # selectinload(User.profile),
                # 预加载用户订单
                # selectinload(User.orders)
            )
        )
        return session.exec(statement).all()
    
    @staticmethod
    def get_user_statistics(session: Session) -> Dict[str, Any]:
        """获取用户统计信息"""
        # 总用户数
        total_users = session.exec(select(func.count(User.id))).one()
        
        # 活跃用户数
        active_users = session.exec(
            select(func.count(User.id)).where(User.is_active == True)
        ).one()
        
        # 今日注册用户数
        today = datetime.now().date()
        today_users = session.exec(
            select(func.count(User.id)).where(
                func.date(User.created_at) == today
            )
        ).one()
        
        # 最近7天注册用户数
        week_ago = datetime.now() - timedelta(days=7)
        week_users = session.exec(
            select(func.count(User.id)).where(
                User.created_at >= week_ago
            )
        ).one()
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "today_registrations": today_users,
            "week_registrations": week_users
        }

# === 复杂查询示例 ===
class AdvancedQueries:
    """高级查询示例"""
    
    @staticmethod
    def get_top_customers(session: Session, limit: int = 10) -> List[Dict]:
        """获取消费最多的客户"""
        statement = (
            select(
                User.id,
                User.username,
                User.email,
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_amount).label('total_spent')
            )
            .join(Order, User.id == Order.customer_id)
            .group_by(User.id, User.username, User.email)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
        )
        
        results = session.exec(statement).all()
        return [
            {
                "user_id": result.id,
                "username": result.username,
                "email": result.email,
                "order_count": result.order_count,
                "total_spent": float(result.total_spent or 0)
            }
            for result in results
         ]
    
    @staticmethod
    def get_running_totals(session: Session) -> List[Dict[str, Any]]:
        """计算运行总计（累计值）"""
        statement = (
            select(
                Order.id,
                Order.order_number,
                Order.created_at,
                Order.total_amount,
                func.sum(Order.total_amount).over(
                    order_by=Order.created_at
                ).label('running_total'),
                func.avg(Order.total_amount).over(
                    order_by=Order.created_at
                    rows=(None, 0)  # 从开始到当前行
                ).label('running_average')
            )
            .order_by(Order.created_at)
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'order_id': result.id,
                'order_number': result.order_number,
                'created_at': result.created_at,
                'total_amount': float(result.total_amount),
                'running_total': float(result.running_total),
                'running_average': float(result.running_average)
            }
            for result in results
        ]
```

---

## 5. 事务处理

### 5.1 基础事务操作

```python
# transaction_management.py
from sqlmodel import Session
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Callable
from database import engine
from models import User, Order, OrderItem, Product
import logging

logger = logging.getLogger(__name__)

class TransactionManager:
    """事务管理器"""
    
    @staticmethod
    @contextmanager
    def transaction(session: Session):
        """事务上下文管理器"""
        try:
            yield session
            session.commit()
            logger.info("事务提交成功")
        except Exception as e:
            session.rollback()
            logger.error(f"事务回滚: {e}")
            raise
    
    @staticmethod
    def execute_in_transaction(
        operations: List[Callable[[Session], Any]],
        session: Optional[Session] = None
    ) -> List[Any]:
        """在事务中执行多个操作"""
        if session is None:
            with Session(engine) as session:
                return TransactionManager._execute_operations(session, operations)
        else:
            return TransactionManager._execute_operations(session, operations)
    
    @staticmethod
    def _execute_operations(
        session: Session, 
        operations: List[Callable[[Session], Any]]
    ) -> List[Any]:
        """执行操作列表"""
        results = []
        try:
            for operation in operations:
                result = operation(session)
                results.append(result)
            
            session.commit()
            logger.info(f"成功执行 {len(operations)} 个操作")
            return results
            
        except Exception as e:
            session.rollback()
            logger.error(f"事务执行失败: {e}")
            raise

class OrderTransactions:
    """订单相关事务操作"""
    
    @staticmethod
    def create_order_with_items(
        session: Session,
        customer_id: int,
        order_data: Dict[str, Any],
        items_data: List[Dict[str, Any]]
    ) -> Order:
        """创建订单及订单项（事务操作）"""
        try:
            # 1. 创建订单
            order = Order(
                customer_id=customer_id,
                **order_data
            )
            session.add(order)
            session.flush()  # 获取订单ID但不提交
            
            # 2. 创建订单项并检查库存
            total_amount = 0
            order_items = []
            
            for item_data in items_data:
                product_id = item_data['product_id']
                quantity = item_data['quantity']
                
                # 检查产品是否存在
                product = session.get(Product, product_id)
                if not product:
                    raise ValueError(f"产品 {product_id} 不存在")
                
                # 检查库存
                if product.stock_quantity < quantity:
                    raise ValueError(
                        f"产品 {product.name} 库存不足，"
                        f"需要 {quantity}，可用 {product.stock_quantity}"
                    )
                
                # 计算价格
                unit_price = item_data.get('unit_price', product.price)
                total_price = unit_price * quantity
                
                # 创建订单项
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    total_price=total_price
                )
                session.add(order_item)
                order_items.append(order_item)
                
                # 更新库存
                product.stock_quantity -= quantity
                session.add(product)
                
                total_amount += total_price
            
            # 3. 更新订单总金额
            order.total_amount = total_amount
            session.add(order)
            
            # 4. 提交事务
            session.commit()
            
            # 5. 刷新对象
            session.refresh(order)
            for item in order_items:
                session.refresh(item)
            
            logger.info(f"成功创建订单 {order.order_number}，包含 {len(order_items)} 个商品")
            return order
            
        except Exception as e:
            session.rollback()
            logger.error(f"创建订单失败: {e}")
            raise
    
    @staticmethod
    def cancel_order(session: Session, order_id: int) -> bool:
        """取消订单（恢复库存）"""
        try:
            # 获取订单
            order = session.get(Order, order_id)
            if not order:
                raise ValueError(f"订单 {order_id} 不存在")
            
            if order.status in ['cancelled', 'shipped', 'delivered']:
                raise ValueError(f"订单状态为 {order.status}，无法取消")
            
            # 获取订单项
            order_items = session.exec(
                select(OrderItem).where(OrderItem.order_id == order_id)
            ).all()
            
            # 恢复库存
            for item in order_items:
                product = session.get(Product, item.product_id)
                if product:
                    product.stock_quantity += item.quantity
                    session.add(product)
            
            # 更新订单状态
            order.status = 'cancelled'
            order.cancelled_at = datetime.utcnow()
            session.add(order)
            
            session.commit()
            
            logger.info(f"成功取消订单 {order.order_number}")
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"取消订单失败: {e}")
            return False
    
    @staticmethod
    def transfer_order(
        session: Session,
        order_id: int,
        new_customer_id: int
    ) -> bool:
        """转移订单到新客户"""
        try:
            # 检查订单
            order = session.get(Order, order_id)
            if not order:
                raise ValueError(f"订单 {order_id} 不存在")
            
            # 检查新客户
            new_customer = session.get(User, new_customer_id)
            if not new_customer:
                raise ValueError(f"客户 {new_customer_id} 不存在")
            
            # 记录原客户
            old_customer_id = order.customer_id
            
            # 转移订单
            order.customer_id = new_customer_id
            order.updated_at = datetime.utcnow()
            session.add(order)
            
            session.commit()
            
            logger.info(
                f"成功将订单 {order.order_number} "
                f"从客户 {old_customer_id} 转移到客户 {new_customer_id}"
            )
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"转移订单失败: {e}")
            return False

### 5.2 嵌套事务和保存点

```python
# nested_transactions.py
from sqlmodel import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from database import engine
import logging

logger = logging.getLogger(__name__)

class SavepointManager:
    """保存点管理器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.savepoints = []
    
    def create_savepoint(self, name: str) -> str:
        """创建保存点"""
        savepoint_name = f"sp_{name}_{len(self.savepoints)}"
        self.session.execute(text(f"SAVEPOINT {savepoint_name}"))
        self.savepoints.append(savepoint_name)
        logger.debug(f"创建保存点: {savepoint_name}")
        return savepoint_name
    
    def rollback_to_savepoint(self, savepoint_name: str):
        """回滚到保存点"""
        if savepoint_name not in self.savepoints:
            raise ValueError(f"保存点 {savepoint_name} 不存在")
        
        self.session.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
        
        # 移除该保存点之后的所有保存点
        index = self.savepoints.index(savepoint_name)
        self.savepoints = self.savepoints[:index + 1]
        
        logger.debug(f"回滚到保存点: {savepoint_name}")
    
    def release_savepoint(self, savepoint_name: str):
        """释放保存点"""
        if savepoint_name not in self.savepoints:
            raise ValueError(f"保存点 {savepoint_name} 不存在")
        
        self.session.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
        self.savepoints.remove(savepoint_name)
        
        logger.debug(f"释放保存点: {savepoint_name}")

class BatchProcessor:
    """批量处理器（使用保存点）"""
    
    @staticmethod
    def process_users_batch(
        session: Session,
        users_data: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """批量处理用户（使用保存点处理错误）"""
        savepoint_manager = SavepointManager(session)
        
        processed = 0
        errors = []
        
        try:
            for i in range(0, len(users_data), batch_size):
                batch = users_data[i:i + batch_size]
                batch_savepoint = savepoint_manager.create_savepoint(f"batch_{i}")
                
                try:
                    # 处理当前批次
                    for user_data in batch:
                        user = User(**user_data)
                        session.add(user)
                    
                    session.flush()  # 检查约束但不提交
                    processed += len(batch)
                    
                    logger.info(f"成功处理批次 {i//batch_size + 1}，{len(batch)} 个用户")
                    
                except Exception as e:
                    # 回滚到批次开始
                    savepoint_manager.rollback_to_savepoint(batch_savepoint)
                    
                    # 逐个处理以找出问题数据
                    for j, user_data in enumerate(batch):
                        user_savepoint = savepoint_manager.create_savepoint(f"user_{i}_{j}")
                        
                        try:
                            user = User(**user_data)
                            session.add(user)
                            session.flush()
                            processed += 1
                            
                        except Exception as user_error:
                            savepoint_manager.rollback_to_savepoint(user_savepoint)
                            errors.append({
                                'index': i + j,
                                'data': user_data,
                                'error': str(user_error)
                            })
                            logger.warning(f"用户 {i + j} 处理失败: {user_error}")
            
            # 提交所有成功的操作
            session.commit()
            
            return {
                'success': True,
                'processed': processed,
                'total': len(users_data),
                'errors': errors
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量处理失败: {e}")
            return {
                'success': False,
                'processed': 0,
                'total': len(users_data),
                'error': str(e)
            }

---

## 6. 批量操作

### 6.1 批量插入

```python
# bulk_operations.py
from sqlmodel import Session
from sqlalchemy import insert, update, delete
from typing import List, Dict, Any
from models import User, Product, Order
from database import engine
import logging

logger = logging.getLogger(__name__)

class BulkOperations:
    """批量操作类"""
    
    @staticmethod
    def bulk_insert_users(
        session: Session,
        users_data: List[Dict[str, Any]]
    ) -> int:
        """批量插入用户"""
        try:
            # 方式1：使用 SQLAlchemy Core 的 insert
            statement = insert(User).values(users_data)
            result = session.execute(statement)
            session.commit()
            
            logger.info(f"批量插入 {len(users_data)} 个用户")
            return len(users_data)
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量插入失败: {e}")
            return 0
    
    @staticmethod
    def bulk_insert_users_orm(
        session: Session,
        users_data: List[Dict[str, Any]]
    ) -> List[User]:
        """批量插入用户（ORM 方式）"""
        try:
            users = [User(**user_data) for user_data in users_data]
            session.add_all(users)
            session.commit()
            
            # 刷新所有对象以获取生成的ID
            for user in users:
                session.refresh(user)
            
            logger.info(f"批量插入 {len(users)} 个用户（ORM）")
            return users
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量插入失败: {e}")
            return []
    
    @staticmethod
    def bulk_insert_with_returning(
        session: Session,
        users_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """批量插入并返回生成的ID"""
        try:
            statement = (
                insert(User)
                .values(users_data)
                .returning(User.id, User.username, User.email)
            )
            
            result = session.execute(statement)
            session.commit()
            
            inserted_users = [
                {
                    'id': row.id,
                    'username': row.username,
                    'email': row.email
                }
                for row in result
            ]
            
            logger.info(f"批量插入 {len(inserted_users)} 个用户并返回ID")
            return inserted_users
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量插入失败: {e}")
            return []

### 6.2 批量更新

```python
class BulkUpdateOperations:
    """批量更新操作"""
    
    @staticmethod
    def bulk_update_users_status(
        session: Session,
        user_ids: List[int],
        is_active: bool
    ) -> int:
        """批量更新用户状态"""
        try:
            statement = (
                update(User)
                .where(User.id.in_(user_ids))
                .values(
                    is_active=is_active,
                    updated_at=datetime.utcnow()
                )
            )
            
            result = session.execute(statement)
            session.commit()
            
            logger.info(f"批量更新 {result.rowcount} 个用户状态")
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量更新失败: {e}")
            return 0
    
    @staticmethod
    def bulk_update_product_prices(
        session: Session,
        price_updates: List[Dict[str, Any]]
    ) -> int:
        """批量更新产品价格
        
        Args:
            price_updates: [{'id': 1, 'price': 99.99}, ...]
        """
        try:
            updated_count = 0
            
            for update_data in price_updates:
                statement = (
                    update(Product)
                    .where(Product.id == update_data['id'])
                    .values(
                        price=update_data['price'],
                        updated_at=datetime.utcnow()
                    )
                )
                
                result = session.execute(statement)
                updated_count += result.rowcount
            
            session.commit()
            
            logger.info(f"批量更新 {updated_count} 个产品价格")
            return updated_count
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量更新价格失败: {e}")
            return 0
    
    @staticmethod
    def conditional_bulk_update(
        session: Session,
        conditions: Dict[str, Any],
        updates: Dict[str, Any]
    ) -> int:
        """条件批量更新"""
        try:
            statement = update(User)
            
            # 添加条件
            for field, value in conditions.items():
                if hasattr(User, field):
                    statement = statement.where(getattr(User, field) == value)
            
            # 添加更新时间戳
            updates['updated_at'] = datetime.utcnow()
            
            statement = statement.values(**updates)
            result = session.execute(statement)
            session.commit()
            
            logger.info(f"条件批量更新 {result.rowcount} 条记录")
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"条件批量更新失败: {e}")
            return 0

### 6.3 批量删除

```python
class BulkDeleteOperations:
    """批量删除操作"""
    
    @staticmethod
    def bulk_delete_users(
        session: Session,
        user_ids: List[int]
    ) -> int:
        """批量删除用户"""
        try:
            statement = delete(User).where(User.id.in_(user_ids))
            result = session.execute(statement)
            session.commit()
            
            logger.info(f"批量删除 {result.rowcount} 个用户")
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量删除失败: {e}")
            return 0
    
    @staticmethod
    def bulk_soft_delete(
        session: Session,
        user_ids: List[int]
    ) -> int:
        """批量软删除"""
        try:
            statement = (
                update(User)
                .where(User.id.in_(user_ids))
                .values(
                    is_active=False,
                    deleted_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            )
            
            result = session.execute(statement)
            session.commit()
            
            logger.info(f"批量软删除 {result.rowcount} 个用户")
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            logger.error(f"批量软删除失败: {e}")
            return 0
    
    @staticmethod
    def cleanup_old_records(
        session: Session,
        days: int = 30
    ) -> Dict[str, int]:
        """清理旧记录"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            # 删除旧的已取消订单
            cancelled_orders = session.execute(
                delete(Order).where(
                    and_(
                        Order.status == 'cancelled',
                        Order.cancelled_at < cutoff_date
                    )
                )
            ).rowcount
            
            # 删除未激活的旧用户
            inactive_users = session.execute(
                delete(User).where(
                    and_(
                        User.is_active == False,
                        User.created_at < cutoff_date
                    )
                )
            ).rowcount
            
            session.commit()
            
            result = {
                'cancelled_orders': cancelled_orders,
                'inactive_users': inactive_users
            }
            
            logger.info(f"清理完成: {result}")
            return result
            
        except Exception as e:
            session.rollback()
            logger.error(f"清理失败: {e}")
            return {'cancelled_orders': 0, 'inactive_users': 0}

# === 使用示例 ===
def bulk_operations_examples():
    """批量操作示例"""
    
    with Session(engine) as session:
        # 1. 批量插入
        users_data = [
            {
                'username': f'user_{i}',
                'email': f'user_{i}@example.com',
                'first_name': f'User{i}',
                'last_name': 'Test'
            }
            for i in range(1000, 1100)
        ]
        
        inserted_count = BulkOperations.bulk_insert_users(session, users_data)
        print(f"批量插入: {inserted_count} 个用户")
        
        # 2. 批量更新
        user_ids = list(range(1000, 1050))
        updated_count = BulkUpdateOperations.bulk_update_users_status(
            session, user_ids, is_active=False
        )
        print(f"批量更新: {updated_count} 个用户")
        
        # 3. 批量删除
        deleted_count = BulkDeleteOperations.bulk_delete_users(
            session, user_ids
        )
        print(f"批量删除: {deleted_count} 个用户")
        
        # 4. 清理旧记录
        cleanup_result = BulkDeleteOperations.cleanup_old_records(session, days=90)
        print(f"清理结果: {cleanup_result}")
```

---

## 7. 性能优化

### 7.1 查询优化

```python
# query_optimization.py
from sqlmodel import Session, select, func
from sqlalchemy import text
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Dict, Any
from models import User, Order, OrderItem, Product
import time

class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def measure_query_time(func):
        """查询时间测量装饰器"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            
            execution_time = end_time - start_time
            print(f"{func.__name__} 执行时间: {execution_time:.4f} 秒")
            
            return result
        return wrapper
    
    @staticmethod
    @measure_query_time
    def get_users_with_orders_naive(session: Session) -> List[User]:
        """获取用户及订单（N+1 查询问题）"""
        users = session.exec(select(User)).all()
        
        for user in users:
            # 这会为每个用户执行一次查询（N+1 问题）
            user.orders = session.exec(
                select(Order).where(Order.customer_id == user.id)
            ).all()
        
        return users
    
    @staticmethod
    @measure_query_time
    def get_users_with_orders_optimized(session: Session) -> List[User]:
        """获取用户及订单（优化版本）"""
        # 使用 joinedload 预加载关联数据
        statement = (
            select(User)
            .options(joinedload(User.orders))
        )
        
        return session.exec(statement).unique().all()
    
    @staticmethod
    @measure_query_time
    def get_users_with_orders_selectin(session: Session) -> List[User]:
        """使用 selectinload 预加载"""
        statement = (
            select(User)
            .options(selectinload(User.orders))
        )
        
        return session.exec(statement).all()
    
    @staticmethod
    def analyze_query_plan(session: Session, statement):
        """分析查询执行计划"""
        # PostgreSQL
        if 'postgresql' in str(session.bind.url):
            explain_query = text(f"EXPLAIN ANALYZE {statement}")
            result = session.execute(explain_query)
            
            print("查询执行计划:")
            for row in result:
                print(row[0])
        
        # SQLite
        elif 'sqlite' in str(session.bind.url):
            explain_query = text(f"EXPLAIN QUERY PLAN {statement}")
            result = session.execute(explain_query)
            
            print("查询执行计划:")
            for row in result:
                print(f"{row.id}|{row.parent}|{row.notused}|{row.detail}")

### 7.2 索引优化

```python
# index_optimization.py
from sqlmodel import SQLModel, Field, create_engine
from sqlalchemy import Index, text
from typing import Optional
from datetime import datetime

# 优化的用户模型（添加索引）
class OptimizedUser(SQLModel, table=True):
    __tablename__ = "optimized_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)  # 单列索引
    email: str = Field(index=True, unique=True)     # 单列索引
    first_name: str
    last_name: str
    is_active: bool = Field(default=True, index=True)  # 状态索引
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: Optional[datetime] = None
    
    # 复合索引
    __table_args__ = (
        Index('idx_user_name_active', 'first_name', 'last_name', 'is_active'),
        Index('idx_user_created_active', 'created_at', 'is_active'),
        Index('idx_user_email_active', 'email', 'is_active'),
    )

class IndexManager:
    """索引管理器"""
    
    @staticmethod
    def create_custom_indexes(session: Session):
        """创建自定义索引"""
        indexes = [
            # 用户表索引
            "CREATE INDEX IF NOT EXISTS idx_users_username_lower ON users (LOWER(username))",
            "CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (LOWER(email))",
            "CREATE INDEX IF NOT EXISTS idx_users_full_name ON users (first_name, last_name)",
            
            # 订单表索引
            "CREATE INDEX IF NOT EXISTS idx_orders_customer_status ON orders (customer_id, status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_created_status ON orders (created_at, status)",
            "CREATE INDEX IF NOT EXISTS idx_orders_total_amount ON orders (total_amount)",
            
            # 订单项表索引
            "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items (product_id)",
            "CREATE INDEX IF NOT EXISTS idx_order_items_order_product ON order_items (order_id, product_id)",
            
            # 产品表索引
            "CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku)",
            "CREATE INDEX IF NOT EXISTS idx_products_category_price ON products (category_id, price)",
            "CREATE INDEX IF NOT EXISTS idx_products_stock ON products (stock_quantity)",
        ]
        
        for index_sql in indexes:
            try:
                session.execute(text(index_sql))
                print(f"创建索引: {index_sql.split()[5]}")
            except Exception as e:
                print(f"创建索引失败: {e}")
        
        session.commit()
    
    @staticmethod
    def analyze_index_usage(session: Session):
        """分析索引使用情况（PostgreSQL）"""
        if 'postgresql' not in str(session.bind.url):
            print("索引分析仅支持 PostgreSQL")
            return
        
        # 查询索引使用统计
        query = text("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan as index_scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes 
        ORDER BY idx_scan DESC
        """)
        
        result = session.execute(query)
        
        print("索引使用统计:")
        print(f"{'表名':<20} {'索引名':<30} {'扫描次数':<10} {'读取元组':<10} {'获取元组':<10}")
        print("-" * 80)
        
        for row in result:
            print(
                f"{row.tablename:<20} {row.indexname:<30} "
                f"{row.index_scans:<10} {row.tuples_read:<10} {row.tuples_fetched:<10}"
            )
    
    @staticmethod
    def find_unused_indexes(session: Session):
        """查找未使用的索引（PostgreSQL）"""
        if 'postgresql' not in str(session.bind.url):
            print("未使用索引分析仅支持 PostgreSQL")
            return
        
        query = text("""
        SELECT 
            schemaname,
            tablename,
            indexname,
            pg_size_pretty(pg_relation_size(indexrelid)) as index_size
        FROM pg_stat_user_indexes 
        WHERE idx_scan = 0
        AND indexname NOT LIKE '%_pkey'
        ORDER BY pg_relation_size(indexrelid) DESC
        """)
        
        result = session.execute(query)
        
        print("未使用的索引:")
        print(f"{'表名':<20} {'索引名':<30} {'大小':<10}")
        print("-" * 60)
        
        for row in result:
            print(f"{row.tablename:<20} {row.indexname:<30} {row.index_size:<10}")

### 7.3 连接池优化

```python
# connection_pool_optimization.py
from sqlmodel import create_engine
from sqlalchemy.pool import QueuePool, StaticPool, NullPool
from sqlalchemy import event
import logging
import time

logger = logging.getLogger(__name__)

class ConnectionPoolManager:
    """连接池管理器"""
    
    @staticmethod
    def create_optimized_engine(database_url: str, **kwargs):
        """创建优化的数据库引擎"""
        
        # 默认连接池配置
        pool_config = {
            'poolclass': QueuePool,
            'pool_size': 10,          # 连接池大小
            'max_overflow': 20,       # 最大溢出连接数
            'pool_timeout': 30,       # 获取连接超时时间
            'pool_recycle': 3600,     # 连接回收时间（秒）
            'pool_pre_ping': True,    # 连接前检查
        }
        
        # 合并用户配置
        pool_config.update(kwargs)
        
        engine = create_engine(database_url, **pool_config)
        
        # 添加连接池事件监听
        ConnectionPoolManager._setup_pool_events(engine)
        
        return engine
    
    @staticmethod
    def _setup_pool_events(engine):
        """设置连接池事件监听"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """SQLite 连接优化"""
            if 'sqlite' in str(engine.url):
                cursor = dbapi_connection.cursor()
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys=ON")
                # 设置 WAL 模式
                cursor.execute("PRAGMA journal_mode=WAL")
                # 设置同步模式
                cursor.execute("PRAGMA synchronous=NORMAL")
                # 设置缓存大小
                cursor.execute("PRAGMA cache_size=10000")
                cursor.close()
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出事件"""
            connection_record.info['checkout_time'] = time.time()
            logger.debug("连接已检出")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接检入事件"""
            if 'checkout_time' in connection_record.info:
                checkout_time = connection_record.info['checkout_time']
                usage_time = time.time() - checkout_time
                logger.debug(f"连接使用时间: {usage_time:.2f} 秒")
                del connection_record.info['checkout_time']
    
    @staticmethod
    def get_pool_status(engine):
        """获取连接池状态"""
        pool = engine.pool
        
        return {
            'pool_size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'invalid': pool.invalid()
        }
    
    @staticmethod
    def monitor_pool_performance(engine, duration: int = 60):
        """监控连接池性能"""
        start_time = time.time()
        
        while time.time() - start_time < duration:
            status = ConnectionPoolManager.get_pool_status(engine)
            logger.info(f"连接池状态: {status}")
            time.sleep(10)

# === 使用示例 ===
def performance_optimization_examples():
    """性能优化示例"""
    
    # 1. 创建优化的引擎
    optimized_engine = ConnectionPoolManager.create_optimized_engine(
        "postgresql://user:password@localhost/mydb",
        pool_size=15,
        max_overflow=25
    )
    
    with Session(optimized_engine) as session:
        # 2. 查询优化比较
        print("=== 查询优化比较 ===")
        
        # N+1 查询问题
        QueryOptimizer.get_users_with_orders_naive(session)
        
        # 优化后的查询
        QueryOptimizer.get_users_with_orders_optimized(session)
        
        # 3. 创建索引
        print("\n=== 创建索引 ===")
        IndexManager.create_custom_indexes(session)
        
        # 4. 分析索引使用
        print("\n=== 索引使用分析 ===")
        IndexManager.analyze_index_usage(session)
        
        # 5. 连接池状态
        print("\n=== 连接池状态 ===")
        pool_status = ConnectionPoolManager.get_pool_status(optimized_engine)
        print(f"连接池状态: {pool_status}")
```

---

## 8. 常见问题与解决方案

### 8.1 连接问题

```python
# connection_troubleshooting.py
from sqlmodel import Session, create_engine
from sqlalchemy.exc import OperationalError, TimeoutError
from typing import Optional
import time
import logging

logger = logging.getLogger(__name__)

class ConnectionTroubleshooter:
    """连接问题排查器"""
    
    @staticmethod
    def test_connection(database_url: str) -> bool:
        """测试数据库连接"""
        try:
            engine = create_engine(database_url)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
            
        except OperationalError as e:
            logger.error(f"数据库连接失败: {e}")
            return False
        except Exception as e:
            logger.error(f"连接测试异常: {e}")
            return False
    
    @staticmethod
    def retry_connection(
        database_url: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[Session]:
        """重试连接"""
        for attempt in range(max_retries):
            try:
                engine = create_engine(database_url)
                session = Session(engine)
                
                # 测试连接
                session.execute(text("SELECT 1"))
                
                logger.info(f"连接成功（第 {attempt + 1} 次尝试）")
                return session
                
            except Exception as e:
                logger.warning(f"连接失败（第 {attempt + 1} 次尝试）: {e}")
                
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避
        
        logger.error(f"连接失败，已重试 {max_retries} 次")
        return None
    
    @staticmethod
    def diagnose_connection_issues(database_url: str) -> Dict[str, Any]:
        """诊断连接问题"""
        diagnosis = {
            'url_valid': False,
            'host_reachable': False,
            'credentials_valid': False,
            'database_exists': False,
            'recommendations': []
        }
        
        try:
            # 1. 检查 URL 格式
            from sqlalchemy.engine.url import make_url
            url = make_url(database_url)
            diagnosis['url_valid'] = True
            
            # 2. 检查主机可达性（简化版）
            if url.host:
                import socket
                try:
                    socket.create_connection((url.host, url.port or 5432), timeout=5)
                    diagnosis['host_reachable'] = True
                except:
                    diagnosis['recommendations'].append("检查数据库服务器是否运行")
            
            # 3. 尝试连接
            engine = create_engine(database_url)
            with engine.connect():
                diagnosis['credentials_valid'] = True
                diagnosis['database_exists'] = True
                
        except Exception as e:
            error_msg = str(e).lower()
            
            if 'authentication failed' in error_msg:
                diagnosis['recommendations'].append("检查用户名和密码")
            elif 'database' in error_msg and 'does not exist' in error_msg:
                diagnosis['recommendations'].append("检查数据库名称是否正确")
            elif 'connection refused' in error_msg:
                diagnosis['recommendations'].append("检查数据库服务是否启动")
            elif 'timeout' in error_msg:
                diagnosis['recommendations'].append("检查网络连接和防火墙设置")
            else:
                diagnosis['recommendations'].append(f"未知错误: {e}")
        
        return diagnosis

### 8.2 性能问题

```python
# performance_troubleshooting.py
from sqlmodel import Session, select
from sqlalchemy import text, event
from typing import List, Dict, Any
import time
import psutil
import logging

logger = logging.getLogger(__name__)

class PerformanceTroubleshooter:
    """性能问题排查器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.slow_queries = []
        self.query_stats = {}
        
        # 设置慢查询监听
        self._setup_slow_query_logging()
    
    def _setup_slow_query_logging(self, threshold: float = 1.0):
        """设置慢查询日志"""
        
        @event.listens_for(self.session.bind, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
        
        @event.listens_for(self.session.bind, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - context._query_start_time
            
            if total > threshold:
                self.slow_queries.append({
                    'sql': statement,
                    'duration': total,
                    'timestamp': time.time()
                })
                logger.warning(f"慢查询检测: {total:.4f}s - {statement[:100]}...")
    
    def analyze_query_performance(self, statement) -> Dict[str, Any]:
        """分析查询性能"""
        start_time = time.time()
        
        # 执行查询
        result = self.session.execute(statement)
        execution_time = time.time() - start_time
        
        # 获取执行计划
        explain_result = None
        try:
            if 'postgresql' in str(self.session.bind.url):
                explain_stmt = text(f"EXPLAIN (ANALYZE, BUFFERS) {statement}")
                explain_result = self.session.execute(explain_stmt).fetchall()
        except Exception as e:
            logger.warning(f"无法获取执行计划: {e}")
        
        return {
            'execution_time': execution_time,
            'row_count': result.rowcount if hasattr(result, 'rowcount') else 0,
            'explain_plan': explain_result,
            'recommendations': self._get_performance_recommendations(execution_time)
        }
    
    def _get_performance_recommendations(self, execution_time: float) -> List[str]:
        """获取性能优化建议"""
        recommendations = []
        
        if execution_time > 5.0:
            recommendations.append("查询执行时间过长，考虑添加索引")
        if execution_time > 2.0:
            recommendations.append("考虑使用查询缓存")
        if execution_time > 1.0:
            recommendations.append("检查是否存在 N+1 查询问题")
        
        return recommendations
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        return {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'active_connections': len(psutil.net_connections())
        }
    
    def generate_performance_report(self) -> Dict[str, Any]:
        """生成性能报告"""
        return {
            'slow_queries_count': len(self.slow_queries),
            'slow_queries': self.slow_queries[-10:],  # 最近10个慢查询
            'system_metrics': self.get_system_metrics(),
            'recommendations': self._generate_general_recommendations()
        }
    
    def _generate_general_recommendations(self) -> List[str]:
        """生成通用优化建议"""
        recommendations = []
        
        if len(self.slow_queries) > 10:
            recommendations.append("检测到多个慢查询，建议优化数据库索引")
        
        metrics = self.get_system_metrics()
        if metrics['cpu_percent'] > 80:
            recommendations.append("CPU 使用率过高，考虑优化查询或增加服务器资源")
        if metrics['memory_percent'] > 80:
            recommendations.append("内存使用率过高，考虑调整连接池大小")
        
        return recommendations

### 8.3 数据一致性问题

```python
# data_consistency_troubleshooting.py
from sqlmodel import Session, select, func
from sqlalchemy import text
from typing import List, Dict, Any
from models import User, Order, OrderItem, Product
import logging

logger = logging.getLogger(__name__)

class DataConsistencyChecker:
    """数据一致性检查器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.issues = []
    
    def check_foreign_key_constraints(self) -> List[Dict[str, Any]]:
        """检查外键约束"""
        issues = []
        
        # 检查订单中的无效客户ID
        invalid_customers = self.session.exec(
            select(Order.id, Order.customer_id)
            .outerjoin(User, Order.customer_id == User.id)
            .where(User.id.is_(None))
        ).all()
        
        if invalid_customers:
            issues.append({
                'type': 'foreign_key_violation',
                'table': 'orders',
                'description': f'发现 {len(invalid_customers)} 个订单引用了不存在的客户',
                'affected_records': [{'order_id': r.id, 'customer_id': r.customer_id} for r in invalid_customers]
            })
        
        # 检查订单项中的无效产品ID
        invalid_products = self.session.exec(
            select(OrderItem.id, OrderItem.product_id)
            .outerjoin(Product, OrderItem.product_id == Product.id)
            .where(Product.id.is_(None))
        ).all()
        
        if invalid_products:
            issues.append({
                'type': 'foreign_key_violation',
                'table': 'order_items',
                'description': f'发现 {len(invalid_products)} 个订单项引用了不存在的产品',
                'affected_records': [{'item_id': r.id, 'product_id': r.product_id} for r in invalid_products]
            })
        
        return issues
    
    def check_data_integrity(self) -> List[Dict[str, Any]]:
        """检查数据完整性"""
        issues = []
        
        # 检查订单总金额是否正确
        incorrect_totals = self.session.exec(
            text("""
            SELECT o.id, o.total_amount, 
                   COALESCE(SUM(oi.total_price), 0) as calculated_total
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            GROUP BY o.id, o.total_amount
            HAVING ABS(o.total_amount - COALESCE(SUM(oi.total_price), 0)) > 0.01
            """)
        ).all()
        
        if incorrect_totals:
            issues.append({
                'type': 'data_integrity_violation',
                'table': 'orders',
                'description': f'发现 {len(incorrect_totals)} 个订单的总金额不正确',
                'affected_records': [
                    {
                        'order_id': r.id,
                        'stored_total': float(r.total_amount),
                        'calculated_total': float(r.calculated_total)
                    }
                    for r in incorrect_totals
                ]
            })
        
        # 检查负库存
        negative_stock = self.session.exec(
            select(Product.id, Product.name, Product.stock_quantity)
            .where(Product.stock_quantity < 0)
        ).all()
        
        if negative_stock:
            issues.append({
                'type': 'business_rule_violation',
                'table': 'products',
                'description': f'发现 {len(negative_stock)} 个产品库存为负数',
                'affected_records': [
                    {
                        'product_id': r.id,
                        'product_name': r.name,
                        'stock_quantity': r.stock_quantity
                    }
                    for r in negative_stock
                ]
            })
        
        return issues
    
    def check_duplicate_data(self) -> List[Dict[str, Any]]:
        """检查重复数据"""
        issues = []
        
        # 检查重复的用户邮箱
        duplicate_emails = self.session.exec(
            select(User.email, func.count(User.id).label('count'))
            .group_by(User.email)
            .having(func.count(User.id) > 1)
        ).all()
        
        if duplicate_emails:
            issues.append({
                'type': 'duplicate_data',
                'table': 'users',
                'description': f'发现 {len(duplicate_emails)} 个重复的邮箱地址',
                'affected_records': [
                    {'email': r.email, 'count': r.count}
                    for r in duplicate_emails
                ]
            })
        
        return issues
    
    def run_full_check(self) -> Dict[str, Any]:
        """运行完整的数据一致性检查"""
        all_issues = []
        
        # 运行各种检查
        all_issues.extend(self.check_foreign_key_constraints())
        all_issues.extend(self.check_data_integrity())
        all_issues.extend(self.check_duplicate_data())
        
        return {
            'total_issues': len(all_issues),
            'issues_by_type': self._group_issues_by_type(all_issues),
            'all_issues': all_issues,
            'recommendations': self._generate_fix_recommendations(all_issues)
        }
    
    def _group_issues_by_type(self, issues: List[Dict[str, Any]]) -> Dict[str, int]:
        """按类型分组问题"""
        grouped = {}
        for issue in issues:
            issue_type = issue['type']
            grouped[issue_type] = grouped.get(issue_type, 0) + 1
        return grouped
    
    def _generate_fix_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """生成修复建议"""
        recommendations = []
        
        for issue in issues:
            if issue['type'] == 'foreign_key_violation':
                recommendations.append(f"修复 {issue['table']} 表中的外键约束违规")
            elif issue['type'] == 'data_integrity_violation':
                recommendations.append(f"重新计算 {issue['table']} 表中的数据")
            elif issue['type'] == 'business_rule_violation':
                recommendations.append(f"修复 {issue['table']} 表中的业务规则违规")
            elif issue['type'] == 'duplicate_data':
                recommendations.append(f"清理 {issue['table']} 表中的重复数据")
        
        return list(set(recommendations))  # 去重
```

---

## 9. 最佳实践

### 9.1 代码组织

```python
# best_practices_example.py
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from models import User, Order, Product
from database import engine
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    """用户仓储模式示例"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        user = User(**user_data)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        return self.session.get(User, user_id)
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        return self.session.exec(
            select(User).where(User.email == email)
        ).first()
    
    def get_active_users(self, limit: int = 100) -> List[User]:
        """获取活跃用户"""
        return self.session.exec(
            select(User)
            .where(User.is_active == True)
            .limit(limit)
        ).all()
    
    def update(self, user_id: int, updates: Dict[str, Any]) -> Optional[User]:
        """更新用户"""
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        for field, value in updates.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """删除用户"""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        self.session.delete(user)
        self.session.commit()
        return True

class UserService:
    """用户服务层"""
    
    def __init__(self, session: Session):
        self.user_repo = UserRepository(session)
        self.session = session
    
    @contextmanager
    def transaction(self):
        """事务上下文管理器"""
        try:
            yield
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
    
    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """用户注册（业务逻辑）"""
        try:
            # 检查邮箱是否已存在
            existing_user = self.user_repo.get_by_email(user_data['email'])
            if existing_user:
                return {
                    'success': False,
                    'error': '邮箱已被注册'
                }
            
            # 创建用户
            with self.transaction():
                user = self.user_repo.create(user_data)
                
                # 可以在这里添加其他业务逻辑
                # 如发送欢迎邮件、创建用户配置等
                
                logger.info(f"用户注册成功: {user.email}")
                
                return {
                    'success': True,
                    'user_id': user.id,
                    'message': '注册成功'
                }
        
        except Exception as e:
            logger.error(f"用户注册失败: {e}")
            return {
                'success': False,
                'error': '注册失败，请稍后重试'
            }

### 9.2 错误处理

```python
# error_handling_best_practices.py
from sqlmodel import Session
from sqlalchemy.exc import (
    IntegrityError, 
    OperationalError, 
    TimeoutError,
    DataError
)
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseErrorHandler:
    """数据库错误处理器"""
    
    @staticmethod
    def handle_database_error(func):
        """数据库错误处理装饰器"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            
            except IntegrityError as e:
                logger.error(f"数据完整性错误: {e}")
                return {
                    'success': False,
                    'error_type': 'integrity_error',
                    'message': '数据完整性约束违规'
                }
            
            except OperationalError as e:
                logger.error(f"操作错误: {e}")
                return {
                    'success': False,
                    'error_type': 'operational_error',
                    'message': '数据库操作失败'
                }
            
            except TimeoutError as e:
                logger.error(f"超时错误: {e}")
                return {
                    'success': False,
                    'error_type': 'timeout_error',
                    'message': '操作超时'
                }
            
            except DataError as e:
                logger.error(f"数据错误: {e}")
                return {
                    'success': False,
                    'error_type': 'data_error',
                    'message': '数据格式错误'
                }
            
            except Exception as e:
                logger.error(f"未知错误: {e}")
                return {
                    'success': False,
                    'error_type': 'unknown_error',
                    'message': '操作失败'
                }
        
        return wrapper
    
    @staticmethod
    def safe_execute(session: Session, operation, *args, **kwargs) -> Dict[str, Any]:
        """安全执行数据库操作"""
        try:
            result = operation(session, *args, **kwargs)
            return {
                'success': True,
                'data': result
            }
        
        except Exception as e:
            session.rollback()
            logger.error(f"操作失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }

### 9.3 配置管理

```python
# configuration_best_practices.py
from pydantic import BaseSettings, Field
from typing import Optional
import os

class DatabaseConfig(BaseSettings):
    """数据库配置"""
    
    # 基础配置
    database_url: str = Field(..., env="DATABASE_URL")
    echo_sql: bool = Field(False, env="ECHO_SQL")
    
    # 连接池配置
    pool_size: int = Field(10, env="DB_POOL_SIZE")
    max_overflow: int = Field(20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(30, env="DB_POOL_TIMEOUT")
    pool_recycle: int = Field(3600, env="DB_POOL_RECYCLE")
    pool_pre_ping: bool = Field(True, env="DB_POOL_PRE_PING")
    
    # 查询配置
    query_timeout: int = Field(30, env="DB_QUERY_TIMEOUT")
    slow_query_threshold: float = Field(1.0, env="SLOW_QUERY_THRESHOLD")
    
    # 安全配置
    ssl_mode: Optional[str] = Field(None, env="DB_SSL_MODE")
    ssl_cert: Optional[str] = Field(None, env="DB_SSL_CERT")
    ssl_key: Optional[str] = Field(None, env="DB_SSL_KEY")
    ssl_ca: Optional[str] = Field(None, env="DB_SSL_CA")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

class AppConfig(BaseSettings):
    """应用配置"""
    
    # 应用基础配置
    app_name: str = Field("SQLModel App", env="APP_NAME")
    debug: bool = Field(False, env="DEBUG")
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    # 数据库配置
    database: DatabaseConfig = DatabaseConfig()
    
    # 缓存配置
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    cache_ttl: int = Field(300, env="CACHE_TTL")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# 使用配置
config = AppConfig()

# 创建引擎
from sqlmodel import create_engine

engine = create_engine(
    config.database.database_url,
    echo=config.database.echo_sql,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    pool_timeout=config.database.pool_timeout,
    pool_recycle=config.database.pool_recycle,
    pool_pre_ping=config.database.pool_pre_ping
)
```

---

## 10. 本章总结

### 10.1 核心概念回顾

本章详细介绍了 SQLModel 中的数据库操作，涵盖了以下核心内容：

1. **数据库连接与配置**
   - 引擎创建和配置
   - 会话管理最佳实践
   - 连接池优化

2. **基础 CRUD 操作**
   - 创建（Create）：单条和批量插入
   - 读取（Read）：简单查询和复杂查询
   - 更新（Update）：单条和批量更新
   - 删除（Delete）：硬删除和软删除

3. **高级查询技术**
   - 复杂条件查询和联表查询
   - 子查询和 CTE（公共表表达式）
   - 窗口函数和聚合查询
   - 查询优化技巧

4. **事务处理**
   - 基础事务操作
   - 嵌套事务和保存点
   - 事务隔离级别
   - 错误处理和回滚

5. **批量操作**
   - 高效的批量插入、更新、删除
   - 批量操作的性能优化
   - 错误处理和部分成功处理

6. **性能优化**
   - 查询性能分析和优化
   - 索引策略和管理
   - 连接池配置和监控
   - N+1 查询问题解决

### 10.2 最佳实践总结

1. **代码组织**
   - 使用仓储模式分离数据访问逻辑
   - 实现服务层处理业务逻辑
   - 采用依赖注入提高可测试性

2. **错误处理**
   - 实现统一的错误处理机制
   - 区分不同类型的数据库错误
   - 提供有意义的错误信息

3. **性能考虑**
   - 合理使用索引
   - 避免 N+1 查询问题
   - 使用连接池管理连接
   - 监控慢查询

4. **安全性**
   - 使用参数化查询防止 SQL 注入
   - 实现适当的访问控制
   - 敏感数据加密存储

### 10.3 常见陷阱与避免方法

1. **会话管理**
   - ❌ 忘记关闭会话导致连接泄漏
   - ✅ 使用上下文管理器自动管理会话

2. **事务处理**
   - ❌ 长时间持有事务导致锁等待
   - ✅ 保持事务简短，及时提交或回滚

3. **查询优化**
   - ❌ 在循环中执行查询（N+1 问题）
   - ✅ 使用预加载或批量查询

4. **错误处理**
   - ❌ 忽略数据库错误或处理不当
   - ✅ 实现完善的错误处理和日志记录

### 10.4 实践检查清单

完成本章学习后，你应该能够：

- [ ] 正确配置和管理数据库连接
- [ ] 实现完整的 CRUD 操作
- [ ] 编写复杂的查询语句
- [ ] 正确使用事务确保数据一致性
- [ ] 实现高效的批量操作
- [ ] 识别和解决性能问题
- [ ] 处理常见的数据库错误
- [ ] 应用最佳实践组织代码

### 10.5 下一步学习

在掌握了基础的数据库操作后，下一章我们将学习：

1. **关系和关联**
   - 一对一、一对多、多对多关系
   - 关系的定义和使用
   - 延迟加载和预加载

2. **数据验证和约束**
   - 字段验证规则
   - 自定义验证器
   - 数据库约束

3. **迁移和版本控制**
   - Alembic 集成
   - 数据库迁移策略
   - 版本管理最佳实践

### 10.6 扩展练习

为了巩固本章知识，建议完成以下练习：

1. **电商系统练习**
   - 实现完整的订单管理系统
   - 包含库存管理和事务处理
   - 添加性能监控和优化

2. **博客系统练习**
   - 实现文章、评论、标签管理
   - 包含复杂查询和搜索功能
   - 实现数据一致性检查

3. **性能测试练习**
   - 创建大量测试数据
   - 对比不同查询方式的性能
   - 实现查询缓存机制

通过这些练习，你将能够在实际项目中熟练运用 SQLModel 进行数据库操作。
    
    @staticmethod
    def get_users_by_order_date_range(
        session: Session, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[User]:
        """获取指定时间范围内有订单的用户"""
        statement = (
            select(User)
            .join(Order, User.id == Order.customer_id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .distinct()
        )
        return session.exec(statement).all()
    
    @staticmethod
    def get_users_without_orders(session: Session) -> List[User]:
        """获取没有订单的用户"""
        # 使用左连接和 NULL 检查
        statement = (
            select(User)
            .outerjoin(Order, User.id == Order.customer_id)
            .where(Order.id.is_(None))
        )
        return session.exec(statement).all()

# === 使用示例 ===
def read_examples():
    """读取操作示例"""
    
    with get_session_context() as session:
        # 1. 基础查询
        user = UserCRUD.get_user_by_id(session, 1)
        if user:
            print(f"用户: {user.username}")
        
        # 2. 条件查询
        active_users = UserCRUD.get_users_by_status(session, is_active=True)
        print(f"活跃用户数: {len(active_users)}")
        
        # 3. 分页查询
        page_result = UserCRUD.get_users_paginated(session, page=1, page_size=5)
        print(f"第1页用户: {len(page_result['users'])} / {page_result['total']}")
        
        # 4. 搜索查询
        search_results = UserCRUD.search_users(
            session, 
            keyword="john",
            filters={'is_active': True}
        )
        print(f"搜索结果: {len(search_results)} 个用户")
        
        # 5. 统计查询
        stats = UserCRUD.get_user_statistics(session)
        print(f"用户统计: {stats}")
        
        # 6. 高级查询
        top_customers = AdvancedQueries.get_top_customers(session, limit=5)
        print(f"前5名客户: {len(top_customers)}")
```

### 3.3 更新操作 (Update)

```python
# crud_update.py
from sqlmodel import Session, select, update
from typing import List, Optional, Dict, Any
from models import User, Product
from datetime import datetime

class UserCRUD:
    """用户更新操作"""
    
    @staticmethod
    def update_user_by_id(
        session: Session, 
        user_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[User]:
        """根据ID更新用户"""
        user = session.get(User, user_id)
        if not user:
            return None
        
        # 更新字段
        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)
        
        # 更新时间戳
        user.updated_at = datetime.utcnow()
        
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    
    @staticmethod
    def update_user_safe(
        session: Session, 
        user_id: int, 
        update_data: Dict[str, Any]
    ) -> Optional[User]:
        """安全更新用户（验证数据）"""
        try:
            user = session.get(User, user_id)
            if not user:
                raise ValueError(f"用户 {user_id} 不存在")
            
            # 验证邮箱唯一性
            if 'email' in update_data:
                existing_user = session.exec(
                    select(User).where(
                        and_(
                            User.email == update_data['email'],
                            User.id != user_id
                        )
                    )
                ).first()
                
                if existing_user:
                    raise ValueError(f"邮箱 {update_data['email']} 已被使用")
            
            # 验证用户名唯一性
            if 'username' in update_data:
                existing_user = session.exec(
                    select(User).where(
                        and_(
                            User.username == update_data['username'],
                            User.id != user_id
                        )
                    )
                ).first()
                
                if existing_user:
                    raise ValueError(f"用户名 {update_data['username']} 已被使用")
            
            # 执行更新
            for field, value in update_data.items():
                if hasattr(user, field):
                    setattr(user, field, value)
            
            user.updated_at = datetime.utcnow()
            
            session.add(user)
            session.commit()
            session.refresh(user)
            return user
            
        except Exception as e:
            session.rollback()
            print(f"更新用户失败: {e}")
            return None
    
    @staticmethod
    def update_users_batch(
        session: Session, 
        updates: List[Dict[str, Any]]
    ) -> List[User]:
        """批量更新用户
        
        Args:
            updates: [{'id': 1, 'data': {'first_name': 'New Name'}}, ...]
        """
        updated_users = []
        
        try:
            for update_item in updates:
                user_id = update_item['id']
                update_data = update_item['data']
                
                user = session.get(User, user_id)
                if user:
                    for field, value in update_data.items():
                        if hasattr(user, field):
                            setattr(user, field, value)
                    
                    user.updated_at = datetime.utcnow()
                    session.add(user)
                    updated_users.append(user)
            
            session.commit()
            
            # 刷新所有更新的用户
            for user in updated_users:
                session.refresh(user)
            
            return updated_users
            
        except Exception as e:
            session.rollback()
            print(f"批量更新失败: {e}")
            return []
    
    @staticmethod
    def bulk_update_users(
        session: Session, 
        filter_conditions: Dict[str, Any],
        update_data: Dict[str, Any]
    ) -> int:
        """批量更新（使用 SQL UPDATE 语句）"""
        try:
            # 构建更新语句
            statement = update(User)
            
            # 添加过滤条件
            for field, value in filter_conditions.items():
                if hasattr(User, field):
                    statement = statement.where(getattr(User, field) == value)
            
            # 添加更新时间戳
            update_data['updated_at'] = datetime.utcnow()
            
            # 执行更新
            statement = statement.values(**update_data)
            result = session.exec(statement)
            session.commit()
            
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            print(f"批量更新失败: {e}")
            return 0
    
    @staticmethod
    def activate_users(session: Session, user_ids: List[int]) -> int:
        """批量激活用户"""
        return UserCRUD.bulk_update_users(
            session,
            filter_conditions={'id': user_ids},  # 这里需要使用 IN 操作
            update_data={'is_active': True}
        )
    
    @staticmethod
    def deactivate_users(session: Session, user_ids: List[int]) -> int:
        """批量停用用户"""
        try:
            statement = (
                update(User)
                .where(User.id.in_(user_ids))
                .values(
                    is_active=False,
                    updated_at=datetime.utcnow()
                )
            )
            result = session.exec(statement)
            session.commit()
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            print(f"批量停用失败: {e}")
            return 0
    
    @staticmethod
    def update_user_last_login(session: Session, user_id: int) -> bool:
        """更新用户最后登录时间"""
        try:
            statement = (
                update(User)
                .where(User.id == user_id)
                .values(last_login_at=datetime.utcnow())
            )
            result = session.exec(statement)
            session.commit()
            return result.rowcount > 0
            
        except Exception as e:
            session.rollback()
            print(f"更新登录时间失败: {e}")
            return False

# === 使用示例 ===
def update_examples():
    """更新操作示例"""
    
    with get_session_context() as session:
        # 1. 单个用户更新
        update_data = {
            "first_name": "John Updated",
            "last_name": "Doe Updated",
            "is_active": True
        }
        updated_user = UserCRUD.update_user_by_id(session, 1, update_data)
        if updated_user:
            print(f"更新用户: {updated_user.username}")
        
        # 2. 安全更新（带验证）
        safe_update_data = {
            "email": "newemail@example.com",
            "username": "new_username"
        }
        safe_updated_user = UserCRUD.update_user_safe(session, 1, safe_update_data)
        if safe_updated_user:
            print(f"安全更新用户: {safe_updated_user.username}")
        
        # 3. 批量更新
        batch_updates = [
            {'id': 1, 'data': {'first_name': 'Alice Updated'}},
            {'id': 2, 'data': {'first_name': 'Bob Updated'}}
        ]
        updated_users = UserCRUD.update_users_batch(session, batch_updates)
        print(f"批量更新 {len(updated_users)} 个用户")
        
        # 4. 批量激活用户
        activated_count = UserCRUD.activate_users(session, [1, 2, 3])
        print(f"激活了 {activated_count} 个用户")
        
        # 5. 更新最后登录时间
        login_updated = UserCRUD.update_user_last_login(session, 1)
        print(f"登录时间更新: {login_updated}")
```

### 3.4 删除操作 (Delete)

```python
# crud_delete.py
from sqlmodel import Session, select, delete
from typing import List, Optional, Dict, Any
from models import User, Order
from datetime import datetime, timedelta

class UserCRUD:
    """用户删除操作"""
    
    @staticmethod
    def delete_user_by_id(session: Session, user_id: int) -> bool:
        """根据ID删除用户"""
        user = session.get(User, user_id)
        if not user:
            return False
        
        session.delete(user)
        session.commit()
        return True
    
    @staticmethod
    def soft_delete_user(session: Session, user_id: int) -> bool:
        """软删除用户（标记为删除，不实际删除）"""
        user = session.get(User, user_id)
        if not user:
            return False
        
        user.is_active = False
        user.deleted_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        session.add(user)
        session.commit()
        return True
    
    @staticmethod
    def delete_user_safe(session: Session, user_id: int) -> Dict[str, Any]:
        """安全删除用户（检查关联数据）"""
        try:
            user = session.get(User, user_id)
            if not user:
                return {"success": False, "message": "用户不存在"}
            
            # 检查是否有关联的订单
            orders_count = session.exec(
                select(func.count(Order.id)).where(Order.customer_id == user_id)
            ).one()
            
            if orders_count > 0:
                return {
                    "success": False, 
                    "message": f"用户有 {orders_count} 个关联订单，无法删除"
                }
            
            # 执行删除
            session.delete(user)
            session.commit()
            
            return {"success": True, "message": "用户删除成功"}
            
        except Exception as e:
            session.rollback()
            return {"success": False, "message": f"删除失败: {str(e)}"}
    
    @staticmethod
    def delete_users_batch(session: Session, user_ids: List[int]) -> Dict[str, Any]:
        """批量删除用户"""
        try:
            deleted_count = 0
            errors = []
            
            for user_id in user_ids:
                user = session.get(User, user_id)
                if user:
                    session.delete(user)
                    deleted_count += 1
                else:
                    errors.append(f"用户 {user_id} 不存在")
            
            session.commit()
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "errors": errors
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "message": f"批量删除失败: {str(e)}"
            }
    
    @staticmethod
    def bulk_delete_users(
        session: Session, 
        filter_conditions: Dict[str, Any]
    ) -> int:
        """批量删除（使用 SQL DELETE 语句）"""
        try:
            statement = delete(User)
            
            # 添加过滤条件
            for field, value in filter_conditions.items():
                if hasattr(User, field):
                    statement = statement.where(getattr(User, field) == value)
            
            result = session.exec(statement)
            session.commit()
            
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            print(f"批量删除失败: {e}")
            return 0
    
    @staticmethod
    def delete_inactive_users(session: Session, days: int = 30) -> int:
        """删除长期不活跃的用户"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        try:
            statement = (
                delete(User)
                .where(
                    and_(
                        User.is_active == False,
                        User.last_login_at < cutoff_date
                    )
                )
            )
            
            result = session.exec(statement)
            session.commit()
            
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            print(f"删除不活跃用户失败: {e}")
            return 0
    
    @staticmethod
    def cleanup_test_users(session: Session) -> int:
        """清理测试用户"""
        try:
            statement = (
                delete(User)
                .where(
                    or_(
                        User.email.like('%test%'),
                        User.username.like('%test%'),
                        User.email.like('%example.com')
                    )
                )
            )
            
            result = session.exec(statement)
            session.commit()
            
            return result.rowcount
            
        except Exception as e:
            session.rollback()
            print(f"清理测试用户失败: {e}")
            return 0
    
    @staticmethod
    def cascade_delete_user(session: Session, user_id: int) -> Dict[str, Any]:
        """级联删除用户及其所有关联数据"""
        try:
            user = session.get(User, user_id)
            if not user:
                return {"success": False, "message": "用户不存在"}
            
            deleted_data = {
                "user": user.username,
                "orders": 0,
                "profiles": 0
            }
            
            # 删除用户订单
            orders_result = session.exec(
                delete(Order).where(Order.customer_id == user_id)
            )
            deleted_data["orders"] = orders_result.rowcount
            
            # 删除用户档案
            profiles_result = session.exec(
                delete(UserProfile).where(UserProfile.user_id == user_id)
            )
            deleted_data["profiles"] = profiles_result.rowcount
            
            # 删除用户
            session.delete(user)
            session.commit()
            
            return {
                "success": True,
                "message": "级联删除成功",
                "deleted_data": deleted_data
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "message": f"级联删除失败: {str(e)}"
            }

# === 使用示例 ===
def delete_examples():
    """删除操作示例"""
    
    with get_session_context() as session:
        # 1. 简单删除
        deleted = UserCRUD.delete_user_by_id(session, 999)  # 假设的用户ID
        print(f"删除用户: {deleted}")
        
        # 2. 软删除
        soft_deleted = UserCRUD.soft_delete_user(session, 998)
        print(f"软删除用户: {soft_deleted}")
        
        # 3. 安全删除
        safe_delete_result = UserCRUD.delete_user_safe(session, 997)
        print(f"安全删除结果: {safe_delete_result}")
        
        # 4. 批量删除
        batch_delete_result = UserCRUD.delete_users_batch(session, [995, 996])
        print(f"批量删除结果: {batch_delete_result}")
        
        # 5. 清理不活跃用户
        inactive_deleted = UserCRUD.delete_inactive_users(session, days=90)
        print(f"删除不活跃用户: {inactive_deleted} 个")
        
        # 6. 清理测试用户
        test_deleted = UserCRUD.cleanup_test_users(session)
        print(f"清理测试用户: {test_deleted} 个")
        
        # 7. 级联删除
        cascade_result = UserCRUD.cascade_delete_user(session, 994)
        print(f"级联删除结果: {cascade_result}")
```

---

## 4. 高级查询操作

### 4.1 复杂条件查询

```python
# advanced_queries.py
from sqlmodel import Session, select, and_, or_, not_, func, case, cast
from sqlalchemy import String, Integer, DateTime, text
from typing import List, Optional, Dict, Any, Tuple
from models import User, Product, Order, OrderItem
from datetime import datetime, timedelta
from decimal import Decimal

class AdvancedQueryBuilder:
    """高级查询构建器"""
    
    def __init__(self, session: Session):
        self.session = session
        self.statement = None
    
    def select_from(self, model):
        """设置查询的主表"""
        self.statement = select(model)
        return self
    
    def where(self, *conditions):
        """添加 WHERE 条件"""
        if self.statement is None:
            raise ValueError("必须先调用 select_from()")
        
        if conditions:
            self.statement = self.statement.where(and_(*conditions))
        return self
    
    def join(self, target, condition=None):
        """添加 JOIN"""
        if condition:
            self.statement = self.statement.join(target, condition)
        else:
            self.statement = self.statement.join(target)
        return self
    
    def left_join(self, target, condition=None):
        """添加 LEFT JOIN"""
        if condition:
            self.statement = self.statement.outerjoin(target, condition)
        else:
            self.statement = self.statement.outerjoin(target)
        return self
    
    def order_by(self, *columns):
        """添加排序"""
        self.statement = self.statement.order_by(*columns)
        return self
    
    def group_by(self, *columns):
        """添加分组"""
        self.statement = self.statement.group_by(*columns)
        return self
    
    def having(self, *conditions):
        """添加 HAVING 条件"""
        if conditions:
            self.statement = self.statement.having(and_(*conditions))
        return self
    
    def limit(self, count: int):
        """限制结果数量"""
        self.statement = self.statement.limit(count)
        return self
    
    def offset(self, count: int):
        """设置偏移量"""
        self.statement = self.statement.offset(count)
        return self
    
    def execute(self):
        """执行查询"""
        return self.session.exec(self.statement)
    
    def all(self):
        """获取所有结果"""
        return self.execute().all()
    
    def first(self):
        """获取第一个结果"""
        return self.execute().first()
    
    def one(self):
        """获取唯一结果"""
        return self.execute().one()
    
    def scalar(self):
        """获取标量结果"""
        return self.execute().scalar()

class ComplexQueries:
    """复杂查询示例"""
    
    @staticmethod
    def search_users_advanced(
        session: Session,
        filters: Dict[str, Any]
    ) -> List[User]:
        """高级用户搜索"""
        builder = AdvancedQueryBuilder(session).select_from(User)
        
        conditions = []
        
        # 关键词搜索
        if 'keyword' in filters and filters['keyword']:
            keyword = f"%{filters['keyword']}%"
            keyword_condition = or_(
                User.username.ilike(keyword),
                User.first_name.ilike(keyword),
                User.last_name.ilike(keyword),
                User.email.ilike(keyword)
            )
            conditions.append(keyword_condition)
        
        # 状态过滤
        if 'is_active' in filters:
            conditions.append(User.is_active == filters['is_active'])
        
        # 注册时间范围
        if 'created_after' in filters:
            conditions.append(User.created_at >= filters['created_after'])
        
        if 'created_before' in filters:
            conditions.append(User.created_at <= filters['created_before'])
        
        # 年龄范围（基于生日）
        if 'min_age' in filters or 'max_age' in filters:
            today = datetime.now().date()
            
            if 'min_age' in filters:
                max_birth_date = today.replace(year=today.year - filters['min_age'])
                conditions.append(User.birth_date <= max_birth_date)
            
            if 'max_age' in filters:
                min_birth_date = today.replace(year=today.year - filters['max_age'])
                conditions.append(User.birth_date >= min_birth_date)
        
        # 订单数量范围
        if 'min_orders' in filters or 'max_orders' in filters:
            builder.left_join(Order, User.id == Order.customer_id)
            builder.group_by(User.id)
            
            having_conditions = []
            if 'min_orders' in filters:
                having_conditions.append(
                    func.count(Order.id) >= filters['min_orders']
                )
            
            if 'max_orders' in filters:
                having_conditions.append(
                    func.count(Order.id) <= filters['max_orders']
                )
            
            if having_conditions:
                builder.having(*having_conditions)
        
        # 应用所有条件
        if conditions:
            builder.where(*conditions)
        
        # 排序
        sort_by = filters.get('sort_by', 'created_at')
        sort_order = filters.get('sort_order', 'desc')
        
        if hasattr(User, sort_by):
            sort_column = getattr(User, sort_by)
            if sort_order.lower() == 'desc':
                sort_column = sort_column.desc()
            builder.order_by(sort_column)
        
        # 分页
        if 'limit' in filters:
            builder.limit(filters['limit'])
        
        if 'offset' in filters:
            builder.offset(filters['offset'])
        
        return builder.all()
    
    @staticmethod
    def get_user_order_summary(session: Session, user_id: int) -> Dict[str, Any]:
        """获取用户订单汇总"""
        # 基础用户信息
        user = session.get(User, user_id)
        if not user:
            return None
        
        # 订单统计
        order_stats = session.exec(
            select(
                func.count(Order.id).label('total_orders'),
                func.sum(Order.total_amount).label('total_spent'),
                func.avg(Order.total_amount).label('avg_order_value'),
                func.max(Order.created_at).label('last_order_date'),
                func.min(Order.created_at).label('first_order_date')
            ).where(Order.customer_id == user_id)
        ).first()
        
        # 按状态分组的订单数
        status_stats = session.exec(
            select(
                Order.status,
                func.count(Order.id).label('count')
            )
            .where(Order.customer_id == user_id)
            .group_by(Order.status)
        ).all()
        
        # 最近订单
        recent_orders = session.exec(
            select(Order)
            .where(Order.customer_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(5)
        ).all()
        
        return {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'order_summary': {
                'total_orders': order_stats.total_orders or 0,
                'total_spent': float(order_stats.total_spent or 0),
                'avg_order_value': float(order_stats.avg_order_value or 0),
                'first_order_date': order_stats.first_order_date,
                'last_order_date': order_stats.last_order_date
            },
            'status_breakdown': {
                status.status: status.count for status in status_stats
            },
            'recent_orders': [
                {
                    'id': order.id,
                    'order_number': order.order_number,
                    'total_amount': float(order.total_amount),
                    'status': order.status,
                    'created_at': order.created_at
                }
                for order in recent_orders
            ]
        }
    
    @staticmethod
    def get_product_sales_analysis(
        session: Session,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """产品销售分析"""
        statement = (
            select(
                Product.id,
                Product.name,
                Product.sku,
                Product.price,
                func.count(OrderItem.id).label('units_sold'),
                func.sum(OrderItem.quantity).label('total_quantity'),
                func.sum(OrderItem.total_price).label('total_revenue'),
                func.avg(OrderItem.unit_price).label('avg_selling_price'),
                # 计算利润（假设有成本字段）
                case(
                    (Product.cost.is_not(None),
                     func.sum(OrderItem.total_price) - 
                     (func.sum(OrderItem.quantity) * Product.cost)),
                    else_=None
                ).label('estimated_profit')
            )
            .join(OrderItem, Product.id == OrderItem.product_id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date,
                    Order.status.in_(['confirmed', 'shipped', 'delivered'])
                )
            )
            .group_by(
                Product.id, Product.name, Product.sku, 
                Product.price, Product.cost
            )
            .order_by(func.sum(OrderItem.total_price).desc())
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'product_id': result.id,
                'product_name': result.name,
                'sku': result.sku,
                'list_price': float(result.price),
                'units_sold': result.units_sold,
                'total_quantity': result.total_quantity,
                'total_revenue': float(result.total_revenue),
                'avg_selling_price': float(result.avg_selling_price or 0),
                'estimated_profit': float(result.estimated_profit or 0)
            }
            for result in results
        ]
    
    @staticmethod
    def get_monthly_sales_trend(
        session: Session,
        months: int = 12
    ) -> List[Dict[str, Any]]:
        """获取月度销售趋势"""
        start_date = datetime.now() - timedelta(days=months * 30)
        
        statement = (
            select(
                func.date_trunc('month', Order.created_at).label('month'),
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_amount).label('total_revenue'),
                func.avg(Order.total_amount).label('avg_order_value'),
                func.count(func.distinct(Order.customer_id)).label('unique_customers')
            )
            .where(
                and_(
                    Order.created_at >= start_date,
                    Order.status.in_(['confirmed', 'shipped', 'delivered'])
                )
            )
            .group_by(func.date_trunc('month', Order.created_at))
            .order_by(func.date_trunc('month', Order.created_at))
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'month': result.month.strftime('%Y-%m'),
                'order_count': result.order_count,
                'total_revenue': float(result.total_revenue),
                'avg_order_value': float(result.avg_order_value),
                'unique_customers': result.unique_customers
            }
            for result in results
        ]

### 4.2 子查询和 CTE

```python
# subqueries_cte.py
from sqlmodel import Session, select, func, text
from sqlalchemy import exists, literal_column
from typing import List, Dict, Any
from models import User, Order, Product, OrderItem

class SubqueryExamples:
    """子查询示例"""
    
    @staticmethod
    def get_users_with_recent_orders(session: Session, days: int = 30) -> List[User]:
        """获取最近有订单的用户（使用 EXISTS 子查询）"""
        recent_date = datetime.now() - timedelta(days=days)
        
        # 使用 EXISTS 子查询
        subquery = (
            select(Order.id)
            .where(
                and_(
                    Order.customer_id == User.id,
                    Order.created_at >= recent_date
                )
            )
        )
        
        statement = (
            select(User)
            .where(exists(subquery))
            .order_by(User.username)
        )
        
        return session.exec(statement).all()
    
    @staticmethod
    def get_top_spending_customers(
        session: Session, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取消费最多的客户（使用标量子查询）"""
        # 子查询：计算每个用户的总消费
        spending_subquery = (
            select(func.sum(Order.total_amount))
            .where(Order.customer_id == User.id)
            .scalar_subquery()
        )
        
        statement = (
            select(
                User.id,
                User.username,
                User.email,
                spending_subquery.label('total_spent')
            )
            .where(spending_subquery.is_not(None))
            .order_by(spending_subquery.desc())
            .limit(limit)
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'user_id': result.id,
                'username': result.username,
                'email': result.email,
                'total_spent': float(result.total_spent or 0)
            }
            for result in results
        ]
    
    @staticmethod
    def get_products_never_ordered(session: Session) -> List[Product]:
        """获取从未被订购的产品（使用 NOT EXISTS）"""
        # NOT EXISTS 子查询
        subquery = (
            select(OrderItem.id)
            .where(OrderItem.product_id == Product.id)
        )
        
        statement = (
            select(Product)
            .where(~exists(subquery))
            .order_by(Product.name)
        )
        
        return session.exec(statement).all()
    
    @staticmethod
    def get_users_above_average_spending(session: Session) -> List[Dict[str, Any]]:
        """获取消费超过平均值的用户"""
        # 计算平均消费的子查询
        avg_spending_subquery = (
            select(func.avg(Order.total_amount))
            .scalar_subquery()
        )
        
        # 每个用户的总消费子查询
        user_spending_subquery = (
            select(func.sum(Order.total_amount))
            .where(Order.customer_id == User.id)
            .scalar_subquery()
        )
        
        statement = (
            select(
                User.id,
                User.username,
                User.email,
                user_spending_subquery.label('total_spent')
            )
            .where(user_spending_subquery > avg_spending_subquery)
            .order_by(user_spending_subquery.desc())
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'user_id': result.id,
                'username': result.username,
                'email': result.email,
                'total_spent': float(result.total_spent or 0)
            }
            for result in results
        ]

class CTEExamples:
    """CTE (Common Table Expression) 示例"""
    
    @staticmethod
    def get_recursive_category_tree(session: Session) -> List[Dict[str, Any]]:
        """递归查询分类树（使用 CTE）"""
        # 注意：这需要数据库支持递归 CTE
        cte_query = text("""
        WITH RECURSIVE category_tree AS (
            -- 基础查询：根分类
            SELECT 
                id, 
                name, 
                parent_id, 
                0 as level,
                CAST(name AS VARCHAR(1000)) as path
            FROM categories 
            WHERE parent_id IS NULL
            
            UNION ALL
            
            -- 递归查询：子分类
            SELECT 
                c.id, 
                c.name, 
                c.parent_id, 
                ct.level + 1,
                CAST(ct.path || ' > ' || c.name AS VARCHAR(1000))
            FROM categories c
            INNER JOIN category_tree ct ON c.parent_id = ct.id
        )
        SELECT * FROM category_tree ORDER BY path
        """)
        
        result = session.exec(cte_query)
        return [
            {
                'id': row.id,
                'name': row.name,
                'parent_id': row.parent_id,
                'level': row.level,
                'path': row.path
            }
            for row in result
        ]
    
    @staticmethod
    def get_sales_ranking_with_cte(session: Session) -> List[Dict[str, Any]]:
        """使用 CTE 计算销售排名"""
        cte_query = text("""
        WITH monthly_sales AS (
            SELECT 
                DATE_TRUNC('month', o.created_at) as month,
                p.id as product_id,
                p.name as product_name,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.total_price) as total_revenue
            FROM orders o
            JOIN order_items oi ON o.id = oi.order_id
            JOIN products p ON oi.product_id = p.id
            WHERE o.status IN ('confirmed', 'shipped', 'delivered')
            GROUP BY DATE_TRUNC('month', o.created_at), p.id, p.name
        ),
        ranked_sales AS (
            SELECT 
                *,
                ROW_NUMBER() OVER (
                    PARTITION BY month 
                    ORDER BY total_revenue DESC
                ) as revenue_rank,
                ROW_NUMBER() OVER (
                    PARTITION BY month 
                    ORDER BY total_quantity DESC
                ) as quantity_rank
            FROM monthly_sales
        )
        SELECT * FROM ranked_sales 
        WHERE revenue_rank <= 10 OR quantity_rank <= 10
        ORDER BY month DESC, revenue_rank
        """)
        
        result = session.exec(cte_query)
        return [
            {
                'month': row.month.strftime('%Y-%m'),
                'product_id': row.product_id,
                'product_name': row.product_name,
                'total_quantity': row.total_quantity,
                'total_revenue': float(row.total_revenue),
                'revenue_rank': row.revenue_rank,
                'quantity_rank': row.quantity_rank
            }
            for row in result
        ]

### 4.3 窗口函数

```python
# window_functions.py
from sqlmodel import Session, select, func, text
from sqlalchemy import desc
from typing import List, Dict, Any
from models import User, Order, Product

class WindowFunctionExamples:
    """窗口函数示例"""
    
    @staticmethod
    def get_user_order_ranking(session: Session) -> List[Dict[str, Any]]:
        """用户订单排名（使用窗口函数）"""
        statement = (
            select(
                User.id,
                User.username,
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_amount).label('total_spent'),
                func.row_number().over(
                    order_by=func.sum(Order.total_amount).desc()
                ).label('spending_rank'),
                func.rank().over(
                    order_by=func.count(Order.id).desc()
                ).label('order_count_rank'),
                func.percent_rank().over(
                    order_by=func.sum(Order.total_amount).desc()
                ).label('spending_percentile')
            )
            .join(Order, User.id == Order.customer_id)
            .group_by(User.id, User.username)
            .order_by(func.sum(Order.total_amount).desc())
        )
        
        results = session.exec(statement).all()
        
        return [
            {
                'user_id': result.id,
                'username': result.username,
                'order_count': result.order_count,
                'total_spent': float(result.total_spent),
                'spending_rank': result.spending_rank,
                'order_count_rank': result.order_count_rank,
                'spending_percentile': float(result.spending_percentile)
            }
            for result in results
        ]