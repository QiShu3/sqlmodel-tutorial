# 第6章：数据验证与约束

## 本章概述

数据验证是确保数据质量和应用程序稳定性的关键环节。SQLModel 结合了 Pydantic 的强大验证功能和 SQLAlchemy 的数据库约束，为开发者提供了多层次的数据验证机制。本章将深入探讨如何在 SQLModel 中实现全面的数据验证和约束。

### 学习目标

- 掌握 SQLModel 的内置验证机制
- 学习自定义验证器的实现
- 理解数据库级约束的配置
- 实现复杂的业务逻辑验证
- 掌握验证错误的处理和用户友好的错误消息
- 学习性能优化的验证策略

### 前置知识

- 完成前5章的学习
- 熟悉 Python 类型注解
- 了解正则表达式基础
- 理解数据库约束概念

---

## 1. 验证基础概念

### 1.1 验证层次结构

```python
# validation_layers.py
from sqlmodel import SQLModel, Field, Session, create_engine, select
from pydantic import validator, root_validator, ValidationError
from sqlalchemy import CheckConstraint, UniqueConstraint, Index
from typing import Optional, List, Union
from datetime import datetime, date
from decimal import Decimal
import re

# 验证层次示例
class ValidationLayers:
    """
    SQLModel 数据验证的三个层次：
    1. 类型验证（Type Validation）- 自动进行
    2. 字段验证（Field Validation）- Pydantic 验证器
    3. 数据库约束（Database Constraints）- SQLAlchemy 约束
    """
    
    @staticmethod
    def demonstrate_validation_flow():
        """演示验证流程"""
        print("验证流程：")
        print("1. 类型检查 -> 2. 字段验证 -> 3. 数据库约束")
        print("4. 业务逻辑验证 -> 5. 持久化")

class User(SQLModel, table=True):
    """用户模型 - 展示多层验证"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 1. 类型验证 + 字段约束
    username: str = Field(
        min_length=3,
        max_length=50,
        regex=r'^[a-zA-Z0-9_]+$',
        description="用户名：3-50字符，只能包含字母、数字和下划线"
    )
    
    email: str = Field(
        max_length=255,
        regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
        description="有效的邮箱地址"
    )
    
    age: Optional[int] = Field(
        default=None,
        ge=0,  # 大于等于0
        le=150,  # 小于等于150
        description="年龄：0-150岁"
    )
    
    salary: Optional[Decimal] = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
        description="薪资：非负数，最多10位数字，2位小数"
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # 2. 自定义验证器
    @validator('username')
    def validate_username(cls, v):
        """用户名自定义验证"""
        if v.lower() in ['admin', 'root', 'system']:
            raise ValueError('用户名不能使用保留字')
        return v
    
    @validator('email')
    def validate_email_domain(cls, v):
        """邮箱域名验证"""
        blocked_domains = ['tempmail.com', '10minutemail.com']
        domain = v.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValueError(f'不允许使用 {domain} 域名')
        return v.lower()
    
    @validator('age')
    def validate_age_logic(cls, v):
        """年龄逻辑验证"""
        if v is not None and v < 13:
            raise ValueError('用户年龄不能小于13岁')
        return v
    
    # 3. 根验证器（跨字段验证）
    @root_validator
    def validate_user_consistency(cls, values):
        """用户数据一致性验证"""
        age = values.get('age')
        salary = values.get('salary')
        
        # 未成年人不能有薪资记录
        if age is not None and age < 18 and salary is not None:
            raise ValueError('未成年用户不能设置薪资信息')
        
        return values
    
    # 4. 数据库约束
    __table_args__ = (
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('email', name='uq_user_email'),
        CheckConstraint('age >= 0 AND age <= 150', name='ck_user_age_range'),
        CheckConstraint('salary >= 0', name='ck_user_salary_positive'),
        Index('idx_user_username', 'username'),
        Index('idx_user_email', 'email'),
        Index('idx_user_active_created', 'is_active', 'created_at'),
    )
```

### 1.2 验证错误处理

```python
# validation_error_handling.py
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from typing import Dict, List, Any
import json

class ValidationErrorHandler:
    """验证错误处理器"""
    
    @staticmethod
    def handle_pydantic_error(error: ValidationError) -> Dict[str, Any]:
        """处理 Pydantic 验证错误"""
        errors = []
        for err in error.errors():
            field_path = ' -> '.join(str(loc) for loc in err['loc'])
            errors.append({
                'field': field_path,
                'message': err['msg'],
                'type': err['type'],
                'input': err.get('input')
            })
        
        return {
            'error_type': 'validation_error',
            'message': '数据验证失败',
            'errors': errors,
            'error_count': len(errors)
        }
    
    @staticmethod
    def handle_integrity_error(error: IntegrityError) -> Dict[str, Any]:
        """处理数据库完整性错误"""
        error_msg = str(error.orig)
        
        # 解析常见的完整性错误
        if 'UNIQUE constraint failed' in error_msg:
            field = error_msg.split('.')[-1] if '.' in error_msg else 'unknown'
            return {
                'error_type': 'unique_constraint_error',
                'message': f'字段 {field} 的值已存在',
                'field': field
            }
        elif 'CHECK constraint failed' in error_msg:
            return {
                'error_type': 'check_constraint_error',
                'message': '数据不满足约束条件',
                'details': error_msg
            }
        elif 'NOT NULL constraint failed' in error_msg:
            field = error_msg.split('.')[-1] if '.' in error_msg else 'unknown'
            return {
                'error_type': 'not_null_error',
                'message': f'字段 {field} 不能为空',
                'field': field
            }
        
        return {
            'error_type': 'database_error',
            'message': '数据库操作失败',
            'details': error_msg
        }
    
    @staticmethod
    def create_user_friendly_message(error_info: Dict[str, Any]) -> str:
        """创建用户友好的错误消息"""
        error_type = error_info.get('error_type')
        
        if error_type == 'validation_error':
            messages = []
            for err in error_info.get('errors', []):
                field = err['field']
                msg = err['message']
                messages.append(f"{field}: {msg}")
            return "输入数据有误：" + "; ".join(messages)
        
        elif error_type == 'unique_constraint_error':
            field = error_info.get('field', '该字段')
            return f"{field} 已被使用，请选择其他值"
        
        elif error_type == 'check_constraint_error':
            return "输入的数据不符合要求，请检查后重试"
        
        elif error_type == 'not_null_error':
            field = error_info.get('field', '必填字段')
            return f"{field} 是必填项，不能为空"
        
        return "操作失败，请稍后重试"

# 使用示例
def demonstrate_error_handling():
    """演示错误处理"""
    handler = ValidationErrorHandler()
    
    # 模拟验证错误
    try:
        # 这会触发验证错误
        user = User(
            username="ad",  # 太短
            email="invalid-email",  # 无效邮箱
            age=-5  # 负数年龄
        )
    except ValidationError as e:
        error_info = handler.handle_pydantic_error(e)
        friendly_msg = handler.create_user_friendly_message(error_info)
        print(f"友好错误消息: {friendly_msg}")
        print(f"详细错误信息: {json.dumps(error_info, indent=2, ensure_ascii=False)}")
```

---

## 2. 内置验证器详解

### 2.1 数值验证

```python
# numeric_validation.py
from sqlmodel import SQLModel, Field
from decimal import Decimal
from typing import Optional
from pydantic import validator, condecimal, conint, confloat

class Product(SQLModel, table=True):
    """商品模型 - 数值验证示例"""
    __tablename__ = "products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基础数值约束
    price: Decimal = Field(
        ge=0.01,  # 大于等于0.01
        le=999999.99,  # 小于等于999999.99
        max_digits=8,  # 最多8位数字
        decimal_places=2,  # 2位小数
        description="商品价格"
    )
    
    # 整数约束
    stock_quantity: int = Field(
        ge=0,  # 非负整数
        description="库存数量"
    )
    
    # 浮点数约束
    weight: Optional[float] = Field(
        default=None,
        gt=0,  # 大于0
        le=1000.0,  # 小于等于1000
        description="商品重量（千克）"
    )
    
    # 百分比（0-100）
    discount_rate: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="折扣率（百分比）"
    )
    
    # 评分（1-5星）
    rating: Optional[float] = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="商品评分（1-5星）"
    )
    
    # 使用 Pydantic 的约束类型
    tax_rate: condecimal(ge=0, le=1, decimal_places=4) = Field(
        default=Decimal('0.0000'),
        description="税率（0-1之间，4位小数）"
    )
    
    # 自定义数值验证
    @validator('price')
    def validate_price_precision(cls, v):
        """验证价格精度"""
        if v is not None:
            # 确保价格是0.01的倍数
            cents = int(v * 100)
            if cents != v * 100:
                raise ValueError('价格必须精确到分（0.01）')
        return v
    
    @validator('discount_rate')
    def validate_discount_logic(cls, v):
        """验证折扣逻辑"""
        if v is not None and v > 0:
            # 折扣率必须是5的倍数
            if v % 5 != 0:
                raise ValueError('折扣率必须是5的倍数')
        return v
    
    @validator('rating')
    def validate_rating_precision(cls, v):
        """验证评分精度"""
        if v is not None:
            # 评分只能是0.5的倍数
            if (v * 2) % 1 != 0:
                raise ValueError('评分必须是0.5的倍数')
        return v

class NumericValidationExamples:
    """数值验证示例"""
    
    @staticmethod
    def create_valid_product() -> Product:
        """创建有效商品"""
        return Product(
            price=Decimal('99.99'),
            stock_quantity=100,
            weight=2.5,
            discount_rate=10.0,
            rating=4.5,
            tax_rate=Decimal('0.0875')
        )
    
    @staticmethod
    def demonstrate_validation_errors():
        """演示验证错误"""
        test_cases = [
            {
                'name': '负价格',
                'data': {'price': Decimal('-10.00')},
                'expected_error': 'ensure this value is greater than or equal to 0.01'
            },
            {
                'name': '价格精度错误',
                'data': {'price': Decimal('10.001')},
                'expected_error': '价格必须精确到分'
            },
            {
                'name': '无效折扣率',
                'data': {'price': Decimal('10.00'), 'discount_rate': 7.0},
                'expected_error': '折扣率必须是5的倍数'
            },
            {
                'name': '无效评分',
                'data': {'price': Decimal('10.00'), 'rating': 3.3},
                'expected_error': '评分必须是0.5的倍数'
            }
        ]
        
        for case in test_cases:
            try:
                Product(**case['data'])
                print(f"❌ {case['name']}: 应该失败但成功了")
            except ValidationError as e:
                print(f"✅ {case['name']}: {e.errors()[0]['msg']}")
```

