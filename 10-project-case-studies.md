# 第十章：项目实战案例

## 概述

本章将通过三个完整的项目实战案例，展示如何在真实场景中应用 SQLModel 构建生产级应用。每个案例都涵盖了从需求分析、架构设计、代码实现到部署运维的完整流程，帮助你将前面学到的知识融会贯通。

### 本章目标

- 掌握完整项目的开发流程
- 学习不同领域的业务建模方法
- 理解生产环境的最佳实践
- 培养解决实际问题的能力

### 案例概览

1. **博客管理系统** - 内容管理类应用
2. **电商订单系统** - 交易处理类应用
3. **任务管理平台** - 协作工具类应用

---

## 案例一：博客管理系统

### 1.1 需求分析

#### 功能需求
- 用户注册、登录、权限管理
- 文章创建、编辑、发布、删除
- 分类和标签管理
- 评论系统
- 搜索功能
- 统计分析

#### 非功能需求
- 支持并发访问
- 响应时间 < 200ms
- 数据安全性
- SEO 友好

### 1.2 架构设计

```python
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Session, create_engine, select
from sqlalchemy import Index, text
from pydantic import EmailStr, validator
import hashlib
import secrets

# 枚举类型定义
class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    EDITOR = "editor"
    AUTHOR = "author"
    READER = "reader"

class PostStatus(str, Enum):
    """文章状态"""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CommentStatus(str, Enum):
    """评论状态"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# 关联表
class PostTagLink(SQLModel, table=True):
    """文章标签关联表"""
    __tablename__ = "post_tag_links"
    
    post_id: Optional[int] = Field(default=None, foreign_key="posts.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tags.id", primary_key=True)

# 基础模型
class TimestampMixin(SQLModel):
    """时间戳混入类"""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)

class User(TimestampMixin, table=True):
    """用户模型"""
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=50)
    email: EmailStr = Field(index=True, unique=True)
    password_hash: str = Field(max_length=255)
    display_name: str = Field(max_length=100)
    bio: Optional[str] = Field(default=None, max_length=500)
    avatar_url: Optional[str] = Field(default=None, max_length=255)
    role: UserRole = Field(default=UserRole.READER)
    is_active: bool = Field(default=True)
    email_verified: bool = Field(default=False)
    last_login: Optional[datetime] = Field(default=None)
    
    # 关系
    posts: List["Post"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")
    
    @validator('password_hash')
    def validate_password_hash(cls, v):
        if len(v) < 60:  # bcrypt hash length
            raise ValueError('Invalid password hash')
        return v
    
    def set_password(self, password: str) -> None:
        """设置密码"""
        import bcrypt
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), 
            bcrypt.gensalt()
        ).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """验证密码"""
        import bcrypt
        return bcrypt.checkpw(
            password.encode('utf-8'), 
            self.password_hash.encode('utf-8')
        )
    
    def generate_api_token(self) -> str:
        """生成 API 令牌"""
        return secrets.token_urlsafe(32)

class Category(TimestampMixin, table=True):
    """分类模型"""
    __tablename__ = "categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=100)
    slug: str = Field(index=True, unique=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    
    # 关系
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"}
    )
    children: List["Category"] = Relationship(back_populates="parent")
    posts: List["Post"] = Relationship(back_populates="category")
    
    @validator('slug')
    def validate_slug(cls, v):
        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        return v

class Tag(TimestampMixin, table=True):
    """标签模型"""
    __tablename__ = "tags"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True, max_length=50)
    slug: str = Field(index=True, unique=True, max_length=50)
    description: Optional[str] = Field(default=None, max_length=200)
    color: Optional[str] = Field(default=None, max_length=7)  # HEX color
    usage_count: int = Field(default=0)
    
    # 关系
    posts: List["Post"] = Relationship(
        back_populates="tags",
        link_model=PostTagLink
    )
    
    @validator('color')
    def validate_color(cls, v):
        if v and not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be a valid HEX color code')
        return v

class Post(TimestampMixin, table=True):
    """文章模型"""
    __tablename__ = "posts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=200)
    slug: str = Field(index=True, unique=True, max_length=200)
    excerpt: Optional[str] = Field(default=None, max_length=500)
    content: str
    status: PostStatus = Field(default=PostStatus.DRAFT, index=True)
    published_at: Optional[datetime] = Field(default=None, index=True)
    featured_image: Optional[str] = Field(default=None, max_length=255)
    meta_title: Optional[str] = Field(default=None, max_length=200)
    meta_description: Optional[str] = Field(default=None, max_length=300)
    view_count: int = Field(default=0)
    like_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    is_featured: bool = Field(default=False)
    allow_comments: bool = Field(default=True)
    
    # 外键
    author_id: int = Field(foreign_key="users.id", index=True)
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id", index=True)
    
    # 关系
    author: User = Relationship(back_populates="posts")
    category: Optional[Category] = Relationship(back_populates="posts")
    tags: List[Tag] = Relationship(
        back_populates="posts",
        link_model=PostTagLink
    )
    comments: List["Comment"] = Relationship(back_populates="post")
    
    def publish(self) -> None:
        """发布文章"""
        self.status = PostStatus.PUBLISHED
        self.published_at = datetime.now()
    
    def generate_excerpt(self, length: int = 200) -> str:
        """生成摘要"""
        if self.excerpt:
            return self.excerpt
        
        # 从内容中提取纯文本
        import re
        text = re.sub(r'<[^>]+>', '', self.content)
        return text[:length] + '...' if len(text) > length else text
    
    def get_reading_time(self) -> int:
        """计算阅读时间（分钟）"""
        import re
        text = re.sub(r'<[^>]+>', '', self.content)
        word_count = len(text.split())
        return max(1, word_count // 200)  # 假设每分钟阅读200字

class Comment(TimestampMixin, table=True):
    """评论模型"""
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(max_length=1000)
    status: CommentStatus = Field(default=CommentStatus.PENDING, index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    like_count: int = Field(default=0)
    
    # 外键
    post_id: int = Field(foreign_key="posts.id", index=True)
    author_id: Optional[int] = Field(default=None, foreign_key="users.id", index=True)
    parent_id: Optional[int] = Field(default=None, foreign_key="comments.id")
    
    # 关系
    post: Post = Relationship(back_populates="comments")
    author: Optional[User] = Relationship(back_populates="comments")
    parent: Optional["Comment"] = Relationship(
        back_populates="replies",
        sa_relationship_kwargs={"remote_side": "Comment.id"}
    )
    replies: List["Comment"] = Relationship(back_populates="parent")
    
    def approve(self) -> None:
        """批准评论"""
        self.status = CommentStatus.APPROVED
    
    def reject(self) -> None:
        """拒绝评论"""
        self.status = CommentStatus.REJECTED

# 数据库索引
Index('idx_posts_status_published', Post.status, Post.published_at)
Index('idx_posts_author_status', Post.author_id, Post.status)
Index('idx_comments_post_status', Comment.post_id, Comment.status)
Index('idx_users_email_active', User.email, User.is_active)
```

### 1.3 服务层实现

