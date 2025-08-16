# 第五章：关系和关联

## 学习目标

通过本章学习，你将掌握：

- SQLModel 中关系的定义和使用
- 一对一、一对多、多对多关系的实现
- 关系的配置选项和最佳实践
- 延迟加载和预加载策略
- 关系查询和操作技巧
- 关系数据的性能优化

---

## 1. 关系基础概念

### 1.1 关系类型概述

在关系型数据库中，表与表之间存在三种基本关系：

1. **一对一（One-to-One）**：一个记录对应另一个表中的一个记录
2. **一对多（One-to-Many）**：一个记录对应另一个表中的多个记录
3. **多对多（Many-to-Many）**：一个记录对应另一个表中的多个记录，反之亦然

### 1.2 SQLModel 中的关系实现

```python
# relationship_basics.py
from sqlmodel import SQLModel, Field, Relationship, create_engine, Session
from typing import Optional, List
from datetime import datetime

# 基础模型定义
class User(SQLModel, table=True):
    """用户模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    email: str = Field(index=True, unique=True)
    full_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    # 关系定义
    profile: Optional["UserProfile"] = Relationship(back_populates="user")
    posts: List["Post"] = Relationship(back_populates="author")
    orders: List["Order"] = Relationship(back_populates="customer")

class UserProfile(SQLModel, table=True):
    """用户资料模型（一对一关系）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[datetime] = None
    
    # 反向关系
    user: Optional[User] = Relationship(back_populates="profile")

class Category(SQLModel, table=True):
    """分类模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    
    # 一对多关系
    posts: List["Post"] = Relationship(back_populates="category")

class Post(SQLModel, table=True):
    """文章模型（一对多关系）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_published: bool = Field(default=False)
    
    # 外键
    author_id: int = Field(foreign_key="user.id")
    category_id: Optional[int] = Field(foreign_key="category.id")
    
    # 关系
    author: Optional[User] = Relationship(back_populates="posts")
    category: Optional[Category] = Relationship(back_populates="posts")
    comments: List["Comment"] = Relationship(back_populates="post")
    tags: List["Tag"] = Relationship(back_populates="posts", link_table="post_tag")

class Comment(SQLModel, table=True):
    """评论模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 外键
    post_id: int = Field(foreign_key="post.id")
    author_id: int = Field(foreign_key="user.id")
    
    # 关系
    post: Optional[Post] = Relationship(back_populates="comments")
    author: Optional[User] = Relationship()

# 多对多关系的链接表
class PostTagLink(SQLModel, table=True):
    """文章标签关联表"""
    __tablename__ = "post_tag"
    
    post_id: int = Field(foreign_key="post.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Tag(SQLModel, table=True):
    """标签模型（多对多关系）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    color: Optional[str] = None
    
    # 多对多关系
    posts: List[Post] = Relationship(back_populates="tags", link_table="post_tag")
```

---

## 2. 一对一关系

### 2.1 基本实现

```python
# one_to_one_relationship.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import Optional
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    
    # 一对一关系
    profile: Optional["UserProfile"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )

class UserProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True)  # 唯一约束确保一对一
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    
    # 反向关系
    user: Optional[User] = Relationship(back_populates="profile")

# 使用示例
def create_user_with_profile(session: Session):
    """创建用户及其资料"""
    
    # 方法1：分别创建
    user = User(username="john_doe", email="john@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    
    profile = UserProfile(
        user_id=user.id,
        bio="Software Developer",
        phone="+1234567890"
    )
    session.add(profile)
    session.commit()
    
    return user

def create_user_with_profile_cascade(session: Session):
    """使用级联创建用户及其资料"""
    
    user = User(username="jane_doe", email="jane@example.com")
    profile = UserProfile(
        bio="Data Scientist",
        phone="+0987654321"
    )
    
    # 建立关系
    user.profile = profile
    
    session.add(user)
    session.commit()
    
    return user

def get_user_with_profile(session: Session, user_id: int):
    """获取用户及其资料"""
    
    # 方法1：使用 joinedload 预加载
    from sqlalchemy.orm import joinedload
    
    user = session.exec(
        select(User)
        .options(joinedload(User.profile))
        .where(User.id == user_id)
    ).first()
    
    if user and user.profile:
        print(f"用户: {user.username}")
        print(f"简介: {user.profile.bio}")
        print(f"电话: {user.profile.phone}")
    
    return user

def update_user_profile(session: Session, user_id: int, bio: str):
    """更新用户资料"""
    
    user = session.get(User, user_id)
    if not user:
        return None
    
    if not user.profile:
        # 如果没有资料，创建一个
        user.profile = UserProfile(bio=bio)
    else:
        # 更新现有资料
        user.profile.bio = bio
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return user
```

### 2.2 高级一对一关系配置

```python
# advanced_one_to_one.py
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import UniqueConstraint
from typing import Optional

class Company(SQLModel, table=True):
    """公司模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    website: Optional[str] = None
    
    # 一对一关系：公司详情
    details: Optional["CompanyDetails"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete-orphan",
            "lazy": "select"  # 延迟加载
        }
    )
    
    # 一对一关系：公司设置
    settings: Optional["CompanySettings"] = Relationship(
        back_populates="company",
        sa_relationship_kwargs={
            "uselist": False,
            "cascade": "all, delete-orphan"
        }
    )

class CompanyDetails(SQLModel, table=True):
    """公司详情模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", unique=True)
    
    description: Optional[str] = None
    founded_year: Optional[int] = None
    employee_count: Optional[int] = None
    revenue: Optional[float] = None
    
    # 反向关系
    company: Optional[Company] = Relationship(back_populates="details")

class CompanySettings(SQLModel, table=True):
    """公司设置模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    company_id: int = Field(foreign_key="company.id", unique=True)
    
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD")
    date_format: str = Field(default="YYYY-MM-DD")
    notification_enabled: bool = Field(default=True)
    
    # 反向关系
    company: Optional[Company] = Relationship(back_populates="settings")

# 使用示例
def create_complete_company(session: Session):
    """创建完整的公司信息"""
    
    company = Company(name="Tech Corp", website="https://techcorp.com")
    
    # 创建公司详情
    details = CompanyDetails(
        description="A leading technology company",
        founded_year=2010,
        employee_count=500,
        revenue=10000000.0
    )
    
    # 创建公司设置
    settings = CompanySettings(
        timezone="America/New_York",
        currency="USD",
        date_format="MM/DD/YYYY"
    )
    
    # 建立关系
    company.details = details
    company.settings = settings
    
    session.add(company)
    session.commit()
    session.refresh(company)
    
    return company

def get_company_full_info(session: Session, company_id: int):
    """获取公司完整信息"""
    from sqlalchemy.orm import joinedload
    
    company = session.exec(
        select(Company)
        .options(
            joinedload(Company.details),
            joinedload(Company.settings)
        )
        .where(Company.id == company_id)
    ).first()
    
    if company:
        print(f"公司: {company.name}")
        if company.details:
            print(f"成立年份: {company.details.founded_year}")
            print(f"员工数: {company.details.employee_count}")
        if company.settings:
            print(f"时区: {company.settings.timezone}")
            print(f"货币: {company.settings.currency}")
    
    return company
```

---

## 3. 一对多关系

### 3.1 基本实现