### 2.2 字符串验证

```python
# string_validation.py
from sqlmodel import SQLModel, Field
from pydantic import validator, constr
from typing import Optional
import re

class UserProfile(SQLModel, table=True):
    """用户资料模型 - 字符串验证示例"""
    __tablename__ = "user_profiles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基础字符串约束
    first_name: str = Field(
        min_length=1,
        max_length=50,
        regex=r'^[a-zA-Z\u4e00-\u9fff\s]+$',  # 支持中英文和空格
        description="名字"
    )
    
    last_name: str = Field(
        min_length=1,
        max_length=50,
        regex=r'^[a-zA-Z\u4e00-\u9fff\s]+$',
        description="姓氏"
    )
    
    # 手机号验证
    phone: Optional[str] = Field(
        default=None,
        regex=r'^1[3-9]\d{9}$',  # 中国手机号格式
        description="手机号码"
    )
    
    # 身份证号验证
    id_card: Optional[str] = Field(
        default=None,
        regex=r'^[1-9]\d{5}(18|19|20)\d{2}((0[1-9])|(1[0-2]))(([0-2][1-9])|10|20|30|31)\d{3}[0-9Xx]$',
        description="身份证号码"
    )
    
    # 使用 constr 约束
    bio: Optional[constr(max_length=500, strip_whitespace=True)] = Field(
        default=None,
        description="个人简介"
    )
    
    # 网址验证
    website: Optional[str] = Field(
        default=None,
        regex=r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$',
        description="个人网站"
    )
    
    # 社交媒体用户名
    twitter_handle: Optional[str] = Field(
        default=None,
        regex=r'^@?[A-Za-z0-9_]{1,15}$',
        description="Twitter用户名"
    )
    
    # 自定义字符串验证
    @validator('first_name', 'last_name')
    def validate_name_content(cls, v):
        """验证姓名内容"""
        if v:
            # 移除多余空格
            v = ' '.join(v.split())
            
            # 检查是否包含数字
            if re.search(r'\d', v):
                raise ValueError('姓名不能包含数字')
            
            # 检查是否包含特殊字符（除了空格）
            if re.search(r'[^a-zA-Z\u4e00-\u9fff\s]', v):
                raise ValueError('姓名只能包含字母、汉字和空格')
        
        return v
    
    @validator('phone')
    def validate_phone_format(cls, v):
        """验证手机号格式"""
        if v:
            # 移除所有非数字字符
            digits_only = re.sub(r'\D', '', v)
            
            # 检查长度
            if len(digits_only) != 11:
                raise ValueError('手机号必须是11位数字')
            
            # 检查运营商前缀
            valid_prefixes = ['13', '14', '15', '16', '17', '18', '19']
            if digits_only[:2] not in valid_prefixes:
                raise ValueError('无效的手机号前缀')
            
            return digits_only
        return v
    
    @validator('id_card')
    def validate_id_card_checksum(cls, v):
        """验证身份证校验位"""
        if v:
            v = v.upper()
            if len(v) != 18:
                raise ValueError('身份证号必须是18位')
            
            # 计算校验位
            weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
            check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']
            
            sum_val = sum(int(v[i]) * weights[i] for i in range(17))
            check_code = check_codes[sum_val % 11]
            
            if v[17] != check_code:
                raise ValueError('身份证号校验位错误')
        
        return v
    
    @validator('bio')
    def validate_bio_content(cls, v):
        """验证个人简介内容"""
        if v:
            # 检查敏感词
            sensitive_words = ['spam', 'advertisement', '广告']
            v_lower = v.lower()
            for word in sensitive_words:
                if word in v_lower:
                    raise ValueError(f'个人简介不能包含敏感词: {word}')
            
            # 检查URL（简介中不允许链接）
            url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
            if re.search(url_pattern, v):
                raise ValueError('个人简介中不能包含链接')
        
        return v
    
    @validator('twitter_handle')
    def validate_twitter_handle(cls, v):
        """验证Twitter用户名"""
        if v:
            # 移除@符号
            if v.startswith('@'):
                v = v[1:]
            
            # 检查保留用户名
            reserved_names = ['admin', 'twitter', 'support', 'api']
            if v.lower() in reserved_names:
                raise ValueError('不能使用保留的用户名')
        
        return v

class StringValidationUtils:
    """字符串验证工具类"""
    
    @staticmethod
    def validate_chinese_name(name: str) -> bool:
        """验证中文姓名"""
        pattern = r'^[\u4e00-\u9fff]{2,4}$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_english_name(name: str) -> bool:
        """验证英文姓名"""
        pattern = r'^[A-Za-z\s]{2,50}$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def clean_phone_number(phone: str) -> str:
        """清理手机号格式"""
        return re.sub(r'\D', '', phone)
    
    @staticmethod
    def mask_sensitive_info(text: str, info_type: str) -> str:
        """遮蔽敏感信息"""
        if info_type == 'phone':
            return re.sub(r'(\d{3})\d{4}(\d{4})', r'\1****\2', text)
        elif info_type == 'id_card':
            return re.sub(r'(\d{6})\d{8}(\d{4})', r'\1********\2', text)
        elif info_type == 'email':
            return re.sub(r'(.{1,3}).*(@.*)', r'\1***\2', text)
        return text
```

### 2.3 日期时间验证

```python
# datetime_validation.py
from sqlmodel import SQLModel, Field
from pydantic import validator
from datetime import datetime, date, time, timedelta
from typing import Optional

class Event(SQLModel, table=True):
    """事件模型 - 日期时间验证示例"""
    __tablename__ = "events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    title: str = Field(max_length=200)
    
    # 日期验证
    event_date: date = Field(description="事件日期")
    
    # 时间验证
    start_time: time = Field(description="开始时间")
    end_time: time = Field(description="结束时间")
    
    # 日期时间验证
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 可选的截止日期
    deadline: Optional[datetime] = Field(default=None, description="截止时间")
    
    # 持续时间（分钟）
    duration_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        le=1440,  # 最多24小时
        description="持续时间（分钟）"
    )
    
    @validator('event_date')
    def validate_event_date(cls, v):
        """验证事件日期"""
        if v < date.today():
            raise ValueError('事件日期不能是过去的日期')
        
        # 不能超过一年后
        max_date = date.today() + timedelta(days=365)
        if v > max_date:
            raise ValueError('事件日期不能超过一年后')
        
        return v
    
    @validator('end_time')
    def validate_end_time(cls, v, values):
        """验证结束时间"""
        start_time = values.get('start_time')
        if start_time and v <= start_time:
            raise ValueError('结束时间必须晚于开始时间')
        return v
    
    @validator('deadline')
    def validate_deadline(cls, v, values):
        """验证截止时间"""
        if v:
            # 截止时间不能是过去
            if v < datetime.utcnow():
                raise ValueError('截止时间不能是过去的时间')
            
            # 截止时间应该在事件日期之前或当天
            event_date = values.get('event_date')
            if event_date:
                event_datetime = datetime.combine(event_date, time.min)
                if v > event_datetime + timedelta(days=1):
                    raise ValueError('截止时间不能晚于事件日期')
        
        return v
    
    @validator('duration_minutes')
    def validate_duration(cls, v, values):
        """验证持续时间"""
        if v:
            start_time = values.get('start_time')
            end_time = values.get('end_time')
            
            if start_time and end_time:
                # 计算实际时间差
                start_minutes = start_time.hour * 60 + start_time.minute
                end_minutes = end_time.hour * 60 + end_time.minute
                
                if end_minutes < start_minutes:
                    # 跨天的情况
                    actual_duration = (24 * 60) - start_minutes + end_minutes
                else:
                    actual_duration = end_minutes - start_minutes
                
                if abs(v - actual_duration) > 5:  # 允许5分钟误差
                    raise ValueError(f'持续时间与开始结束时间不匹配，实际时长: {actual_duration}分钟')
        
        return v

class DateTimeValidationUtils:
    """日期时间验证工具类"""
    
    @staticmethod
    def is_business_day(date_obj: date) -> bool:
        """检查是否为工作日"""
        return date_obj.weekday() < 5
    
    @staticmethod
    def is_business_hours(time_obj: time) -> bool:
        """检查是否为工作时间（9:00-18:00）"""
        return time(9, 0) <= time_obj <= time(18, 0)
    
    @staticmethod
    def get_next_business_day(date_obj: date) -> date:
        """获取下一个工作日"""
        next_day = date_obj + timedelta(days=1)
        while not DateTimeValidationUtils.is_business_day(next_day):
            next_day += timedelta(days=1)
        return next_day
    
    @staticmethod
    def validate_age_from_birthdate(birthdate: date, min_age: int = 0, max_age: int = 150) -> bool:
        """根据出生日期验证年龄"""
        today = date.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
        return min_age <= age <= max_age
    
    @staticmethod
    def format_duration(minutes: int) -> str:
        """格式化持续时间"""
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{hours}小时{mins}分钟" if mins > 0 else f"{hours}小时"
        return f"{mins}分钟"

class BusinessEvent(SQLModel, table=True):
    """商务事件模型 - 业务时间验证"""
    __tablename__ = "business_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    event_date: date
    start_time: time
    end_time: time
    
    @validator('event_date')
    def validate_business_date(cls, v):
        """验证商务日期（只能是工作日）"""
        if not DateTimeValidationUtils.is_business_day(v):
            raise ValueError('商务事件只能安排在工作日')
        return v
    
    @validator('start_time', 'end_time')
    def validate_business_time(cls, v):
        """验证商务时间（只能在工作时间）"""
        if not DateTimeValidationUtils.is_business_hours(v):
            raise ValueError('商务事件只能安排在工作时间（9:00-18:00）')
        return v
```

