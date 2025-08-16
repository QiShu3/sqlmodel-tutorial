# 第九章：高级特性与扩展

## 本章概述

本章将深入探讨 SQLModel 的高级特性和扩展功能，包括自定义字段类型、高级查询技术、插件系统、与其他框架的集成、性能优化技巧以及实际项目中的最佳实践。通过学习这些高级特性，你将能够充分发挥 SQLModel 的潜力，构建更加强大和灵活的应用程序。

## 学习目标

- 掌握 SQLModel 的高级字段类型和自定义字段
- 学习复杂查询和高级 ORM 技术
- 了解 SQLModel 的插件系统和扩展机制
- 掌握与其他框架和库的集成方法
- 学习高级性能优化技巧
- 了解实际项目中的最佳实践

## 1. 自定义字段类型

### 1.1 基础自定义字段

```python
from typing import Any, Optional, Type
from sqlalchemy import TypeDecorator, String, Integer
from sqlalchemy.types import UserDefinedType
from sqlmodel import SQLModel, Field
import json
import uuid
from datetime import datetime
from decimal import Decimal
import re

class JSONField(TypeDecorator):
    """JSON 字段类型"""
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Any, dialect) -> Optional[str]:
        """将 Python 对象转换为 JSON 字符串"""
        if value is not None:
            return json.dumps(value, ensure_ascii=False, default=str)
        return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Any:
        """将 JSON 字符串转换为 Python 对象"""
        if value is not None:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return value

class EncryptedField(TypeDecorator):
    """加密字段类型"""
    
    impl = String
    cache_ok = True
    
    def __init__(self, secret_key: str, *args, **kwargs):
        self.secret_key = secret_key
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """加密数据"""
        if value is not None:
            # 这里使用简单的示例，实际应用中应使用更安全的加密方法
            from cryptography.fernet import Fernet
            f = Fernet(self.secret_key.encode())
            return f.encrypt(value.encode()).decode()
        return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """解密数据"""
        if value is not None:
            try:
                from cryptography.fernet import Fernet
                f = Fernet(self.secret_key.encode())
                return f.decrypt(value.encode()).decode()
            except Exception:
                return value
        return value

class EmailField(TypeDecorator):
    """邮箱字段类型"""
    
    impl = String(255)
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """验证并处理邮箱"""
        if value is not None:
            # 邮箱格式验证
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                raise ValueError(f"无效的邮箱格式: {value}")
            return value.lower().strip()
        return value

class PhoneField(TypeDecorator):
    """电话号码字段类型"""
    
    impl = String(20)
    cache_ok = True
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """验证并格式化电话号码"""
        if value is not None:
            # 移除所有非数字字符
            cleaned = re.sub(r'\D', '', value)
            
            # 中国手机号码验证
            if len(cleaned) == 11 and cleaned.startswith('1'):
                return f"{cleaned[:3]}-{cleaned[3:7]}-{cleaned[7:]}"
            else:
                raise ValueError(f"无效的电话号码格式: {value}")
        return value

class MoneyField(TypeDecorator):
    """货币字段类型"""
    
    impl = Integer  # 以分为单位存储
    cache_ok = True
    
    def process_bind_param(self, value, dialect) -> Optional[int]:
        """将元转换为分"""
        if value is not None:
            if isinstance(value, (int, float, Decimal)):
                return int(Decimal(str(value)) * 100)
            elif isinstance(value, str):
                return int(Decimal(value) * 100)
        return value
    
    def process_result_value(self, value: Optional[int], dialect) -> Optional[Decimal]:
        """将分转换为元"""
        if value is not None:
            return Decimal(value) / 100
        return value

# 使用自定义字段的模型示例
class UserProfile(SQLModel, table=True):
    """用户档案模型"""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(sa_column_kwargs={"type_": EmailField()})
    phone: Optional[str] = Field(default=None, sa_column_kwargs={"type_": PhoneField()})
    preferences: Optional[dict] = Field(default=None, sa_column_kwargs={"type_": JSONField()})
    balance: Optional[Decimal] = Field(default=None, sa_column_kwargs={"type_": MoneyField()})
    
    # 敏感信息加密存储
    secret_key = "your-secret-key-here"  # 实际应用中应从环境变量获取
    encrypted_data: Optional[str] = Field(
        default=None, 
        sa_column_kwargs={"type_": EncryptedField(secret_key)}
    )
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)

class CustomFieldValidator:
    """自定义字段验证器"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """验证邮箱格式"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """验证电话号码"""
        cleaned = re.sub(r'\D', '', phone)
        return len(cleaned) == 11 and cleaned.startswith('1')
    
    @staticmethod
    def validate_password_strength(password: str) -> dict:
        """验证密码强度"""
        result = {
            'is_valid': True,
            'score': 0,
            'issues': []
        }
        
        if len(password) < 8:
            result['issues'].append('密码长度至少8位')
            result['is_valid'] = False
        else:
            result['score'] += 1
        
        if not re.search(r'[A-Z]', password):
            result['issues'].append('密码应包含大写字母')
        else:
            result['score'] += 1
        
        if not re.search(r'[a-z]', password):
            result['issues'].append('密码应包含小写字母')
        else:
            result['score'] += 1
        
        if not re.search(r'\d', password):
            result['issues'].append('密码应包含数字')
        else:
            result['score'] += 1
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            result['issues'].append('密码应包含特殊字符')
        else:
            result['score'] += 1
        
        if result['issues']:
            result['is_valid'] = False
        
        return result
```

### 1.2 复合字段类型

```python
from typing import List, Dict, Union
from dataclasses import dataclass
from enum import Enum

class AddressType(str, Enum):
    """地址类型枚举"""
    HOME = "home"
    WORK = "work"
    OTHER = "other"

@dataclass
class Address:
    """地址数据类"""
    street: str
    city: str
    state: str
    postal_code: str
    country: str = "中国"
    address_type: AddressType = AddressType.HOME
    
    def to_dict(self) -> dict:
        return {
            'street': self.street,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'address_type': self.address_type.value
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Address':
        return cls(
            street=data['street'],
            city=data['city'],
            state=data['state'],
            postal_code=data['postal_code'],
            country=data.get('country', '中国'),
            address_type=AddressType(data.get('address_type', 'home'))
        )

class AddressField(TypeDecorator):
    """地址字段类型"""
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Optional[Address], dialect) -> Optional[str]:
        """将地址对象转换为 JSON 字符串"""
        if value is not None:
            if isinstance(value, Address):
                return json.dumps(value.to_dict(), ensure_ascii=False)
            elif isinstance(value, dict):
                return json.dumps(value, ensure_ascii=False)
        return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[Address]:
        """将 JSON 字符串转换为地址对象"""
        if value is not None:
            try:
                data = json.loads(value)
                return Address.from_dict(data)
            except (json.JSONDecodeError, TypeError, KeyError):
                return None
        return value

class TagsField(TypeDecorator):
    """标签字段类型"""
    
    impl = String
    cache_ok = True
    
    def process_bind_param(self, value: Optional[List[str]], dialect) -> Optional[str]:
        """将标签列表转换为逗号分隔的字符串"""
        if value is not None:
            if isinstance(value, list):
                # 清理和验证标签
                cleaned_tags = []
                for tag in value:
                    if isinstance(tag, str) and tag.strip():
                        cleaned_tag = tag.strip().lower()
                        if cleaned_tag not in cleaned_tags:
                            cleaned_tags.append(cleaned_tag)
                return ','.join(cleaned_tags)
        return value
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[List[str]]:
        """将逗号分隔的字符串转换为标签列表"""
        if value is not None and value.strip():
            return [tag.strip() for tag in value.split(',') if tag.strip()]
        return []

# 使用复合字段的模型
class UserExtended(SQLModel, table=True):
    """扩展用户模型"""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(sa_column_kwargs={"type_": EmailField()})
    
    # 地址信息
    address: Optional[Address] = Field(
        default=None, 
        sa_column_kwargs={"type_": AddressField()}
    )
    
    # 标签
    tags: Optional[List[str]] = Field(
        default=None, 
        sa_column_kwargs={"type_": TagsField()}
    )
    
    # 用户偏好设置
    preferences: Optional[dict] = Field(
        default=None, 
        sa_column_kwargs={"type_": JSONField()}
    )
    
    created_at: datetime = Field(default_factory=datetime.now)

class FieldTypeManager:
    """字段类型管理器"""
    
    def __init__(self):
        self.custom_types = {
            'json': JSONField,
            'email': EmailField,
            'phone': PhoneField,
            'money': MoneyField,
            'address': AddressField,
            'tags': TagsField
        }
    
    def register_type(self, name: str, field_type: Type[TypeDecorator]):
        """注册自定义字段类型"""
        self.custom_types[name] = field_type
    
    def get_type(self, name: str) -> Optional[Type[TypeDecorator]]:
        """获取字段类型"""
        return self.custom_types.get(name)
    
    def create_field(self, field_type: str, **kwargs) -> Field:
        """创建字段"""
        custom_type = self.get_type(field_type)
        if custom_type:
            return Field(sa_column_kwargs={"type_": custom_type(**kwargs)})
        else:
            raise ValueError(f"未知的字段类型: {field_type}")

# 使用示例
field_manager = FieldTypeManager()

# 创建自定义字段
email_field = field_manager.create_field('email')
json_field = field_manager.create_field('json')
money_field = field_manager.create_field('money')
```

## 2. 高级查询技术

### 2.1 复杂查询构建器