```python
# one_to_many_relationship.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import Optional, List
from datetime import datetime

class Department(SQLModel, table=True):
    """部门模型（一的一方）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    description: Optional[str] = None
    budget: Optional[float] = None
    
    # 一对多关系：一个部门有多个员工
    employees: List["Employee"] = Relationship(
        back_populates="department",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    
    # 一对多关系：一个部门有多个项目
    projects: List["Project"] = Relationship(back_populates="department")

class Employee(SQLModel, table=True):
    """员工模型（多的一方）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    position: str
    salary: Optional[float] = None
    hire_date: datetime = Field(default_factory=datetime.utcnow)
    
    # 外键
    department_id: Optional[int] = Field(foreign_key="department.id")
    
    # 多对一关系：多个员工属于一个部门
    department: Optional[Department] = Relationship(back_populates="employees")
    
    # 一对多关系：一个员工有多个任务
    tasks: List["Task"] = Relationship(back_populates="assignee")

class Project(SQLModel, table=True):
    """项目模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = Field(default="planning")
    
    # 外键
    department_id: int = Field(foreign_key="department.id")
    
    # 关系
    department: Optional[Department] = Relationship(back_populates="projects")
    tasks: List["Task"] = Relationship(back_populates="project")

class Task(SQLModel, table=True):
    """任务模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    status: str = Field(default="todo")
    priority: str = Field(default="medium")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime] = None
    
    # 外键
    project_id: int = Field(foreign_key="project.id")
    assignee_id: Optional[int] = Field(foreign_key="employee.id")
    
    # 关系
    project: Optional[Project] = Relationship(back_populates="tasks")
    assignee: Optional[Employee] = Relationship(back_populates="tasks")

# 使用示例
def create_department_with_employees(session: Session):
    """创建部门及其员工"""
    
    # 创建部门
    dept = Department(
        name="Engineering",
        description="Software Development Department",
        budget=1000000.0
    )
    
    # 创建员工
    employees = [
        Employee(
            name="Alice Johnson",
            email="alice@company.com",
            position="Senior Developer",
            salary=90000.0
        ),
        Employee(
            name="Bob Smith",
            email="bob@company.com",
            position="Junior Developer",
            salary=60000.0
        ),
        Employee(
            name="Carol Davis",
            email="carol@company.com",
            position="Team Lead",
            salary=110000.0
        )
    ]
    
    # 建立关系
    dept.employees = employees
    
    session.add(dept)
    session.commit()
    session.refresh(dept)
    
    return dept

def get_department_with_employees(session: Session, dept_id: int):
    """获取部门及其所有员工"""
    from sqlalchemy.orm import selectinload
    
    dept = session.exec(
        select(Department)
        .options(selectinload(Department.employees))
        .where(Department.id == dept_id)
    ).first()
    
    if dept:
        print(f"部门: {dept.name}")
        print(f"预算: ${dept.budget:,.2f}")
        print(f"员工数量: {len(dept.employees)}")
        
        for emp in dept.employees:
            print(f"  - {emp.name} ({emp.position}) - ${emp.salary:,.2f}")
    
    return dept

def add_employee_to_department(session: Session, dept_id: int, employee_data: dict):
    """向部门添加新员工"""
    
    dept = session.get(Department, dept_id)
    if not dept:
        return None
    
    employee = Employee(**employee_data, department_id=dept_id)
    session.add(employee)
    session.commit()
    session.refresh(employee)
    
    return employee

def transfer_employee(session: Session, employee_id: int, new_dept_id: int):
    """转移员工到新部门"""
    
    employee = session.get(Employee, employee_id)
    new_dept = session.get(Department, new_dept_id)
    
    if not employee or not new_dept:
        return None
    
    old_dept_name = employee.department.name if employee.department else "无部门"
    
    employee.department_id = new_dept_id
    session.add(employee)
    session.commit()
    session.refresh(employee)
    
    print(f"员工 {employee.name} 从 {old_dept_name} 转移到 {new_dept.name}")
    
    return employee
```

### 3.2 复杂一对多关系

```python
# complex_one_to_many.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy import func, and_, or_
from typing import Optional, List
from datetime import datetime, timedelta
from enum import Enum

class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Customer(SQLModel, table=True):
    """客户模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    phone: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_vip: bool = Field(default=False)
    
    # 一对多关系：客户的订单
    orders: List["Order"] = Relationship(
        back_populates="customer",
        sa_relationship_kwargs={
            "order_by": "Order.created_at.desc()",  # 按创建时间倒序
            "lazy": "select"
        }
    )
    
    # 一对多关系：客户的地址
    addresses: List["CustomerAddress"] = Relationship(
        back_populates="customer",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class CustomerAddress(SQLModel, table=True):
    """客户地址模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(foreign_key="customer.id")
    
    label: str  # 如："家庭地址"、"办公地址"
    street: str
    city: str
    state: str
    zip_code: str
    country: str = Field(default="US")
    is_default: bool = Field(default=False)
    
    # 关系
    customer: Optional[Customer] = Relationship(back_populates="addresses")

class Order(SQLModel, table=True):
    """订单模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    order_number: str = Field(unique=True, index=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    total_amount: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    
    # 外键
    customer_id: int = Field(foreign_key="customer.id")
    
    # 关系
    customer: Optional[Customer] = Relationship(back_populates="orders")
    items: List["OrderItem"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    payments: List["Payment"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Product(SQLModel, table=True):
    """产品模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    stock_quantity: int = Field(default=0)
    
    # 一对多关系：产品的订单项
    order_items: List["OrderItem"] = Relationship(back_populates="product")

class OrderItem(SQLModel, table=True):
    """订单项模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    quantity: int
    unit_price: float
    total_price: float
    
    # 外键
    order_id: int = Field(foreign_key="order.id")
    product_id: int = Field(foreign_key="product.id")
    
    # 关系
    order: Optional[Order] = Relationship(back_populates="items")
    product: Optional[Product] = Relationship(back_populates="order_items")

class Payment(SQLModel, table=True):
    """支付模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    amount: float
    payment_method: str
    transaction_id: Optional[str] = None
    status: str = Field(default="pending")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 外键
    order_id: int = Field(foreign_key="order.id")
    
    # 关系
    order: Optional[Order] = Relationship(back_populates="payments")

# 复杂查询示例
class OrderService:
    """订单服务类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_customer_orders_summary(self, customer_id: int) -> dict:
        """获取客户订单摘要"""
        from sqlalchemy.orm import selectinload
        
        customer = self.session.exec(
            select(Customer)
            .options(
                selectinload(Customer.orders).selectinload(Order.items),
                selectinload(Customer.addresses)
            )
            .where(Customer.id == customer_id)
        ).first()
        
        if not customer:
            return {}
        
        # 计算统计信息
        total_orders = len(customer.orders)
        total_spent = sum(order.total_amount for order in customer.orders)
        
        # 按状态分组
        status_counts = {}
        for order in customer.orders:
            status = order.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # 最近订单
        recent_orders = sorted(
            customer.orders,
            key=lambda x: x.created_at,
            reverse=True
        )[:5]
        
        return {
            'customer_info': {
                'name': customer.name,
                'email': customer.email,
                'is_vip': customer.is_vip,
                'addresses_count': len(customer.addresses)
            },
            'order_summary': {
                'total_orders': total_orders,
                'total_spent': total_spent,
                'average_order_value': total_spent / total_orders if total_orders > 0 else 0,
                'status_breakdown': status_counts
            },
            'recent_orders': [
                {
                    'id': order.id,
                    'order_number': order.order_number,
                    'status': order.status.value,
                    'total_amount': order.total_amount,
                    'created_at': order.created_at,
                    'items_count': len(order.items)
                }
                for order in recent_orders
            ]
        }
    
    def get_orders_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[OrderStatus] = None
    ) -> List[Order]:
        """按日期范围获取订单"""
        from sqlalchemy.orm import selectinload
        
        query = select(Order).options(
            selectinload(Order.customer),
            selectinload(Order.items).selectinload(OrderItem.product)
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        
        if status:
            query = query.where(Order.status == status)
        
        return self.session.exec(query).all()
    
    def get_top_customers(self, limit: int = 10) -> List[dict]:
        """获取消费最多的客户"""
        
        # 使用子查询计算每个客户的总消费
        subquery = (
            select(
                Customer.id,
                Customer.name,
                Customer.email,
                func.count(Order.id).label('order_count'),
                func.sum(Order.total_amount).label('total_spent')
            )
            .join(Order)
            .where(Order.status != OrderStatus.CANCELLED)
            .group_by(Customer.id, Customer.name, Customer.email)
            .order_by(func.sum(Order.total_amount).desc())
            .limit(limit)
        )
        
        results = self.session.exec(subquery).all()
        
        return [
            {
                'customer_id': r.id,
                'name': r.name,
                'email': r.email,
                'order_count': r.order_count,
                'total_spent': float(r.total_spent)
            }
            for r in results
        ]
    
    def create_order_with_items(
        self,
        customer_id: int,
        items_data: List[dict]
    ) -> Order:
        """创建订单及其订单项"""
        
        # 生成订单号
        import uuid
        order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # 创建订单
        order = Order(
            order_number=order_number,
            customer_id=customer_id
        )
        
        total_amount = 0.0
        order_items = []
        
        # 创建订单项
        for item_data in items_data:
            product = self.session.get(Product, item_data['product_id'])
            if not product:
                raise ValueError(f"Product {item_data['product_id']} not found")
            
            quantity = item_data['quantity']
            unit_price = product.price
            total_price = quantity * unit_price
            
            order_item = OrderItem(
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                product_id=product.id
            )
            
            order_items.append(order_item)
            total_amount += total_price
        
        # 设置订单总金额和订单项
        order.total_amount = total_amount
        order.items = order_items
        
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        
        return order
```