---

## 3. 自定义验证器

### 3.1 字段级验证器

```python
# custom_field_validators.py
from sqlmodel import SQLModel, Field
from pydantic import validator
from typing import Optional, List
import hashlib
import re
from datetime import datetime

class Account(SQLModel, table=True):
    """账户模型 - 自定义字段验证器示例"""
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    username: str = Field(min_length=3, max_length=30)
    password_hash: str = Field(description="密码哈希")
    email: str = Field(max_length=255)
    
    # 银行卡号
    bank_card: Optional[str] = Field(default=None, max_length=19)
    
    # 信用卡号
    credit_card: Optional[str] = Field(default=None, max_length=19)
    
    # 社会保险号
    ssn: Optional[str] = Field(default=None, max_length=11)
    
    # IP地址
    last_login_ip: Optional[str] = Field(default=None, max_length=45)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('username')
    def validate_username_rules(cls, v):
        """用户名验证规则"""
        # 只能包含字母、数字、下划线
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        
        # 必须以字母开头
        if not v[0].isalpha():
            raise ValueError('用户名必须以字母开头')
        
        # 不能全是数字
        if v.isdigit():
            raise ValueError('用户名不能全是数字')
        
        # 检查保留词
        reserved_words = [
            'admin', 'administrator', 'root', 'system', 'user',
            'test', 'guest', 'anonymous', 'null', 'undefined'
        ]
        if v.lower() in reserved_words:
            raise ValueError(f'用户名不能使用保留词: {v}')
        
        return v.lower()
    
    @validator('password_hash')
    def validate_password_hash(cls, v):
        """密码哈希验证"""
        # 检查是否为有效的哈希格式（这里假设使用SHA-256）
        if len(v) != 64 or not re.match(r'^[a-fA-F0-9]+$', v):
            raise ValueError('无效的密码哈希格式')
        return v.lower()
    
    @validator('email')
    def validate_email_advanced(cls, v):
        """高级邮箱验证"""
        # 基础格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式无效')
        
        # 分离用户名和域名
        local_part, domain = v.rsplit('@', 1)
        
        # 验证本地部分
        if len(local_part) > 64:
            raise ValueError('邮箱用户名部分不能超过64个字符')
        
        if local_part.startswith('.') or local_part.endswith('.'):
            raise ValueError('邮箱用户名不能以点号开始或结束')
        
        if '..' in local_part:
            raise ValueError('邮箱用户名不能包含连续的点号')
        
        # 验证域名部分
        if len(domain) > 253:
            raise ValueError('邮箱域名部分不能超过253个字符')
        
        # 检查一次性邮箱域名
        disposable_domains = [
            '10minutemail.com', 'tempmail.org', 'guerrillamail.com',
            'mailinator.com', 'yopmail.com'
        ]
        if domain.lower() in disposable_domains:
            raise ValueError('不允许使用一次性邮箱')
        
        return v.lower()
    
    @validator('bank_card')
    def validate_bank_card(cls, v):
        """银行卡号验证（Luhn算法）"""
        if v:
            # 移除空格和连字符
            card_number = re.sub(r'[\s-]', '', v)
            
            # 检查是否全为数字
            if not card_number.isdigit():
                raise ValueError('银行卡号只能包含数字')
            
            # 检查长度
            if len(card_number) < 13 or len(card_number) > 19:
                raise ValueError('银行卡号长度必须在13-19位之间')
            
            # Luhn算法验证
            def luhn_check(card_num):
                def digits_of(n):
                    return [int(d) for d in str(n)]
                
                digits = digits_of(card_num)
                odd_digits = digits[-1::-2]
                even_digits = digits[-2::-2]
                checksum = sum(odd_digits)
                for d in even_digits:
                    checksum += sum(digits_of(d * 2))
                return checksum % 10 == 0
            
            if not luhn_check(card_number):
                raise ValueError('银行卡号校验失败')
            
            return card_number
        return v
    
    @validator('credit_card')
    def validate_credit_card(cls, v):
        """信用卡号验证"""
        if v:
            # 移除空格和连字符
            card_number = re.sub(r'[\s-]', '', v)
            
            # 检查是否全为数字
            if not card_number.isdigit():
                raise ValueError('信用卡号只能包含数字')
            
            # 检查卡类型和长度
            card_patterns = {
                'Visa': (r'^4[0-9]{12}(?:[0-9]{3})?$', [13, 16]),
                'MasterCard': (r'^5[1-5][0-9]{14}$', [16]),
                'American Express': (r'^3[47][0-9]{13}$', [15]),
                'Discover': (r'^6(?:011|5[0-9]{2})[0-9]{12}$', [16]),
                'UnionPay': (r'^62[0-9]{14,17}$', [16, 17, 18, 19])
            }
            
            card_type = None
            for card_name, (pattern, lengths) in card_patterns.items():
                if re.match(pattern, card_number) and len(card_number) in lengths:
                    card_type = card_name
                    break
            
            if not card_type:
                raise ValueError('无效的信用卡号格式')
            
            return card_number
        return v
    
    @validator('ssn')
    def validate_ssn(cls, v):
        """社会保险号验证（美国SSN格式）"""
        if v:
            # 移除连字符
            ssn = re.sub(r'-', '', v)
            
            # 检查格式
            if not re.match(r'^\d{9}$', ssn):
                raise ValueError('SSN必须是9位数字')
            
            # 检查无效的SSN
            invalid_ssns = [
                '000000000', '111111111', '222222222', '333333333',
                '444444444', '555555555', '666666666', '777777777',
                '888888888', '999999999'
            ]
            
            if ssn in invalid_ssns:
                raise ValueError('无效的SSN号码')
            
            # 检查区域号（前3位）
            area_number = ssn[:3]
            if area_number in ['000', '666'] or area_number.startswith('9'):
                raise ValueError('无效的SSN区域号')
            
            # 检查组号（中间2位）
            group_number = ssn[3:5]
            if group_number == '00':
                raise ValueError('无效的SSN组号')
            
            # 检查序列号（后4位）
            serial_number = ssn[5:]
            if serial_number == '0000':
                raise ValueError('无效的SSN序列号')
            
            return f'{ssn[:3]}-{ssn[3:5]}-{ssn[5:]}'
        return v
    
    @validator('last_login_ip')
    def validate_ip_address(cls, v):
        """IP地址验证（支持IPv4和IPv6）"""
        if v:
            import ipaddress
            try:
                ip = ipaddress.ip_address(v)
                
                # 检查是否为私有地址
                if ip.is_private:
                    # 允许私有地址，但记录日志
                    pass
                
                # 检查是否为回环地址
                if ip.is_loopback:
                    # 在开发环境中允许
                    pass
                
                # 检查是否为保留地址
                if ip.is_reserved:
                    raise ValueError('不允许使用保留的IP地址')
                
                return str(ip)
            except ValueError:
                raise ValueError('无效的IP地址格式')
        return v

class CustomValidationUtils:
    """自定义验证工具类"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def validate_password_strength(password: str) -> List[str]:
        """验证密码强度"""
        issues = []
        
        if len(password) < 8:
            issues.append('密码长度至少8位')
        
        if not re.search(r'[a-z]', password):
            issues.append('密码必须包含小写字母')
        
        if not re.search(r'[A-Z]', password):
            issues.append('密码必须包含大写字母')
        
        if not re.search(r'\d', password):
            issues.append('密码必须包含数字')
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            issues.append('密码必须包含特殊字符')
        
        # 检查常见弱密码
        weak_passwords = [
            'password', '123456', 'qwerty', 'abc123',
            'password123', '123456789', 'welcome'
        ]
        if password.lower() in weak_passwords:
            issues.append('不能使用常见的弱密码')
        
        return issues
    
    @staticmethod
    def mask_sensitive_data(data: str, data_type: str) -> str:
        """遮蔽敏感数据"""
        if data_type == 'bank_card':
            return f"****-****-****-{data[-4:]}" if len(data) >= 4 else "****"
        elif data_type == 'ssn':
            return f"***-**-{data[-4:]}" if len(data) >= 4 else "***-**-****"
        elif data_type == 'email':
            local, domain = data.rsplit('@', 1)
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1] if len(local) > 2 else '*' * len(local)
            return f"{masked_local}@{domain}"
        return data
```