```python
from typing import Any, Dict, List, Optional, Union, Callable
from sqlalchemy import and_, or_, not_, func, case, cast, literal_column
from sqlalchemy.orm import aliased, selectinload, joinedload
from sqlalchemy.sql import Select
from sqlmodel import select
from datetime import datetime, timedelta
from enum import Enum

class QueryOperator(str, Enum):
    """查询操作符"""
    EQ = "eq"          # 等于
    NE = "ne"          # 不等于
    GT = "gt"          # 大于
    GTE = "gte"        # 大于等于
    LT = "lt"          # 小于
    LTE = "lte"        # 小于等于
    LIKE = "like"      # 模糊匹配
    ILIKE = "ilike"    # 忽略大小写模糊匹配
    IN = "in"          # 在列表中
    NOT_IN = "not_in"  # 不在列表中
    IS_NULL = "is_null"        # 为空
    IS_NOT_NULL = "is_not_null"  # 不为空
    BETWEEN = "between"        # 在范围内
    CONTAINS = "contains"      # 包含（JSON）
    STARTS_WITH = "starts_with"  # 以...开始
    ENDS_WITH = "ends_with"    # 以...结束

class QueryBuilder:
    """查询构建器"""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.query = select(model_class)
        self.joins = []
        self.filters = []
        self.order_by_clauses = []
        self.group_by_clauses = []
        self.having_clauses = []
        self.limit_value = None
        self.offset_value = None
    
    def filter(self, field: str, operator: QueryOperator, value: Any) -> 'QueryBuilder':
        """添加过滤条件"""
        column = getattr(self.model_class, field)
        
        if operator == QueryOperator.EQ:
            condition = column == value
        elif operator == QueryOperator.NE:
            condition = column != value
        elif operator == QueryOperator.GT:
            condition = column > value
        elif operator == QueryOperator.GTE:
            condition = column >= value
        elif operator == QueryOperator.LT:
            condition = column < value
        elif operator == QueryOperator.LTE:
            condition = column <= value
        elif operator == QueryOperator.LIKE:
            condition = column.like(f"%{value}%")
        elif operator == QueryOperator.ILIKE:
            condition = column.ilike(f"%{value}%")
        elif operator == QueryOperator.IN:
            condition = column.in_(value)
        elif operator == QueryOperator.NOT_IN:
            condition = ~column.in_(value)
        elif operator == QueryOperator.IS_NULL:
            condition = column.is_(None)
        elif operator == QueryOperator.IS_NOT_NULL:
            condition = column.is_not(None)
        elif operator == QueryOperator.BETWEEN:
            condition = column.between(value[0], value[1])
        elif operator == QueryOperator.CONTAINS:
            condition = column.contains(value)
        elif operator == QueryOperator.STARTS_WITH:
            condition = column.like(f"{value}%")
        elif operator == QueryOperator.ENDS_WITH:
            condition = column.like(f"%{value}")
        else:
            raise ValueError(f"不支持的操作符: {operator}")
        
        self.filters.append(condition)
        return self
    
    def filter_by_dict(self, filters: Dict[str, Any]) -> 'QueryBuilder':
        """通过字典添加过滤条件"""
        for field, value in filters.items():
            if '__' in field:
                field_name, operator = field.split('__', 1)
                try:
                    op = QueryOperator(operator)
                    self.filter(field_name, op, value)
                except ValueError:
                    # 如果操作符无效，使用等于操作
                    self.filter(field, QueryOperator.EQ, value)
            else:
                self.filter(field, QueryOperator.EQ, value)
        return self
    
    def join(self, *args, **kwargs) -> 'QueryBuilder':
        """添加连接"""
        self.query = self.query.join(*args, **kwargs)
        return self
    
    def left_join(self, *args, **kwargs) -> 'QueryBuilder':
        """添加左连接"""
        self.query = self.query.outerjoin(*args, **kwargs)
        return self
    
    def order_by(self, *columns) -> 'QueryBuilder':
        """添加排序"""
        for column in columns:
            if isinstance(column, str):
                if column.startswith('-'):
                    # 降序
                    field_name = column[1:]
                    field = getattr(self.model_class, field_name)
                    self.order_by_clauses.append(field.desc())
                else:
                    # 升序
                    field = getattr(self.model_class, column)
                    self.order_by_clauses.append(field.asc())
            else:
                self.order_by_clauses.append(column)
        return self
    
    def group_by(self, *columns) -> 'QueryBuilder':
        """添加分组"""
        for column in columns:
            if isinstance(column, str):
                field = getattr(self.model_class, column)
                self.group_by_clauses.append(field)
            else:
                self.group_by_clauses.append(column)
        return self
    
    def having(self, condition) -> 'QueryBuilder':
        """添加 HAVING 条件"""
        self.having_clauses.append(condition)
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """设置限制数量"""
        self.limit_value = limit
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """设置偏移量"""
        self.offset_value = offset
        return self
    
    def paginate(self, page: int, per_page: int) -> 'QueryBuilder':
        """分页"""
        self.limit_value = per_page
        self.offset_value = (page - 1) * per_page
        return self
    
    def build(self) -> Select:
        """构建查询"""
        query = self.query
        
        # 应用过滤条件
        if self.filters:
            query = query.where(and_(*self.filters))
        
        # 应用分组
        if self.group_by_clauses:
            query = query.group_by(*self.group_by_clauses)
        
        # 应用 HAVING 条件
        if self.having_clauses:
            query = query.having(and_(*self.having_clauses))
        
        # 应用排序
        if self.order_by_clauses:
            query = query.order_by(*self.order_by_clauses)
        
        # 应用限制和偏移
        if self.limit_value is not None:
            query = query.limit(self.limit_value)
        
        if self.offset_value is not None:
            query = query.offset(self.offset_value)
        
        return query

class AdvancedQueryBuilder(QueryBuilder):
    """高级查询构建器"""
    
    def search(self, search_term: str, fields: List[str]) -> 'AdvancedQueryBuilder':
        """全文搜索"""
        if not search_term or not fields:
            return self
        
        search_conditions = []
        for field in fields:
            column = getattr(self.model_class, field)
            search_conditions.append(column.ilike(f"%{search_term}%"))
        
        if search_conditions:
            self.filters.append(or_(*search_conditions))
        
        return self
    
    def date_range(self, field: str, start_date: datetime, end_date: datetime) -> 'AdvancedQueryBuilder':
        """日期范围过滤"""
        column = getattr(self.model_class, field)
        self.filters.append(and_(
            column >= start_date,
            column <= end_date
        ))
        return self
    
    def recent(self, field: str, days: int) -> 'AdvancedQueryBuilder':
        """最近几天的记录"""
        start_date = datetime.now() - timedelta(days=days)
        return self.date_range(field, start_date, datetime.now())
    
    def aggregate(self, aggregations: Dict[str, str]) -> 'AdvancedQueryBuilder':
        """聚合查询"""
        select_columns = []
        
        for alias, expression in aggregations.items():
            if expression.startswith('count('):
                field = expression[6:-1]  # 提取字段名
                if field == '*':
                    select_columns.append(func.count().label(alias))
                else:
                    column = getattr(self.model_class, field)
                    select_columns.append(func.count(column).label(alias))
            elif expression.startswith('sum('):
                field = expression[4:-1]
                column = getattr(self.model_class, field)
                select_columns.append(func.sum(column).label(alias))
            elif expression.startswith('avg('):
                field = expression[4:-1]
                column = getattr(self.model_class, field)
                select_columns.append(func.avg(column).label(alias))
            elif expression.startswith('max('):
                field = expression[4:-1]
                column = getattr(self.model_class, field)
                select_columns.append(func.max(column).label(alias))
            elif expression.startswith('min('):
                field = expression[4:-1]
                column = getattr(self.model_class, field)
                select_columns.append(func.min(column).label(alias))
        
        if select_columns:
            self.query = select(*select_columns)
        
        return self
    
    def conditional_filter(self, condition: bool, field: str, operator: QueryOperator, value: Any) -> 'AdvancedQueryBuilder':
        """条件性过滤"""
        if condition:
            self.filter(field, operator, value)
        return self
    
    def dynamic_filter(self, filters: Dict[str, Any], ignore_none: bool = True) -> 'AdvancedQueryBuilder':
        """动态过滤"""
        for field, value in filters.items():
            if ignore_none and value is None:
                continue
            
            if isinstance(value, dict) and 'operator' in value and 'value' in value:
                operator = QueryOperator(value['operator'])
                self.filter(field, operator, value['value'])
            else:
                self.filter(field, QueryOperator.EQ, value)
        
        return self

# 使用示例
class QueryService:
    """查询服务"""
    
    def __init__(self, session):
        self.session = session
    
    async def search_users(self, 
                          search_term: Optional[str] = None,
                          filters: Optional[Dict[str, Any]] = None,
                          page: int = 1,
                          per_page: int = 20) -> Dict[str, Any]:
        """搜索用户"""
        
        builder = AdvancedQueryBuilder(UserExtended)
        
        # 全文搜索
        if search_term:
            builder.search(search_term, ['username', 'email'])
        
        # 动态过滤
        if filters:
            builder.dynamic_filter(filters)
        
        # 分页
        builder.paginate(page, per_page)
        
        # 排序
        builder.order_by('-created_at')
        
        # 执行查询
        query = builder.build()
        result = await self.session.exec(query)
        users = result.all()
        
        # 计算总数
        count_builder = AdvancedQueryBuilder(UserExtended)
        if search_term:
            count_builder.search(search_term, ['username', 'email'])
        if filters:
            count_builder.dynamic_filter(filters)
        
        count_query = count_builder.aggregate({'total': 'count(*)'}).build()
        count_result = await self.session.exec(count_query)
        total = count_result.first().total
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        
        # 总用户数
        total_users_query = AdvancedQueryBuilder(UserExtended).aggregate({
            'total_users': 'count(*)'
        }).build()
        
        # 最近30天注册用户数
        recent_users_query = AdvancedQueryBuilder(UserExtended).recent(
            'created_at', 30
        ).aggregate({
            'recent_users': 'count(*)'
        }).build()
        
        # 按标签分组统计
        # 这需要更复杂的查询，这里简化处理
        
        total_result = await self.session.exec(total_users_query)
        recent_result = await self.session.exec(recent_users_query)
        
        return {
            'total_users': total_result.first().total_users,
            'recent_users': recent_result.first().recent_users
        }
```

### 2.2 子查询和 CTE（公共表表达式）