---

## 4. 多对多关系

### 4.1 基本实现

```python
# many_to_many_relationship.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import Optional, List
from datetime import datetime

# 多对多关系的链接表
class StudentCourseLink(SQLModel, table=True):
    """学生课程关联表"""
    __tablename__ = "student_course"
    
    student_id: int = Field(foreign_key="student.id", primary_key=True)
    course_id: int = Field(foreign_key="course.id", primary_key=True)
    
    # 额外字段
    enrolled_at: datetime = Field(default_factory=datetime.utcnow)
    grade: Optional[str] = None
    is_active: bool = Field(default=True)

class Student(SQLModel, table=True):
    """学生模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    student_id: str = Field(unique=True)
    major: Optional[str] = None
    year: int = Field(default=1)
    
    # 多对多关系：学生选修的课程
    courses: List["Course"] = Relationship(
        back_populates="students",
        link_table="student_course"
    )

class Course(SQLModel, table=True):
    """课程模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    code: str = Field(unique=True)
    description: Optional[str] = None
    credits: int = Field(default=3)
    max_students: int = Field(default=30)
    
    # 外键
    instructor_id: Optional[int] = Field(foreign_key="instructor.id")
    
    # 多对多关系：选修该课程的学生
    students: List[Student] = Relationship(
        back_populates="courses",
        link_table="student_course"
    )
    
    # 一对多关系：课程的授课教师
    instructor: Optional["Instructor"] = Relationship(back_populates="courses")

class Instructor(SQLModel, table=True):
    """教师模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(unique=True)
    department: str
    title: str = Field(default="Assistant Professor")
    
    # 一对多关系：教师授课的课程
    courses: List[Course] = Relationship(back_populates="instructor")

# 使用示例
def create_students_and_courses(session: Session):
    """创建学生和课程"""
    
    # 创建教师
    instructor1 = Instructor(
        name="Dr. Smith",
        email="smith@university.edu",
        department="Computer Science",
        title="Professor"
    )
    
    instructor2 = Instructor(
        name="Dr. Johnson",
        email="johnson@university.edu",
        department="Mathematics",
        title="Associate Professor"
    )
    
    session.add_all([instructor1, instructor2])
    session.commit()
    
    # 创建课程
    courses = [
        Course(
            name="Introduction to Programming",
            code="CS101",
            description="Basic programming concepts",
            credits=4,
            instructor_id=instructor1.id
        ),
        Course(
            name="Data Structures",
            code="CS201",
            description="Advanced data structures and algorithms",
            credits=4,
            instructor_id=instructor1.id
        ),
        Course(
            name="Calculus I",
            code="MATH101",
            description="Differential calculus",
            credits=3,
            instructor_id=instructor2.id
        ),
        Course(
            name="Linear Algebra",
            code="MATH201",
            description="Vectors, matrices, and linear transformations",
            credits=3,
            instructor_id=instructor2.id
        )
    ]
    
    session.add_all(courses)
    session.commit()
    
    # 创建学生
    students = [
        Student(
            name="Alice Brown",
            email="alice@student.edu",
            student_id="S001",
            major="Computer Science",
            year=2
        ),
        Student(
            name="Bob Wilson",
            email="bob@student.edu",
            student_id="S002",
            major="Mathematics",
            year=1
        ),
        Student(
            name="Carol Davis",
            email="carol@student.edu",
            student_id="S003",
            major="Computer Science",
            year=3
        )
    ]
    
    session.add_all(students)
    session.commit()
    
    return students, courses

def enroll_students_in_courses(session: Session):
    """为学生注册课程"""
    
    # 获取学生和课程
    alice = session.exec(select(Student).where(Student.student_id == "S001")).first()
    bob = session.exec(select(Student).where(Student.student_id == "S002")).first()
    carol = session.exec(select(Student).where(Student.student_id == "S003")).first()
    
    cs101 = session.exec(select(Course).where(Course.code == "CS101")).first()
    cs201 = session.exec(select(Course).where(Course.code == "CS201")).first()
    math101 = session.exec(select(Course).where(Course.code == "MATH101")).first()
    math201 = session.exec(select(Course).where(Course.code == "MATH201")).first()
    
    # Alice 选修 CS101, CS201, MATH101
    alice.courses = [cs101, cs201, math101]
    
    # Bob 选修 MATH101, MATH201, CS101
    bob.courses = [math101, math201, cs101]
    
    # Carol 选修 CS201, MATH201
    carol.courses = [cs201, math201]
    
    session.add_all([alice, bob, carol])
    session.commit()

def get_student_courses(session: Session, student_id: str):
    """获取学生的所有课程"""
    from sqlalchemy.orm import selectinload
    
    student = session.exec(
        select(Student)
        .options(selectinload(Student.courses).selectinload(Course.instructor))
        .where(Student.student_id == student_id)
    ).first()
    
    if student:
        print(f"学生: {student.name} ({student.student_id})")
        print(f"专业: {student.major}, 年级: {student.year}")
        print("选修课程:")
        
        for course in student.courses:
            instructor_name = course.instructor.name if course.instructor else "未分配"
            print(f"  - {course.code}: {course.name} ({course.credits}学分) - 教师: {instructor_name}")
    
    return student

def get_course_students(session: Session, course_code: str):
    """获取课程的所有学生"""
    from sqlalchemy.orm import selectinload
    
    course = session.exec(
        select(Course)
        .options(
            selectinload(Course.students),
            selectinload(Course.instructor)
        )
        .where(Course.code == course_code)
    ).first()
    
    if course:
        instructor_name = course.instructor.name if course.instructor else "未分配"
        print(f"课程: {course.code} - {course.name}")
        print(f"教师: {instructor_name}")
        print(f"学分: {course.credits}, 最大学生数: {course.max_students}")
        print(f"当前注册学生数: {len(course.students)}")
        print("注册学生:")
        
        for student in course.students:
            print(f"  - {student.student_id}: {student.name} ({student.major}, 年级{student.year})")
    
    return course
```

### 4.2 带有额外字段的多对多关系