### 3.2 模型级验证器

```python
# model_level_validators.py
from sqlmodel import SQLModel, Field
from pydantic import root_validator, ValidationError
from typing import Optional, Dict, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

class Order(SQLModel, table=True):
    """订单模型 - 模型级验证器示例"""
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基础字段
    customer_id: int = Field(foreign_key="customers.id")
    order_date: date = Field(default_factory=date.today)
    
    # 金额字段
    subtotal: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    tax_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    discount_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_fee: Decimal = Field(ge=0, max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    
    # 状态字段
    status: str = Field(regex=r'^(pending|confirmed|shipped|delivered|cancelled)$')
    payment_status: str = Field(regex=r'^(pending|paid|failed|refunded)$')
    
    # 日期字段
    expected_delivery_date: Optional[date] = Field(default=None)
    actual_delivery_date: Optional[date] = Field(default=None)
    
    # 优惠相关
    coupon_code: Optional[str] = Field(default=None, max_length=50)
    discount_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    
    @root_validator
    def validate_order_amounts(cls, values):
        """验证订单金额计算"""
        subtotal = values.get('subtotal', Decimal('0'))
        tax_amount = values.get('tax_amount', Decimal('0'))
        discount_amount = values.get('discount_amount', Decimal('0'))
        shipping_fee = values.get('shipping_fee', Decimal('0'))
        total_amount = values.get('total_amount', Decimal('0'))
        
        # 计算预期总金额
        expected_total = subtotal + tax_amount + shipping_fee - discount_amount
        
        # 允许0.01的误差（由于浮点数精度问题）
        if abs(total_amount - expected_total) > Decimal('0.01'):
            raise ValueError(
                f'总金额计算错误: 期望 {expected_total}, 实际 {total_amount}'
            )
        
        return values
    
    @root_validator
    def validate_discount_logic(cls, values):
        """验证折扣逻辑"""
        subtotal = values.get('subtotal', Decimal('0'))
        discount_amount = values.get('discount_amount', Decimal('0'))
        discount_rate = values.get('discount_rate')
        coupon_code = values.get('coupon_code')
        
        # 如果有折扣金额，必须有优惠券代码或折扣率
        if discount_amount > 0:
            if not coupon_code and not discount_rate:
                raise ValueError('有折扣金额时必须提供优惠券代码或折扣率')
        
        # 如果有折扣率，验证折扣金额
        if discount_rate:
            expected_discount = subtotal * discount_rate
            if abs(discount_amount - expected_discount) > Decimal('0.01'):
                raise ValueError(
                    f'折扣金额与折扣率不匹配: 期望 {expected_discount}, 实际 {discount_amount}'
                )
        
        # 折扣金额不能超过小计
        if discount_amount > subtotal:
            raise ValueError('折扣金额不能超过商品小计')
        
        return values
    
    @root_validator
    def validate_status_consistency(cls, values):
        """验证状态一致性"""
        status = values.get('status')
        payment_status = values.get('payment_status')
        actual_delivery_date = values.get('actual_delivery_date')
        
        # 已发货的订单必须已付款
        if status in ['shipped', 'delivered'] and payment_status != 'paid':
            raise ValueError('已发货的订单必须已付款')
        
        # 已取消的订单不能已发货
        if status == 'cancelled' and payment_status == 'paid':
            # 已付款的取消订单应该是退款状态
            values['payment_status'] = 'refunded'
        
        # 已交付的订单必须有实际交付日期
        if status == 'delivered' and not actual_delivery_date:
            raise ValueError('已交付的订单必须有实际交付日期')
        
        # 未交付的订单不能有实际交付日期
        if status != 'delivered' and actual_delivery_date:
            raise ValueError('未交付的订单不能有实际交付日期')
        
        return values
    
    @root_validator
    def validate_delivery_dates(cls, values):
        """验证交付日期"""
        order_date = values.get('order_date')
        expected_delivery_date = values.get('expected_delivery_date')
        actual_delivery_date = values.get('actual_delivery_date')
        
        # 预期交付日期不能早于订单日期
        if expected_delivery_date and order_date:
            if expected_delivery_date < order_date:
                raise ValueError('预期交付日期不能早于订单日期')
            
            # 预期交付日期不能超过30天
            if expected_delivery_date > order_date + timedelta(days=30):
                raise ValueError('预期交付日期不能超过订单日期30天')
        
        # 实际交付日期不能早于订单日期
        if actual_delivery_date and order_date:
            if actual_delivery_date < order_date:
                raise ValueError('实际交付日期不能早于订单日期')
        
        # 实际交付日期不能晚于预期交付日期超过7天
        if actual_delivery_date and expected_delivery_date:
            if actual_delivery_date > expected_delivery_date + timedelta(days=7):
                raise ValueError('实际交付日期不能晚于预期交付日期超过7天')
        
        return values

class Employee(SQLModel, table=True):
    """员工模型 - 复杂业务逻辑验证"""
    __tablename__ = "employees"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 基础信息
    employee_id: str = Field(unique=True, max_length=20)
    first_name: str = Field(max_length=50)
    last_name: str = Field(max_length=50)
    birth_date: date
    hire_date: date
    
    # 职位信息
    department: str = Field(max_length=100)
    position: str = Field(max_length=100)
    level: int = Field(ge=1, le=10)  # 职级 1-10
    
    # 薪资信息
    base_salary: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    bonus_percentage: Optional[Decimal] = Field(default=None, ge=0, le=1)
    
    # 工作状态
    employment_type: str = Field(regex=r'^(full_time|part_time|contract|intern)$')
    status: str = Field(regex=r'^(active|inactive|terminated)$', default='active')
    
    # 管理关系
    manager_id: Optional[int] = Field(default=None, foreign_key="employees.id")
    
    # 离职信息
    termination_date: Optional[date] = Field(default=None)
    termination_reason: Optional[str] = Field(default=None, max_length=500)
    
    @root_validator
    def validate_employee_age(cls, values):
        """验证员工年龄"""
        birth_date = values.get('birth_date')
        hire_date = values.get('hire_date')
        employment_type = values.get('employment_type')
        
        if birth_date and hire_date:
            # 计算入职时年龄
            age_at_hire = hire_date.year - birth_date.year
            if (hire_date.month, hire_date.day) < (birth_date.month, birth_date.day):
                age_at_hire -= 1
            
            # 实习生最小年龄16岁
            if employment_type == 'intern' and age_at_hire < 16:
                raise ValueError('实习生入职时年龄不能小于16岁')
            
            # 正式员工最小年龄18岁
            if employment_type in ['full_time', 'part_time'] and age_at_hire < 18:
                raise ValueError('正式员工入职时年龄不能小于18岁')
            
            # 最大年龄65岁
            if age_at_hire > 65:
                raise ValueError('入职时年龄不能超过65岁')
        
        return values
    
    @root_validator
    def validate_salary_by_level(cls, values):
        """根据职级验证薪资"""
        level = values.get('level')
        base_salary = values.get('base_salary')
        employment_type = values.get('employment_type')
        
        if level and base_salary and employment_type == 'full_time':
            # 定义职级薪资范围
            salary_ranges = {
                1: (Decimal('3000'), Decimal('5000')),    # 初级
                2: (Decimal('4000'), Decimal('7000')),
                3: (Decimal('6000'), Decimal('10000')),
                4: (Decimal('8000'), Decimal('15000')),
                5: (Decimal('12000'), Decimal('20000')),  # 中级
                6: (Decimal('15000'), Decimal('25000')),
                7: (Decimal('20000'), Decimal('35000')),
                8: (Decimal('25000'), Decimal('45000')),  # 高级
                9: (Decimal('35000'), Decimal('60000')),
                10: (Decimal('50000'), Decimal('100000')), # 专家级
            }
            
            min_salary, max_salary = salary_ranges.get(level, (Decimal('0'), Decimal('999999')))
            
            if base_salary < min_salary or base_salary > max_salary:
                raise ValueError(
                    f'职级{level}的薪资范围应在{min_salary}-{max_salary}之间，当前薪资：{base_salary}'
                )
        
        return values
    
    @root_validator
    def validate_management_hierarchy(cls, values):
        """验证管理层级"""
        level = values.get('level')
        manager_id = values.get('manager_id')
        employee_id = values.get('id')
        
        # 职级1-3的员工必须有直接上级
        if level and level <= 3 and not manager_id:
            raise ValueError('初级员工必须指定直接上级')
        
        # 不能自己管理自己
        if manager_id and employee_id and manager_id == employee_id:
            raise ValueError('员工不能管理自己')
        
        # 职级10的员工不应该有上级（除非是CEO等特殊情况）
        if level == 10 and manager_id:
            # 这里可以添加特殊逻辑，比如检查是否为CEO
            pass
        
        return values
    
    @root_validator
    def validate_termination_info(cls, values):
        """验证离职信息"""
        status = values.get('status')
        termination_date = values.get('termination_date')
        termination_reason = values.get('termination_reason')
        hire_date = values.get('hire_date')
        
        # 已离职员工必须有离职日期和原因
        if status == 'terminated':
            if not termination_date:
                raise ValueError('已离职员工必须有离职日期')
            if not termination_reason:
                raise ValueError('已离职员工必须有离职原因')
            
            # 离职日期不能早于入职日期
            if hire_date and termination_date < hire_date:
                raise ValueError('离职日期不能早于入职日期')
            
            # 离职日期不能是未来
            if termination_date > date.today():
                raise ValueError('离职日期不能是未来日期')
        
        # 在职员工不应该有离职信息
        elif status == 'active':
            if termination_date:
                raise ValueError('在职员工不应该有离职日期')
            if termination_reason:
                raise ValueError('在职员工不应该有离职原因')
        
        return values

class ModelValidationUtils:
    """模型验证工具类"""
    
    @staticmethod
    def validate_business_rules(model_data: Dict[str, Any], rules: Dict[str, Any]) -> List[str]:
        """通用业务规则验证"""
        errors = []
        
        for rule_name, rule_config in rules.items():
            try:
                rule_type = rule_config['type']
                
                if rule_type == 'required_if':
                    # 条件必填验证
                    condition_field = rule_config['condition_field']
                    condition_value = rule_config['condition_value']
                    required_field = rule_config['required_field']
                    
                    if (model_data.get(condition_field) == condition_value and 
                        not model_data.get(required_field)):
                        errors.append(f'{required_field} 在 {condition_field}={condition_value} 时为必填项')
                
                elif rule_type == 'mutually_exclusive':
                    # 互斥字段验证
                    fields = rule_config['fields']
                    filled_fields = [f for f in fields if model_data.get(f)]
                    
                    if len(filled_fields) > 1:
                        errors.append(f'字段 {fields} 不能同时填写')
                
                elif rule_type == 'at_least_one':
                    # 至少一个字段必填
                    fields = rule_config['fields']
                    filled_fields = [f for f in fields if model_data.get(f)]
                    
                    if not filled_fields:
                        errors.append(f'字段 {fields} 中至少需要填写一个')
                
                elif rule_type == 'date_range':
                    # 日期范围验证
                    start_field = rule_config['start_field']
                    end_field = rule_config['end_field']
                    
                    start_date = model_data.get(start_field)
                    end_date = model_data.get(end_field)
                    
                    if start_date and end_date and start_date > end_date:
                        errors.append(f'{start_field} 不能晚于 {end_field}')
                
            except Exception as e:
                errors.append(f'规则 {rule_name} 验证失败: {str(e)}')
        
        return errors

---

## 4. 数据库约束

### 4.1 基础约束

```python
# database_constraints.py
from sqlmodel import SQLModel, Field
from sqlalchemy import CheckConstraint, UniqueConstraint, ForeignKeyConstraint, Index
from typing import Optional
from datetime import datetime
from decimal import Decimal