```python
from typing import Optional, List, Dict, Any
from sqlmodel import Session, select, func, and_, or_
from sqlalchemy import desc, asc
from datetime import datetime, timedelta
import re

class BlogService:
    """博客服务类"""
    
    def __init__(self, session: Session):
        self.session = session
    
    # 用户管理
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        # 检查用户名和邮箱是否已存在
        existing_user = self.session.exec(
            select(User).where(
                or_(User.username == user_data['username'], 
                    User.email == user_data['email'])
            )
        ).first()
        
        if existing_user:
            if existing_user.username == user_data['username']:
                raise ValueError("用户名已存在")
            else:
                raise ValueError("邮箱已存在")
        
        user = User(**user_data)
        if 'password' in user_data:
            user.set_password(user_data['password'])
        
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """用户认证"""
        user = self.session.exec(
            select(User).where(
                and_(User.username == username, User.is_active == True)
            )
        ).first()
        
        if user and user.check_password(password):
            user.last_login = datetime.now()
            self.session.add(user)
            self.session.commit()
            return user
        
        return None
    
    # 分类管理
    async def create_category(self, category_data: Dict[str, Any]) -> Category:
        """创建分类"""
        # 生成 slug
        if 'slug' not in category_data:
            category_data['slug'] = self._generate_slug(category_data['name'])
        
        category = Category(**category_data)
        self.session.add(category)
        self.session.commit()
        self.session.refresh(category)
        return category
    
    async def get_category_tree(self) -> List[Category]:
        """获取分类树"""
        categories = self.session.exec(
            select(Category)
            .where(Category.is_active == True)
            .order_by(Category.sort_order, Category.name)
        ).all()
        
        # 构建树形结构
        category_dict = {cat.id: cat for cat in categories}
        root_categories = []
        
        for category in categories:
            if category.parent_id is None:
                root_categories.append(category)
            else:
                parent = category_dict.get(category.parent_id)
                if parent:
                    if not hasattr(parent, '_children'):
                        parent._children = []
                    parent._children.append(category)
        
        return root_categories
    
    # 标签管理
    async def create_tag(self, tag_data: Dict[str, Any]) -> Tag:
        """创建标签"""
        if 'slug' not in tag_data:
            tag_data['slug'] = self._generate_slug(tag_data['name'])
        
        tag = Tag(**tag_data)
        self.session.add(tag)
        self.session.commit()
        self.session.refresh(tag)
        return tag
    
    async def get_popular_tags(self, limit: int = 20) -> List[Tag]:
        """获取热门标签"""
        return self.session.exec(
            select(Tag)
            .order_by(desc(Tag.usage_count))
            .limit(limit)
        ).all()
    
    # 文章管理
    async def create_post(self, post_data: Dict[str, Any], tag_names: List[str] = None) -> Post:
        """创建文章"""
        # 生成 slug
        if 'slug' not in post_data:
            post_data['slug'] = self._generate_slug(post_data['title'])
        
        post = Post(**post_data)
        
        # 处理标签
        if tag_names:
            tags = []
            for tag_name in tag_names:
                tag = self.session.exec(
                    select(Tag).where(Tag.name == tag_name)
                ).first()
                
                if not tag:
                    tag = Tag(name=tag_name, slug=self._generate_slug(tag_name))
                    self.session.add(tag)
                
                tag.usage_count += 1
                tags.append(tag)
            
            post.tags = tags
        
        self.session.add(post)
        self.session.commit()
        self.session.refresh(post)
        return post
    
    async def publish_post(self, post_id: int) -> Post:
        """发布文章"""
        post = self.session.get(Post, post_id)
        if not post:
            raise ValueError("文章不存在")
        
        post.publish()
        self.session.add(post)
        self.session.commit()
        return post
    
    async def get_posts(
        self, 
        status: PostStatus = None,
        category_id: int = None,
        tag_id: int = None,
        author_id: int = None,
        search: str = None,
        page: int = 1,
        per_page: int = 10
    ) -> Dict[str, Any]:
        """获取文章列表"""
        query = select(Post)
        
        # 添加过滤条件
        conditions = []
        
        if status:
            conditions.append(Post.status == status)
        
        if category_id:
            conditions.append(Post.category_id == category_id)
        
        if author_id:
            conditions.append(Post.author_id == author_id)
        
        if tag_id:
            query = query.join(PostTagLink).where(PostTagLink.tag_id == tag_id)
        
        if search:
            search_term = f"%{search}%"
            conditions.append(
                or_(
                    Post.title.ilike(search_term),
                    Post.content.ilike(search_term),
                    Post.excerpt.ilike(search_term)
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 计算总数
        total_query = select(func.count(Post.id)).select_from(query.subquery())
        total = self.session.exec(total_query).one()
        
        # 分页和排序
        posts = self.session.exec(
            query
            .order_by(desc(Post.published_at))
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        
        return {
            'posts': posts,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    async def get_post_by_slug(self, slug: str) -> Optional[Post]:
        """根据 slug 获取文章"""
        post = self.session.exec(
            select(Post).where(
                and_(Post.slug == slug, Post.status == PostStatus.PUBLISHED)
            )
        ).first()
        
        if post:
            # 增加浏览量
            post.view_count += 1
            self.session.add(post)
            self.session.commit()
        
        return post
    
    # 评论管理
    async def create_comment(
        self, 
        post_id: int, 
        content: str, 
        author_id: int = None,
        parent_id: int = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> Comment:
        """创建评论"""
        post = self.session.get(Post, post_id)
        if not post:
            raise ValueError("文章不存在")
        
        if not post.allow_comments:
            raise ValueError("该文章不允许评论")
        
        comment = Comment(
            post_id=post_id,
            content=content,
            author_id=author_id,
            parent_id=parent_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        self.session.add(comment)
        
        # 更新文章评论数
        post.comment_count += 1
        self.session.add(post)
        
        self.session.commit()
        self.session.refresh(comment)
        return comment
    
    async def get_post_comments(self, post_id: int) -> List[Comment]:
        """获取文章评论"""
        comments = self.session.exec(
            select(Comment)
            .where(
                and_(
                    Comment.post_id == post_id,
                    Comment.status == CommentStatus.APPROVED
                )
            )
            .order_by(Comment.created_at)
        ).all()
        
        # 构建评论树
        comment_dict = {comment.id: comment for comment in comments}
        root_comments = []
        
        for comment in comments:
            if comment.parent_id is None:
                root_comments.append(comment)
            else:
                parent = comment_dict.get(comment.parent_id)
                if parent:
                    if not hasattr(parent, '_replies'):
                        parent._replies = []
                    parent._replies.append(comment)
        
        return root_comments
    
    # 统计分析
    async def get_blog_stats(self) -> Dict[str, Any]:
        """获取博客统计信息"""
        # 文章统计
        total_posts = self.session.exec(
            select(func.count(Post.id))
        ).one()
        
        published_posts = self.session.exec(
            select(func.count(Post.id))
            .where(Post.status == PostStatus.PUBLISHED)
        ).one()
        
        # 用户统计
        total_users = self.session.exec(
            select(func.count(User.id))
        ).one()
        
        active_users = self.session.exec(
            select(func.count(User.id))
            .where(User.is_active == True)
        ).one()
        
        # 评论统计
        total_comments = self.session.exec(
            select(func.count(Comment.id))
        ).one()
        
        approved_comments = self.session.exec(
            select(func.count(Comment.id))
            .where(Comment.status == CommentStatus.APPROVED)
        ).one()
        
        # 最近30天的文章发布趋势
        thirty_days_ago = datetime.now() - timedelta(days=30)
        recent_posts = self.session.exec(
            select(func.count(Post.id))
            .where(
                and_(
                    Post.status == PostStatus.PUBLISHED,
                    Post.published_at >= thirty_days_ago
                )
            )
        ).one()
        
        return {
            'posts': {
                'total': total_posts,
                'published': published_posts,
                'recent': recent_posts
            },
            'users': {
                'total': total_users,
                'active': active_users
            },
            'comments': {
                'total': total_comments,
                'approved': approved_comments
            }
        }
    
    def _generate_slug(self, text: str) -> str:
        """生成 URL 友好的 slug"""
        # 转换为小写并替换空格为连字符
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
```

### 1.4 API 层实现

```python
from fastapi import FastAPI, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
import jwt
from datetime import datetime, timedelta

# Pydantic 模型
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    display_name: str
    bio: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: str
    bio: Optional[str]
    avatar_url: Optional[str]
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    featured_image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_featured: bool = False
    allow_comments: bool = True

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    featured_image: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    is_featured: Optional[bool] = None
    allow_comments: Optional[bool] = None

class PostResponse(BaseModel):
    id: int
    title: str
    slug: str
    excerpt: Optional[str]
    content: str
    status: PostStatus
    published_at: Optional[datetime]
    featured_image: Optional[str]
    view_count: int
    like_count: int
    comment_count: int
    is_featured: bool
    author: UserResponse
    category: Optional[Dict[str, Any]]
    tags: List[Dict[str, Any]]
    reading_time: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class CommentCreate(BaseModel):
    content: str
    parent_id: Optional[int] = None

class CommentResponse(BaseModel):
    id: int
    content: str
    status: CommentStatus
    like_count: int
    author: Optional[UserResponse]
    parent_id: Optional[int]
    replies: List["CommentResponse"] = []
    created_at: datetime
    
    class Config:
        from_attributes = True

# JWT 认证
class JWTAuth:
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
    
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(hours=24)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.PyJWTError:
            return None

# FastAPI 应用
app = FastAPI(
    title="博客管理系统 API",
    description="基于 SQLModel 的博客管理系统",
    version="1.0.0"
)

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 依赖注入
security = HTTPBearer()
jwt_auth = JWTAuth(secret_key="your-secret-key")  # 生产环境中应该从环境变量读取

def get_session():
    with Session(engine) as session:
        yield session

def get_blog_service(session: Session = Depends(get_session)):
    return BlogService(session)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
) -> User:
    token = credentials.credentials
    payload = jwt_auth.verify_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = session.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

# 认证端点
@app.post("/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    blog_service: BlogService = Depends(get_blog_service)
):
    try:
        user = await blog_service.create_user(user_data.dict())
        return UserResponse.from_orm(user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(
    user_data: UserLogin,
    blog_service: BlogService = Depends(get_blog_service)
):
    user = await blog_service.authenticate_user(user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = jwt_auth.create_access_token(
        data={"sub": str(user.id), "username": user.username}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.from_orm(user)
    }

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return UserResponse.from_orm(current_user)

# 文章端点
@app.get("/posts", response_model=Dict[str, Any])
async def get_posts(
    status: Optional[PostStatus] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    author_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    blog_service: BlogService = Depends(get_blog_service)
):
    result = await blog_service.get_posts(
        status=status,
        category_id=category_id,
        tag_id=tag_id,
        author_id=author_id,
        search=search,
        page=page,
        per_page=per_page
    )
    
    # 转换为响应模型
    posts_response = []
    for post in result['posts']:
        post_dict = {
            **post.__dict__,
            'author': UserResponse.from_orm(post.author),
            'category': post.category.__dict__ if post.category else None,
            'tags': [tag.__dict__ for tag in post.tags],
            'reading_time': post.get_reading_time()
        }
        posts_response.append(post_dict)
    
    return {
        **result,
        'posts': posts_response
    }

@app.get("/posts/{slug}", response_model=PostResponse)
async def get_post_by_slug(
    slug: str,
    blog_service: BlogService = Depends(get_blog_service)
):
    post = await blog_service.get_post_by_slug(slug)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return PostResponse(
        **post.__dict__,
        author=UserResponse.from_orm(post.author),
        category=post.category.__dict__ if post.category else None,
        tags=[tag.__dict__ for tag in post.tags],
        reading_time=post.get_reading_time()
    )

@app.post("/posts", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    blog_service: BlogService = Depends(get_blog_service)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR, UserRole.AUTHOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    post_dict = post_data.dict(exclude={'tags'})
    post_dict['author_id'] = current_user.id
    
    post = await blog_service.create_post(
        post_dict, 
        tag_names=post_data.tags or []
    )
    
    return PostResponse(
        **post.__dict__,
        author=UserResponse.from_orm(post.author),
        category=post.category.__dict__ if post.category else None,
        tags=[tag.__dict__ for tag in post.tags],
        reading_time=post.get_reading_time()
    )

@app.put("/posts/{post_id}/publish")
async def publish_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    blog_service: BlogService = Depends(get_blog_service)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    try:
        post = await blog_service.publish_post(post_id)
        return {"message": "Post published successfully", "post_id": post.id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# 评论端点
@app.get("/posts/{post_id}/comments", response_model=List[CommentResponse])
async def get_post_comments(
    post_id: int,
    blog_service: BlogService = Depends(get_blog_service)
):
    comments = await blog_service.get_post_comments(post_id)
    
    def build_comment_response(comment):
        return CommentResponse(
            **comment.__dict__,
            author=UserResponse.from_orm(comment.author) if comment.author else None,
            replies=[build_comment_response(reply) for reply in getattr(comment, '_replies', [])]
        )
    
    return [build_comment_response(comment) for comment in comments]

@app.post("/posts/{post_id}/comments", response_model=CommentResponse)
async def create_comment(
    post_id: int,
    comment_data: CommentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    blog_service: BlogService = Depends(get_blog_service)
):
    try:
        comment = await blog_service.create_comment(
            post_id=post_id,
            content=comment_data.content,
            author_id=current_user.id,
            parent_id=comment_data.parent_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent")
        )
        
        return CommentResponse(
            **comment.__dict__,
            author=UserResponse.from_orm(comment.author) if comment.author else None,
            replies=[]
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 分类和标签端点
@app.get("/categories")
async def get_categories(
    blog_service: BlogService = Depends(get_blog_service)
):
    categories = await blog_service.get_category_tree()
    return [category.__dict__ for category in categories]

@app.get("/tags")
async def get_popular_tags(
    limit: int = Query(20, ge=1, le=100),
    blog_service: BlogService = Depends(get_blog_service)
):
    tags = await blog_service.get_popular_tags(limit)
    return [tag.__dict__ for tag in tags]

# 统计端点
@app.get("/stats")
async def get_blog_stats(
    current_user: User = Depends(get_current_user),
    blog_service: BlogService = Depends(get_blog_service)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.EDITOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return await blog_service.get_blog_stats()

# 错误处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat()
            }
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "timestamp": datetime.now().isoformat()
            }
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 1.5 前端集成示例

#### React 组件示例

```typescript
// types/blog.ts
export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string;
  bio?: string;
  avatar_url?: string;
  role: 'admin' | 'editor' | 'author' | 'reader';
  created_at: string;
}