```python
# advanced_many_to_many.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ProjectRole(str, Enum):
    """项目角色枚举"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

class ProjectMemberLink(SQLModel, table=True):
    """项目成员关联表（带额外字段）"""
    __tablename__ = "project_member"
    
    project_id: int = Field(foreign_key="project.id", primary_key=True)
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    
    # 额外字段
    role: ProjectRole = Field(default=ProjectRole.MEMBER)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    hours_contributed: float = Field(default=0.0)
    last_activity: Optional[datetime] = None

class User(SQLModel, table=True):
    """用户模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    full_name: str
    is_active: bool = Field(default=True)
    
    # 多对多关系：用户参与的项目
    projects: List["Project"] = Relationship(
        back_populates="members",
        link_table="project_member"
    )

class Project(SQLModel, table=True):
    """项目模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None
    status: str = Field(default="active")
    
    # 多对多关系：项目的成员
    members: List[User] = Relationship(
        back_populates="projects",
        link_table="project_member"
    )

# 高级操作类
class ProjectMembershipService:
    """项目成员管理服务"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_member_to_project(
        self,
        project_id: int,
        user_id: int,
        role: ProjectRole = ProjectRole.MEMBER
    ) -> Optional[ProjectMemberLink]:
        """添加成员到项目"""
        
        # 检查是否已经是成员
        existing = self.session.exec(
            select(ProjectMemberLink)
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.user_id == user_id
            )
        ).first()
        
        if existing:
            if not existing.is_active:
                # 重新激活成员
                existing.is_active = True
                existing.role = role
                existing.joined_at = datetime.utcnow()
                self.session.add(existing)
                self.session.commit()
                return existing
            else:
                return None  # 已经是活跃成员
        
        # 创建新的成员关系
        membership = ProjectMemberLink(
            project_id=project_id,
            user_id=user_id,
            role=role
        )
        
        self.session.add(membership)
        self.session.commit()
        
        return membership
    
    def remove_member_from_project(self, project_id: int, user_id: int) -> bool:
        """从项目中移除成员"""
        
        membership = self.session.exec(
            select(ProjectMemberLink)
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.user_id == user_id
            )
        ).first()
        
        if membership:
            membership.is_active = False
            self.session.add(membership)
            self.session.commit()
            return True
        
        return False
    
    def update_member_role(
        self,
        project_id: int,
        user_id: int,
        new_role: ProjectRole
    ) -> Optional[ProjectMemberLink]:
        """更新成员角色"""
        
        membership = self.session.exec(
            select(ProjectMemberLink)
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.user_id == user_id,
                ProjectMemberLink.is_active == True
            )
        ).first()
        
        if membership:
            membership.role = new_role
            self.session.add(membership)
            self.session.commit()
            return membership
        
        return None
    
    def get_project_members_with_details(self, project_id: int) -> List[dict]:
        """获取项目成员详细信息"""
        
        # 使用原生 SQL 查询获取详细信息
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                u.id as user_id,
                u.username,
                u.full_name,
                u.email,
                pm.role,
                pm.joined_at,
                pm.hours_contributed,
                pm.last_activity
            FROM users u
            JOIN project_member pm ON u.id = pm.user_id
            WHERE pm.project_id = :project_id 
                AND pm.is_active = true
            ORDER BY pm.joined_at
        """)
        
        results = self.session.exec(query, {"project_id": project_id}).all()
        
        return [
            {
                'user_id': r.user_id,
                'username': r.username,
                'full_name': r.full_name,
                'email': r.email,
                'role': r.role,
                'joined_at': r.joined_at,
                'hours_contributed': r.hours_contributed,
                'last_activity': r.last_activity
            }
            for r in results
        ]
    
    def get_user_projects_with_roles(self, user_id: int) -> List[dict]:
        """获取用户参与的项目及角色"""
        
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                p.id as project_id,
                p.name,
                p.description,
                p.status,
                p.deadline,
                pm.role,
                pm.joined_at,
                pm.hours_contributed
            FROM projects p
            JOIN project_member pm ON p.id = pm.project_id
            WHERE pm.user_id = :user_id 
                AND pm.is_active = true
            ORDER BY pm.joined_at DESC
        """)
        
        results = self.session.exec(query, {"user_id": user_id}).all()
        
        return [
            {
                'project_id': r.project_id,
                'name': r.name,
                'description': r.description,
                'status': r.status,
                'deadline': r.deadline,
                'role': r.role,
                'joined_at': r.joined_at,
                'hours_contributed': r.hours_contributed
            }
            for r in results
        ]
    
    def update_member_activity(
        self,
        project_id: int,
        user_id: int,
        hours_to_add: float = 0.0
    ) -> Optional[ProjectMemberLink]:
        """更新成员活动信息"""
        
        membership = self.session.exec(
            select(ProjectMemberLink)
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.user_id == user_id,
                ProjectMemberLink.is_active == True
            )
        ).first()
        
        if membership:
            membership.last_activity = datetime.utcnow()
            if hours_to_add > 0:
                membership.hours_contributed += hours_to_add
            
            self.session.add(membership)
            self.session.commit()
            return membership
        
        return None
    
    def get_project_statistics(self, project_id: int) -> dict:
        """获取项目统计信息"""
        
        from sqlalchemy import text, func
        
        # 获取成员统计
        member_stats = self.session.exec(
            select(
                func.count(ProjectMemberLink.user_id).label('total_members'),
                func.sum(ProjectMemberLink.hours_contributed).label('total_hours')
            )
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.is_active == True
            )
        ).first()
        
        # 按角色统计
        role_stats = self.session.exec(
            select(
                ProjectMemberLink.role,
                func.count(ProjectMemberLink.user_id).label('count')
            )
            .where(
                ProjectMemberLink.project_id == project_id,
                ProjectMemberLink.is_active == True
            )
            .group_by(ProjectMemberLink.role)
        ).all()
        
        return {
            'total_members': member_stats.total_members or 0,
            'total_hours': float(member_stats.total_hours or 0),
            'role_distribution': {
                role.role: role.count for role in role_stats
            }
        }
```

---

## 5. 关系配置和优化

### 5.1 加载策略

```python
# loading_strategies.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy.orm import selectinload, joinedload, subqueryload
from typing import Optional, List

class Author(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str
    
    # 配置不同的加载策略
    books: List["Book"] = Relationship(
        back_populates="author",
        sa_relationship_kwargs={
            "lazy": "select",  # 延迟加载（默认）
            "order_by": "Book.published_date.desc()"
        }
    )

class Book(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    published_date: datetime
    
    author_id: int = Field(foreign_key="author.id")
    
    author: Optional[Author] = Relationship(
        back_populates="books",
        sa_relationship_kwargs={"lazy": "joined"}  # 立即加载
    )
    
    reviews: List["Review"] = Relationship(
        back_populates="book",
        sa_relationship_kwargs={"lazy": "subquery"}  # 子查询加载
    )

class Review(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rating: int
    comment: str
    
    book_id: int = Field(foreign_key="book.id")
    
    book: Optional[Book] = Relationship(back_populates="reviews")

# 加载策略示例
class LoadingStrategiesDemo:
    """加载策略演示"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def demo_lazy_loading(self):
        """演示延迟加载（N+1 问题）"""
        print("=== 延迟加载演示 ===")
        
        # 这会导致 N+1 查询问题
        authors = self.session.exec(select(Author)).all()
        
        for author in authors:
            print(f"作者: {author.name}")
            # 每次访问 books 都会触发一次查询
            print(f"书籍数量: {len(author.books)}")
    
    def demo_eager_loading_joinedload(self):
        """演示预加载 - joinedload"""
        print("=== 预加载 (joinedload) 演示 ===")
        
        # 使用 LEFT JOIN 一次性加载所有数据
        authors = self.session.exec(
            select(Author)
            .options(joinedload(Author.books))
        ).unique().all()  # unique() 去除重复
        
        for author in authors:
            print(f"作者: {author.name}")
            print(f"书籍数量: {len(author.books)}")
            for book in author.books:
                print(f"  - {book.title}")
    
    def demo_eager_loading_selectinload(self):
        """演示预加载 - selectinload"""
        print("=== 预加载 (selectinload) 演示 ===")
        
        # 使用 IN 查询加载相关数据
        authors = self.session.exec(
            select(Author)
            .options(selectinload(Author.books))
        ).all()
        
        for author in authors:
            print(f"作者: {author.name}")
            print(f"书籍数量: {len(author.books)}")
    
    def demo_nested_loading(self):
        """演示嵌套加载"""
        print("=== 嵌套加载演示 ===")
        
        # 加载作者、书籍和评论
        authors = self.session.exec(
            select(Author)
            .options(
                selectinload(Author.books)
                .selectinload(Book.reviews)
            )
        ).all()
        
        for author in authors:
            print(f"作者: {author.name}")
            for book in author.books:
                print(f"  书籍: {book.title}")
                print(f"    评论数: {len(book.reviews)}")
                for review in book.reviews[:2]:  # 只显示前2个评论
                    print(f"      评分: {review.rating}/5")
    
    def demo_subquery_loading(self):
        """演示子查询加载"""
        print("=== 子查询加载演示 ===")
        
        # 使用子查询加载
        authors = self.session.exec(
            select(Author)
            .options(subqueryload(Author.books))
        ).all()
        
        for author in authors:
            print(f"作者: {author.name} - 书籍: {len(author.books)}")
    
    def demo_conditional_loading(self):
        """演示条件加载"""
        print("=== 条件加载演示 ===")
        
        # 只加载特定条件的相关数据
        from sqlalchemy import and_
        
        authors = self.session.exec(
            select(Author)
            .options(
                selectinload(Author.books).where(
                    Book.published_date >= datetime(2020, 1, 1)
                )
            )
        ).all()
        
        for author in authors:
            recent_books = [b for b in author.books if b.published_date >= datetime(2020, 1, 1)]
            print(f"作者: {author.name} - 2020年后的书籍: {len(recent_books)}")
```