class Customer(SQLModel, table=True):
    """客户模型 - 数据库约束示例"""
    __tablename__ = "customers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 唯一约束
    email: str = Field(max_length=255, unique=True)
    phone: Optional[str] = Field(default=None, max_length=20)
    
    # 非空约束
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    
    # 检查约束
    age: Optional[int] = Field(default=None)
    credit_limit: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # 状态字段
    status: str = Field(max_length=20, default='active')
    
    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 数据库约束定义
    __table_args__ = (
        # 检查约束
        CheckConstraint('age >= 0 AND age <= 150', name='ck_customer_age_range'),
        CheckConstraint('credit_limit >= 0', name='ck_customer_credit_positive'),
        CheckConstraint("status IN ('active', 'inactive', 'suspended')", name='ck_customer_status'),
        
        # 唯一约束
        UniqueConstraint('email', name='uq_customer_email'),
        UniqueConstraint('phone', name='uq_customer_phone'),
        
        # 复合唯一约束
        UniqueConstraint('first_name', 'last_name', 'phone', name='uq_customer_identity'),
        
        # 索引
        Index('idx_customer_name', 'last_name', 'first_name'),
        Index('idx_customer_status_created', 'status', 'created_at'),
        Index('idx_customer_email_lower', 'email'),  # 可以添加函数索引
    )