```python
from sqlalchemy import exists, literal, union_all
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

class SubqueryBuilder:
    """子查询构建器"""
    
    def __init__(self, session):
        self.session = session
    
    async def users_with_recent_activity(self, days: int = 30) -> List[UserExtended]:
        """获取最近有活动的用户"""
        
        # 假设有一个 UserActivity 模型
        recent_activity_subquery = (
            select(UserActivity.user_id)
            .where(UserActivity.created_at >= datetime.now() - timedelta(days=days))
            .distinct()
        ).subquery()
        
        query = (
            select(UserExtended)
            .where(UserExtended.id.in_(select(recent_activity_subquery.c.user_id)))
        )
        
        result = await self.session.exec(query)
        return result.all()
    
    async def users_without_orders(self) -> List[UserExtended]:
        """获取没有订单的用户"""
        
        # 使用 NOT EXISTS
        query = (
            select(UserExtended)
            .where(~exists().where(Order.user_id == UserExtended.id))
        )
        
        result = await self.session.exec(query)
        return result.all()
    
    async def top_users_by_order_value(self, limit: int = 10) -> List[Dict[str, Any]]:
        """按订单总价值获取顶级用户"""
        
        # 子查询计算每个用户的订单总价值
        user_order_value = (
            select(
                Order.user_id,
                func.sum(Order.total_amount).label('total_value')
            )
            .group_by(Order.user_id)
        ).subquery()
        
        # 主查询连接用户信息
        query = (
            select(
                UserExtended.id,
                UserExtended.username,
                UserExtended.email,
                user_order_value.c.total_value
            )
            .join(user_order_value, UserExtended.id == user_order_value.c.user_id)
            .order_by(user_order_value.c.total_value.desc())
            .limit(limit)
        )
        
        result = await self.session.exec(query)
        return [
            {
                'id': row.id,
                'username': row.username,
                'email': row.email,
                'total_value': row.total_value
            }
            for row in result.all()
        ]
    
    async def user_activity_summary_with_cte(self, user_id: int) -> Dict[str, Any]:
        """使用 CTE 获取用户活动摘要"""
        
        # 定义 CTE
        monthly_activity = (
            select(
                func.date_trunc('month', UserActivity.created_at).label('month'),
                func.count().label('activity_count')
            )
            .where(UserActivity.user_id == user_id)
            .group_by(func.date_trunc('month', UserActivity.created_at))
        ).cte('monthly_activity')
        
        # 使用 CTE 的主查询
        query = (
            select(
                monthly_activity.c.month,
                monthly_activity.c.activity_count,
                func.lag(monthly_activity.c.activity_count).over(
                    order_by=monthly_activity.c.month
                ).label('prev_month_count')
            )
            .select_from(monthly_activity)
            .order_by(monthly_activity.c.month.desc())
        )
        
        result = await self.session.exec(query)
        return [
            {
                'month': row.month,
                'activity_count': row.activity_count,
                'prev_month_count': row.prev_month_count,
                'growth': (
                    ((row.activity_count - row.prev_month_count) / row.prev_month_count * 100)
                    if row.prev_month_count else None
                )
            }
            for row in result.all()
        ]
    
    async def complex_user_segmentation(self) -> Dict[str, List[Dict[str, Any]]]:
        """复杂用户分段分析"""
        
        # 高价值用户 CTE
        high_value_users = (
            select(
                Order.user_id,
                func.sum(Order.total_amount).label('total_spent')
            )
            .group_by(Order.user_id)
            .having(func.sum(Order.total_amount) > 1000)
        ).cte('high_value_users')
        
        # 活跃用户 CTE
        active_users = (
            select(
                UserActivity.user_id,
                func.count().label('activity_count')
            )
            .where(UserActivity.created_at >= datetime.now() - timedelta(days=30))
            .group_by(UserActivity.user_id)
            .having(func.count() > 10)
        ).cte('active_users')
        
        # 高价值且活跃的用户
        vip_users_query = (
            select(
                UserExtended.id,
                UserExtended.username,
                UserExtended.email,
                high_value_users.c.total_spent,
                active_users.c.activity_count
            )
            .join(high_value_users, UserExtended.id == high_value_users.c.user_id)
            .join(active_users, UserExtended.id == active_users.c.user_id)
        )
        
        # 高价值但不活跃的用户
        at_risk_users_query = (
            select(
                UserExtended.id,
                UserExtended.username,
                UserExtended.email,
                high_value_users.c.total_spent
            )
            .join(high_value_users, UserExtended.id == high_value_users.c.user_id)
            .outerjoin(active_users, UserExtended.id == active_users.c.user_id)
            .where(active_users.c.user_id.is_(None))
        )
        
        # 执行查询
        vip_result = await self.session.exec(vip_users_query)
        at_risk_result = await self.session.exec(at_risk_users_query)
        
        return {
            'vip_users': [
                {
                    'id': row.id,
                    'username': row.username,
                    'email': row.email,
                    'total_spent': row.total_spent,
                    'activity_count': row.activity_count
                }
                for row in vip_result.all()
            ],
            'at_risk_users': [
                {
                    'id': row.id,
                    'username': row.username,
                    'email': row.email,
                    'total_spent': row.total_spent
                }
                for row in at_risk_result.all()
            ]
        }
```

## 3. 插件系统与扩展

### 3.1 插件基础架构

```python
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Callable
from dataclasses import dataclass
import inspect
import importlib
from pathlib import Path

@dataclass
class PluginInfo:
    """插件信息"""
    name: str
    version: str
    description: str
    author: str
    dependencies: List[str] = None
    enabled: bool = True

class PluginInterface(ABC):
    """插件接口"""
    
    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """插件信息"""
        pass
    
    @abstractmethod
    async def initialize(self, app_context: Dict[str, Any]) -> None:
        """初始化插件"""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """清理插件资源"""
        pass
    
    async def on_model_create(self, model_instance: Any) -> None:
        """模型创建时的钩子"""
        pass
    
    async def on_model_update(self, model_instance: Any, changes: Dict[str, Any]) -> None:
        """模型更新时的钩子"""
        pass
    
    async def on_model_delete(self, model_instance: Any) -> None:
        """模型删除时的钩子"""
        pass
    
    async def on_query_execute(self, query: str, params: Dict[str, Any]) -> None:
        """查询执行时的钩子"""
        pass

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, PluginInterface] = {}
        self.hooks: Dict[str, List[Callable]] = {
            'model_create': [],
            'model_update': [],
            'model_delete': [],
            'query_execute': []
        }
        self.app_context: Dict[str, Any] = {}
    
    def register_plugin(self, plugin: PluginInterface) -> None:
        """注册插件"""
        plugin_name = plugin.info.name
        
        if plugin_name in self.plugins:
            raise ValueError(f"插件 {plugin_name} 已经注册")
        
        self.plugins[plugin_name] = plugin
        
        # 注册钩子
        self._register_hooks(plugin)
    
    def _register_hooks(self, plugin: PluginInterface) -> None:
        """注册插件钩子"""
        if hasattr(plugin, 'on_model_create'):
            self.hooks['model_create'].append(plugin.on_model_create)
        
        if hasattr(plugin, 'on_model_update'):
            self.hooks['model_update'].append(plugin.on_model_update)
        
        if hasattr(plugin, 'on_model_delete'):
            self.hooks['model_delete'].append(plugin.on_model_delete)
        
        if hasattr(plugin, 'on_query_execute'):
            self.hooks['query_execute'].append(plugin.on_query_execute)
    
    async def initialize_plugins(self, app_context: Dict[str, Any]) -> None:
        """初始化所有插件"""
        self.app_context = app_context
        
        for plugin in self.plugins.values():
            if plugin.info.enabled:
                try:
                    await plugin.initialize(app_context)
                    logger.info(f"插件 {plugin.info.name} 初始化成功")
                except Exception as e:
                    logger.error(f"插件 {plugin.info.name} 初始化失败: {e}")
    
    async def cleanup_plugins(self) -> None:
        """清理所有插件"""
        for plugin in self.plugins.values():
            try:
                await plugin.cleanup()
            except Exception as e:
                logger.error(f"插件 {plugin.info.name} 清理失败: {e}")
    
    async def trigger_hook(self, hook_name: str, *args, **kwargs) -> None:
        """触发钩子"""
        if hook_name in self.hooks:
            for hook_func in self.hooks[hook_name]:
                try:
                    await hook_func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"钩子 {hook_name} 执行失败: {e}")
    
    def get_plugin(self, name: str) -> Optional[PluginInterface]:
        """获取插件"""
        return self.plugins.get(name)
    
    def list_plugins(self) -> List[PluginInfo]:
        """列出所有插件"""
        return [plugin.info for plugin in self.plugins.values()]
    
    def enable_plugin(self, name: str) -> None:
        """启用插件"""
        if name in self.plugins:
            self.plugins[name].info.enabled = True
    
    def disable_plugin(self, name: str) -> None:
        """禁用插件"""
        if name in self.plugins:
            self.plugins[name].info.enabled = False
    
    def load_plugins_from_directory(self, directory: Path) -> None:
        """从目录加载插件"""
        for plugin_file in directory.glob("*.py"):
            if plugin_file.name.startswith("__"):
                continue
            
            try:
                module_name = plugin_file.stem
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # 查找插件类
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, PluginInterface) and 
                        obj != PluginInterface):
                        plugin_instance = obj()
                        self.register_plugin(plugin_instance)
                        break
                        
            except Exception as e:
                logger.error(f"加载插件文件 {plugin_file} 失败: {e}")

# 全局插件管理器实例
plugin_manager = PluginManager()
```

### 3.2 内置插件示例