export interface Post {
  id: number;
  title: string;
  slug: string;
  excerpt?: string;
  content: string;
  status: 'draft' | 'published' | 'archived';
  published_at?: string;
  featured_image?: string;
  view_count: number;
  like_count: number;
  comment_count: number;
  is_featured: boolean;
  author: User;
  category?: any;
  tags: any[];
  reading_time: number;
  created_at: string;
  updated_at?: string;
}

export interface Comment {
  id: number;
  content: string;
  status: 'pending' | 'approved' | 'rejected';
  like_count: number;
  author?: User;
  parent_id?: number;
  replies: Comment[];
  created_at: string;
}

// services/api.ts
class BlogAPI {
  private baseURL = 'http://localhost:8000';
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });
 };
 ```

## 2. 电商订单系统

### 2.1 需求分析

电商订单系统是一个复杂的业务场景，涉及商品管理、库存控制、订单处理、支付集成、物流跟踪等多个方面。

**核心功能需求：**
- 商品管理：商品信息、分类、库存、价格
- 购物车：商品添加、数量调整、价格计算
- 订单管理：订单创建、状态跟踪、支付处理
- 库存控制：实时库存、预占库存、库存释放
- 支付集成：多种支付方式、支付状态同步
- 物流跟踪：发货、配送、签收状态
- 用户管理：用户信息、收货地址、订单历史

**技术挑战：**
- 高并发下的库存一致性
- 分布式事务处理
- 订单状态机管理
- 支付回调处理
- 数据一致性保证

### 2.2 架构设计

```python
from sqlmodel import SQLModel, Field, Relationship, Session, create_engine, select
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import json

# 枚举定义
class OrderStatus(str, Enum):
    PENDING = "pending"          # 待支付
    PAID = "paid"                # 已支付
    CONFIRMED = "confirmed"      # 已确认
    SHIPPED = "shipped"          # 已发货
    DELIVERED = "delivered"      # 已送达
    COMPLETED = "completed"      # 已完成
    CANCELLED = "cancelled"      # 已取消
    REFUNDED = "refunded"        # 已退款

class PaymentStatus(str, Enum):
    PENDING = "pending"          # 待支付
    PROCESSING = "processing"    # 处理中
    SUCCESS = "success"          # 支付成功
    FAILED = "failed"            # 支付失败
    CANCELLED = "cancelled"      # 已取消
    REFUNDED = "refunded"        # 已退款

class PaymentMethod(str, Enum):
    ALIPAY = "alipay"            # 支付宝
    WECHAT = "wechat"            # 微信支付
    CREDIT_CARD = "credit_card"  # 信用卡
    BANK_TRANSFER = "bank_transfer"  # 银行转账

class ProductStatus(str, Enum):
    ACTIVE = "active"            # 上架
    INACTIVE = "inactive"        # 下架
    OUT_OF_STOCK = "out_of_stock"  # 缺货

# 关联表
class CartItem(SQLModel, table=True):
    __tablename__ = "cart_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 关系
    user: "User" = Relationship(back_populates="cart_items")
    product: "Product" = Relationship(back_populates="cart_items")
    
    @property
    def total_price(self) -> Decimal:
        return self.unit_price * self.quantity

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(max_digits=10, decimal_places=2)
    total_price: Decimal = Field(max_digits=10, decimal_places=2)
    
    # 关系
    order: "Order" = Relationship(back_populates="items")
    product: "Product" = Relationship(back_populates="order_items")

# 核心模型
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=50)
    email: str = Field(unique=True, index=True, max_length=100)
    password_hash: str = Field(max_length=255)
    phone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 关系
    addresses: List["Address"] = Relationship(back_populates="user")
    orders: List["Order"] = Relationship(back_populates="user")
    cart_items: List["CartItem"] = Relationship(back_populates="user")
    
    def get_default_address(self) -> Optional["Address"]:
        """获取默认地址"""
        for address in self.addresses:
            if address.is_default:
                return address
        return None

class Address(SQLModel, table=True):
    __tablename__ = "addresses"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=50)  # 收货人姓名
    phone: str = Field(max_length=20)  # 收货人电话
    province: str = Field(max_length=50)  # 省份
    city: str = Field(max_length=50)  # 城市
    district: str = Field(max_length=50)  # 区县
    detail: str = Field(max_length=200)  # 详细地址
    postal_code: Optional[str] = Field(default=None, max_length=10)  # 邮编
    is_default: bool = Field(default=False)  # 是否默认地址
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    user: User = Relationship(back_populates="addresses")
    orders: List["Order"] = Relationship(back_populates="shipping_address")
    
    @property
    def full_address(self) -> str:
        """完整地址"""
        return f"{self.province}{self.city}{self.district}{self.detail}"

class Category(SQLModel, table=True):
    __tablename__ = "categories"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, max_length=100)
    description: Optional[str] = Field(default=None)
    parent_id: Optional[int] = Field(default=None, foreign_key="categories.id")
    sort_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    products: List["Product"] = Relationship(back_populates="category")
    parent: Optional["Category"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={"remote_side": "Category.id"}
    )
    children: List["Category"] = Relationship(back_populates="parent")

class Product(SQLModel, table=True):
    __tablename__ = "products"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=200, index=True)
    description: Optional[str] = Field(default=None)
    sku: str = Field(unique=True, max_length=50, index=True)  # 商品编码
    category_id: Optional[int] = Field(default=None, foreign_key="categories.id")
    price: Decimal = Field(max_digits=10, decimal_places=2, ge=0)
    cost_price: Optional[Decimal] = Field(default=None, max_digits=10, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0)  # 库存数量
    reserved_quantity: int = Field(default=0, ge=0)  # 预占数量
    sold_quantity: int = Field(default=0, ge=0)  # 已售数量
    weight: Optional[Decimal] = Field(default=None, max_digits=8, decimal_places=3)  # 重量(kg)
    dimensions: Optional[str] = Field(default=None)  # 尺寸 JSON
    images: Optional[str] = Field(default=None)  # 图片 JSON
    attributes: Optional[str] = Field(default=None)  # 属性 JSON
    status: ProductStatus = Field(default=ProductStatus.ACTIVE)
    is_featured: bool = Field(default=False)  # 是否推荐
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 关系
    category: Optional[Category] = Relationship(back_populates="products")
    cart_items: List[CartItem] = Relationship(back_populates="product")
    order_items: List[OrderItem] = Relationship(back_populates="product")
    inventory_logs: List["InventoryLog"] = Relationship(back_populates="product")
    
    @property
    def available_quantity(self) -> int:
        """可用库存"""
        return self.stock_quantity - self.reserved_quantity
    
    @property
    def image_list(self) -> List[str]:
        """图片列表"""
        if self.images:
            return json.loads(self.images)
        return []
    
    @property
    def attribute_dict(self) -> Dict[str, Any]:
        """属性字典"""
        if self.attributes:
            return json.loads(self.attributes)
        return {}
    
    def can_order(self, quantity: int) -> bool:
        """检查是否可以下单"""
        return (
            self.status == ProductStatus.ACTIVE and
            self.available_quantity >= quantity
        )

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_no: str = Field(unique=True, max_length=50, index=True)  # 订单号
    user_id: int = Field(foreign_key="users.id", index=True)
    status: OrderStatus = Field(default=OrderStatus.PENDING, index=True)
    
    # 金额信息
    subtotal: Decimal = Field(max_digits=10, decimal_places=2)  # 商品小计
    shipping_fee: Decimal = Field(default=Decimal('0'), max_digits=10, decimal_places=2)  # 运费
    discount_amount: Decimal = Field(default=Decimal('0'), max_digits=10, decimal_places=2)  # 优惠金额
    total_amount: Decimal = Field(max_digits=10, decimal_places=2)  # 总金额
    
    # 收货信息
    shipping_address_id: Optional[int] = Field(default=None, foreign_key="addresses.id")
    shipping_name: str = Field(max_length=50)  # 收货人姓名
    shipping_phone: str = Field(max_length=20)  # 收货人电话
    shipping_address: str = Field(max_length=500)  # 收货地址
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    paid_at: Optional[datetime] = Field(default=None)
    shipped_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    
    # 备注信息
    remark: Optional[str] = Field(default=None, max_length=500)  # 订单备注
    cancel_reason: Optional[str] = Field(default=None, max_length=200)  # 取消原因
    
    # 关系
    user: User = Relationship(back_populates="orders")
    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List["Payment"] = Relationship(back_populates="order")
    shipping_address_rel: Optional[Address] = Relationship(back_populates="orders")
    logistics: List["Logistics"] = Relationship(back_populates="order")
    
    def __init__(self, **data):
        if 'order_no' not in data:
            data['order_no'] = self.generate_order_no()
        super().__init__(**data)
    
    @staticmethod
    def generate_order_no() -> str:
        """生成订单号"""
        import time
        timestamp = str(int(time.time()))
        random_str = str(uuid.uuid4()).replace('-', '')[:8]
        return f"ORD{timestamp}{random_str}".upper()
    
    def can_cancel(self) -> bool:
        """检查是否可以取消"""
        return self.status in [OrderStatus.PENDING, OrderStatus.PAID]
    
    def can_pay(self) -> bool:
        """检查是否可以支付"""
        return self.status == OrderStatus.PENDING
    
    def can_ship(self) -> bool:
        """检查是否可以发货"""
        return self.status in [OrderStatus.PAID, OrderStatus.CONFIRMED]