class Invoice(SQLModel, table=True):
    """发票模型 - 外键约束示例"""
    __tablename__ = "invoices"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 外键约束
    customer_id: int = Field(foreign_key="customers.id")
    
    # 发票编号（唯一）
    invoice_number: str = Field(max_length=50, unique=True)
    
    # 金额字段
    amount: Decimal = Field(max_digits=12, decimal_places=2)
    tax_amount: Decimal = Field(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_amount: Decimal = Field(max_digits=12, decimal_places=2)
    
    # 状态和日期
    status: str = Field(max_length=20, default='draft')
    issue_date: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = Field(default=None)
    paid_date: Optional[datetime] = Field(default=None)
    
    __table_args__ = (
        # 外键约束（显式定义）
        ForeignKeyConstraint(['customer_id'], ['customers.id'], name='fk_invoice_customer'),
        
        # 检查约束
        CheckConstraint('amount > 0', name='ck_invoice_amount_positive'),
        CheckConstraint('tax_amount >= 0', name='ck_invoice_tax_non_negative'),
        CheckConstraint('total_amount > 0', name='ck_invoice_total_positive'),
        CheckConstraint('total_amount = amount + tax_amount', name='ck_invoice_total_calculation'),
        CheckConstraint("status IN ('draft', 'sent', 'paid', 'overdue', 'cancelled')", name='ck_invoice_status'),
        
        # 日期约束
        CheckConstraint('due_date >= issue_date', name='ck_invoice_due_after_issue'),
        CheckConstraint('paid_date >= issue_date', name='ck_invoice_paid_after_issue'),
        
        # 复合索引
        Index('idx_invoice_customer_status', 'customer_id', 'status'),
        Index('idx_invoice_dates', 'issue_date', 'due_date'),
        Index('idx_invoice_number', 'invoice_number'),
    )

class DatabaseConstraintExamples:
    """数据库约束示例"""
    
    @staticmethod
    def create_advanced_constraints():
        """创建高级约束示例"""
        
        class Product(SQLModel, table=True):
            """商品模型 - 高级约束"""
            __tablename__ = "products_advanced"
            
            id: Optional[int] = Field(default=None, primary_key=True)
            
            # 商品信息
            sku: str = Field(max_length=50, unique=True)
            name: str = Field(max_length=200)
            category_id: int = Field(foreign_key="categories.id")
            
            # 价格信息
            cost_price: Decimal = Field(max_digits=10, decimal_places=2)
            selling_price: Decimal = Field(max_digits=10, decimal_places=2)
            discount_price: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
            
            # 库存信息
            stock_quantity: int = Field(default=0)
            min_stock_level: int = Field(default=0)
            max_stock_level: int = Field(default=1000)
            
            # 状态
            is_active: bool = Field(default=True)
            is_featured: bool = Field(default=False)
            
            # 时间戳
            created_at: datetime = Field(default_factory=datetime.utcnow)
            
            __table_args__ = (
                # 价格约束
                CheckConstraint('cost_price > 0', name='ck_product_cost_positive'),
                CheckConstraint('selling_price > 0', name='ck_product_selling_positive'),
                CheckConstraint('selling_price >= cost_price', name='ck_product_selling_ge_cost'),
                CheckConstraint(
                    'discount_price IS NULL OR (discount_price > 0 AND discount_price < selling_price)',
                    name='ck_product_discount_valid'
                ),
                
                # 库存约束
                CheckConstraint('stock_quantity >= 0', name='ck_product_stock_non_negative'),
                CheckConstraint('min_stock_level >= 0', name='ck_product_min_stock_non_negative'),
                CheckConstraint('max_stock_level > min_stock_level', name='ck_product_max_gt_min_stock'),
                CheckConstraint('stock_quantity <= max_stock_level', name='ck_product_stock_within_max'),
                
                # 业务逻辑约束
                CheckConstraint(
                    '(is_featured = false) OR (is_featured = true AND is_active = true)',
                    name='ck_product_featured_must_be_active'
                ),
                
                # 复合唯一约束
                UniqueConstraint('name', 'category_id', name='uq_product_name_category'),
                
                # 性能索引
                Index('idx_product_category_active', 'category_id', 'is_active'),
                Index('idx_product_price_range', 'selling_price', 'discount_price'),
                Index('idx_product_stock_level', 'stock_quantity', 'min_stock_level'),
                Index('idx_product_featured_active', 'is_featured', 'is_active', 'created_at'),
            )
        
        return Product
```

### 4.2 复杂约束

```python
# complex_constraints.py
from sqlmodel import SQLModel, Field, text
from sqlalchemy import CheckConstraint, UniqueConstraint, Index, event
from sqlalchemy.schema import DDL
from typing import Optional
from datetime import datetime, date
from decimal import Decimal

class Account(SQLModel, table=True):
    """账户模型 - 复杂约束示例"""
    __tablename__ = "accounts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 账户信息
    account_number: str = Field(max_length=20, unique=True)
    account_type: str = Field(max_length=20)  # savings, checking, credit
    
    # 余额信息
    balance: Decimal = Field(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    available_balance: Decimal = Field(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    credit_limit: Optional[Decimal] = Field(default=None, max_digits=15, decimal_places=2)
    
    # 利率信息
    interest_rate: Optional[Decimal] = Field(default=None, max_digits=5, decimal_places=4)
    
    # 状态信息
    status: str = Field(max_length=20, default='active')
    is_frozen: bool = Field(default=False)
    
    # 客户信息
    customer_id: int = Field(foreign_key="customers.id")
    
    # 时间信息
    opened_date: date = Field(default_factory=date.today)
    closed_date: Optional[date] = Field(default=None)
    last_transaction_date: Optional[datetime] = Field(default=None)
    
    __table_args__ = (
        # 基础约束
        CheckConstraint("account_type IN ('savings', 'checking', 'credit')", name='ck_account_type'),
        CheckConstraint("status IN ('active', 'inactive', 'closed', 'suspended')", name='ck_account_status'),
        
        # 余额约束
        CheckConstraint('available_balance <= balance', name='ck_account_available_le_balance'),
        
        # 信用账户特殊约束
        CheckConstraint(
            "(account_type != 'credit') OR (account_type = 'credit' AND credit_limit IS NOT NULL AND credit_limit > 0)",
            name='ck_account_credit_has_limit'
        ),
        
        # 储蓄账户余额不能为负
        CheckConstraint(
            "(account_type != 'savings') OR (account_type = 'savings' AND balance >= 0)",
            name='ck_account_savings_non_negative'
        ),
        
        # 支票账户可以有小额透支
        CheckConstraint(
            "(account_type != 'checking') OR (account_type = 'checking' AND balance >= -1000)",
            name='ck_account_checking_overdraft_limit'
        ),
        
        # 信用账户余额约束
        CheckConstraint(
            "(account_type != 'credit') OR (account_type = 'credit' AND balance >= -credit_limit)",
            name='ck_account_credit_within_limit'
        ),
        
        # 利率约束
        CheckConstraint(
            "interest_rate IS NULL OR (interest_rate >= 0 AND interest_rate <= 1)",
            name='ck_account_interest_rate_range'
        ),
        
        # 日期约束
        CheckConstraint('closed_date IS NULL OR closed_date >= opened_date', name='ck_account_close_after_open'),
        CheckConstraint(
            "(status != 'closed') OR (status = 'closed' AND closed_date IS NOT NULL)",
            name='ck_account_closed_has_date'
        ),
        
        # 冻结状态约束
        CheckConstraint(
            "(is_frozen = false) OR (is_frozen = true AND status IN ('active', 'suspended'))",
            name='ck_account_frozen_status'
        ),
        
        # 复合索引
        Index('idx_account_customer_type', 'customer_id', 'account_type'),
        Index('idx_account_status_type', 'status', 'account_type'),
        Index('idx_account_balance_type', 'account_type', 'balance'),
    )

class Transaction(SQLModel, table=True):
    """交易模型 - 复杂业务约束"""
    __tablename__ = "transactions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 交易基础信息
    transaction_id: str = Field(max_length=50, unique=True)
    transaction_type: str = Field(max_length=20)  # deposit, withdrawal, transfer, payment
    
    # 账户信息
    from_account_id: Optional[int] = Field(default=None, foreign_key="accounts.id")
    to_account_id: Optional[int] = Field(default=None, foreign_key="accounts.id")
    
    # 金额信息
    amount: Decimal = Field(max_digits=15, decimal_places=2)
    fee: Decimal = Field(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # 状态信息
    status: str = Field(max_length=20, default='pending')
    
    # 描述信息
    description: Optional[str] = Field(default=None, max_length=500)
    reference_number: Optional[str] = Field(default=None, max_length=100)
    
    # 时间信息
    transaction_date: datetime = Field(default_factory=datetime.utcnow)
    processed_date: Optional[datetime] = Field(default=None)
    
    __table_args__ = (
        # 交易类型约束
        CheckConstraint(
            "transaction_type IN ('deposit', 'withdrawal', 'transfer', 'payment', 'fee', 'interest')",
            name='ck_transaction_type'
        ),
        
        # 状态约束
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'failed', 'cancelled')",
            name='ck_transaction_status'
        ),
        
        # 金额约束
        CheckConstraint('amount > 0', name='ck_transaction_amount_positive'),
        CheckConstraint('fee >= 0', name='ck_transaction_fee_non_negative'),
        
        # 账户约束
        CheckConstraint(
            "(transaction_type IN ('deposit', 'withdrawal', 'fee', 'interest') AND from_account_id IS NOT NULL AND to_account_id IS NULL) OR "
            "(transaction_type = 'transfer' AND from_account_id IS NOT NULL AND to_account_id IS NOT NULL AND from_account_id != to_account_id) OR "
            "(transaction_type = 'payment' AND from_account_id IS NOT NULL)",
            name='ck_transaction_account_logic'
        ),
        
        # 处理时间约束
        CheckConstraint(
            "processed_date IS NULL OR processed_date >= transaction_date",
            name='ck_transaction_processed_after_created'
        ),
        
        # 状态与处理时间的一致性
        CheckConstraint(
            "(status NOT IN ('completed', 'failed')) OR (status IN ('completed', 'failed') AND processed_date IS NOT NULL)",
            name='ck_transaction_completed_has_processed_date'
        ),
        
        # 索引
        Index('idx_transaction_account_date', 'from_account_id', 'transaction_date'),
        Index('idx_transaction_type_status', 'transaction_type', 'status'),
        Index('idx_transaction_date_amount', 'transaction_date', 'amount'),
        Index('idx_transaction_reference', 'reference_number'),
    )

# 创建触发器和存储过程的示例
class DatabaseTriggerExamples:
    """数据库触发器示例"""
    
    @staticmethod
    def create_audit_trigger():
        """创建审计触发器"""
        # 更新时间戳触发器
        update_timestamp_trigger = DDL("""
            CREATE OR REPLACE FUNCTION update_timestamp()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            CREATE TRIGGER trigger_update_timestamp
                BEFORE UPDATE ON customers
                FOR EACH ROW
                EXECUTE FUNCTION update_timestamp();
        """)
        
        return update_timestamp_trigger
    
    @staticmethod
    def create_balance_check_trigger():
        """创建余额检查触发器"""
        balance_check_trigger = DDL("""
            CREATE OR REPLACE FUNCTION check_account_balance()
            RETURNS TRIGGER AS $$
            BEGIN
                -- 检查储蓄账户余额不能为负
                IF NEW.account_type = 'savings' AND NEW.balance < 0 THEN
                    RAISE EXCEPTION '储蓄账户余额不能为负数';
                END IF;
                
                -- 检查信用账户不能超过信用额度
                IF NEW.account_type = 'credit' AND NEW.balance < -NEW.credit_limit THEN
                    RAISE EXCEPTION '超过信用额度限制';
                END IF;
                
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            
            CREATE TRIGGER trigger_check_account_balance
                BEFORE INSERT OR UPDATE ON accounts
                FOR EACH ROW
                EXECUTE FUNCTION check_account_balance();
        """)
        
        return balance_check_trigger

# 事件监听器示例
@event.listens_for(Account, 'before_insert')
def generate_account_number(mapper, connection, target):
    """自动生成账户号码"""
    if not target.account_number:
        # 生成账户号码逻辑
        import random
        import string
        
        prefix = {
            'savings': 'SAV',
            'checking': 'CHK', 
            'credit': 'CRD'
        }.get(target.account_type, 'ACC')
        
        suffix = ''.join(random.choices(string.digits, k=10))
        target.account_number = f"{prefix}{suffix}"

@event.listens_for(Transaction, 'before_insert')
def validate_transaction_business_rules(mapper, connection, target):
    """验证交易业务规则"""
    # 检查转账交易的账户不能相同
    if (target.transaction_type == 'transfer' and 
        target.from_account_id == target.to_account_id):
        raise ValueError('转账的源账户和目标账户不能相同')
    
    # 检查大额交易
    if target.amount > Decimal('10000'):
        # 大额交易需要特殊处理
        target.status = 'pending'  # 需要人工审核
```

---

## 5. 错误处理与异常管理

### 5.1 验证错误处理

```python
# error_handling.py
from sqlmodel import SQLModel, Field, Session
from pydantic import ValidationError, validator
from sqlalchemy.exc import IntegrityError, CheckViolation
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

class ValidationErrorHandler:
    """验证错误处理器"""
    
    @staticmethod
    def handle_pydantic_error(error: ValidationError) -> Dict[str, Any]:
        """处理 Pydantic 验证错误"""
        formatted_errors = []
        
        for error_detail in error.errors():
            field_path = ' -> '.join(str(loc) for loc in error_detail['loc'])
            error_msg = error_detail['msg']
            error_type = error_detail['type']
            
            formatted_error = {
                'field': field_path,
                'message': error_msg,
                'type': error_type,
                'input_value': error_detail.get('input')
            }
            
            formatted_errors.append(formatted_error)
        
        return {
            'error_type': 'validation_error',
            'message': '数据验证失败',
            'details': formatted_errors,
            'error_count': len(formatted_errors)
        }
    
    @staticmethod
    def handle_database_error(error: Exception) -> Dict[str, Any]:
        """处理数据库错误"""
        if isinstance(error, IntegrityError):
            # 完整性约束错误
            if 'UNIQUE constraint failed' in str(error):
                return {
                    'error_type': 'unique_constraint_violation',
                    'message': '数据重复，违反唯一性约束',
                    'details': str(error.orig)
                }
            elif 'FOREIGN KEY constraint failed' in str(error):
                return {
                    'error_type': 'foreign_key_violation',
                    'message': '外键约束违反',
                    'details': str(error.orig)
                }
            elif 'CHECK constraint failed' in str(error):
                return {
                    'error_type': 'check_constraint_violation',
                    'message': '检查约束违反',
                    'details': str(error.orig)
                }
            else:
                return {
                    'error_type': 'integrity_error',
                    'message': '数据完整性错误',
                    'details': str(error.orig)
                }
        
        return {
            'error_type': 'database_error',
            'message': '数据库操作失败',
            'details': str(error)
        }

class ValidationService:
    """验证服务类"""
    
    def __init__(self, session: Session):
        self.session = session
        self.logger = logging.getLogger(__name__)
    
    def validate_and_create(self, model_class: type, data: Dict[str, Any]) -> Dict[str, Any]:
        """验证并创建模型实例"""
        try:
            # 1. Pydantic 验证
            instance = model_class(**data)
            
            # 2. 自定义业务验证
            business_errors = self._validate_business_rules(instance, data)
            if business_errors:
                return {
                    'success': False,
                    'error_type': 'business_validation_error',
                    'message': '业务规则验证失败',
                    'details': business_errors
                }
            
            # 3. 数据库操作
            self.session.add(instance)
            self.session.commit()
            
            return {
                'success': True,
                'data': instance,
                'message': '创建成功'
            }
            
        except ValidationError as e:
            self.session.rollback()
            error_info = ValidationErrorHandler.handle_pydantic_error(e)
            self.logger.error(f"Pydantic validation error: {error_info}")
            return {'success': False, **error_info}
            
        except IntegrityError as e:
            self.session.rollback()
            error_info = ValidationErrorHandler.handle_database_error(e)
            self.logger.error(f"Database integrity error: {error_info}")
            return {'success': False, **error_info}
            
        except Exception as e:
            self.session.rollback()
            self.logger.error(f"Unexpected error: {str(e)}")
            return {
                'success': False,
                'error_type': 'unexpected_error',
                'message': '操作失败',
                'details': str(e)
            }
    
    def _validate_business_rules(self, instance: SQLModel, data: Dict[str, Any]) -> List[str]:
        """验证业务规则"""
        errors = []
        
        # 根据模型类型执行不同的业务验证
        if hasattr(instance, '__business_rules__'):
            rules = getattr(instance, '__business_rules__')
            errors.extend(ModelValidationUtils.validate_business_rules(data, rules))
        
        return errors

# 使用示例
class UserWithValidation(SQLModel, table=True):
    """带验证的用户模型"""
    __tablename__ = "users_with_validation"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    age: Optional[int] = Field(default=None, ge=0, le=150)
    status: str = Field(default='active')
    
    # 业务规则定义
    __business_rules__ = {
        'username_unique': {
            'type': 'unique_check',
            'field': 'username',
            'message': '用户名已存在'
        },
        'email_unique': {
            'type': 'unique_check',
            'field': 'email',
            'message': '邮箱已被使用'
        }
    }
    
    @validator('username')
    def validate_username(cls, v):
        if not v.isalnum():
            raise ValueError('用户名只能包含字母和数字')
        return v.lower()
    
    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'suspended']
        if v not in allowed_statuses:
            raise ValueError(f'状态必须是 {allowed_statuses} 中的一个')
        return v

# 错误处理装饰器
def handle_validation_errors(func):
    """验证错误处理装饰器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            return ValidationErrorHandler.handle_pydantic_error(e)
        except IntegrityError as e:
            return ValidationErrorHandler.handle_database_error(e)
        except Exception as e:
            return {
                'error_type': 'unexpected_error',
                'message': '操作失败',
                'details': str(e)
            }
    return wrapper

@handle_validation_errors
def create_user_safe(session: Session, user_data: Dict[str, Any]):
    """安全创建用户"""
    user = UserWithValidation(**user_data)
    session.add(user)
    session.commit()
    return {'success': True, 'data': user}
```

### 5.2 批量验证处理

```python
# batch_validation.py
from typing import List, Dict, Any, Tuple
from sqlmodel import Session
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio

class BatchValidationService:
    """批量验证服务"""
    
    def __init__(self, session: Session, max_workers: int = 4):
        self.session = session
        self.max_workers = max_workers
        self.validation_service = ValidationService(session)
    
    def validate_batch(self, model_class: type, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量验证数据"""
        results = {
            'total': len(data_list),
            'success_count': 0,
            'error_count': 0,
            'successes': [],
            'errors': []
        }
        
        # 使用线程池并行验证
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有验证任务
            future_to_index = {
                executor.submit(self._validate_single, model_class, data, index): index
                for index, data in enumerate(data_list)
            }
            
            # 收集结果
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    result['index'] = index
                    
                    if result['success']:
                        results['success_count'] += 1
                        results['successes'].append(result)
                    else:
                        results['error_count'] += 1
                        results['errors'].append(result)
                        
                except Exception as e:
                    results['error_count'] += 1
                    results['errors'].append({
                        'index': index,
                        'success': False,
                        'error_type': 'processing_error',
                        'message': f'处理第 {index} 项时发生错误',
                        'details': str(e)
                    })
        
        return results
    
    def _validate_single(self, model_class: type, data: Dict[str, Any], index: int) -> Dict[str, Any]:
        """验证单个数据项"""
        try:
            # 创建新的会话用于线程安全
            with Session(self.session.bind) as thread_session:
                validation_service = ValidationService(thread_session)
                result = validation_service.validate_and_create(model_class, data)
                result['original_data'] = data
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error_type': 'validation_error',
                'message': f'验证失败',
                'details': str(e),
                'original_data': data
            }
    
    async def validate_batch_async(self, model_class: type, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """异步批量验证"""
        results = {
            'total': len(data_list),
            'success_count': 0,
            'error_count': 0,
            'successes': [],
            'errors': []
        }
        
        # 创建异步任务
        tasks = [
            self._validate_single_async(model_class, data, index)
            for index, data in enumerate(data_list)
        ]
        
        # 等待所有任务完成
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for index, result in enumerate(completed_tasks):
            if isinstance(result, Exception):
                results['error_count'] += 1
                results['errors'].append({
                    'index': index,
                    'success': False,
                    'error_type': 'async_processing_error',
                    'message': f'异步处理第 {index} 项时发生错误',
                    'details': str(result)
                })
            else:
                result['index'] = index
                if result['success']:
                    results['success_count'] += 1
                    results['successes'].append(result)
                else:
                    results['error_count'] += 1
                    results['errors'].append(result)
        
        return results
    
    async def _validate_single_async(self, model_class: type, data: Dict[str, Any], index: int) -> Dict[str, Any]:
        """异步验证单个数据项"""
        # 在异步环境中运行同步验证
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self._validate_single, 
            model_class, 
            data, 
            index
        )