```python
import asyncio
from datetime import datetime
from typing import Any, Dict

class AuditLogPlugin(PluginInterface):
    """审计日志插件"""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="audit_log",
            version="1.0.0",
            description="记录模型变更的审计日志",
            author="SQLModel Team"
        )
    
    async def initialize(self, app_context: Dict[str, Any]) -> None:
        """初始化插件"""
        self.session = app_context.get('session')
        logger.info("审计日志插件已初始化")
    
    async def cleanup(self) -> None:
        """清理插件资源"""
        logger.info("审计日志插件已清理")
    
    async def on_model_create(self, model_instance: Any) -> None:
        """记录模型创建"""
        await self._log_change('CREATE', model_instance)
    
    async def on_model_update(self, model_instance: Any, changes: Dict[str, Any]) -> None:
        """记录模型更新"""
        await self._log_change('UPDATE', model_instance, changes)
    
    async def on_model_delete(self, model_instance: Any) -> None:
        """记录模型删除"""
        await self._log_change('DELETE', model_instance)
    
    async def _log_change(self, action: str, model_instance: Any, changes: Dict[str, Any] = None) -> None:
        """记录变更"""
        log_entry = {
            'action': action,
            'model_type': model_instance.__class__.__name__,
            'model_id': getattr(model_instance, 'id', None),
            'changes': changes,
            'timestamp': datetime.now(),
            'user_id': getattr(model_instance, '_current_user_id', None)
        }
        
        # 这里可以保存到数据库或发送到日志系统
        logger.info(f"审计日志: {log_entry}")

class CachePlugin(PluginInterface):
    """缓存插件"""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="cache",
            version="1.0.0",
            description="提供模型级别的缓存功能",
            author="SQLModel Team"
        )
    
    async def initialize(self, app_context: Dict[str, Any]) -> None:
        """初始化插件"""
        self.cache = {}  # 简单的内存缓存，实际应用中应使用 Redis
        self.cache_ttl = 300  # 5分钟
        logger.info("缓存插件已初始化")
    
    async def cleanup(self) -> None:
        """清理插件资源"""
        self.cache.clear()
        logger.info("缓存插件已清理")
    
    def get_cache_key(self, model_type: str, model_id: Any) -> str:
        """生成缓存键"""
        return f"{model_type}:{model_id}"
    
    async def get_from_cache(self, model_type: str, model_id: Any) -> Any:
        """从缓存获取"""
        cache_key = self.get_cache_key(model_type, model_id)
        cache_entry = self.cache.get(cache_key)
        
        if cache_entry:
            timestamp, data = cache_entry
            if (datetime.now() - timestamp).seconds < self.cache_ttl:
                return data
            else:
                # 缓存过期，删除
                del self.cache[cache_key]
        
        return None
    
    async def set_cache(self, model_type: str, model_id: Any, data: Any) -> None:
        """设置缓存"""
        cache_key = self.get_cache_key(model_type, model_id)
        self.cache[cache_key] = (datetime.now(), data)
    
    async def invalidate_cache(self, model_type: str, model_id: Any) -> None:
        """使缓存失效"""
        cache_key = self.get_cache_key(model_type, model_id)
        if cache_key in self.cache:
            del self.cache[cache_key]
    
    async def on_model_update(self, model_instance: Any, changes: Dict[str, Any]) -> None:
        """模型更新时使缓存失效"""
        model_type = model_instance.__class__.__name__
        model_id = getattr(model_instance, 'id', None)
        if model_id:
            await self.invalidate_cache(model_type, model_id)
    
    async def on_model_delete(self, model_instance: Any) -> None:
        """模型删除时使缓存失效"""
        model_type = model_instance.__class__.__name__
        model_id = getattr(model_instance, 'id', None)
        if model_id:
            await self.invalidate_cache(model_type, model_id)

class ValidationPlugin(PluginInterface):
    """验证插件"""
    
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="validation",
            version="1.0.0",
            description="提供高级数据验证功能",
            author="SQLModel Team"
        )
    
    async def initialize(self, app_context: Dict[str, Any]) -> None:
        """初始化插件"""
        self.validators = {}
        self._register_default_validators()
        logger.info("验证插件已初始化")
    
    async def cleanup(self) -> None:
        """清理插件资源"""
        self.validators.clear()
        logger.info("验证插件已清理")
    
    def _register_default_validators(self) -> None:
        """注册默认验证器"""
        self.validators['email'] = self._validate_email
        self.validators['phone'] = self._validate_phone
        self.validators['password'] = self._validate_password
    
    def register_validator(self, name: str, validator_func: Callable) -> None:
        """注册自定义验证器"""
        self.validators[name] = validator_func
    
    async def _validate_email(self, value: str) -> bool:
        """验证邮箱"""
        return CustomFieldValidator.validate_email(value)
    
    async def _validate_phone(self, value: str) -> bool:
        """验证电话"""
        return CustomFieldValidator.validate_phone(value)
    
    async def _validate_password(self, value: str) -> bool:
        """验证密码"""
        result = CustomFieldValidator.validate_password_strength(value)
        return result['is_valid']
    
    async def validate_model(self, model_instance: Any) -> List[str]:
        """验证模型"""
        errors = []
        
        # 获取模型的验证规则（这里简化处理）
        validation_rules = getattr(model_instance.__class__, '_validation_rules', {})
        
        for field_name, rules in validation_rules.items():
            field_value = getattr(model_instance, field_name, None)
            
            for rule in rules:
                validator_name = rule.get('validator')
                if validator_name in self.validators:
                    try:
                        is_valid = await self.validators[validator_name](field_value)
                        if not is_valid:
                            errors.append(f"{field_name}: {rule.get('message', '验证失败')}")
                    except Exception as e:
                        errors.append(f"{field_name}: 验证器错误 - {e}")
        
        return errors
    
    async def on_model_create(self, model_instance: Any) -> None:
        """创建时验证"""
        errors = await self.validate_model(model_instance)
        if errors:
            raise ValueError(f"模型验证失败: {', '.join(errors)}")
    
    async def on_model_update(self, model_instance: Any, changes: Dict[str, Any]) -> None:
        """更新时验证"""
        errors = await self.validate_model(model_instance)
        if errors:
            raise ValueError(f"模型验证失败: {', '.join(errors)}")

# 注册插件
plugin_manager.register_plugin(AuditLogPlugin())
plugin_manager.register_plugin(CachePlugin())
plugin_manager.register_plugin(ValidationPlugin())
```

### 3.3 插件装饰器和中间件

```python
from functools import wraps
from typing import Callable, Any

def with_plugins(hook_name: str):
    """插件装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 执行前钩子
            await plugin_manager.trigger_hook(f"before_{hook_name}", *args, **kwargs)
            
            try:
                # 执行原函数
                result = await func(*args, **kwargs)
                
                # 执行后钩子
                await plugin_manager.trigger_hook(f"after_{hook_name}", result, *args, **kwargs)
                
                return result
            except Exception as e:
                # 错误钩子
                await plugin_manager.trigger_hook(f"error_{hook_name}", e, *args, **kwargs)
                raise
        
        return wrapper
    return decorator

class PluginMiddleware:
    """插件中间件"""
    
    def __init__(self, session):
        self.session = session
    
    async def __aenter__(self):
        # 会话开始时的钩子
        await plugin_manager.trigger_hook('session_start', self.session)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 会话结束时的钩子
        if exc_type:
            await plugin_manager.trigger_hook('session_error', exc_val, self.session)
        else:
            await plugin_manager.trigger_hook('session_end', self.session)

# 使用示例
class EnhancedUserService:
    """增强的用户服务（集成插件）"""
    
    def __init__(self, session):
        self.session = session
    
    @with_plugins('create_user')
    async def create_user(self, user_data: dict) -> UserExtended:
        """创建用户"""
        user = UserExtended(**user_data)
        
        # 触发模型创建钩子
        await plugin_manager.trigger_hook('model_create', user)
        
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    @with_plugins('update_user')
    async def update_user(self, user_id: int, updates: dict) -> UserExtended:
        """更新用户"""
        user = await self.session.get(UserExtended, user_id)
        if not user:
            raise ValueError(f"用户 {user_id} 不存在")
        
        # 记录变更
        changes = {}
        for key, value in updates.items():
            if hasattr(user, key):
                old_value = getattr(user, key)
                if old_value != value:
                    changes[key] = {'old': old_value, 'new': value}
                    setattr(user, key, value)
        
        if changes:
            # 触发模型更新钩子
            await plugin_manager.trigger_hook('model_update', user, changes)
            
            await self.session.commit()
            await self.session.refresh(user)
        
        return user
    
    @with_plugins('delete_user')
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.session.get(UserExtended, user_id)
        if not user:
            return False
        
        # 触发模型删除钩子
        await plugin_manager.trigger_hook('model_delete', user)
        
        await self.session.delete(user)
        await self.session.commit()
        
        return True
    
    async def get_user_with_cache(self, user_id: int) -> Optional[UserExtended]:
        """使用缓存获取用户"""
        # 尝试从缓存获取
        cache_plugin = plugin_manager.get_plugin('cache')
        if cache_plugin:
            cached_user = await cache_plugin.get_from_cache('UserExtended', user_id)
            if cached_user:
                return cached_user
        
        # 从数据库获取
        user = await self.session.get(UserExtended, user_id)
        
        # 设置缓存
        if user and cache_plugin:
            await cache_plugin.set_cache('UserExtended', user_id, user)
        
        return user

# 使用插件中间件的示例
async def example_with_middleware():
    """使用插件中间件的示例"""
    async with PluginMiddleware(session) as middleware:
        user_service = EnhancedUserService(session)
        
        # 创建用户
        user_data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'preferences': {'theme': 'dark', 'language': 'zh-CN'}
        }
        
        user = await user_service.create_user(user_data)
        print(f"创建用户: {user.username}")
        
        # 更新用户
        updates = {'preferences': {'theme': 'light', 'language': 'en-US'}}
        updated_user = await user_service.update_user(user.id, updates)
        print(f"更新用户: {updated_user.preferences}")
```

## 4. 与其他框架集成

### 4.1 FastAPI 集成

```python
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import jwt
from datetime import datetime, timedelta

class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    email: str
    password: str
    preferences: Optional[dict] = None

class UserResponse(BaseModel):
    """用户响应模型"""
    id: int
    username: str
    email: str
    preferences: Optional[dict] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    """用户更新模型"""
    username: Optional[str] = None
    email: Optional[str] = None
    preferences: Optional[dict] = None

class FastAPIIntegration:
    """FastAPI 集成类"""
    
    def __init__(self, app: FastAPI, session_factory):
        self.app = app
        self.session_factory = session_factory
        self.security = HTTPBearer()
        self.secret_key = "your-secret-key"  # 应从环境变量获取
        
        self._setup_middleware()
        self._setup_routes()
    
    def _setup_middleware(self):
        """设置中间件"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    async def get_session(self):
        """获取数据库会话"""
        async with self.session_factory() as session:
            yield session
    
    async def get_current_user(self, 
                              credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
                              session = Depends(get_session)) -> UserExtended:
        """获取当前用户"""
        try:
            payload = jwt.decode(credentials.credentials, self.secret_key, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if user_id is None:
                raise HTTPException(status_code=401, detail="无效的认证令牌")
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
        
        user = await session.get(UserExtended, user_id)
        if user is None:
            raise HTTPException(status_code=401, detail="用户不存在")
        
        return user
    
    def create_access_token(self, user_id: int) -> str:
        """创建访问令牌"""
        expire = datetime.utcnow() + timedelta(hours=24)
        payload = {
            "user_id": user_id,
            "exp": expire
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def _setup_routes(self):
        """设置路由"""
        
        @self.app.post("/users/", response_model=UserResponse)
        async def create_user(
            user_data: UserCreate,
            background_tasks: BackgroundTasks,
            session = Depends(self.get_session)
        ):
            """创建用户"""
            async with PluginMiddleware(session):
                user_service = EnhancedUserService(session)
                
                try:
                    user = await user_service.create_user(user_data.dict())
                    
                    # 后台任务：发送欢迎邮件
                    background_tasks.add_task(self.send_welcome_email, user.email)
                    
                    return UserResponse.from_orm(user)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.get("/users/{user_id}", response_model=UserResponse)
        async def get_user(
            user_id: int,
            session = Depends(self.get_session),
            current_user: UserExtended = Depends(self.get_current_user)
        ):
            """获取用户"""
            user_service = EnhancedUserService(session)
            user = await user_service.get_user_with_cache(user_id)
            
            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")
            
            return UserResponse.from_orm(user)
        
        @self.app.put("/users/{user_id}", response_model=UserResponse)
        async def update_user(
            user_id: int,
            user_data: UserUpdate,
            session = Depends(self.get_session),
            current_user: UserExtended = Depends(self.get_current_user)
        ):
            """更新用户"""
            # 权限检查
            if current_user.id != user_id:
                raise HTTPException(status_code=403, detail="权限不足")
            
            async with PluginMiddleware(session):
                user_service = EnhancedUserService(session)
                
                try:
                    updates = {k: v for k, v in user_data.dict().items() if v is not None}
                    user = await user_service.update_user(user_id, updates)
                    return UserResponse.from_orm(user)
                except ValueError as e:
                    raise HTTPException(status_code=400, detail=str(e))
        
        @self.app.delete("/users/{user_id}")
        async def delete_user(
            user_id: int,
            session = Depends(self.get_session),
            current_user: UserExtended = Depends(self.get_current_user)
        ):
            """删除用户"""
            # 权限检查
            if current_user.id != user_id:
                raise HTTPException(status_code=403, detail="权限不足")
            
            async with PluginMiddleware(session):
                user_service = EnhancedUserService(session)
                
                success = await user_service.delete_user(user_id)
                if not success:
                    raise HTTPException(status_code=404, detail="用户不存在")
                
                return {"message": "用户删除成功"}
        
        @self.app.get("/users/", response_model=List[UserResponse])
        async def list_users(
            page: int = 1,
            per_page: int = 20,
            search: Optional[str] = None,
            session = Depends(self.get_session),
            current_user: UserExtended = Depends(self.get_current_user)
        ):
            """用户列表"""
            query_service = QueryService(session)
            
            filters = {}
            if search:
                # 这里可以添加更复杂的搜索逻辑
                pass
            
            result = await query_service.search_users(
                search_term=search,
                filters=filters,
                page=page,
                per_page=per_page
            )
            
            return [UserResponse.from_orm(user) for user in result['users']]
    
    async def send_welcome_email(self, email: str):
        """发送欢迎邮件（后台任务）"""
        # 这里实现邮件发送逻辑
        print(f"发送欢迎邮件到: {email}")

# 使用示例
app = FastAPI(title="SQLModel Advanced API", version="1.0.0")
fastapi_integration = FastAPIIntegration(app, session_factory)
```