class Payment(SQLModel, table=True):
    __tablename__ = "payments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    payment_no: str = Field(unique=True, max_length=50, index=True)  # 支付单号
    order_id: int = Field(foreign_key="orders.id", index=True)
    method: PaymentMethod = Field(index=True)
    status: PaymentStatus = Field(default=PaymentStatus.PENDING, index=True)
    amount: Decimal = Field(max_digits=10, decimal_places=2)
    
    # 第三方支付信息
    third_party_no: Optional[str] = Field(default=None, max_length=100)  # 第三方支付单号
    third_party_response: Optional[str] = Field(default=None)  # 第三方响应 JSON
    
    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now)
    paid_at: Optional[datetime] = Field(default=None)
    failed_at: Optional[datetime] = Field(default=None)
    cancelled_at: Optional[datetime] = Field(default=None)
    
    # 备注
    remark: Optional[str] = Field(default=None, max_length=500)
    failure_reason: Optional[str] = Field(default=None, max_length=200)
    
    # 关系
    order: Order = Relationship(back_populates="payments")
    
    def __init__(self, **data):
        if 'payment_no' not in data:
            data['payment_no'] = self.generate_payment_no()
        super().__init__(**data)
    
    @staticmethod
    def generate_payment_no() -> str:
        """生成支付单号"""
        import time
        timestamp = str(int(time.time()))
        random_str = str(uuid.uuid4()).replace('-', '')[:8]
        return f"PAY{timestamp}{random_str}".upper()

class Logistics(SQLModel, table=True):
    __tablename__ = "logistics"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id", index=True)
    tracking_no: str = Field(max_length=100, index=True)  # 物流单号
    company: str = Field(max_length=50)  # 物流公司
    status: str = Field(max_length=50)  # 物流状态
    current_location: Optional[str] = Field(default=None, max_length=200)  # 当前位置
    estimated_delivery: Optional[datetime] = Field(default=None)  # 预计送达时间
    actual_delivery: Optional[datetime] = Field(default=None)  # 实际送达时间
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default=None)
    
    # 关系
    order: Order = Relationship(back_populates="logistics")
    tracks: List["LogisticsTrack"] = Relationship(back_populates="logistics")

class LogisticsTrack(SQLModel, table=True):
    __tablename__ = "logistics_tracks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    logistics_id: int = Field(foreign_key="logistics.id", index=True)
    status: str = Field(max_length=50)  # 状态
    location: Optional[str] = Field(default=None, max_length=200)  # 位置
    description: str = Field(max_length=500)  # 描述
    occurred_at: datetime = Field()  # 发生时间
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    logistics: Logistics = Relationship(back_populates="tracks")