# 使用示例
def example_batch_validation():
    """批量验证使用示例"""
    from sqlalchemy import create_engine
    
    engine = create_engine("sqlite:///validation_example.db")
    
    # 测试数据
    user_data_list = [
        {'username': 'user1', 'email': 'user1@example.com', 'age': 25},
        {'username': 'user2', 'email': 'user2@example.com', 'age': 30},
        {'username': 'invalid', 'email': 'invalid-email', 'age': -5},  # 无效数据
        {'username': 'user4', 'email': 'user4@example.com', 'age': 35},
    ]
    
    with Session(engine) as session:
        batch_service = BatchValidationService(session)
        
        # 批量验证
        results = batch_service.validate_batch(UserWithValidation, user_data_list)
        
        print(f"总计: {results['total']}")
        print(f"成功: {results['success_count']}")
        print(f"失败: {results['error_count']}")
        
        # 打印错误详情
        for error in results['errors']:
            print(f"错误 {error['index']}: {error['message']}")
            if 'details' in error:
                print(f"  详情: {error['details']}")
```

---

## 6. 性能优化

### 6.1 验证性能优化

```python
# validation_performance.py
from sqlmodel import SQLModel, Field
from pydantic import validator
from typing import Dict, Any, List, Optional, Set
from functools import lru_cache
import re
import time

class PerformanceOptimizedValidator:
    """性能优化的验证器"""
    
    def __init__(self):
        # 缓存编译的正则表达式
        self._regex_cache: Dict[str, re.Pattern] = {}
        
        # 缓存验证结果
        self._validation_cache: Dict[str, bool] = {}
        
        # 预编译常用正则表达式
        self._precompile_regex()
    
    def _precompile_regex(self):
        """预编译常用正则表达式"""
        patterns = {
            'email': r'^[\w\.-]+@[\w\.-]+\.\w+$',
            'phone': r'^\+?1?\d{9,15}$',
            'username': r'^[a-zA-Z0-9_]{3,20}$',
            'password': r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)[a-zA-Z\d@$!%*?&]{8,}$',
            'url': r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
        }
        
        for name, pattern in patterns.items():
            self._regex_cache[name] = re.compile(pattern)
    
    @lru_cache(maxsize=1000)
    def validate_email(self, email: str) -> bool:
        """缓存的邮箱验证"""
        return bool(self._regex_cache['email'].match(email))
    
    @lru_cache(maxsize=1000)
    def validate_phone(self, phone: str) -> bool:
        """缓存的电话验证"""
        return bool(self._regex_cache['phone'].match(phone))
    
    @lru_cache(maxsize=500)
    def validate_username(self, username: str) -> bool:
        """缓存的用户名验证"""
        return bool(self._regex_cache['username'].match(username))
    
    def validate_batch_emails(self, emails: List[str]) -> Dict[str, bool]:
        """批量邮箱验证"""
        results = {}
        pattern = self._regex_cache['email']
        
        for email in emails:
            # 先检查缓存
            cache_key = f"email_{email}"
            if cache_key in self._validation_cache:
                results[email] = self._validation_cache[cache_key]
            else:
                # 验证并缓存结果
                is_valid = bool(pattern.match(email))
                self._validation_cache[cache_key] = is_valid
                results[email] = is_valid
        
        return results

# 全局验证器实例
validator_instance = PerformanceOptimizedValidator()

class OptimizedUser(SQLModel, table=True):
    """性能优化的用户模型"""
    __tablename__ = "optimized_users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(min_length=3, max_length=20)
    email: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    
    @validator('email')
    def validate_email(cls, v):
        if not validator_instance.validate_email(v):
            raise ValueError('邮箱格式无效')
        return v.lower()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not validator_instance.validate_phone(v):
            raise ValueError('电话号码格式无效')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        if not validator_instance.validate_username(v):
            raise ValueError('用户名格式无效')
        return v.lower()