### 4.2 Celery 集成

```python
from celery import Celery
from celery.result import AsyncResult
from typing import Any, Dict
import json

class CeleryIntegration:
    """Celery 集成类"""
    
    def __init__(self, broker_url: str = "redis://localhost:6379/0"):
        self.celery_app = Celery(
            'sqlmodel_tasks',
            broker=broker_url,
            backend=broker_url
        )
        
        self._setup_tasks()
    
    def _setup_tasks(self):
        """设置任务"""
        
        @self.celery_app.task(bind=True)
        def process_user_data(self, user_id: int, processing_type: str):
            """处理用户数据任务"""
            try:
                # 这里实现具体的数据处理逻辑
                result = self._process_user_data_sync(user_id, processing_type)
                return {
                    'status': 'success',
                    'result': result,
                    'user_id': user_id,
                    'processing_type': processing_type
                }
            except Exception as e:
                self.retry(countdown=60, max_retries=3)
                return {
                    'status': 'error',
                    'error': str(e),
                    'user_id': user_id,
                    'processing_type': processing_type
                }
        
        @self.celery_app.task
        def send_notification(user_id: int, message: str, notification_type: str = 'email'):
            """发送通知任务"""
            # 实现通知发送逻辑
            print(f"发送{notification_type}通知给用户{user_id}: {message}")
            return {'status': 'sent', 'user_id': user_id, 'type': notification_type}
        
        @self.celery_app.task
        def generate_report(report_type: str, filters: Dict[str, Any]):
            """生成报告任务"""
            # 实现报告生成逻辑
            report_data = self._generate_report_sync(report_type, filters)
            return {
                'status': 'completed',
                'report_type': report_type,
                'data': report_data
            }
        
        # 保存任务引用
        self.process_user_data = process_user_data
        self.send_notification = send_notification
        self.generate_report = generate_report
    
    def _process_user_data_sync(self, user_id: int, processing_type: str) -> Dict[str, Any]:
        """同步处理用户数据"""
        # 这里实现具体的处理逻辑
        return {
            'processed_at': datetime.now().isoformat(),
            'processing_type': processing_type,
            'user_id': user_id
        }
    
    def _generate_report_sync(self, report_type: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """同步生成报告"""
        # 这里实现报告生成逻辑
        return {
            'generated_at': datetime.now().isoformat(),
            'report_type': report_type,
            'filters': filters,
            'data': []
        }
    
    def submit_task(self, task_name: str, *args, **kwargs) -> str:
        """提交任务"""
        task = getattr(self, task_name)
        result = task.delay(*args, **kwargs)
        return result.id
    
    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """获取任务结果"""
        result = AsyncResult(task_id, app=self.celery_app)
        
        return {
            'task_id': task_id,
            'status': result.status,
            'result': result.result if result.ready() else None,
            'traceback': result.traceback if result.failed() else None
        }
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        self.celery_app.control.revoke(task_id, terminate=True)
        return True

# Celery 任务服务
class TaskService:
    """任务服务"""
    
    def __init__(self, celery_integration: CeleryIntegration):
        self.celery = celery_integration
    
    async def process_user_async(self, user_id: int, processing_type: str) -> str:
        """异步处理用户"""
        task_id = self.celery.submit_task(
            'process_user_data',
            user_id,
            processing_type
        )
        return task_id
    
    async def send_notification_async(self, user_id: int, message: str, notification_type: str = 'email') -> str:
        """异步发送通知"""
        task_id = self.celery.submit_task(
            'send_notification',
            user_id,
            message,
            notification_type
        )
        return task_id
    
    async def generate_report_async(self, report_type: str, filters: Dict[str, Any]) -> str:
        """异步生成报告"""
        task_id = self.celery.submit_task(
            'generate_report',
            report_type,
            filters
        )
        return task_id
    
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return self.celery.get_task_result(task_id)

# 在 FastAPI 中集成 Celery
celery_integration = CeleryIntegration()
task_service = TaskService(celery_integration)

@app.post("/tasks/process-user/{user_id}")
async def process_user_task(
    user_id: int,
    processing_type: str,
    current_user: UserExtended = Depends(fastapi_integration.get_current_user)
):
    """提交用户处理任务"""
    task_id = await task_service.process_user_async(user_id, processing_type)
    return {"task_id": task_id, "message": "任务已提交"}

@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: UserExtended = Depends(fastapi_integration.get_current_user)
):
    """获取任务状态"""
    status = await task_service.get_task_status(task_id)
    return status
```

## 5. 数据迁移工具

### 5.1 迁移管理器

```python
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import importlib.util
import inspect

class Migration(SQLModel, table=True):
    """迁移记录模型"""
    __tablename__ = "migrations"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    batch: int
    executed_at: datetime = Field(default_factory=datetime.now)

class MigrationBase:
    """迁移基类"""
    
    def __init__(self, session):
        self.session = session
    
    async def up(self):
        """执行迁移"""
        raise NotImplementedError
    
    async def down(self):
        """回滚迁移"""
        raise NotImplementedError
    
    def get_name(self) -> str:
        """获取迁移名称"""
        return self.__class__.__name__

class MigrationManager:
    """迁移管理器"""
    
    def __init__(self, session, migrations_dir: str = "migrations"):
        self.session = session
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
    
    async def create_migrations_table(self):
        """创建迁移表"""
        from sqlalchemy import text
        
        # 检查表是否存在
        result = await self.session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'")
        )
        
        if not result.fetchone():
            # 创建迁移表
            await self.session.execute(
                text("""
                CREATE TABLE migrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    batch INTEGER NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
            )
            await self.session.commit()
    
    def discover_migrations(self) -> List[str]:
        """发现迁移文件"""
        migration_files = []
        
        for file_path in self.migrations_dir.glob("*.py"):
            if file_path.name != "__init__.py":
                migration_files.append(file_path.stem)
        
        return sorted(migration_files)
    
    async def get_executed_migrations(self) -> List[str]:
        """获取已执行的迁移"""
        result = await self.session.execute(
            select(Migration.name).order_by(Migration.executed_at)
        )
        return [row[0] for row in result.fetchall()]
    
    async def get_pending_migrations(self) -> List[str]:
        """获取待执行的迁移"""
        all_migrations = self.discover_migrations()
        executed_migrations = await self.get_executed_migrations()
        
        return [m for m in all_migrations if m not in executed_migrations]
    
    def load_migration(self, migration_name: str) -> MigrationBase:
        """加载迁移类"""
        migration_file = self.migrations_dir / f"{migration_name}.py"
        
        if not migration_file.exists():
            raise FileNotFoundError(f"Migration file not found: {migration_file}")
        
        # 动态导入迁移模块
        spec = importlib.util.spec_from_file_location(migration_name, migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 查找迁移类
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, MigrationBase) and 
                obj != MigrationBase):
                return obj(self.session)
        
        raise ValueError(f"No migration class found in {migration_file}")
    
    async def run_migration(self, migration_name: str) -> bool:
        """执行单个迁移"""
        try:
            migration = self.load_migration(migration_name)
            
            # 执行迁移
            await migration.up()
            
            # 记录迁移
            batch = await self.get_next_batch()
            migration_record = Migration(
                name=migration_name,
                batch=batch
            )
            
            self.session.add(migration_record)
            await self.session.commit()
            
            print(f"✓ 迁移 {migration_name} 执行成功")
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"✗ 迁移 {migration_name} 执行失败: {e}")
            return False
    
    async def rollback_migration(self, migration_name: str) -> bool:
        """回滚单个迁移"""
        try:
            migration = self.load_migration(migration_name)
            
            # 执行回滚
            await migration.down()
            
            # 删除迁移记录
            result = await self.session.execute(
                select(Migration).where(Migration.name == migration_name)
            )
            migration_record = result.scalar_one_or_none()
            
            if migration_record:
                await self.session.delete(migration_record)
                await self.session.commit()
            
            print(f"✓ 迁移 {migration_name} 回滚成功")
            return True
            
        except Exception as e:
            await self.session.rollback()
            print(f"✗ 迁移 {migration_name} 回滚失败: {e}")
            return False
    
    async def migrate(self) -> int:
        """执行所有待执行的迁移"""
        await self.create_migrations_table()
        
        pending_migrations = await self.get_pending_migrations()
        
        if not pending_migrations:
            print("没有待执行的迁移")
            return 0
        
        success_count = 0
        for migration_name in pending_migrations:
            if await self.run_migration(migration_name):
                success_count += 1
            else:
                break  # 遇到失败的迁移时停止
        
        print(f"执行了 {success_count}/{len(pending_migrations)} 个迁移")
        return success_count
    
    async def rollback(self, steps: int = 1) -> int:
        """回滚指定数量的迁移"""
        executed_migrations = await self.get_executed_migrations()
        
        if not executed_migrations:
            print("没有可回滚的迁移")
            return 0
        
        # 获取最后执行的迁移
        migrations_to_rollback = executed_migrations[-steps:]
        migrations_to_rollback.reverse()  # 按相反顺序回滚
        
        success_count = 0
        for migration_name in migrations_to_rollback:
            if await self.rollback_migration(migration_name):
                success_count += 1
            else:
                break
        
        print(f"回滚了 {success_count}/{len(migrations_to_rollback)} 个迁移")
        return success_count
    
    async def get_next_batch(self) -> int:
        """获取下一个批次号"""
        result = await self.session.execute(
            select(func.max(Migration.batch))
        )
        max_batch = result.scalar()
        return (max_batch or 0) + 1
    
    async def status(self) -> Dict[str, Any]:
        """获取迁移状态"""
        all_migrations = self.discover_migrations()
        executed_migrations = await self.get_executed_migrations()
        pending_migrations = await self.get_pending_migrations()
        
        return {
            'total_migrations': len(all_migrations),
            'executed_migrations': len(executed_migrations),
            'pending_migrations': len(pending_migrations),
            'executed_list': executed_migrations,
            'pending_list': pending_migrations
        }

# 迁移示例
class CreateUsersTable(MigrationBase):
    """创建用户表迁移"""
    
    async def up(self):
        """创建用户表"""
        from sqlalchemy import text
        
        await self.session.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
    
    async def down(self):
        """删除用户表"""
        from sqlalchemy import text
        
        await self.session.execute(text("DROP TABLE IF EXISTS users"))

class AddUserPreferences(MigrationBase):
    """添加用户偏好字段"""
    
    async def up(self):
        """添加偏好字段"""
        from sqlalchemy import text
        
        await self.session.execute(text("""
            ALTER TABLE users ADD COLUMN preferences TEXT
        """))
    
    async def down(self):
        """删除偏好字段"""
        from sqlalchemy import text
        
        # SQLite 不支持 DROP COLUMN，需要重建表
        await self.session.execute(text("""
            CREATE TABLE users_backup AS 
            SELECT id, username, email, password_hash, created_at, updated_at 
            FROM users
        """))
        
        await self.session.execute(text("DROP TABLE users"))
        
        await self.session.execute(text("""
            ALTER TABLE users_backup RENAME TO users
        """))
```