### 5.2 关系配置选项

```python
# relationship_configuration.py
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import ForeignKey, UniqueConstraint
from typing import Optional, List

class Parent(SQLModel, table=True):
    """父模型 - 展示各种关系配置"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    
    # 基本一对多关系
    children: List["Child"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",  # 级联删除
            "order_by": "Child.created_at",   # 排序
            "lazy": "select",                 # 加载策略
            "passive_deletes": True           # 被动删除
        }
    )
    
    # 带条件的关系
    active_children: List["Child"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "and_(Parent.id == Child.parent_id, Child.is_active == True)",
            "viewonly": True  # 只读关系
        }
    )
    
    # 计数关系
    children_count: int = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Parent.id == Child.parent_id",
            "viewonly": True,
            "sync_backref": False
        }
    )

class Child(SQLModel, table=True):
    """子模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 外键
    parent_id: int = Field(foreign_key="parent.id")
    
    # 反向关系
    parent: Optional[Parent] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"lazy": "joined"}
    )

# 自引用关系示例
class Category(SQLModel, table=True):
    """分类模型 - 自引用关系"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    
    # 自引用外键
    parent_id: Optional[int] = Field(foreign_key="category.id")
    
    # 自引用关系
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "remote_side": "Category.id",  # 指定远程端
            "lazy": "joined"
        }
    )
    
    children: List["Category"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "Category.name"
        }
    )

# 多态关系示例
class Vehicle(SQLModel, table=True):
    """车辆基类"""
    id: Optional[int] = Field(default=None, primary_key=True)
    brand: str
    model: str
    year: int
    vehicle_type: str  # 多态标识符
    
    __mapper_args__ = {
        "polymorphic_identity": "vehicle",
        "polymorphic_on": "vehicle_type"
    }

class Car(Vehicle, table=True):
    """汽车模型"""
    doors: int = Field(default=4)
    fuel_type: str = Field(default="gasoline")
    
    __mapper_args__ = {
        "polymorphic_identity": "car"
    }

class Motorcycle(Vehicle, table=True):
    """摩托车模型"""
    engine_size: int  # cc
    has_sidecar: bool = Field(default=False)
    
    __mapper_args__ = {
        "polymorphic_identity": "motorcycle"
    }

# 关系配置工具类
class RelationshipConfigHelper:
    """关系配置助手类"""
    
    @staticmethod
    def create_one_to_one_config(cascade: bool = True, lazy: str = "select"):
        """创建一对一关系配置"""
        config = {
            "uselist": False,
            "lazy": lazy
        }
        
        if cascade:
            config["cascade"] = "all, delete-orphan"
        
        return config
    
    @staticmethod
    def create_one_to_many_config(
        cascade: bool = True,
        order_by: Optional[str] = None,
        lazy: str = "select"
    ):
        """创建一对多关系配置"""
        config = {
            "lazy": lazy
        }
        
        if cascade:
            config["cascade"] = "all, delete-orphan"
        
        if order_by:
            config["order_by"] = order_by
        
        return config
    
    @staticmethod
    def create_many_to_many_config(
        order_by: Optional[str] = None,
        lazy: str = "select"
    ):
        """创建多对多关系配置"""
        config = {
            "lazy": lazy
        }
        
        if order_by:
            config["order_by"] = order_by
        
        return config
```

### 5.3 性能优化技巧

```python
# performance_optimization.py
from sqlmodel import SQLModel, Field, Relationship, Session, select
from sqlalchemy.orm import selectinload, joinedload, contains_eager
from sqlalchemy import func, and_, or_
from typing import Optional, List

class OptimizedQueryService:
    """优化查询服务"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_users_with_recent_posts(self, days: int = 30) -> List[User]:
        """获取有最近文章的用户（优化版）"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 使用 join 和 contains_eager 优化
        users = self.session.exec(
            select(User)
            .join(Post)
            .options(contains_eager(User.posts))
            .where(Post.created_at >= cutoff_date)
            .order_by(User.id, Post.created_at.desc())
        ).unique().all()
        
        return users
    
    def get_popular_posts_with_stats(self, limit: int = 10) -> List[dict]:
        """获取热门文章及统计信息"""
        
        # 使用子查询计算统计信息
        comment_count_subq = (
            select(
                Comment.post_id,
                func.count(Comment.id).label('comment_count')
            )
            .group_by(Comment.post_id)
            .subquery()
        )
        
        # 主查询
        posts = self.session.exec(
            select(
                Post,
                func.coalesce(comment_count_subq.c.comment_count, 0).label('comment_count')
            )
            .outerjoin(comment_count_subq, Post.id == comment_count_subq.c.post_id)
            .options(joinedload(Post.author))
            .order_by(func.coalesce(comment_count_subq.c.comment_count, 0).desc())
            .limit(limit)
        ).all()
        
        return [
            {
                'post': post[0],
                'comment_count': post[1],
                'author_name': post[0].author.name if post[0].author else None
            }
            for post in posts
        ]
    
    def bulk_load_user_data(self, user_ids: List[int]) -> dict:
        """批量加载用户数据"""
        
        # 批量加载用户基本信息
        users = self.session.exec(
            select(User)
            .where(User.id.in_(user_ids))
        ).all()
        
        # 批量加载用户文章
        posts = self.session.exec(
            select(Post)
            .options(joinedload(Post.author))
            .where(Post.author_id.in_(user_ids))
            .order_by(Post.created_at.desc())
        ).all()
        
        # 批量加载用户资料
        profiles = self.session.exec(
            select(UserProfile)
            .where(UserProfile.user_id.in_(user_ids))
        ).all()
        
        # 组织数据
        user_data = {}
        for user in users:
            user_data[user.id] = {
                'user': user,
                'posts': [],
                'profile': None
            }
        
        # 分配文章
        for post in posts:
            if post.author_id in user_data:
                user_data[post.author_id]['posts'].append(post)
        
        # 分配资料
        for profile in profiles:
            if profile.user_id in user_data:
                user_data[profile.user_id]['profile'] = profile
        
        return user_data
    
    def get_category_tree_optimized(self) -> List[dict]:
        """优化的分类树查询"""
        
        # 一次性加载所有分类
        categories = self.session.exec(
            select(Category)
            .order_by(Category.parent_id.nullsfirst(), Category.name)
        ).all()
        
        # 构建树结构
        category_map = {cat.id: cat for cat in categories}
        tree = []
        
        for category in categories:
            if category.parent_id is None:
                # 根分类
                tree.append(self._build_category_node(category, category_map))
        
        return tree
    
    def _build_category_node(self, category: Category, category_map: dict) -> dict:
        """构建分类节点"""
        node = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'children': []
        }
        
        # 查找子分类
        for cat in category_map.values():
            if cat.parent_id == category.id:
                child_node = self._build_category_node(cat, category_map)
                node['children'].append(child_node)
        
        return node
    
    def get_user_activity_summary(self, user_id: int, days: int = 30) -> dict:
        """获取用户活动摘要"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 使用单个查询获取所有统计信息
        from sqlalchemy import text
        
        query = text("""
            SELECT 
                COUNT(DISTINCT p.id) as post_count,
                COUNT(DISTINCT c.id) as comment_count,
                COALESCE(SUM(CASE WHEN p.created_at >= :cutoff_date THEN 1 ELSE 0 END), 0) as recent_posts,
                COALESCE(SUM(CASE WHEN c.created_at >= :cutoff_date THEN 1 ELSE 0 END), 0) as recent_comments
            FROM users u
            LEFT JOIN posts p ON u.id = p.author_id
            LEFT JOIN comments c ON u.id = c.author_id
            WHERE u.id = :user_id
        """)
        
        result = self.session.exec(
            query,
            {"user_id": user_id, "cutoff_date": cutoff_date}
        ).first()
        
        return {
            'total_posts': result.post_count,
            'total_comments': result.comment_count,
            'recent_posts': result.recent_posts,
            'recent_comments': result.recent_comments,
            'activity_score': result.recent_posts * 2 + result.recent_comments
        }
```