class ValidationPerformanceMonitor:
    """验证性能监控器"""
    
    def __init__(self):
        self.validation_times: List[float] = []
        self.validation_counts: Dict[str, int] = {}
    
    def time_validation(self, func):
        """验证时间装饰器"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time
                self.validation_times.append(duration)
                
                func_name = func.__name__
                self.validation_counts[func_name] = self.validation_counts.get(func_name, 0) + 1
        
        return wrapper
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        if not self.validation_times:
            return {'message': '暂无验证数据'}
        
        return {
            'total_validations': len(self.validation_times),
            'average_time': sum(self.validation_times) / len(self.validation_times),
            'min_time': min(self.validation_times),
            'max_time': max(self.validation_times),
            'total_time': sum(self.validation_times),
            'validation_counts': self.validation_counts
        }
    
    def clear_stats(self):
        """清除统计数据"""
        self.validation_times.clear()
        self.validation_counts.clear()

# 全局性能监控器
performance_monitor = ValidationPerformanceMonitor()

# 性能优化的批量验证
class BatchValidationOptimizer:
    """批量验证优化器"""
    
    @staticmethod
    def optimize_unique_checks(session, model_class: type, field_values: List[Any], field_name: str) -> Set[Any]:
        """优化唯一性检查"""
        # 一次查询检查所有值
        existing_values = session.query(getattr(model_class, field_name)).filter(
            getattr(model_class, field_name).in_(field_values)
        ).all()
        
        return {value[0] for value in existing_values}
    
    @staticmethod
    def batch_validate_with_db_check(session, model_class: type, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """带数据库检查的批量验证"""
        results = {
            'valid_items': [],
            'invalid_items': [],
            'duplicate_items': []
        }
        
        # 提取需要检查唯一性的字段值
        emails = [item.get('email') for item in data_list if item.get('email')]
        usernames = [item.get('username') for item in data_list if item.get('username')]
        
        # 批量检查唯一性
        existing_emails = BatchValidationOptimizer.optimize_unique_checks(
            session, model_class, emails, 'email'
        )
        existing_usernames = BatchValidationOptimizer.optimize_unique_checks(
            session, model_class, usernames, 'username'
        )
        
        # 验证每个项目
        for index, data in enumerate(data_list):
            try:
                # Pydantic 验证
                instance = model_class(**data)
                
                # 检查唯一性
                has_duplicate = False
                duplicate_fields = []
                
                if data.get('email') in existing_emails:
                    has_duplicate = True
                    duplicate_fields.append('email')
                
                if data.get('username') in existing_usernames:
                    has_duplicate = True
                    duplicate_fields.append('username')
                
                if has_duplicate:
                    results['duplicate_items'].append({
                        'index': index,
                        'data': data,
                        'duplicate_fields': duplicate_fields
                    })
                else:
                    results['valid_items'].append({
                        'index': index,
                        'instance': instance,
                        'data': data
                    })
                    
            except Exception as e:
                results['invalid_items'].append({
                    'index': index,
                    'data': data,
                    'error': str(e)
                })
        
        return results
```

### 6.2 数据库约束优化

```python
# constraint_optimization.py
from sqlalchemy import Index, text
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class OptimizedConstraintModel(SQLModel, table=True):
    """优化约束的模型"""
    __tablename__ = "optimized_constraints"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 使用部分索引优化性能
    email: str = Field(max_length=255, unique=True)
    status: str = Field(max_length=20, default='active')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    __table_args__ = (
        # 部分索引 - 只为活跃用户创建索引
        Index('idx_active_users_email', 'email', postgresql_where=text("status = 'active'")),
        
        # 复合索引优化查询
        Index('idx_status_created', 'status', 'created_at'),
        
        # 函数索引 - 用于大小写不敏感搜索
        Index('idx_email_lower', text('lower(email)')),
    )

class ConstraintPerformanceAnalyzer:
    """约束性能分析器"""
    
    @staticmethod
    def analyze_constraint_performance(session, table_name: str) -> Dict[str, Any]:
        """分析约束性能"""
        # PostgreSQL 示例
        constraint_query = text("""
            SELECT 
                conname as constraint_name,
                contype as constraint_type,
                pg_get_constraintdef(oid) as definition
            FROM pg_constraint 
            WHERE conrelid = :table_name::regclass
        """)
        
        index_query = text("""
            SELECT 
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as size
            FROM pg_indexes 
            WHERE tablename = :table_name
        """)
        
        try:
            constraints = session.execute(constraint_query, {'table_name': table_name}).fetchall()
            indexes = session.execute(index_query, {'table_name': table_name}).fetchall()
            
            return {
                'constraints': [dict(row) for row in constraints],
                'indexes': [dict(row) for row in indexes]
            }
        except Exception as e:
            return {'error': str(e)}
```

---

## 7. 最佳实践

### 7.1 验证设计原则

1. **分层验证**
   - 前端验证：用户体验优化
   - 模型验证：数据格式和业务规则
   - 数据库约束：数据完整性保证

2. **性能考虑**
   - 使用缓存减少重复验证
   - 批量操作优化数据库查询
   - 合理使用索引提升约束检查性能

3. **错误处理**
   - 提供清晰的错误信息
   - 区分不同类型的验证错误
   - 实现优雅的错误恢复机制

### 7.2 常见陷阱与避免方法

1. **过度验证**
   ```python
   # ❌ 错误：重复验证
   class User(SQLModel, table=True):
       email: str = Field(regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
       
       @validator('email')
       def validate_email_again(cls, v):
           # 重复的邮箱验证
           if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', v):
               raise ValueError('邮箱格式无效')
           return v
   
   # ✅ 正确：避免重复验证
   class User(SQLModel, table=True):
       email: str = Field(regex=r'^[\w\.-]+@[\w\.-]+\.\w+$')
   ```

2. **忽略数据库约束**
   ```python
   # ❌ 错误：只有模型验证
   class Product(SQLModel, table=True):
       price: float = Field(gt=0)
   
   # ✅ 正确：模型验证 + 数据库约束
   class Product(SQLModel, table=True):
       price: Decimal = Field(max_digits=10, decimal_places=2)
       
       __table_args__ = (
           CheckConstraint('price > 0', name='ck_product_price_positive'),
       )
   ```

3. **性能问题**
   ```python
   # ❌ 错误：每次都查询数据库
   @validator('username')
   def validate_username_unique(cls, v, values, **kwargs):
       # 每次验证都查询数据库
       session = get_session()
       if session.query(User).filter(User.username == v).first():
           raise ValueError('用户名已存在')
       return v
   
   # ✅ 正确：使用数据库约束 + 批量检查
   class User(SQLModel, table=True):
       username: str = Field(unique=True)
   ```

---

## 8. 本章总结

### 8.1 核心概念回顾

1. **验证层次**
   - Pydantic 字段验证：数据类型和格式
   - 自定义验证器：复杂业务逻辑
   - 数据库约束：数据完整性保证

2. **约束类型**
   - 检查约束：值范围和条件验证
   - 唯一约束：防止重复数据
   - 外键约束：引用完整性
   - 复合约束：多字段联合验证

3. **错误处理**
   - 验证错误分类和处理
   - 批量操作错误管理
   - 性能优化策略

### 8.2 最佳实践总结

1. **设计原则**
   - 分层验证，各司其职
   - 性能优先，合理缓存
   - 错误友好，信息清晰

2. **性能优化**
   - 使用编译缓存和结果缓存
   - 批量操作减少数据库查询
   - 合理设计索引和约束

3. **维护性**
   - 验证规则集中管理
   - 错误处理统一标准
   - 性能监控和分析

### 8.3 常见陷阱与避免方法

1. **避免过度验证**：不要在多个层次重复相同的验证逻辑
2. **平衡性能与安全**：在验证完整性和执行效率之间找到平衡
3. **错误信息友好**：提供有助于用户理解和修正的错误信息

### 8.4 实践检查清单

- [ ] 是否为所有关键字段添加了适当的验证？
- [ ] 是否使用了数据库约束来保证数据完整性？
- [ ] 是否实现了完善的错误处理机制？
- [ ] 是否考虑了验证的性能影响？
- [ ] 是否为批量操作提供了优化方案？
- [ ] 是否有监控和分析验证性能的机制？

### 8.5 下一步学习

在掌握了验证与约束的基础知识后，建议继续学习：

1. **第7章：查询优化与性能调优** - 深入了解查询性能优化
2. **第8章：测试与调试** - 学习如何测试验证逻辑
3. **第9章：部署与运维** - 了解生产环境中的验证策略

### 8.6 扩展练习

1. **设计一个完整的用户管理系统**，包含注册、登录、权限验证等功能
2. **实现一个电商订单系统**，包含库存验证、价格计算、状态流转等业务规则
3. **创建一个性能监控系统**，跟踪和分析验证操作的性能指标
4. **开发一个验证规则配置系统**，允许动态配置和修改验证规则

通过本章的学习，你应该能够：
- 设计和实现完整的数据验证体系
- 合理使用数据库约束保证数据完整性
- 处理各种验证错误和异常情况
- 优化验证性能，提升应用响应速度
- 在实际项目中应用验证最佳实践

---

**下一章预告**：在第7章中，我们将深入探讨 SQLModel 的查询优化与性能调优，学习如何编写高效的查询语句，优化数据库性能，以及监控和分析查询执行情况。