### 5.2 迁移生成器

```python
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

class MigrationGenerator:
    """迁移生成器"""
    
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
    
    def generate_migration_name(self, description: str) -> str:
        """生成迁移文件名"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_description = description.lower().replace(" ", "_")
        return f"{timestamp}_{clean_description}"
    
    def create_migration_file(self, name: str, content: str) -> Path:
        """创建迁移文件"""
        file_path = self.migrations_dir / f"{name}.py"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def generate_create_table_migration(self, table_name: str, columns: List[Dict[str, Any]]) -> str:
        """生成创建表的迁移"""
        class_name = f"Create{table_name.title().replace('_', '')}Table"
        
        # 生成列定义
        column_definitions = []
        for col in columns:
            col_def = f"                {col['name']} {col['type']}"
            if col.get('primary_key'):
                col_def += " PRIMARY KEY"
            if col.get('autoincrement'):
                col_def += " AUTOINCREMENT"
            if col.get('unique'):
                col_def += " UNIQUE"
            if col.get('not_null'):
                col_def += " NOT NULL"
            if col.get('default'):
                col_def += f" DEFAULT {col['default']}"
            
            column_definitions.append(col_def)
        
        columns_sql = ",\n".join(column_definitions)
        
        return f'''
from migrations.migration_base import MigrationBase
from sqlalchemy import text

class {class_name}(MigrationBase):
    """创建 {table_name} 表"""
    
    async def up(self):
        """创建表"""
        await self.session.execute(text("""
            CREATE TABLE {table_name} (
{columns_sql}
            )
        """))
    
    async def down(self):
        """删除表"""
        await self.session.execute(text("DROP TABLE IF EXISTS {table_name}"))
'''
    
    def generate_add_column_migration(self, table_name: str, column_name: str, column_type: str, **options) -> str:
        """生成添加列的迁移"""
        class_name = f"Add{column_name.title().replace('_', '')}To{table_name.title().replace('_', '')}"
        
        column_def = f"{column_name} {column_type}"
        if options.get('not_null'):
            column_def += " NOT NULL"
        if options.get('default'):
            column_def += f" DEFAULT {options['default']}"
        
        return f'''
from migrations.migration_base import MigrationBase
from sqlalchemy import text

class {class_name}(MigrationBase):
    """添加 {column_name} 列到 {table_name} 表"""
    
    async def up(self):
        """添加列"""
        await self.session.execute(text("""
            ALTER TABLE {table_name} ADD COLUMN {column_def}
        """))
    
    async def down(self):
        """删除列（SQLite 限制，需要重建表）"""
        # 注意：SQLite 不支持 DROP COLUMN
        # 这里需要根据实际情况实现表重建逻辑
        raise NotImplementedError("SQLite 不支持删除列，需要手动实现表重建")
'''
    
    def generate_create_index_migration(self, table_name: str, index_name: str, columns: List[str], unique: bool = False) -> str:
        """生成创建索引的迁移"""
        class_name = f"Create{index_name.title().replace('_', '')}Index"
        
        unique_keyword = "UNIQUE " if unique else ""
        columns_str = ", ".join(columns)
        
        return f'''
from migrations.migration_base import MigrationBase
from sqlalchemy import text

class {class_name}(MigrationBase):
    """创建 {index_name} 索引"""
    
    async def up(self):
        """创建索引"""
        await self.session.execute(text("""
            CREATE {unique_keyword}INDEX {index_name} ON {table_name} ({columns_str})
        """))
    
    async def down(self):
        """删除索引"""
        await self.session.execute(text("DROP INDEX IF EXISTS {index_name}"))
'''

# 使用示例
async def migration_example():
    """迁移使用示例"""
    # 创建迁移管理器
    migration_manager = MigrationManager(session)
    
    # 查看迁移状态
    status = await migration_manager.status()
    print(f"迁移状态: {status}")
    
    # 执行迁移
    await migration_manager.migrate()
    
    # 回滚最后一个迁移
    await migration_manager.rollback(1)
    
    # 生成新的迁移
    generator = MigrationGenerator()
    
    # 生成创建表的迁移
    migration_name = generator.generate_migration_name("create posts table")
    migration_content = generator.generate_create_table_migration(
        "posts",
        [
            {'name': 'id', 'type': 'INTEGER', 'primary_key': True, 'autoincrement': True},
            {'name': 'title', 'type': 'VARCHAR(200)', 'not_null': True},
            {'name': 'content', 'type': 'TEXT'},
            {'name': 'user_id', 'type': 'INTEGER', 'not_null': True},
            {'name': 'created_at', 'type': 'TIMESTAMP', 'default': 'CURRENT_TIMESTAMP'}
        ]
    )
    
    migration_file = generator.create_migration_file(migration_name, migration_content)
    print(f"创建迁移文件: {migration_file}")
```

## 6. 测试工具

### 6.1 测试基础设施

```python
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
import tempfile
import os

class TestDatabase:
    """测试数据库管理器"""
    
    def __init__(self, database_url: str = None):
        if database_url is None:
            # 使用临时文件作为测试数据库
            self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
            self.database_url = f"sqlite+aiosqlite:///{self.temp_db.name}"
        else:
            self.database_url = database_url
            self.temp_db = None
        
        self.engine = create_async_engine(
            self.database_url,
            echo=False,  # 测试时不输出 SQL
            future=True
        )
        
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def create_tables(self):
        """创建所有表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    
    async def drop_tables(self):
        """删除所有表"""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
    
    async def get_session(self) -> AsyncSession:
        """获取数据库会话"""
        return self.session_factory()
    
    async def cleanup(self):
        """清理资源"""
        await self.engine.dispose()
        
        if self.temp_db:
            self.temp_db.close()
            os.unlink(self.temp_db.name)

class TestDataFactory:
    """测试数据工厂"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_user(self, **kwargs) -> UserExtended:
        """创建测试用户"""
        default_data = {
            'username': 'test_user',
            'email': 'test@example.com',
            'password_hash': 'hashed_password',
            'preferences': {'theme': 'light'}
        }
        default_data.update(kwargs)
        
        user = UserExtended(**default_data)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        return user
    
    async def create_multiple_users(self, count: int, **kwargs) -> List[UserExtended]:
        """创建多个测试用户"""
        users = []
        
        for i in range(count):
            user_data = {
                'username': f'test_user_{i}',
                'email': f'test_{i}@example.com',
                **kwargs
            }
            user = await self.create_user(**user_data)
            users.append(user)
        
        return users
    
    async def create_post(self, user_id: int, **kwargs) -> 'Post':
        """创建测试文章"""
        default_data = {
            'title': 'Test Post',
            'content': 'This is a test post content.',
            'user_id': user_id
        }
        default_data.update(kwargs)
        
        post = Post(**default_data)
        self.session.add(post)
        await self.session.commit()
        await self.session.refresh(post)
        
        return post

# Pytest fixtures
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def test_db() -> AsyncGenerator[TestDatabase, None]:
    """测试数据库 fixture"""
    db = TestDatabase()
    await db.create_tables()
    
    yield db
    
    await db.drop_tables()
    await db.cleanup()

@pytest.fixture
async def session(test_db: TestDatabase) -> AsyncGenerator[AsyncSession, None]:
    """数据库会话 fixture"""
    async with test_db.get_session() as session:
        yield session

@pytest.fixture
async def test_data_factory(session: AsyncSession) -> TestDataFactory:
    """测试数据工厂 fixture"""
    return TestDataFactory(session)

# 测试用例示例
class TestUserService:
    """用户服务测试"""
    
    async def test_create_user(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试创建用户"""
        user_service = EnhancedUserService(session)
        
        user_data = {
            'username': 'new_user',
            'email': 'new@example.com',
            'password': 'password123',
            'preferences': {'theme': 'dark'}
        }
        
        user = await user_service.create_user(user_data)
        
        assert user.id is not None
        assert user.username == 'new_user'
        assert user.email == 'new@example.com'
        assert user.preferences == {'theme': 'dark'}
    
    async def test_get_user_with_cache(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试缓存获取用户"""
        # 创建测试用户
        user = await test_data_factory.create_user(username='cache_test')
        
        user_service = EnhancedUserService(session)
        
        # 第一次获取（从数据库）
        retrieved_user = await user_service.get_user_with_cache(user.id)
        assert retrieved_user.username == 'cache_test'
        
        # 第二次获取（从缓存）
        cached_user = await user_service.get_user_with_cache(user.id)
        assert cached_user.username == 'cache_test'
    
    async def test_update_user(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试更新用户"""
        user = await test_data_factory.create_user()
        user_service = EnhancedUserService(session)
        
        updates = {
            'username': 'updated_user',
            'preferences': {'theme': 'dark', 'language': 'en'}
        }
        
        updated_user = await user_service.update_user(user.id, updates)
        
        assert updated_user.username == 'updated_user'
        assert updated_user.preferences == {'theme': 'dark', 'language': 'en'}
    
    async def test_delete_user(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试删除用户"""
        user = await test_data_factory.create_user()
        user_service = EnhancedUserService(session)
        
        success = await user_service.delete_user(user.id)
        assert success is True
        
        # 验证用户已删除
        deleted_user = await session.get(UserExtended, user.id)
        assert deleted_user is None
    
    @pytest.mark.parametrize("user_count", [5, 10, 20])
    async def test_bulk_operations(self, session: AsyncSession, test_data_factory: TestDataFactory, user_count: int):
        """测试批量操作"""
        users = await test_data_factory.create_multiple_users(user_count)
        
        # 验证创建的用户数量
        assert len(users) == user_count
        
        # 验证每个用户都有唯一的用户名和邮箱
        usernames = [user.username for user in users]
        emails = [user.email for user in users]
        
        assert len(set(usernames)) == user_count
        assert len(set(emails)) == user_count

class TestQueryBuilder:
    """查询构建器测试"""
    
    async def test_basic_query(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试基本查询"""
        # 创建测试数据
        users = await test_data_factory.create_multiple_users(5)
        
        query_builder = AdvancedQueryBuilder(session, UserExtended)
        
        # 测试基本查询
        result = await query_builder.where('username', 'like', 'test_user_%').execute()
        assert len(result) == 5
    
    async def test_complex_query(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试复杂查询"""
        # 创建测试数据
        await test_data_factory.create_user(username='admin', email='admin@example.com')
        await test_data_factory.create_user(username='user1', email='user1@example.com')
        await test_data_factory.create_user(username='user2', email='user2@example.com')
        
        query_builder = AdvancedQueryBuilder(session, UserExtended)
        
        # 测试复杂查询
        result = await query_builder.where('username', 'in', ['admin', 'user1']).order_by('username').execute()
        
        assert len(result) == 2
        assert result[0].username == 'admin'
        assert result[1].username == 'user1'
    
    async def test_pagination(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试分页"""
        # 创建测试数据
        await test_data_factory.create_multiple_users(20)
        
        query_builder = AdvancedQueryBuilder(session, UserExtended)
        
        # 测试分页
        result = await query_builder.paginate(page=1, per_page=5)
        
        assert result['total'] == 20
        assert len(result['items']) == 5
        assert result['page'] == 1
        assert result['per_page'] == 5
        assert result['pages'] == 4

# 性能测试
class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_bulk_insert_performance(self, session: AsyncSession):
        """测试批量插入性能"""
        import time
        
        start_time = time.time()
        
        # 批量创建用户
        users = []
        for i in range(1000):
            user = UserExtended(
                username=f'perf_user_{i}',
                email=f'perf_{i}@example.com',
                password_hash='hashed_password'
            )
            users.append(user)
        
        session.add_all(users)
        await session.commit()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"批量插入 1000 个用户耗时: {execution_time:.2f} 秒")
        
        # 验证插入成功
        result = await session.execute(select(func.count(UserExtended.id)))
        count = result.scalar()
        assert count >= 1000
    
    @pytest.mark.asyncio
    async def test_query_performance(self, session: AsyncSession, test_data_factory: TestDataFactory):
        """测试查询性能"""
        import time
        
        # 创建大量测试数据
        await test_data_factory.create_multiple_users(1000)
        
        start_time = time.time()
        
        # 执行复杂查询
        query_builder = AdvancedQueryBuilder(session, UserExtended)
        result = await query_builder.where('username', 'like', 'test_user_%').limit(100).execute()
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"查询 100 个用户耗时: {execution_time:.2f} 秒")
        
        assert len(result) == 100
        assert execution_time < 1.0  # 应该在 1 秒内完成

# 运行测试的示例命令
# pytest tests/ -v --asyncio-mode=auto
# pytest tests/test_performance.py -v --asyncio-mode=auto -s
```