class InventoryLog(SQLModel, table=True):
    __tablename__ = "inventory_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    type: str = Field(max_length=20, index=True)  # 类型：in/out/reserve/release
    quantity: int = Field()  # 数量变化
    before_quantity: int = Field()  # 变化前数量
    after_quantity: int = Field()  # 变化后数量
    reference_type: Optional[str] = Field(default=None, max_length=50)  # 关联类型
    reference_id: Optional[int] = Field(default=None)  # 关联ID
    remark: Optional[str] = Field(default=None, max_length=200)  # 备注
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
     product: Product = Relationship(back_populates="inventory_logs")
 ```

### 2.3 服务层实现

```python
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import selectinload
from contextlib import contextmanager
import asyncio
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class ECommerceService:
    def __init__(self, session: Session):
        self.session = session
    
    # 用户管理
    async def create_user(self, user_data: Dict[str, Any]) -> User:
        """创建用户"""
        # 检查用户名和邮箱是否已存在
        existing_user = self.session.exec(
            select(User).where(
                or_(User.username == user_data['username'], 
                    User.email == user_data['email'])
            )
        ).first()
        
        if existing_user:
            if existing_user.username == user_data['username']:
                raise ValueError("用户名已存在")
            else:
                raise ValueError("邮箱已存在")
        
        # 创建用户
        user = User(**user_data)
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    async def add_address(self, user_id: int, address_data: Dict[str, Any]) -> Address:
        """添加收货地址"""
        # 如果设置为默认地址，先取消其他默认地址
        if address_data.get('is_default', False):
            self.session.exec(
                select(Address)
                .where(Address.user_id == user_id)
                .where(Address.is_default == True)
            ).update({'is_default': False})
        
        address = Address(user_id=user_id, **address_data)
        self.session.add(address)
        self.session.commit()
        self.session.refresh(address)
        return address
    
    # 商品管理
    async def create_product(self, product_data: Dict[str, Any]) -> Product:
        """创建商品"""
        # 检查SKU是否已存在
        existing_product = self.session.exec(
            select(Product).where(Product.sku == product_data['sku'])
        ).first()
        
        if existing_product:
            raise ValueError("商品SKU已存在")
        
        product = Product(**product_data)
        self.session.add(product)
        self.session.commit()
        self.session.refresh(product)
        
        # 记录库存日志
        if product.stock_quantity > 0:
            await self._log_inventory(
                product.id, 'in', product.stock_quantity, 
                0, product.stock_quantity, 'product', product.id, '初始库存'
            )
        
        return product
    
    async def update_inventory(self, product_id: int, quantity: int, 
                             operation: str, reference_type: str = None, 
                             reference_id: int = None, remark: str = None) -> Product:
        """更新库存"""
        product = self.session.get(Product, product_id)
        if not product:
            raise ValueError("商品不存在")
        
        before_quantity = product.stock_quantity
        
        if operation == 'in':  # 入库
            product.stock_quantity += quantity
        elif operation == 'out':  # 出库
            if product.stock_quantity < quantity:
                raise ValueError("库存不足")
            product.stock_quantity -= quantity
        elif operation == 'reserve':  # 预占
            if product.available_quantity < quantity:
                raise ValueError("可用库存不足")
            product.reserved_quantity += quantity
        elif operation == 'release':  # 释放预占
            if product.reserved_quantity < quantity:
                raise ValueError("预占库存不足")
            product.reserved_quantity -= quantity
        else:
            raise ValueError("无效的操作类型")
        
        self.session.add(product)
        self.session.commit()
        
        # 记录库存日志
        await self._log_inventory(
            product_id, operation, quantity, before_quantity, 
            product.stock_quantity, reference_type, reference_id, remark
        )
        
        return product
    
    async def _log_inventory(self, product_id: int, operation: str, quantity: int,
                           before_quantity: int, after_quantity: int,
                           reference_type: str = None, reference_id: int = None,
                           remark: str = None):
        """记录库存日志"""
        log = InventoryLog(
            product_id=product_id,
            type=operation,
            quantity=quantity,
            before_quantity=before_quantity,
            after_quantity=after_quantity,
            reference_type=reference_type,
            reference_id=reference_id,
            remark=remark
        )
        self.session.add(log)
        self.session.commit()
    
    # 购物车管理
    async def add_to_cart(self, user_id: int, product_id: int, quantity: int) -> CartItem:
        """添加到购物车"""
        # 检查商品是否存在且可购买
        product = self.session.get(Product, product_id)
        if not product or not product.can_order(quantity):
            raise ValueError("商品不存在或库存不足")
        
        # 检查购物车中是否已有该商品
        existing_item = self.session.exec(
            select(CartItem).where(
                and_(CartItem.user_id == user_id, CartItem.product_id == product_id)
            )
        ).first()
        
        if existing_item:
            # 更新数量
            new_quantity = existing_item.quantity + quantity
            if not product.can_order(new_quantity):
                raise ValueError("库存不足")
            
            existing_item.quantity = new_quantity
            existing_item.unit_price = product.price
            existing_item.updated_at = datetime.now()
            self.session.add(existing_item)
            cart_item = existing_item
        else:
            # 创建新的购物车项
            cart_item = CartItem(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity,
                unit_price=product.price
            )
            self.session.add(cart_item)
        
        self.session.commit()
        self.session.refresh(cart_item)
        return cart_item
    
    async def get_cart_items(self, user_id: int) -> List[CartItem]:
        """获取购物车商品"""
        return self.session.exec(
            select(CartItem)
            .where(CartItem.user_id == user_id)
            .options(selectinload(CartItem.product))
        ).all()
    
    async def clear_cart(self, user_id: int):
        """清空购物车"""
        cart_items = self.session.exec(
            select(CartItem).where(CartItem.user_id == user_id)
        ).all()
        
        for item in cart_items:
            self.session.delete(item)
        
        self.session.commit()
    
    # 订单管理
    async def create_order(self, user_id: int, address_id: int, 
                         cart_item_ids: List[int] = None, 
                         remark: str = None) -> Order:
        """创建订单"""
        # 获取用户信息
        user = self.session.get(User, user_id)
        if not user or not user.is_active:
            raise ValueError("用户不存在或已禁用")
        
        # 获取收货地址
        address = self.session.get(Address, address_id)
        if not address or address.user_id != user_id:
            raise ValueError("收货地址不存在")
        
        # 获取购物车商品
        cart_query = select(CartItem).where(CartItem.user_id == user_id)
        if cart_item_ids:
            cart_query = cart_query.where(CartItem.id.in_(cart_item_ids))
        
        cart_items = self.session.exec(
            cart_query.options(selectinload(CartItem.product))
        ).all()
        
        if not cart_items:
            raise ValueError("购物车为空")
        
        # 检查库存并预占
        for item in cart_items:
            if not item.product.can_order(item.quantity):
                raise ValueError(f"商品 {item.product.name} 库存不足")
        
        # 计算金额
        subtotal = sum(item.total_price for item in cart_items)
        shipping_fee = await self._calculate_shipping_fee(cart_items, address)
        total_amount = subtotal + shipping_fee
        
        # 创建订单
        order = Order(
            user_id=user_id,
            subtotal=subtotal,
            shipping_fee=shipping_fee,
            total_amount=total_amount,
            shipping_address_id=address_id,
            shipping_name=address.name,
            shipping_phone=address.phone,
            shipping_address=address.full_address,
            remark=remark
        )
        
        self.session.add(order)
        self.session.flush()  # 获取订单ID
        
        # 创建订单项并预占库存
        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
                total_price=item.total_price
            )
            self.session.add(order_item)
            
            # 预占库存
            await self.update_inventory(
                item.product_id, item.quantity, 'reserve',
                'order', order.id, f'订单 {order.order_no} 预占库存'
            )
            
            # 删除购物车项
            self.session.delete(item)
        
        self.session.commit()
        self.session.refresh(order)
        return order
    
    async def _calculate_shipping_fee(self, cart_items: List[CartItem], 
                                    address: Address) -> Decimal:
        """计算运费"""
        # 简单的运费计算逻辑
        total_weight = sum(
            (item.product.weight or Decimal('0.5')) * item.quantity 
            for item in cart_items
        )
        
        # 基础运费
        base_fee = Decimal('10.00')
        
        # 重量费用（每公斤2元）
        weight_fee = total_weight * Decimal('2.00')
        
        # 偏远地区加收费用
        remote_areas = ['西藏', '新疆', '内蒙古']
        if any(area in address.province for area in remote_areas):
            base_fee += Decimal('20.00')
        
        return base_fee + weight_fee
    
    async def pay_order(self, order_id: int, payment_method: PaymentMethod) -> Payment:
        """支付订单"""
        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("订单不存在")
        
        if not order.can_pay():
            raise ValueError("订单状态不允许支付")
        
        # 创建支付记录
        payment = Payment(
            order_id=order_id,
            method=payment_method,
            amount=order.total_amount
        )
        
        self.session.add(payment)
        self.session.commit()
        self.session.refresh(payment)
        
        # 这里应该调用第三方支付接口
        # 模拟支付成功
        await self._handle_payment_success(payment.id)
        
        return payment
    
    async def _handle_payment_success(self, payment_id: int):
        """处理支付成功"""
        payment = self.session.get(Payment, payment_id)
        if not payment:
            return
        
        # 更新支付状态
        payment.status = PaymentStatus.SUCCESS
        payment.paid_at = datetime.now()
        
        # 更新订单状态
        order = payment.order
        order.status = OrderStatus.PAID
        order.paid_at = datetime.now()
        
        # 扣减库存
        for item in order.items:
            # 释放预占库存
            await self.update_inventory(
                item.product_id, item.quantity, 'release',
                'order', order.id, f'订单 {order.order_no} 释放预占库存'
            )
            
            # 扣减实际库存
            await self.update_inventory(
                item.product_id, item.quantity, 'out',
                'order', order.id, f'订单 {order.order_no} 扣减库存'
            )
            
            # 更新销量
            product = self.session.get(Product, item.product_id)
            product.sold_quantity += item.quantity
            self.session.add(product)
        
        self.session.commit()
    
    async def cancel_order(self, order_id: int, reason: str = None) -> Order:
        """取消订单"""
        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("订单不存在")
        
        if not order.can_cancel():
            raise ValueError("订单状态不允许取消")
        
        # 释放预占库存
        for item in order.items:
            await self.update_inventory(
                item.product_id, item.quantity, 'release',
                'order', order.id, f'订单 {order.order_no} 取消释放库存'
            )
        
        # 更新订单状态
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now()
        order.cancel_reason = reason
        
        # 如果已支付，需要退款
        if order.status == OrderStatus.PAID:
            await self._process_refund(order_id)
        
        self.session.commit()
        return order
    
    async def _process_refund(self, order_id: int):
        """处理退款"""
        # 这里应该调用第三方支付接口进行退款
        # 模拟退款成功
        order = self.session.get(Order, order_id)
        for payment in order.payments:
            if payment.status == PaymentStatus.SUCCESS:
                payment.status = PaymentStatus.REFUNDED
                self.session.add(payment)
        
        order.status = OrderStatus.REFUNDED
        self.session.add(order)
    
    async def ship_order(self, order_id: int, tracking_no: str, 
                       company: str) -> Logistics:
        """发货"""
        order = self.session.get(Order, order_id)
        if not order:
            raise ValueError("订单不存在")
        
        if not order.can_ship():
            raise ValueError("订单状态不允许发货")
        
        # 创建物流记录
        logistics = Logistics(
            order_id=order_id,
            tracking_no=tracking_no,
            company=company,
            status="已发货"
        )
        
        self.session.add(logistics)
        
        # 更新订单状态
        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.now()
        
        self.session.commit()
        self.session.refresh(logistics)
        return logistics
    
    # 查询方法
    async def get_orders(self, user_id: int = None, status: OrderStatus = None,
                       page: int = 1, per_page: int = 10) -> Dict[str, Any]:
        """获取订单列表"""
        query = select(Order)
        
        if user_id:
            query = query.where(Order.user_id == user_id)
        
        if status:
            query = query.where(Order.status == status)
        
        # 计算总数
        total = self.session.exec(
            select(func.count(Order.id)).where(query.whereclause)
        ).one()
        
        # 分页查询
        orders = self.session.exec(
            query
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .options(selectinload(Order.user))
            .order_by(Order.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        
        return {
            'orders': orders,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    async def get_order_by_no(self, order_no: str) -> Optional[Order]:
        """根据订单号获取订单"""
        return self.session.exec(
            select(Order)
            .where(Order.order_no == order_no)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .options(selectinload(Order.payments))
            .options(selectinload(Order.logistics).selectinload(Logistics.tracks))
        ).first()
    
    async def get_sales_stats(self, start_date: datetime = None, 
                            end_date: datetime = None) -> Dict[str, Any]:
        """获取销售统计"""
        query = select(Order).where(Order.status.in_([
            OrderStatus.COMPLETED, OrderStatus.SHIPPED, OrderStatus.DELIVERED
        ]))
        
        if start_date:
            query = query.where(Order.created_at >= start_date)
        
        if end_date:
            query = query.where(Order.created_at <= end_date)
        
        orders = self.session.exec(query).all()
        
        total_orders = len(orders)
        total_amount = sum(order.total_amount for order in orders)
        avg_order_amount = total_amount / total_orders if total_orders > 0 else 0
        
        # 商品销量统计
        product_sales = {}
        for order in orders:
            for item in order.items:
                if item.product_id not in product_sales:
                    product_sales[item.product_id] = {
                        'product_name': item.product.name,
                        'quantity': 0,
                        'amount': Decimal('0')
                    }
                product_sales[item.product_id]['quantity'] += item.quantity
                product_sales[item.product_id]['amount'] += item.total_price
        
        return {
             'total_orders': total_orders,
             'total_amount': float(total_amount),
             'avg_order_amount': float(avg_order_amount),
             'product_sales': list(product_sales.values())
         }
 ```

### 2.4 API层实现

```python
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import jwt
from datetime import datetime, timedelta

app = FastAPI(title="电商订单系统 API")
security = HTTPBearer()

# Pydantic 模型
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    phone: str = None
    real_name: str = None

class UserLogin(BaseModel):
    username: str
    password: str

class AddressCreate(BaseModel):
    name: str
    phone: str
    province: str
    city: str
    district: str
    detail: str
    is_default: bool = False

class ProductCreate(BaseModel):
    name: str
    sku: str
    description: str = None
    price: float
    stock_quantity: int
    category_id: int
    weight: float = None
    images: List[str] = []

class CartItemAdd(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    address_id: int
    cart_item_ids: List[int] = None
    remark: str = None

class PaymentCreate(BaseModel):
    order_id: int
    payment_method: str

class ShipmentCreate(BaseModel):
    order_id: int
    tracking_no: str
    company: str

# JWT 认证
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        return user_id
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

# 依赖注入
def get_service():
    session = get_session()
    return ECommerceService(session)

# 用户认证接口
@app.post("/auth/register")
async def register(user_data: UserCreate, service: ECommerceService = Depends(get_service)):
    try:
        user = await service.create_user(user_data.dict())
        return {"message": "用户注册成功", "user_id": user.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/auth/login")
async def login(user_data: UserLogin, service: ECommerceService = Depends(get_service)):
    # 验证用户凭据（这里简化处理）
    user = service.session.exec(
        select(User).where(User.username == user_data.username)
    ).first()
    
    if not user or not user.verify_password(user_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    access_token = create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}

# 用户地址管理
@app.post("/addresses")
async def add_address(
    address_data: AddressCreate,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    try:
        address = await service.add_address(current_user, address_data.dict())
        return address
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/addresses")
async def get_addresses(
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    addresses = service.session.exec(
        select(Address).where(Address.user_id == current_user)
    ).all()
    return addresses

# 商品管理
@app.post("/products")
async def create_product(
    product_data: ProductCreate,
    service: ECommerceService = Depends(get_service)
):
    try:
        product = await service.create_product(product_data.dict())
        return product
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/products")
async def get_products(
    category_id: Optional[int] = None,
    page: int = 1,
    per_page: int = 20,
    service: ECommerceService = Depends(get_service)
):
    query = select(Product).where(Product.status == ProductStatus.ACTIVE)
    
    if category_id:
        query = query.where(Product.category_id == category_id)
    
    # 计算总数
    total = service.session.exec(
        select(func.count(Product.id)).where(query.whereclause)
    ).one()
    
    # 分页查询
    products = service.session.exec(
        query
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).all()
    
    return {
        'products': products,
        'total': total,
        'page': page,
        'per_page': per_page,
        'pages': (total + per_page - 1) // per_page
    }

@app.get("/products/{product_id}")
async def get_product(
    product_id: int,
    service: ECommerceService = Depends(get_service)
):
    product = service.session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product

# 购物车管理
@app.post("/cart/items")
async def add_to_cart(
    item_data: CartItemAdd,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    try:
        cart_item = await service.add_to_cart(
            current_user, item_data.product_id, item_data.quantity
        )
        return cart_item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/cart/items")
async def get_cart_items(
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    cart_items = await service.get_cart_items(current_user)
    return cart_items

@app.delete("/cart/items")
async def clear_cart(
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    await service.clear_cart(current_user)
    return {"message": "购物车已清空"}

# 订单管理
@app.post("/orders")
async def create_order(
    order_data: OrderCreate,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    try:
        order = await service.create_order(
            current_user, order_data.address_id, 
            order_data.cart_item_ids, order_data.remark
        )
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/orders")
async def get_orders(
    status: Optional[str] = None,
    page: int = 1,
    per_page: int = 10,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    order_status = OrderStatus(status) if status else None
    result = await service.get_orders(
        user_id=current_user, status=order_status, page=page, per_page=per_page
    )
    return result

@app.get("/orders/{order_no}")
async def get_order(
    order_no: str,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    order = await service.get_order_by_no(order_no)
    if not order or order.user_id != current_user:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order

@app.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: int,
    reason: str = None,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    try:
        order = await service.cancel_order(order_id, reason)
        return order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 支付接口
@app.post("/payments")
async def pay_order(
    payment_data: PaymentCreate,
    current_user: int = Depends(get_current_user),
    service: ECommerceService = Depends(get_service)
):
    try:
        payment_method = PaymentMethod(payment_data.payment_method)
        payment = await service.pay_order(payment_data.order_id, payment_method)
        return payment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 发货接口（管理员）
@app.post("/shipments")
async def ship_order(
    shipment_data: ShipmentCreate,
    service: ECommerceService = Depends(get_service)
):
    try:
        logistics = await service.ship_order(
            shipment_data.order_id, 
            shipment_data.tracking_no, 
            shipment_data.company
        )
        return logistics
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 统计接口
@app.get("/stats/sales")
async def get_sales_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    service: ECommerceService = Depends(get_service)
):
    stats = await service.get_sales_stats(start_date, end_date)
    return stats

# 错误处理
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return HTTPException(status_code=400, detail=str(exc))

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return HTTPException(status_code=500, detail="内部服务器错误")
```

## 3. 任务管理平台

### 3.1 需求分析

任务管理平台是一个团队协作工具，主要功能包括：

**核心功能：**
- 项目管理：创建、编辑、删除项目
- 任务管理：任务创建、分配、状态跟踪
- 团队协作：成员管理、权限控制
- 时间跟踪：工时记录、进度统计
- 文件管理：附件上传、版本控制
- 通知系统：实时消息、邮件提醒

**技术挑战：**
- 复杂的权限控制系统
- 实时协作功能
- 大量数据的查询优化
- 文件存储和管理
- 消息推送机制

### 3.2 架构设计

```python
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# 枚举定义
class ProjectStatus(str, Enum):
    PLANNING = "planning"      # 规划中
    ACTIVE = "active"          # 进行中
    ON_HOLD = "on_hold"        # 暂停
    COMPLETED = "completed"    # 已完成
    CANCELLED = "cancelled"    # 已取消

class TaskStatus(str, Enum):
    TODO = "todo"              # 待办
    IN_PROGRESS = "in_progress" # 进行中
    REVIEW = "review"          # 待审核
    DONE = "done"              # 已完成
    CANCELLED = "cancelled"    # 已取消

class TaskPriority(str, Enum):
    LOW = "low"                # 低
    MEDIUM = "medium"          # 中
    HIGH = "high"              # 高
    URGENT = "urgent"          # 紧急

class UserRole(str, Enum):
    ADMIN = "admin"            # 管理员
    PROJECT_MANAGER = "pm"     # 项目经理
    DEVELOPER = "developer"    # 开发者
    TESTER = "tester"          # 测试员
    VIEWER = "viewer"          # 查看者

class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"        # 任务分配
    TASK_UPDATED = "task_updated"          # 任务更新
    TASK_COMPLETED = "task_completed"      # 任务完成
    PROJECT_UPDATED = "project_updated"    # 项目更新
    COMMENT_ADDED = "comment_added"        # 评论添加
    FILE_UPLOADED = "file_uploaded"        # 文件上传

# 关联表
class ProjectMember(SQLModel, table=True):
    __tablename__ = "project_members"
    
    project_id: int = Field(foreign_key="projects.id", primary_key=True)
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    role: UserRole = Field(default=UserRole.DEVELOPER)
    joined_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    project: "Project" = Relationship(back_populates="members")
    user: "User" = Relationship(back_populates="project_memberships")

class TaskAssignee(SQLModel, table=True):
    __tablename__ = "task_assignees"
    
    task_id: int = Field(foreign_key="tasks.id", primary_key=True)
    user_id: int = Field(foreign_key="users.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    task: "Task" = Relationship(back_populates="assignees")
    user: "User" = Relationship(back_populates="task_assignments")

# 核心模型
class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    full_name: str
    avatar: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    project_memberships: List[ProjectMember] = Relationship(back_populates="user")
    task_assignments: List[TaskAssignee] = Relationship(back_populates="user")
    created_projects: List["Project"] = Relationship(back_populates="creator")
    created_tasks: List["Task"] = Relationship(back_populates="creator")
    time_logs: List["TimeLog"] = Relationship(back_populates="user")
    comments: List["Comment"] = Relationship(back_populates="author")
    notifications: List["Notification"] = Relationship(back_populates="user")
    
    def verify_password(self, password: str) -> bool:
        # 密码验证逻辑
        return True
    
    @property
    def active_projects(self) -> List["Project"]:
        return [pm.project for pm in self.project_memberships 
                if pm.project.status == ProjectStatus.ACTIVE]

class Project(SQLModel, table=True):
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    status: ProjectStatus = Field(default=ProjectStatus.PLANNING)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[Decimal] = None
    creator_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    creator: User = Relationship(back_populates="created_projects")
    members: List[ProjectMember] = Relationship(back_populates="project")
    tasks: List["Task"] = Relationship(back_populates="project")
    files: List["ProjectFile"] = Relationship(back_populates="project")
    
    @property
    def progress(self) -> float:
        """计算项目进度"""
        if not self.tasks:
            return 0.0
        
        completed_tasks = sum(1 for task in self.tasks if task.status == TaskStatus.DONE)
        return (completed_tasks / len(self.tasks)) * 100
    
    @property
    def total_hours(self) -> Decimal:
        """计算总工时"""
        return sum(task.total_hours for task in self.tasks)
    
    def get_member_role(self, user_id: int) -> Optional[UserRole]:
        """获取成员角色"""
        for member in self.members:
            if member.user_id == user_id:
                return member.role
        return None

class Task(SQLModel, table=True):
    __tablename__ = "tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    description: Optional[str] = None
    status: TaskStatus = Field(default=TaskStatus.TODO, index=True)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM, index=True)
    estimated_hours: Optional[Decimal] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    
    # 外键
    project_id: int = Field(foreign_key="projects.id", index=True)
    creator_id: int = Field(foreign_key="users.id")
    parent_task_id: Optional[int] = Field(foreign_key="tasks.id", default=None)
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    project: Project = Relationship(back_populates="tasks")
    creator: User = Relationship(back_populates="created_tasks")
    assignees: List[TaskAssignee] = Relationship(back_populates="task")
    parent_task: Optional["Task"] = Relationship(
        back_populates="subtasks",
        sa_relationship_kwargs={"remote_side": "Task.id"}
    )
    subtasks: List["Task"] = Relationship(back_populates="parent_task")
    time_logs: List["TimeLog"] = Relationship(back_populates="task")
    comments: List["Comment"] = Relationship(back_populates="task")
    files: List["TaskFile"] = Relationship(back_populates="task")
    
    @property
    def total_hours(self) -> Decimal:
        """计算总工时"""
        return sum(log.hours for log in self.time_logs)
    
    @property
    def is_overdue(self) -> bool:
        """是否逾期"""
        if not self.due_date or self.status == TaskStatus.DONE:
            return False
        return date.today() > self.due_date
    
    def can_edit(self, user_id: int) -> bool:
        """检查用户是否可以编辑任务"""
        # 创建者可以编辑
        if self.creator_id == user_id:
            return True
        
        # 分配给的用户可以编辑
        for assignee in self.assignees:
            if assignee.user_id == user_id:
                return True
        
        # 项目管理员可以编辑
        role = self.project.get_member_role(user_id)
        return role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]

class TimeLog(SQLModel, table=True):
    __tablename__ = "time_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hours: Decimal = Field(gt=0)
    description: Optional[str] = None
    date: date = Field(default_factory=date.today)
    
    # 外键
    task_id: int = Field(foreign_key="tasks.id")
    user_id: int = Field(foreign_key="users.id")
    
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    task: Task = Relationship(back_populates="time_logs")
    user: User = Relationship(back_populates="time_logs")

class Comment(SQLModel, table=True):
    __tablename__ = "comments"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str
    
    # 外键
    task_id: int = Field(foreign_key="tasks.id")
    author_id: int = Field(foreign_key="users.id")
    
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    task: Task = Relationship(back_populates="comments")
    author: User = Relationship(back_populates="comments")

class ProjectFile(SQLModel, table=True):
    __tablename__ = "project_files"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    file_path: str
    
    # 外键
    project_id: int = Field(foreign_key="projects.id")
    uploaded_by: int = Field(foreign_key="users.id")
    
    uploaded_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    project: Project = Relationship(back_populates="files")
    uploader: User = Relationship()

class TaskFile(SQLModel, table=True):
    __tablename__ = "task_files"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    file_path: str
    
    # 外键
    task_id: int = Field(foreign_key="tasks.id")
    uploaded_by: int = Field(foreign_key="users.id")
    
    uploaded_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
    task: Task = Relationship(back_populates="files")
    uploader: User = Relationship()

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    type: NotificationType
    title: str
    content: str
    is_read: bool = Field(default=False)
    
    # 外键
    user_id: int = Field(foreign_key="users.id")
    
    created_at: datetime = Field(default_factory=datetime.now)
    
    # 关系
     user: User = Relationship(back_populates="notifications")
 ```

### 3.3 服务层实现

```python
from sqlalchemy import func, and_, or_, desc
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
import logging

logger = logging.getLogger(__name__)

class TaskManagementService:
    def __init__(self, session: Session):
        self.session = session
    
    # 项目管理
    async def create_project(self, creator_id: int, project_data: Dict[str, Any]) -> Project:
        """创建项目"""
        project = Project(
            creator_id=creator_id,
            **project_data
        )
        
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        
        # 添加创建者为项目管理员
        await self.add_project_member(project.id, creator_id, UserRole.PROJECT_MANAGER)
        
        return project
    
    async def add_project_member(self, project_id: int, user_id: int, 
                               role: UserRole = UserRole.DEVELOPER) -> ProjectMember:
        """添加项目成员"""
        # 检查是否已是成员
        existing_member = self.session.exec(
            select(ProjectMember).where(
                and_(ProjectMember.project_id == project_id,
                     ProjectMember.user_id == user_id)
            )
        ).first()
        
        if existing_member:
            # 更新角色
            existing_member.role = role
            self.session.add(existing_member)
            member = existing_member
        else:
            # 添加新成员
            member = ProjectMember(
                project_id=project_id,
                user_id=user_id,
                role=role
            )
            self.session.add(member)
        
        self.session.commit()
        self.session.refresh(member)
        
        # 发送通知
        await self._send_notification(
            user_id, NotificationType.PROJECT_UPDATED,
            "项目邀请", f"您已被邀请加入项目"
        )
        
        return member
    
    async def get_user_projects(self, user_id: int, status: ProjectStatus = None) -> List[Project]:
        """获取用户参与的项目"""
        query = (
            select(Project)
            .join(ProjectMember)
            .where(ProjectMember.user_id == user_id)
            .options(selectinload(Project.members))
        )
        
        if status:
            query = query.where(Project.status == status)
        
        return self.session.exec(query.order_by(Project.updated_at.desc())).all()
    
    # 任务管理
    async def create_task(self, creator_id: int, task_data: Dict[str, Any]) -> Task:
        """创建任务"""
        # 验证项目权限
        project = self.session.get(Project, task_data['project_id'])
        if not project:
            raise ValueError("项目不存在")
        
        role = project.get_member_role(creator_id)
        if not role:
            raise ValueError("您不是项目成员")
        
        task = Task(
            creator_id=creator_id,
            **task_data
        )
        
        self.session.add(task)
        self.session.commit()
        self.session.refresh(task)
        
        return task
    
    async def assign_task(self, task_id: int, user_ids: List[int], 
                        assigner_id: int) -> List[TaskAssignee]:
        """分配任务"""
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("任务不存在")
        
        # 检查权限
        if not task.can_edit(assigner_id):
            raise ValueError("没有权限分配此任务")
        
        # 清除现有分配
        existing_assignees = self.session.exec(
            select(TaskAssignee).where(TaskAssignee.task_id == task_id)
        ).all()
        
        for assignee in existing_assignees:
            self.session.delete(assignee)
        
        # 添加新分配
        new_assignees = []
        for user_id in user_ids:
            # 验证用户是项目成员
            role = task.project.get_member_role(user_id)
            if not role:
                continue
            
            assignee = TaskAssignee(
                task_id=task_id,
                user_id=user_id
            )
            self.session.add(assignee)
            new_assignees.append(assignee)
            
            # 发送通知
            await self._send_notification(
                user_id, NotificationType.TASK_ASSIGNED,
                "任务分配", f"您被分配了新任务：{task.title}"
            )
        
        self.session.commit()
        return new_assignees
    
    async def update_task_status(self, task_id: int, status: TaskStatus, 
                               user_id: int) -> Task:
        """更新任务状态"""
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("任务不存在")
        
        if not task.can_edit(user_id):
            raise ValueError("没有权限编辑此任务")
        
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        
        if status == TaskStatus.DONE:
            task.completed_at = datetime.now()
        
        self.session.add(task)
        self.session.commit()
        
        # 发送通知给相关人员
        if status == TaskStatus.DONE:
            await self._notify_task_completion(task)
        
        return task
    
    async def get_user_tasks(self, user_id: int, status: TaskStatus = None,
                           project_id: int = None, page: int = 1, 
                           per_page: int = 20) -> Dict[str, Any]:
        """获取用户任务"""
        query = (
            select(Task)
            .join(TaskAssignee)
            .where(TaskAssignee.user_id == user_id)
            .options(selectinload(Task.project))
            .options(selectinload(Task.assignees))
        )
        
        if status:
            query = query.where(Task.status == status)
        
        if project_id:
            query = query.where(Task.project_id == project_id)
        
        # 计算总数
        total = self.session.exec(
            select(func.count(Task.id)).where(query.whereclause)
        ).one()
        
        # 分页查询
        tasks = self.session.exec(
            query
            .order_by(Task.priority.desc(), Task.due_date.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        
        return {
            'tasks': tasks,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    # 时间记录
    async def log_time(self, user_id: int, task_id: int, hours: float, 
                     description: str = None, log_date: date = None) -> TimeLog:
        """记录工时"""
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("任务不存在")
        
        # 检查用户是否被分配到此任务
        is_assigned = any(assignee.user_id == user_id for assignee in task.assignees)
        if not is_assigned and task.creator_id != user_id:
            raise ValueError("您未被分配到此任务")
        
        time_log = TimeLog(
            task_id=task_id,
            user_id=user_id,
            hours=Decimal(str(hours)),
            description=description,
            date=log_date or date.today()
        )
        
        self.session.add(time_log)
        self.session.commit()
        self.session.refresh(time_log)
        
        return time_log
    
    async def get_time_logs(self, user_id: int = None, task_id: int = None,
                          project_id: int = None, start_date: date = None,
                          end_date: date = None) -> List[TimeLog]:
        """获取工时记录"""
        query = select(TimeLog).options(
            selectinload(TimeLog.task).selectinload(Task.project),
            selectinload(TimeLog.user)
        )
        
        if user_id:
            query = query.where(TimeLog.user_id == user_id)
        
        if task_id:
            query = query.where(TimeLog.task_id == task_id)
        
        if project_id:
            query = query.join(Task).where(Task.project_id == project_id)
        
        if start_date:
            query = query.where(TimeLog.date >= start_date)
        
        if end_date:
            query = query.where(TimeLog.date <= end_date)
        
        return self.session.exec(
            query.order_by(TimeLog.date.desc())
        ).all()
    
    # 评论管理
    async def add_comment(self, user_id: int, task_id: int, content: str) -> Comment:
        """添加评论"""
        task = self.session.get(Task, task_id)
        if not task:
            raise ValueError("任务不存在")
        
        # 检查用户是否有权限查看此任务
        role = task.project.get_member_role(user_id)
        if not role:
            raise ValueError("没有权限访问此任务")
        
        comment = Comment(
            task_id=task_id,
            author_id=user_id,
            content=content
        )
        
        self.session.add(comment)
        self.session.commit()
        self.session.refresh(comment)
        
        # 通知任务相关人员
        await self._notify_comment_added(task, comment)
        
        return comment
    
    async def get_task_comments(self, task_id: int) -> List[Comment]:
        """获取任务评论"""
        return self.session.exec(
            select(Comment)
            .where(Comment.task_id == task_id)
            .options(selectinload(Comment.author))
            .order_by(Comment.created_at.asc())
        ).all()
    
    # 统计分析
    async def get_project_stats(self, project_id: int) -> Dict[str, Any]:
        """获取项目统计"""
        project = self.session.get(Project, project_id)
        if not project:
            raise ValueError("项目不存在")
        
        # 任务统计
        task_stats = self.session.exec(
            select(
                Task.status,
                func.count(Task.id).label('count')
            )
            .where(Task.project_id == project_id)
            .group_by(Task.status)
        ).all()
        
        # 工时统计
        total_hours = self.session.exec(
            select(func.sum(TimeLog.hours))
            .join(Task)
            .where(Task.project_id == project_id)
        ).one() or Decimal('0')
        
        # 成员工时统计
        member_hours = self.session.exec(
            select(
                User.full_name,
                func.sum(TimeLog.hours).label('hours')
            )
            .join(TimeLog)
            .join(Task)
            .where(Task.project_id == project_id)
            .group_by(User.id, User.full_name)
        ).all()
        
        return {
            'project': project,
            'task_stats': {status: count for status, count in task_stats},
            'total_hours': float(total_hours),
            'member_hours': [
                {'name': name, 'hours': float(hours)} 
                for name, hours in member_hours
            ],
            'progress': project.progress
        }
    
    async def get_user_stats(self, user_id: int, start_date: date = None,
                           end_date: date = None) -> Dict[str, Any]:
        """获取用户统计"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()
        
        # 任务完成统计
        completed_tasks = self.session.exec(
            select(func.count(Task.id))
            .join(TaskAssignee)
            .where(
                and_(
                    TaskAssignee.user_id == user_id,
                    Task.status == TaskStatus.DONE,
                    Task.completed_at >= datetime.combine(start_date, datetime.min.time()),
                    Task.completed_at <= datetime.combine(end_date, datetime.max.time())
                )
            )
        ).one()
        
        # 工时统计
        total_hours = self.session.exec(
            select(func.sum(TimeLog.hours))
            .where(
                and_(
                    TimeLog.user_id == user_id,
                    TimeLog.date >= start_date,
                    TimeLog.date <= end_date
                )
            )
        ).one() or Decimal('0')
        
        # 每日工时
        daily_hours = self.session.exec(
            select(
                TimeLog.date,
                func.sum(TimeLog.hours).label('hours')
            )
            .where(
                and_(
                    TimeLog.user_id == user_id,
                    TimeLog.date >= start_date,
                    TimeLog.date <= end_date
                )
            )
            .group_by(TimeLog.date)
            .order_by(TimeLog.date)
        ).all()
        
        return {
            'completed_tasks': completed_tasks,
            'total_hours': float(total_hours),
            'daily_hours': [
                {'date': str(date), 'hours': float(hours)}
                for date, hours in daily_hours
            ]
        }
    
    # 通知系统
    async def _send_notification(self, user_id: int, type: NotificationType,
                               title: str, content: str):
        """发送通知"""
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            content=content
        )
        
        self.session.add(notification)
        self.session.commit()
    
    async def _notify_task_completion(self, task: Task):
        """通知任务完成"""
        # 通知项目创建者和管理员
        project_managers = [
            member.user_id for member in task.project.members
            if member.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]
        ]
        
        for user_id in project_managers:
            await self._send_notification(
                user_id, NotificationType.TASK_COMPLETED,
                "任务完成", f"任务 '{task.title}' 已完成"
            )
    
    async def _notify_comment_added(self, task: Task, comment: Comment):
        """通知评论添加"""
        # 通知任务分配者（除了评论作者）
        notify_users = set()
        
        # 添加任务创建者
        if task.creator_id != comment.author_id:
            notify_users.add(task.creator_id)
        
        # 添加任务分配者
        for assignee in task.assignees:
            if assignee.user_id != comment.author_id:
                notify_users.add(assignee.user_id)
        
        for user_id in notify_users:
            await self._send_notification(
                user_id, NotificationType.COMMENT_ADDED,
                "新评论", f"任务 '{task.title}' 有新评论"
            )
    
    async def get_user_notifications(self, user_id: int, unread_only: bool = False,
                                   page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """获取用户通知"""
        query = select(Notification).where(Notification.user_id == user_id)
        
        if unread_only:
            query = query.where(Notification.is_read == False)
        
        # 计算总数
        total = self.session.exec(
            select(func.count(Notification.id)).where(query.whereclause)
        ).one()
        
        # 分页查询
        notifications = self.session.exec(
            query
            .order_by(Notification.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()
        
        return {
            'notifications': notifications,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': (total + per_page - 1) // per_page
        }
    
    async def mark_notification_read(self, notification_id: int, user_id: int):
        """标记通知为已读"""
        notification = self.session.get(Notification, notification_id)
        if notification and notification.user_id == user_id:
            notification.is_read = True
            self.session.add(notification)
            self.session.commit()
```

## 本章总结

### 核心概念回顾

通过三个项目实战案例，我们深入学习了 SQLModel 在生产级应用中的实践：

1. **博客管理系统**：展示了基础的 CRUD 操作、关系管理和 API 设计
2. **电商订单系统**：演示了复杂业务逻辑、事务处理和库存管理
3. **任务管理平台**：实现了权限控制、实时协作和统计分析

### 最佳实践总结

**模型设计：**
- 合理使用枚举类型定义状态和类型
- 设计清晰的关系和外键约束
- 添加必要的索引提升查询性能
- 实现业务方法和属性计算

**服务层架构：**
- 将业务逻辑封装在服务类中
- 使用事务确保数据一致性
- 实现完善的错误处理机制
- 添加日志记录和监控

**API 设计：**
- 使用 Pydantic 模型进行数据验证
- 实现 JWT 认证和权限控制
- 提供完整的 CRUD 接口
- 添加分页和过滤功能

### 常见陷阱与避免方法

**性能陷阱：**
- N+1 查询问题：使用 `selectinload` 预加载关系
- 大数据量查询：实现分页和索引优化
- 复杂统计查询：使用聚合函数和子查询

**业务逻辑陷阱：**
- 并发控制：使用乐观锁或悲观锁
- 数据一致性：合理使用事务边界
- 权限控制：实现细粒度的权限检查

**架构陷阱：**
- 紧耦合：保持服务层和数据层的分离
- 缺乏测试：编写单元测试和集成测试
- 缺乏监控：添加日志和性能监控

### 实践检查清单

**开发阶段：**
- [ ] 设计合理的数据模型和关系
- [ ] 实现完整的业务逻辑
- [ ] 添加数据验证和错误处理
- [ ] 编写单元测试和集成测试

**部署阶段：**
- [ ] 配置生产环境数据库
- [ ] 设置监控和日志系统
- [ ] 实现备份和恢复策略
- [ ] 配置负载均衡和缓存

**运维阶段：**
- [ ] 监控系统性能和错误
- [ ] 定期备份和维护数据库
- [ ] 优化查询和索引
- [ ] 处理用户反馈和问题

### 下一步学习

**深入学习方向：**
1. **微服务架构**：学习如何将单体应用拆分为微服务
2. **分布式系统**：了解分布式事务和一致性
3. **性能优化**：深入学习数据库优化和缓存策略
4. **DevOps 实践**：学习 CI/CD 和容器化部署

**推荐资源：**
- FastAPI 官方文档
- SQLAlchemy 高级特性
- 分布式系统设计
- 微服务架构模式

**扩展练习：**

**初级练习：**
1. 为博客系统添加标签功能
2. 实现电商系统的优惠券功能
3. 为任务管理系统添加甘特图功能

**中级练习：**
1. 实现博客系统的全文搜索
2. 添加电商系统的推荐算法
3. 实现任务管理系统的工作流引擎

**高级练习：**
1. 将系统拆分为微服务架构
2. 实现分布式事务处理
3. 添加实时协作功能

**项目实战：**
1. **在线教育平台**：课程管理、学习进度跟踪、考试系统
2. **客户关系管理系统**：客户管理、销售流程、数据分析
3. **物联网数据平台**：设备管理、数据采集、实时监控

通过这些项目案例的学习和实践，您已经掌握了使用 SQLModel 构建生产级应用的核心技能。继续实践和探索，您将能够构建更加复杂和强大的应用系统。

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // 认证
  async login(username: string, password: string) {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async register(userData: any) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async getCurrentUser() {
    return this.request('/auth/me');
  }

  // 文章
  async getPosts(params: any = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/posts?${queryString}`);
  }

  async getPost(slug: string) {
    return this.request(`/posts/${slug}`);
  }

  async createPost(postData: any) {
    return this.request('/posts', {
      method: 'POST',
      body: JSON.stringify(postData),
    });
  }

  async publishPost(postId: number) {
    return this.request(`/posts/${postId}/publish`, {
      method: 'PUT',
    });
  }

  // 评论
  async getComments(postId: number) {
    return this.request(`/posts/${postId}/comments`);
  }

  async createComment(postId: number, commentData: any) {
    return this.request(`/posts/${postId}/comments`, {
      method: 'POST',
      body: JSON.stringify(commentData),
    });
  }

  // 分类和标签
  async getCategories() {
    return this.request('/categories');
  }

  async getTags() {
    return this.request('/tags');
  }

  // 统计
  async getStats() {
    return this.request('/stats');
  }
}

export const blogAPI = new BlogAPI();

// components/PostList.tsx
import React, { useState, useEffect } from 'react';
import { Post } from '../types/blog';
import { blogAPI } from '../services/api';

interface PostListProps {
  category?: number;
  tag?: number;
  search?: string;
}

export const PostList: React.FC<PostListProps> = ({ category, tag, search }) => {
  const [posts, setPosts] = useState<Post[]>([]);
  const [loading, setLoading] = useState(true);
  const [pagination, setPagination] = useState({
    page: 1,
    per_page: 10,
    total: 0,
    pages: 0,
  });

  useEffect(() => {
    loadPosts();
  }, [category, tag, search, pagination.page]);

  const loadPosts = async () => {
    try {
      setLoading(true);
      const params: any = {
        page: pagination.page,
        per_page: pagination.per_page,
        status: 'published',
      };

      if (category) params.category_id = category;
      if (tag) params.tag_id = tag;
      if (search) params.search = search;

      const response = await blogAPI.getPosts(params);
      setPosts(response.posts);
      setPagination({
        page: response.page,
        per_page: response.per_page,
        total: response.total,
        pages: response.pages,
      });
    } catch (error) {
      console.error('Failed to load posts:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (page: number) => {
    setPagination(prev => ({ ...prev, page }));
  };

  if (loading) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <div className="post-list">
      {posts.map(post => (
        <article key={post.id} className="post-item">
          {post.featured_image && (
            <img 
              src={post.featured_image} 
              alt={post.title}
              className="post-image"
            />
          )}
          <div className="post-content">
            <h2 className="post-title">
              <a href={`/posts/${post.slug}`}>{post.title}</a>
            </h2>
            <div className="post-meta">
              <span className="author">作者：{post.author.display_name}</span>
              <span className="date">
                发布时间：{new Date(post.published_at!).toLocaleDateString()}
              </span>
              <span className="reading-time">阅读时间：{post.reading_time} 分钟</span>
            </div>
            <p className="post-excerpt">{post.excerpt}</p>
            <div className="post-tags">
              {post.tags.map(tag => (
                <span key={tag.id} className="tag">{tag.name}</span>
              ))}
            </div>
            <div className="post-stats">
              <span>浏览：{post.view_count}</span>
              <span>点赞：{post.like_count}</span>
              <span>评论：{post.comment_count}</span>
            </div>
          </div>
        </article>
      ))}
      
      {pagination.pages > 1 && (
        <div className="pagination">
          {Array.from({ length: pagination.pages }, (_, i) => i + 1).map(page => (
            <button
              key={page}
              onClick={() => handlePageChange(page)}
              className={page === pagination.page ? 'active' : ''}
            >
              {page}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

// components/PostDetail.tsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Post, Comment } from '../types/blog';
import { blogAPI } from '../services/api';
import { CommentList } from './CommentList';

export const PostDetail: React.FC = () => {
  const { slug } = useParams<{ slug: string }>();
  const [post, setPost] = useState<Post | null>(null);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (slug) {
      loadPost();
      loadComments();
    }
  }, [slug]);

  const loadPost = async () => {
    try {
      const response = await blogAPI.getPost(slug!);
      setPost(response);
    } catch (error) {
      console.error('Failed to load post:', error);
    }
  };

  const loadComments = async () => {
    try {
      const response = await blogAPI.getComments(post?.id!);
      setComments(response);
    } catch (error) {
      console.error('Failed to load comments:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading || !post) {
    return <div className="loading">加载中...</div>;
  }

  return (
    <article className="post-detail">
      <header className="post-header">
        <h1 className="post-title">{post.title}</h1>
        <div className="post-meta">
          <span className="author">作者：{post.author.display_name}</span>
          <span className="date">
            发布时间：{new Date(post.published_at!).toLocaleDateString()}
          </span>
          <span className="reading-time">阅读时间：{post.reading_time} 分钟</span>
        </div>
        {post.featured_image && (
          <img 
            src={post.featured_image} 
            alt={post.title}
            className="featured-image"
          />
        )}
      </header>
      
      <div className="post-content" 
           dangerouslySetInnerHTML={{ __html: post.content }} />
      
      <footer className="post-footer">
        <div className="post-tags">
          {post.tags.map(tag => (
            <span key={tag.id} className="tag">{tag.name}</span>
          ))}
        </div>
        <div className="post-stats">
          <span>浏览：{post.view_count}</span>
          <span>点赞：{post.like_count}</span>
          <span>评论：{post.comment_count}</span>
        </div>
      </footer>
      
      {post.allow_comments && (
        <section className="comments-section">
          <h3>评论</h3>
          <CommentList 
            comments={comments} 
            postId={post.id}
            onCommentAdded={loadComments}
          />
        </section>
      )}
    </article>
  );
};
```
```