---

## 6. 关系查询技巧

### 6.1 复杂关系查询

```python
# complex_relationship_queries.py
from sqlmodel import SQLModel, Session, select
from sqlalchemy import func, and_, or_, exists, not_
from sqlalchemy.orm import aliased
from typing import List, Optional

class AdvancedRelationshipQueries:
    """高级关系查询"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def find_users_without_posts(self) -> List[User]:
        """查找没有发布文章的用户"""
        
        users = self.session.exec(
            select(User)
            .where(
                ~exists().where(Post.author_id == User.id)
            )
        ).all()
        
        return users
    
    def find_posts_with_multiple_tags(self, min_tags: int = 3) -> List[Post]:
        """查找有多个标签的文章"""
        
        posts = self.session.exec(
            select(Post)
            .join(PostTagLink)
            .group_by(Post.id)
            .having(func.count(PostTagLink.tag_id) >= min_tags)
        ).all()
        
        return posts
    
    def find_users_with_posts_in_multiple_categories(self) -> List[User]:
        """查找在多个分类中发布文章的用户"""
        
        users = self.session.exec(
            select(User)
            .join(Post)
            .join(Category)
            .group_by(User.id)
            .having(func.count(func.distinct(Category.id)) > 1)
        ).all()
        
        return users
    
    def find_popular_tag_combinations(self, min_frequency: int = 5) -> List[dict]:
        """查找流行的标签组合"""
        
        # 使用自连接查找标签组合
        tag1 = aliased(PostTagLink)
        tag2 = aliased(PostTagLink)
        
        combinations = self.session.exec(
            select(
                tag1.tag_id.label('tag1_id'),
                tag2.tag_id.label('tag2_id'),
                func.count().label('frequency')
            )
            .select_from(tag1)
            .join(tag2, tag1.post_id == tag2.post_id)
            .where(tag1.tag_id < tag2.tag_id)  # 避免重复组合
            .group_by(tag1.tag_id, tag2.tag_id)
            .having(func.count() >= min_frequency)
            .order_by(func.count().desc())
        ).all()
        
        # 获取标签名称
        tag_names = {}
        for combo in combinations:
            for tag_id in [combo.tag1_id, combo.tag2_id]:
                if tag_id not in tag_names:
                    tag = self.session.get(Tag, tag_id)
                    tag_names[tag_id] = tag.name if tag else f"Tag-{tag_id}"
        
        return [
            {
                'tag1': tag_names[combo.tag1_id],
                'tag2': tag_names[combo.tag2_id],
                'frequency': combo.frequency
            }
            for combo in combinations
        ]
    
    def find_users_by_activity_pattern(
        self,
        min_posts: int = 5,
        min_comments: int = 10
    ) -> List[dict]:
        """根据活动模式查找用户"""
        
        # 子查询：用户文章数
        post_counts = (
            select(
                Post.author_id,
                func.count(Post.id).label('post_count')
            )
            .group_by(Post.author_id)
            .subquery()
        )
        
        # 子查询：用户评论数
        comment_counts = (
            select(
                Comment.author_id,
                func.count(Comment.id).label('comment_count')
            )
            .group_by(Comment.author_id)
            .subquery()
        )
        
        # 主查询
        results = self.session.exec(
            select(
                User,
                func.coalesce(post_counts.c.post_count, 0).label('posts'),
                func.coalesce(comment_counts.c.comment_count, 0).label('comments')
            )
            .outerjoin(post_counts, User.id == post_counts.c.author_id)
            .outerjoin(comment_counts, User.id == comment_counts.c.author_id)
            .where(
                and_(
                    func.coalesce(post_counts.c.post_count, 0) >= min_posts,
                    func.coalesce(comment_counts.c.comment_count, 0) >= min_comments
                )
            )
        ).all()
        
        return [
            {
                'user': result[0],
                'post_count': result[1],
                'comment_count': result[2],
                'activity_ratio': result[2] / max(result[1], 1)  # 评论/文章比率
            }
            for result in results
        ]
    
    def find_trending_posts(self, days: int = 7) -> List[dict]:
        """查找趋势文章"""
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 计算文章的趋势分数
        trending_posts = self.session.exec(
            select(
                Post,
                func.count(Comment.id).label('recent_comments'),
                func.count(func.distinct(Comment.author_id)).label('unique_commenters')
            )
            .outerjoin(
                Comment,
                and_(
                    Comment.post_id == Post.id,
                    Comment.created_at >= cutoff_date
                )
            )
            .where(Post.created_at >= cutoff_date - timedelta(days=30))  # 最近30天的文章
            .group_by(Post.id)
            .order_by(
                (func.count(Comment.id) * 2 + func.count(func.distinct(Comment.author_id))).desc()
            )
            .limit(20)
        ).all()
        
        return [
             {
                 'post': result[0],
                 'recent_comments': result[1],
                 'unique_commenters': result[2],
                 'trend_score': result[1] * 2 + result[2]
             }
             for result in trending_posts
         ]
```

### 6.2 关系数据的聚合查询