## 7. 最佳实践

### 7.1 代码组织最佳实践

```python
from typing import Dict, Any, List
from pathlib import Path
import inspect

class ProjectStructureBestPractices:
    """项目结构最佳实践"""
    
    @staticmethod
    def get_recommended_structure() -> Dict[str, Any]:
        """获取推荐的项目结构"""
        return {
            'project_root': {
                'app/': {
                    '__init__.py': 'Application package',
                    'main.py': 'FastAPI application entry point',
                    'config/': {
                        '__init__.py': '',
                        'database.py': 'Database configuration',
                        'settings.py': 'Application settings',
                        'logging.py': 'Logging configuration'
                    },
                    'models/': {
                        '__init__.py': '',
                        'base.py': 'Base model classes',
                        'user.py': 'User related models',
                        'mixins.py': 'Model mixins'
                    },
                    'services/': {
                        '__init__.py': '',
                        'user_service.py': 'User business logic',
                        'auth_service.py': 'Authentication logic'
                    },
                    'api/': {
                        '__init__.py': '',
                        'v1/': {
                            '__init__.py': '',
                            'endpoints/': {
                                '__init__.py': '',
                                'users.py': 'User endpoints',
                                'auth.py': 'Auth endpoints'
                            }
                        }
                    },
                    'core/': {
                        '__init__.py': '',
                        'database.py': 'Database connection',
                        'security.py': 'Security utilities',
                        'exceptions.py': 'Custom exceptions'
                    },
                    'utils/': {
                        '__init__.py': '',
                        'validators.py': 'Custom validators',
                        'helpers.py': 'Helper functions'
                    }
                },
                'migrations/': {
                    '__init__.py': '',
                    'migration_base.py': 'Migration base class',
                    '001_initial.py': 'Initial migration'
                },
                'tests/': {
                    '__init__.py': '',
                    'conftest.py': 'Pytest configuration',
                    'test_models.py': 'Model tests',
                    'test_services.py': 'Service tests',
                    'test_api.py': 'API tests'
                },
                'scripts/': {
                    'migrate.py': 'Migration script',
                    'seed_data.py': 'Data seeding script'
                },
                'requirements.txt': 'Python dependencies',
                'pyproject.toml': 'Project configuration',
                'README.md': 'Project documentation',
                '.env.example': 'Environment variables example',
                'docker-compose.yml': 'Docker configuration'
            }
        }
    
    @staticmethod
    def get_coding_standards() -> Dict[str, List[str]]:
        """获取编码标准"""
        return {
            'naming_conventions': [
                '使用 snake_case 命名变量和函数',
                '使用 PascalCase 命名类',
                '使用 UPPER_CASE 命名常量',
                '使用描述性的名称，避免缩写',
                '模型类名应该是单数形式'
            ],
            'model_design': [
                '每个模型应该有明确的职责',
                '使用适当的字段类型和约束',
                '添加必要的索引',
                '使用 Enum 类型表示固定选项',
                '添加适当的文档字符串'
            ],
            'service_layer': [
                '业务逻辑应该在服务层实现',
                '服务方法应该是原子性的',
                '使用依赖注入',
                '添加适当的错误处理',
                '使用类型提示'
            ],
            'api_design': [
                '遵循 RESTful 设计原则',
                '使用适当的 HTTP 状态码',
                '添加请求和响应验证',
                '实现适当的错误处理',
                '添加 API 文档'
            ],
            'testing': [
                '为每个功能编写测试',
                '使用测试数据工厂',
                '测试边界条件',
                '使用模拟对象隔离测试',
                '保持测试的独立性'
            ]
        }

class PerformanceOptimizationBestPractices:
    """性能优化最佳实践"""
    
    @staticmethod
    def get_database_optimization_tips() -> List[str]:
        """获取数据库优化建议"""
        return [
            '为经常查询的字段添加索引',
            '使用复合索引优化多字段查询',
            '避免 N+1 查询问题',
            '使用 eager loading 预加载关联数据',
            '使用分页避免大量数据查询',
            '使用连接池管理数据库连接',
            '定期分析查询性能',
            '使用缓存减少数据库访问',
            '优化数据库配置参数',
            '定期维护数据库统计信息'
        ]
    
    @staticmethod
    def get_application_optimization_tips() -> List[str]:
        """获取应用优化建议"""
        return [
            '使用异步编程提高并发性能',
            '实现适当的缓存策略',
            '使用连接池管理外部连接',
            '优化序列化和反序列化',
            '使用压缩减少网络传输',
            '实现请求限流和熔断',
            '监控应用性能指标',
            '使用 CDN 加速静态资源',
            '优化内存使用',
            '使用负载均衡分散请求'
        ]

class SecurityBestPractices:
    """安全最佳实践"""
    
    @staticmethod
    def get_security_checklist() -> Dict[str, List[str]]:
        """获取安全检查清单"""
        return {
            'authentication': [
                '使用强密码策略',
                '实现多因素认证',
                '使用安全的会话管理',
                '实现账户锁定机制',
                '记录认证事件'
            ],
            'authorization': [
                '实现基于角色的访问控制',
                '使用最小权限原则',
                '验证所有 API 端点的权限',
                '实现资源级别的权限控制',
                '定期审查权限设置'
            ],
            'data_protection': [
                '加密敏感数据',
                '使用 HTTPS 传输数据',
                '实现数据脱敏',
                '定期备份数据',
                '实现数据删除策略'
            ],
            'input_validation': [
                '验证所有用户输入',
                '使用参数化查询防止 SQL 注入',
                '实现 CSRF 保护',
                '验证文件上传',
                '限制请求大小'
            ],
            'monitoring': [
                '记录安全事件',
                '监控异常访问模式',
                '实现入侵检测',
                '定期安全审计',
                '建立事件响应流程'
            ]
        }

class DeploymentBestPractices:
    """部署最佳实践"""
    
    @staticmethod
    def get_deployment_checklist() -> List[str]:
        """获取部署检查清单"""
        return [
            '使用环境变量管理配置',
            '实现健康检查端点',
            '配置适当的日志级别',
            '设置监控和告警',
            '实现优雅关闭',
            '使用容器化部署',
            '配置负载均衡',
            '实现自动扩缩容',
            '设置备份策略',
            '准备回滚计划',
            '进行性能测试',
            '配置安全策略',
            '文档化部署流程',
            '培训运维团队'
        ]
    
    @staticmethod
    def get_monitoring_setup() -> Dict[str, Any]:
        """获取监控设置"""
        return {
            'application_metrics': [
                '请求响应时间',
                '请求成功率',
                '并发用户数',
                '错误率',
                '内存使用率',
                'CPU 使用率'
            ],
            'database_metrics': [
                '查询响应时间',
                '连接池使用率',
                '慢查询数量',
                '锁等待时间',
                '数据库大小',
                '索引使用率'
            ],
            'business_metrics': [
                '用户注册数',
                '活跃用户数',
                '业务转化率',
                '收入指标',
                '用户满意度',
                '功能使用率'
            ],
            'alerts': [
                '服务不可用',
                '响应时间过长',
                '错误率过高',
                '资源使用率过高',
                '数据库连接失败',
                '磁盘空间不足'
            ]
        }

# 使用示例
def best_practices_example():
    """最佳实践使用示例"""
    # 获取项目结构建议
    structure = ProjectStructureBestPractices.get_recommended_structure()
    print("推荐的项目结构:")
    print(structure)
    
    # 获取编码标准
    standards = ProjectStructureBestPractices.get_coding_standards()
    print("\n编码标准:")
    for category, rules in standards.items():
        print(f"\n{category}:")
        for rule in rules:
            print(f"  - {rule}")
    
    # 获取性能优化建议
    db_tips = PerformanceOptimizationBestPractices.get_database_optimization_tips()
    print("\n数据库优化建议:")
    for tip in db_tips:
        print(f"  - {tip}")
    
    # 获取安全检查清单
    security_checklist = SecurityBestPractices.get_security_checklist()
    print("\n安全检查清单:")
    for category, items in security_checklist.items():
        print(f"\n{category}:")
        for item in items:
            print(f"  - {item}")
    
    # 获取部署检查清单
    deployment_checklist = DeploymentBestPractices.get_deployment_checklist()
    print("\n部署检查清单:")
    for item in deployment_checklist:
        print(f"  - {item}")
```