```python
# aggregation_queries.py
from sqlmodel import SQLModel, Session, select
from sqlalchemy import func, case, extract
from typing import List, Dict, Any

class RelationshipAggregationQueries:
    """关系数据聚合查询"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_user_statistics(self) -> List[Dict[str, Any]]:
        """获取用户统计信息"""
        
        stats = self.session.exec(
            select(
                User.id,
                User.name,
                func.count(func.distinct(Post.id)).label('post_count'),
                func.count(func.distinct(Comment.id)).label('comment_count'),
                func.avg(Post.view_count).label('avg_post_views'),
                func.max(Post.created_at).label('last_post_date')
            )
            .outerjoin(Post, User.id == Post.author_id)
            .outerjoin(Comment, User.id == Comment.author_id)
            .group_by(User.id, User.name)
            .order_by(func.count(func.distinct(Post.id)).desc())
        ).all()
        
        return [
            {
                'user_id': stat.id,
                'name': stat.name,
                'post_count': stat.post_count,
                'comment_count': stat.comment_count,
                'avg_post_views': float(stat.avg_post_views or 0),
                'last_post_date': stat.last_post_date
            }
            for stat in stats
        ]
    
    def get_category_analytics(self) -> List[Dict[str, Any]]:
        """获取分类分析数据"""
        
        analytics = self.session.exec(
            select(
                Category.id,
                Category.name,
                func.count(Post.id).label('post_count'),
                func.count(func.distinct(Post.author_id)).label('author_count'),
                func.sum(Post.view_count).label('total_views'),
                func.avg(Post.view_count).label('avg_views'),
                func.count(Comment.id).label('total_comments')
            )
            .outerjoin(Post, Category.id == Post.category_id)
            .outerjoin(Comment, Post.id == Comment.post_id)
            .group_by(Category.id, Category.name)
            .order_by(func.count(Post.id).desc())
        ).all()
        
        return [
            {
                'category_id': item.id,
                'name': item.name,
                'post_count': item.post_count,
                'author_count': item.author_count,
                'total_views': item.total_views or 0,
                'avg_views': float(item.avg_views or 0),
                'total_comments': item.total_comments,
                'engagement_rate': (item.total_comments / max(item.post_count, 1)) if item.post_count else 0
            }
            for item in analytics
        ]
    
    def get_monthly_activity_trends(self, year: int) -> List[Dict[str, Any]]:
        """获取月度活动趋势"""
        
        trends = self.session.exec(
            select(
                extract('month', Post.created_at).label('month'),
                func.count(Post.id).label('post_count'),
                func.count(func.distinct(Post.author_id)).label('active_authors'),
                func.sum(Post.view_count).label('total_views')
            )
            .where(extract('year', Post.created_at) == year)
            .group_by(extract('month', Post.created_at))
            .order_by(extract('month', Post.created_at))
        ).all()
        
        return [
            {
                'month': int(trend.month),
                'post_count': trend.post_count,
                'active_authors': trend.active_authors,
                'total_views': trend.total_views or 0,
                'avg_posts_per_author': trend.post_count / max(trend.active_authors, 1)
            }
            for trend in trends
        ]
    
    def get_tag_popularity_ranking(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取标签流行度排名"""
        
        rankings = self.session.exec(
            select(
                Tag.id,
                Tag.name,
                func.count(PostTagLink.post_id).label('usage_count'),
                func.count(func.distinct(Post.author_id)).label('author_count'),
                func.sum(Post.view_count).label('total_views'),
                func.avg(Post.view_count).label('avg_views')
            )
            .join(PostTagLink, Tag.id == PostTagLink.tag_id)
            .join(Post, PostTagLink.post_id == Post.id)
            .group_by(Tag.id, Tag.name)
            .order_by(func.count(PostTagLink.post_id).desc())
            .limit(limit)
        ).all()
        
        return [
            {
                'tag_id': rank.id,
                'name': rank.name,
                'usage_count': rank.usage_count,
                'author_count': rank.author_count,
                'total_views': rank.total_views or 0,
                'avg_views': float(rank.avg_views or 0),
                'popularity_score': rank.usage_count * 2 + rank.author_count
            }
            for rank in rankings
        ]
    
    def get_user_engagement_metrics(self, user_id: int) -> Dict[str, Any]:
        """获取用户参与度指标"""
        
        # 基础统计
        basic_stats = self.session.exec(
            select(
                func.count(func.distinct(Post.id)).label('post_count'),
                func.count(func.distinct(Comment.id)).label('comment_count'),
                func.sum(Post.view_count).label('total_views'),
                func.avg(Post.view_count).label('avg_views')
            )
            .select_from(User)
            .outerjoin(Post, User.id == Post.author_id)
            .outerjoin(Comment, User.id == Comment.author_id)
            .where(User.id == user_id)
        ).first()
        
        # 获得的评论数（别人对用户文章的评论）
        received_comments = self.session.exec(
            select(func.count(Comment.id))
            .select_from(Post)
            .join(Comment, Post.id == Comment.post_id)
            .where(
                and_(
                    Post.author_id == user_id,
                    Comment.author_id != user_id  # 排除自己的评论
                )
            )
        ).first()
        
        # 使用的标签数
        tag_count = self.session.exec(
            select(func.count(func.distinct(PostTagLink.tag_id)))
            .select_from(Post)
            .join(PostTagLink, Post.id == PostTagLink.post_id)
            .where(Post.author_id == user_id)
        ).first()
        
        return {
            'post_count': basic_stats.post_count,
            'comment_count': basic_stats.comment_count,
            'total_views': basic_stats.total_views or 0,
            'avg_views': float(basic_stats.avg_views or 0),
            'received_comments': received_comments or 0,
            'unique_tags_used': tag_count or 0,
            'engagement_ratio': (received_comments or 0) / max(basic_stats.post_count, 1),
            'activity_score': (
                (basic_stats.post_count * 3) +
                (basic_stats.comment_count * 1) +
                ((received_comments or 0) * 2)
            )
        }
```

---

## 7. 最佳实践与性能优化

### 7.1 关系设计最佳实践

```python
# relationship_best_practices.py
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Index, CheckConstraint
from typing import Optional, List
from datetime import datetime

# 1. 合理的外键约束
class OptimizedUser(SQLModel, table=True):
    """优化的用户模型"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    email: str = Field(index=True, unique=True, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    is_active: bool = Field(default=True, index=True)
    
    # 关系配置
    posts: List["OptimizedPost"] = Relationship(
        back_populates="author",
        sa_relationship_kwargs={
            "lazy": "select",  # 按需加载
            "cascade": "all, delete-orphan",
            "order_by": "OptimizedPost.created_at.desc()"
        }
    )
    
    profile: Optional["OptimizedUserProfile"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={
            "lazy": "joined",  # 通常需要一起加载
            "cascade": "all, delete-orphan"
        }
    )

class OptimizedPost(SQLModel, table=True):
    """优化的文章模型"""
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200, index=True)
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    view_count: int = Field(default=0, index=True)
    is_published: bool = Field(default=False, index=True)
    
    # 外键设计
    author_id: int = Field(foreign_key="users.id", index=True)
    category_id: Optional[int] = Field(foreign_key="categories.id", index=True)
    
    # 关系配置
    author: Optional[OptimizedUser] = Relationship(
        back_populates="posts",
        sa_relationship_kwargs={"lazy": "joined"}  # 文章通常需要作者信息
    )
    
    category: Optional["OptimizedCategory"] = Relationship(
        sa_relationship_kwargs={"lazy": "joined"}
    )
    
    comments: List["OptimizedComment"] = Relationship(
        back_populates="post",
        sa_relationship_kwargs={
            "lazy": "select",
            "cascade": "all, delete-orphan",
            "order_by": "OptimizedComment.created_at.asc()"
        }
    )
    
    # 复合索引
    __table_args__ = (
        Index('idx_author_created', 'author_id', 'created_at'),
        Index('idx_category_published', 'category_id', 'is_published'),
        Index('idx_published_created', 'is_published', 'created_at'),
        CheckConstraint('view_count >= 0', name='check_view_count_positive')
    )

class OptimizedComment(SQLModel, table=True):
    """优化的评论模型"""
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    is_approved: bool = Field(default=True, index=True)
    
    # 外键
    post_id: int = Field(foreign_key="posts.id", index=True)
    author_id: int = Field(foreign_key="users.id", index=True)
    parent_id: Optional[int] = Field(foreign_key="comments.id")  # 支持回复
    
    # 关系
    post: Optional[OptimizedPost] = Relationship(
        back_populates="comments",
        sa_relationship_kwargs={"lazy": "joined"}
    )
    
    author: Optional[OptimizedUser] = Relationship(
        sa_relationship_kwargs={"lazy": "joined"}
    )
    
    # 自引用关系（回复）
    parent: Optional["OptimizedComment"] = Relationship(
        sa_relationship_kwargs={
            "remote_side": "OptimizedComment.id",
            "lazy": "joined"
        }
    )
    
    replies: List["OptimizedComment"] = Relationship(
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "OptimizedComment.created_at.asc()"
        }
    )
    
    __table_args__ = (
        Index('idx_post_created', 'post_id', 'created_at'),
        Index('idx_author_created', 'author_id', 'created_at'),
    )

# 2. 性能优化工具类
class RelationshipPerformanceOptimizer:
    """关系性能优化器"""
    
    @staticmethod
    def get_optimized_loading_strategy(relationship_type: str, usage_pattern: str) -> dict:
        """根据使用模式获取优化的加载策略"""
        
        strategies = {
            "one_to_one": {
                "always_needed": {"lazy": "joined"},
                "sometimes_needed": {"lazy": "select"},
                "rarely_needed": {"lazy": "noload"}
            },
            "one_to_many": {
                "small_collections": {"lazy": "joined"},
                "medium_collections": {"lazy": "select"},
                "large_collections": {"lazy": "dynamic"}
            },
            "many_to_many": {
                "small_collections": {"lazy": "selectin"},
                "medium_collections": {"lazy": "select"},
                "large_collections": {"lazy": "dynamic"}
            }
        }
        
        return strategies.get(relationship_type, {}).get(usage_pattern, {"lazy": "select"})
    
    @staticmethod
    def create_optimized_indexes(model_class, relationships: List[str]) -> List[Index]:
        """为关系创建优化索引"""
        indexes = []
        
        for rel in relationships:
            # 外键索引
            fk_field = f"{rel}_id"
            if hasattr(model_class, fk_field):
                indexes.append(Index(f"idx_{fk_field}", fk_field))
            
            # 复合索引（外键 + 创建时间）
            if hasattr(model_class, 'created_at'):
                indexes.append(Index(f"idx_{fk_field}_created", fk_field, 'created_at'))
        
        return indexes
```

### 7.2 常见问题与解决方案

```python
# common_issues_solutions.py
from sqlmodel import SQLModel, Session, select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy import event
from typing import List

class RelationshipTroubleshooting:
    """关系问题排查与解决"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def solve_n_plus_1_problem(self, user_ids: List[int]) -> List[dict]:
        """解决 N+1 查询问题"""
        
        # 错误方式：会产生 N+1 查询
        # users = session.exec(select(User).where(User.id.in_(user_ids))).all()
        # for user in users:
        #     print(f"{user.name}: {len(user.posts)} posts")  # 每次访问都会查询
        
        # 正确方式：使用预加载
        users = self.session.exec(
            select(User)
            .options(selectinload(User.posts))  # 预加载文章
            .where(User.id.in_(user_ids))
        ).all()
        
        return [
            {
                'user': user.name,
                'post_count': len(user.posts),
                'posts': [post.title for post in user.posts]
            }
            for user in users
        ]
    
    def handle_circular_references(self) -> dict:
        """处理循环引用问题"""
        
        # 使用 back_populates 而不是 backref
        # 在序列化时排除循环引用
        
        user = self.session.exec(
            select(User)
            .options(selectinload(User.posts))
            .first()
        ).first()
        
        if user:
            # 安全的序列化方式
            return {
                'id': user.id,
                'name': user.name,
                'posts': [
                    {
                        'id': post.id,
                        'title': post.title,
                        'author_id': post.author_id  # 只包含 ID，避免循环
                    }
                    for post in user.posts
                ]
            }
        
        return {}
    
    def optimize_large_collections(self, user_id: int) -> dict:
        """优化大集合的处理"""
        
        # 对于大量数据，使用分页和计数
        from sqlalchemy import func
        
        # 获取总数
        total_posts = self.session.exec(
            select(func.count(Post.id))
            .where(Post.author_id == user_id)
        ).first()
        
        # 分页获取数据
        recent_posts = self.session.exec(
            select(Post)
            .where(Post.author_id == user_id)
            .order_by(Post.created_at.desc())
            .limit(10)
        ).all()
        
        return {
            'total_posts': total_posts,
            'recent_posts': [
                {
                    'id': post.id,
                    'title': post.title,
                    'created_at': post.created_at.isoformat()
                }
                for post in recent_posts
            ]
        }
    
    def debug_relationship_loading(self):
        """调试关系加载"""
        
        # 启用 SQL 日志
        import logging
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
        
        # 监听查询事件
        @event.listens_for(self.session.bind, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            print(f"SQL: {statement}")
            print(f"Parameters: {parameters}")
        
        # 执行查询并观察 SQL
        users = self.session.exec(
            select(User)
            .options(joinedload(User.posts))
            .limit(5)
        ).all()
        
        return len(users)

# 3. 关系验证工具
class RelationshipValidator:
    """关系验证工具"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def validate_foreign_key_integrity(self) -> List[dict]:
        """验证外键完整性"""
        issues = []
        
        # 检查孤立的文章（作者不存在）
        orphaned_posts = self.session.exec(
            select(Post)
            .outerjoin(User, Post.author_id == User.id)
            .where(User.id.is_(None))
        ).all()
        
        if orphaned_posts:
            issues.append({
                'type': 'orphaned_posts',
                'count': len(orphaned_posts),
                'post_ids': [post.id for post in orphaned_posts]
            })
        
        # 检查孤立的评论（文章不存在）
        orphaned_comments = self.session.exec(
            select(Comment)
            .outerjoin(Post, Comment.post_id == Post.id)
            .where(Post.id.is_(None))
        ).all()
        
        if orphaned_comments:
            issues.append({
                'type': 'orphaned_comments',
                'count': len(orphaned_comments),
                'comment_ids': [comment.id for comment in orphaned_comments]
            })
        
        return issues
    
    def validate_relationship_consistency(self) -> List[dict]:
        """验证关系一致性"""
        issues = []
        
        # 检查双向关系一致性
        users_with_posts = self.session.exec(
            select(User)
            .join(Post)
            .options(selectinload(User.posts))
        ).unique().all()
        
        for user in users_with_posts:
            for post in user.posts:
                if post.author_id != user.id:
                    issues.append({
                        'type': 'relationship_inconsistency',
                        'user_id': user.id,
                        'post_id': post.id,
                        'expected_author_id': user.id,
                        'actual_author_id': post.author_id
                    })
        
        return issues
```

---

## 8. 本章总结

### 8.1 核心概念回顾

本章详细介绍了 SQLModel 中关系和关联的定义与使用：

1. **关系类型**：
   - 一对一关系：用户与用户资料
   - 一对多关系：用户与文章、文章与评论
   - 多对多关系：文章与标签
   - 自引用关系：分类树、评论回复

2. **关系配置**：
   - `back_populates`：双向关系配置
   - `sa_relationship_kwargs`：SQLAlchemy 关系参数
   - 加载策略：`lazy`、`cascade`、`order_by`

3. **性能优化**：
   - 预加载策略：`joinedload`、`selectinload`、`contains_eager`
   - 查询优化：避免 N+1 问题、批量加载
   - 索引设计：外键索引、复合索引

### 8.2 最佳实践总结

1. **设计原则**：
   - 合理设计外键约束
   - 选择适当的加载策略
   - 避免循环引用问题
   - 考虑数据量和访问模式

2. **性能优化**：
   - 使用预加载避免 N+1 查询
   - 为外键字段创建索引
   - 对大集合使用分页
   - 监控和分析查询性能

3. **代码组织**：
   - 使用 `back_populates` 而不是 `backref`
   - 将关系配置集中管理
   - 创建专门的查询服务类
   - 实现关系验证工具

### 8.3 常见陷阱与避免方法

1. **N+1 查询问题**：
   - 问题：在循环中访问关系属性
   - 解决：使用预加载策略

2. **循环引用**：
   - 问题：序列化时出现无限循环
   - 解决：使用 `back_populates`，序列化时排除循环字段

3. **内存占用过大**：
   - 问题：一次性加载大量关联数据
   - 解决：使用分页、延迟加载或动态关系

4. **外键约束错误**：
   - 问题：删除被引用的记录
   - 解决：正确配置 `cascade` 选项

### 8.4 实践检查清单

- [ ] 正确定义了所有关系类型
- [ ] 配置了适当的加载策略
- [ ] 创建了必要的数据库索引
- [ ] 实现了关系数据的查询方法
- [ ] 处理了 N+1 查询问题
- [ ] 验证了外键完整性
- [ ] 测试了关系的增删改查操作
- [ ] 优化了复杂查询的性能
- [ ] 实现了数据验证和错误处理
- [ ] 编写了相关的单元测试

### 8.5 下一步学习

完成本章学习后，建议继续学习：

1. **第6章：数据验证与约束** - 学习如何实现复杂的数据验证规则
2. **第7章：迁移与版本管理** - 掌握数据库结构变更管理
3. **第8章：高级查询技巧** - 深入学习复杂查询和性能优化
4. **第9章：测试策略** - 学习如何测试包含关系的模型

### 8.6 扩展练习

1. **博客系统关系设计**：
   - 设计完整的博客系统关系模型
   - 实现用户、文章、评论、分类、标签的关系
   - 添加点赞、收藏等功能

2. **电商系统关系优化**：
   - 设计商品、订单、用户的关系
   - 实现购物车、订单历史查询
   - 优化商品推荐查询性能

3. **社交网络关系**：
   - 实现用户关注关系（多对多自引用）
   - 设计动态时间线查询
   - 实现好友推荐算法

4. **性能基准测试**：
   - 创建大量测试数据
   - 比较不同加载策略的性能
   - 分析查询执行计划
   - 优化慢查询

通过本章的学习，你应该能够熟练地在 SQLModel 中设计和实现各种类型的关系，并能够优化关系查询的性能。关系是数据库设计的核心，掌握好关系的使用对于构建高效的应用程序至关重要。