### 7.2 错误处理最佳实践

```python
from typing import Optional, Dict, Any
from enum import Enum
import logging
import traceback
from datetime import datetime

class ErrorSeverity(str, Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """错误分类"""
    VALIDATION = "validation"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"

class CustomException(Exception):
    """自定义异常基类"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.now()
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'error_code': self.error_code,
            'message': self.message,
            'category': self.category.value,
            'severity': self.severity.value,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }

class ValidationError(CustomException):
    """验证错误"""
    
    def __init__(self, message: str, field: str = None, value: Any = None):
        details = {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        
        super().__init__(
            message=message,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=details
        )

class DatabaseError(CustomException):
    """数据库错误"""
    
    def __init__(self, message: str, operation: str = None, table: str = None):
        details = {}
        if operation:
            details['operation'] = operation
        if table:
            details['table'] = table
        
        super().__init__(
            message=message,
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details
        )

class BusinessLogicError(CustomException):
    """业务逻辑错误"""
    
    def __init__(self, message: str, business_rule: str = None):
        details = {}
        if business_rule:
            details['business_rule'] = business_rule
        
        super().__init__(
            message=message,
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details=details
        )

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def handle_exception(self, exc: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理异常"""
        context = context or {}
        
        if isinstance(exc, CustomException):
            return self._handle_custom_exception(exc, context)
        else:
            return self._handle_generic_exception(exc, context)
    
    def _handle_custom_exception(self, exc: CustomException, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理自定义异常"""
        error_data = exc.to_dict()
        error_data['context'] = context
        
        # 根据严重程度选择日志级别
        if exc.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(f"Critical error: {exc.message}", extra=error_data)
        elif exc.severity == ErrorSeverity.HIGH:
            self.logger.error(f"High severity error: {exc.message}", extra=error_data)
        elif exc.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(f"Medium severity error: {exc.message}", extra=error_data)
        else:
            self.logger.info(f"Low severity error: {exc.message}", extra=error_data)
        
        return error_data
    
    def _handle_generic_exception(self, exc: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理通用异常"""
        error_data = {
            'error_code': exc.__class__.__name__,
            'message': str(exc),
            'category': ErrorCategory.SYSTEM.value,
            'severity': ErrorSeverity.HIGH.value,
            'details': {
                'traceback': traceback.format_exc()
            },
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        self.logger.error(f"Unhandled exception: {str(exc)}", extra=error_data)
        
        return error_data
    
    def create_error_response(self, error_data: Dict[str, Any], include_details: bool = False) -> Dict[str, Any]:
        """创建错误响应"""
        response = {
            'error': {
                'code': error_data['error_code'],
                'message': error_data['message'],
                'timestamp': error_data['timestamp']
            }
        }
        
        if include_details:
            response['error']['details'] = error_data.get('details', {})
            response['error']['category'] = error_data.get('category')
            response['error']['severity'] = error_data.get('severity')
        
        return response

# 装饰器用于自动错误处理
def handle_errors(include_details: bool = False):
    """错误处理装饰器"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                error_data = error_handler.handle_exception(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                return error_handler.create_error_response(error_data, include_details)
        
        def sync_wrapper(*args, **kwargs):
            error_handler = ErrorHandler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_data = error_handler.handle_exception(e, {
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                return error_handler.create_error_response(error_data, include_details)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# 使用示例
class UserServiceWithErrorHandling:
    """带错误处理的用户服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.error_handler = ErrorHandler()
    
    @handle_errors(include_details=True)
    async def create_user(self, user_data: Dict[str, Any]) -> UserExtended:
        """创建用户"""
        # 验证输入
        if not user_data.get('username'):
            raise ValidationError("用户名不能为空", field="username")
        
        if not user_data.get('email'):
            raise ValidationError("邮箱不能为空", field="email")
        
        # 检查用户名是否已存在
        existing_user = await self.session.execute(
            select(UserExtended).where(UserExtended.username == user_data['username'])
        )
        
        if existing_user.scalar_one_or_none():
            raise BusinessLogicError(
                "用户名已存在",
                business_rule="unique_username"
            )
        
        try:
            user = UserExtended(**user_data)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            return user
        
        except Exception as e:
            await self.session.rollback()
            raise DatabaseError(
                "创建用户失败",
                operation="insert",
                table="users"
            ) from e
    
    @handle_errors()
    async def get_user(self, user_id: int) -> Optional[UserExtended]:
        """获取用户"""
        if user_id <= 0:
            raise ValidationError("用户ID必须大于0", field="user_id", value=user_id)
        
        try:
            user = await self.session.get(UserExtended, user_id)
            return user
        
        except Exception as e:
            raise DatabaseError(
                 "获取用户失败",
                 operation="select",
                 table="users"
             ) from e
```

## 8. 本章总结

### 8.1 核心概念回顾

本章深入探讨了 SQLModel 的高级特性和扩展功能，主要包括：

1. **自定义字段类型**
   - 创建符合业务需求的字段类型
   - 实现数据验证和转换逻辑
   - 支持复杂数据结构的存储

2. **高级查询技术**
   - 动态查询构建器
   - 复杂的过滤和聚合操作
   - 子查询和 CTE 支持

3. **插件系统**
   - 可扩展的架构设计
   - 插件生命周期管理
   - 中间件集成

4. **框架集成**
   - FastAPI 深度集成
   - Celery 异步任务处理
   - 第三方服务集成

5. **数据迁移工具**
   - 自动化迁移管理
   - 版本控制和回滚
   - 迁移脚本生成

6. **测试工具**
   - 测试数据库管理
   - 测试数据工厂
   - 性能测试支持

### 8.2 最佳实践总结

#### 代码组织
- 采用清晰的项目结构
- 遵循编码标准和命名约定
- 实现适当的分层架构
- 使用依赖注入和控制反转

#### 性能优化
- 数据库查询优化
- 缓存策略实施
- 异步编程应用
- 资源使用监控

#### 安全考虑
- 输入验证和清理
- 权限控制和认证
- 数据加密和保护
- 安全事件监控

#### 错误处理
- 统一的异常处理机制
- 详细的错误分类和记录
- 优雅的错误恢复
- 用户友好的错误信息

### 8.3 常见陷阱与避免方法

#### 性能陷阱
1. **N+1 查询问题**
   - 陷阱：在循环中执行查询
   - 避免：使用 eager loading 或批量查询

2. **过度复杂的查询**
   - 陷阱：在单个查询中包含过多逻辑
   - 避免：分解为多个简单查询或使用视图

3. **缺乏索引**
   - 陷阱：忽略数据库索引优化
   - 避免：定期分析查询性能并添加必要索引

#### 架构陷阱
1. **紧耦合设计**
   - 陷阱：组件之间过度依赖
   - 避免：使用接口和依赖注入

2. **缺乏抽象层**
   - 陷阱：业务逻辑直接操作数据库
   - 避免：实现服务层和仓储模式

3. **忽略错误处理**
   - 陷阱：不处理或错误处理异常
   - 避免：实现统一的错误处理机制

#### 安全陷阱
1. **SQL 注入**
   - 陷阱：直接拼接 SQL 语句
   - 避免：使用参数化查询

2. **敏感数据泄露**
   - 陷阱：在日志中记录敏感信息
   - 避免：实现数据脱敏和安全日志

3. **权限控制缺失**
   - 陷阱：缺乏适当的访问控制
   - 避免：实现基于角色的权限系统

### 8.4 实践检查清单

#### 开发阶段
- [ ] 设计清晰的数据模型
- [ ] 实现适当的验证逻辑
- [ ] 添加必要的索引
- [ ] 编写单元测试
- [ ] 实现错误处理
- [ ] 添加日志记录
- [ ] 进行代码审查

#### 测试阶段
- [ ] 功能测试覆盖
- [ ] 性能测试验证
- [ ] 安全测试检查
- [ ] 集成测试确认
- [ ] 边界条件测试
- [ ] 错误场景测试

#### 部署阶段
- [ ] 环境配置验证
- [ ] 数据库迁移执行
- [ ] 监控系统配置
- [ ] 备份策略实施
- [ ] 安全策略应用
- [ ] 性能基线建立

#### 运维阶段
- [ ] 监控指标跟踪
- [ ] 日志分析处理
- [ ] 性能优化调整
- [ ] 安全事件响应
- [ ] 备份恢复测试
- [ ] 容量规划更新

### 8.5 下一步学习

#### 深入学习方向
1. **高级数据库特性**
   - 分区表和分片
   - 全文搜索
   - 地理空间数据
   - 时间序列数据

2. **微服务架构**
   - 服务拆分策略
   - 分布式事务
   - 服务发现和注册
   - API 网关设计

3. **云原生技术**
   - 容器化部署
   - Kubernetes 编排
   - 服务网格
   - 无服务器架构

4. **数据工程**
   - 数据管道构建
   - 实时数据处理
   - 数据湖和数据仓库
   - 机器学习集成

#### 推荐资源
1. **官方文档**
   - SQLModel 官方文档
   - SQLAlchemy 高级特性
   - FastAPI 最佳实践
   - Pydantic 深入指南

2. **开源项目**
   - 研究优秀的开源项目
   - 参与社区贡献
   - 学习最佳实践

3. **技术博客和书籍**
   - 数据库设计原理
   - 微服务架构模式
   - 高性能 Python
   - 系统设计面试

### 8.6 扩展练习

#### 初级练习
1. **自定义字段类型**
   - 创建一个货币字段类型
   - 实现一个颜色字段类型
   - 设计一个评分字段类型

2. **查询构建器**
   - 扩展查询构建器支持更多操作符
   - 实现查询缓存机制
   - 添加查询性能分析

#### 中级练习
1. **插件系统**
   - 开发一个权限控制插件
   - 创建一个数据同步插件
   - 实现一个通知系统插件

2. **框架集成**
   - 集成 Redis 缓存
   - 添加 Elasticsearch 支持
   - 实现消息队列集成

#### 高级练习
1. **分布式系统**
   - 实现数据库分片
   - 设计分布式缓存
   - 构建事件驱动架构

2. **性能优化**
   - 实现查询优化器
   - 设计自适应缓存
   - 构建性能监控系统

#### 项目实战
1. **电商系统**
   - 设计商品管理系统
   - 实现订单处理流程
   - 构建推荐系统

2. **内容管理系统**
   - 设计文章发布系统
   - 实现评论和互动
   - 构建搜索功能

3. **数据分析平台**
   - 设计数据收集系统
   - 实现实时分析
   - 构建可视化界面

---

通过本章的学习，你已经掌握了 SQLModel 的高级特性和扩展功能。这些知识将帮助你构建更加强大、灵活和可维护的应用程序。记住，技术的学习是一个持续的过程，保持好奇心和实践精神，不断探索新的可能性。

在下一章中，我们将探讨 SQLModel 在实际项目中的应用案例，通过具体的项目实战来巩固和应用所学知识。