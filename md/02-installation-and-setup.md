# SQLModel 安装配置指南

## 📖 章节概览

本章将指导您完成 SQLModel 开发环境的搭建，从 Python 环境配置到第一个可运行的示例。我们将涵盖不同操作系统的安装方法、数据库选择、开发工具配置以及常见问题的解决方案。

## 🎯 学习目标

完成本章学习后，您将能够：
- ✅ 配置适合 SQLModel 开发的 Python 环境
- ✅ 正确安装 SQLModel 及其依赖
- ✅ 选择并配置合适的数据库
- ✅ 设置高效的开发工具
- ✅ 运行第一个 SQLModel 程序
- ✅ 解决常见的安装和配置问题

---

## 1. 环境要求

### 1.1 Python 版本要求

```bash
# SQLModel 支持的 Python 版本
Python 3.7+  # 最低要求
Python 3.8+  # 推荐版本
Python 3.9+  # 更好的类型注解支持
Python 3.10+ # 最佳体验（联合类型语法）
Python 3.11+ # 性能最优
```

**版本选择建议**：
- 🟢 **生产环境**：Python 3.9 或 3.10（稳定性与特性的平衡）
- 🟡 **学习环境**：Python 3.10+（最新特性体验）
- 🔴 **避免使用**：Python 3.7（即将停止支持）

### 1.2 系统要求

| 操作系统 | 最低版本 | 推荐版本 | 备注 |
|----------|----------|----------|------|
| **Windows** | Windows 10 | Windows 11 | 支持 WSL2 |
| **macOS** | macOS 10.14 | macOS 12+ | 支持 Apple Silicon |
| **Linux** | Ubuntu 18.04+ | Ubuntu 22.04+ | 其他发行版同等版本 |

### 1.3 硬件要求

```yaml
最低配置:
  内存: 4GB RAM
  存储: 2GB 可用空间
  处理器: 双核 2.0GHz

推荐配置:
  内存: 8GB+ RAM
  存储: 10GB+ 可用空间（包含数据库）
  处理器: 四核 2.5GHz+
```

---

## 2. Python 环境配置

### 2.1 检查现有 Python 环境

```bash
# 检查 Python 版本
python --version
# 或
python3 --version

# 检查 pip 版本
pip --version
# 或
pip3 --version

# 检查已安装的包
pip list
```

**预期输出示例**：
```
Python 3.10.8
pip 22.3.1 from /usr/local/lib/python3.10/site-packages/pip (python 3.10)
```

### 2.2 安装 Python（如果需要）

#### Windows 系统

```powershell
# 方法 1: 从官网下载安装包
# 访问 https://www.python.org/downloads/
# 下载最新版本的 Python 安装包

# 方法 2: 使用 Chocolatey
choco install python

# 方法 3: 使用 Microsoft Store
# 搜索 "Python" 并安装

# 方法 4: 使用 pyenv-win
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv
# 然后配置环境变量
```

#### macOS 系统

```bash
# 方法 1: 使用 Homebrew（推荐）
brew install python@3.10

# 方法 2: 使用 pyenv
brew install pyenv
pyenv install 3.10.8
pyenv global 3.10.8

# 方法 3: 从官网下载
# 访问 https://www.python.org/downloads/macos/
```

#### Linux 系统

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.10 python3.10-pip python3.10-venv

# CentOS/RHEL/Fedora
sudo dnf install python3.10 python3-pip

# 使用 pyenv（推荐）
curl https://pyenv.run | bash
pyenv install 3.10.8
pyenv global 3.10.8
```

### 2.3 虚拟环境配置

#### 为什么需要虚拟环境？

```mermaid
graph TD
    A["🏠 系统 Python"] --> B["📦 全局包"]
    A --> C["🔒 权限问题"]
    A --> D["⚠️ 版本冲突"]
    
    E["🏗️ 虚拟环境"] --> F["🔐 隔离环境"]
    E --> G["📋 依赖管理"]
    E --> H["🚀 部署一致性"]
    
    style A fill:#ffcccc
    style E fill:#ccffcc
```

#### 创建虚拟环境

```bash
# 方法 1: 使用 venv（Python 内置）
python -m venv sqlmodel-env

# 方法 2: 使用 virtualenv
pip install virtualenv
virtualenv sqlmodel-env

# 方法 3: 使用 conda
conda create -n sqlmodel-env python=3.10

# 方法 4: 使用 poetry（推荐用于项目管理）
poetry init
poetry install
```

#### 激活虚拟环境

```bash
# Windows
sqlmodel-env\Scripts\activate

# macOS/Linux
source sqlmodel-env/bin/activate

# Conda
conda activate sqlmodel-env

# Poetry
poetry shell
```

**激活成功的标志**：
```bash
# 命令行前缀会显示虚拟环境名称
(sqlmodel-env) $ python --version
Python 3.10.8
```

---

## 3. SQLModel 安装

### 3.1 基础安装

```bash
# 确保虚拟环境已激活
(sqlmodel-env) $ pip install sqlmodel

# 验证安装
(sqlmodel-env) $ python -c "import sqlmodel; print(sqlmodel.__version__)"
0.0.8  # 版本号可能不同
```

### 3.2 完整安装（推荐）

```bash
# 安装 SQLModel 及常用数据库驱动
pip install sqlmodel[all]

# 或者分别安装
pip install sqlmodel
pip install psycopg2-binary  # PostgreSQL
pip install pymysql          # MySQL
pip install aiomysql         # MySQL 异步
pip install asyncpg          # PostgreSQL 异步
```

### 3.3 开发环境安装

```bash
# 安装开发和测试相关的包
pip install sqlmodel
pip install pytest           # 测试框架
pip install pytest-asyncio   # 异步测试
pip install black            # 代码格式化
pip install mypy             # 类型检查
pip install pre-commit       # Git 钩子
pip install jupyter          # Jupyter Notebook
```

### 3.4 使用 requirements.txt

创建 `requirements.txt` 文件：

```txt
# requirements.txt
sqlmodel==0.0.8
fastapi==0.104.1
uvicorn[standard]==0.24.0
psycopg2-binary==2.9.7
pymysql==1.1.0
pytest==7.4.3
black==23.10.1
mypy==1.7.0
```

安装依赖：
```bash
pip install -r requirements.txt
```

### 3.5 使用 Poetry（推荐）

创建 `pyproject.toml` 文件：

```toml
[tool.poetry]
name = "sqlmodel-project"
version = "0.1.0"
description = "SQLModel learning project"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.10"
sqlmodel = "^0.0.8"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
psycopg2-binary = "^2.9.7"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
black = "^23.10.1"
mypy = "^1.7.0"
pre-commit = "^3.5.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

安装依赖：
```bash
poetry install
```

---

## 4. 数据库配置

### 4.1 数据库选择指南

| 数据库 | 适用场景 | 优势 | 劣势 |
|--------|----------|------|------|
| **SQLite** | 学习、原型、小型应用 | 零配置、文件数据库 | 并发限制、功能有限 |
| **PostgreSQL** | 生产环境、复杂应用 | 功能强大、标准兼容 | 配置复杂、资源占用 |
| **MySQL** | Web 应用、中型项目 | 性能好、生态丰富 | 标准兼容性一般 |
| **SQL Server** | 企业环境、.NET 集成 | 企业特性、工具丰富 | 许可成本、平台限制 |

### 4.2 SQLite 配置（推荐入门）

```python
# sqlite_config.py
from sqlmodel import create_engine

# SQLite 数据库配置
DATABASE_URL = "sqlite:///./test.db"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 打印 SQL 语句（开发时有用）
    connect_args={"check_same_thread": False}  # SQLite 特定配置
)

print("SQLite 数据库配置完成")
print(f"数据库文件位置: {DATABASE_URL}")
```

**优势**：
- ✅ 无需安装额外软件
- ✅ 零配置即可使用
- ✅ 适合学习和开发

### 4.3 PostgreSQL 配置

#### 安装 PostgreSQL

```bash
# Windows (使用 Chocolatey)
choco install postgresql

# macOS (使用 Homebrew)
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql

# 使用 Docker（推荐）
docker run --name postgres-db \
  -e POSTGRES_PASSWORD=mypassword \
  -e POSTGRES_DB=sqlmodel_db \
  -p 5432:5432 \
  -d postgres:15
```

#### PostgreSQL 配置代码

```python
# postgresql_config.py
from sqlmodel import create_engine
import os

# PostgreSQL 数据库配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://username:password@localhost:5432/sqlmodel_db"
)

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接
    pool_timeout=30,     # 连接超时
    pool_recycle=3600    # 连接回收时间
)

print("PostgreSQL 数据库配置完成")
```

#### 环境变量配置

创建 `.env` 文件：
```bash
# .env
DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/sqlmodel_db
DATABASE_ECHO=True
DATABASE_POOL_SIZE=10
```

使用环境变量：
```python
# config.py
from sqlmodel import create_engine
from dotenv import load_dotenv
import os

# 加载环境变量
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
DATABASE_ECHO = os.getenv("DATABASE_ECHO", "False").lower() == "true"

engine = create_engine(
    DATABASE_URL,
    echo=DATABASE_ECHO
)
```

### 4.4 MySQL 配置

#### 安装 MySQL

```bash
# Windows (使用 Chocolatey)
choco install mysql

# macOS (使用 Homebrew)
brew install mysql
brew services start mysql

# Ubuntu/Debian
sudo apt update
sudo apt install mysql-server
sudo systemctl start mysql

# 使用 Docker
docker run --name mysql-db \
  -e MYSQL_ROOT_PASSWORD=rootpassword \
  -e MYSQL_DATABASE=sqlmodel_db \
  -e MYSQL_USER=myuser \
  -e MYSQL_PASSWORD=mypassword \
  -p 3306:3306 \
  -d mysql:8.0
```

#### MySQL 配置代码

```python
# mysql_config.py
from sqlmodel import create_engine

# MySQL 数据库配置
DATABASE_URL = "mysql+pymysql://username:password@localhost:3306/sqlmodel_db"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
    pool_recycle=3600,
    connect_args={
        "charset": "utf8mb4",
        "use_unicode": True
    }
)

print("MySQL 数据库配置完成")
```

---

## 5. 开发工具配置

### 5.1 IDE/编辑器推荐

#### Visual Studio Code（推荐）

**必装扩展**：
```json
{
  "recommendations": [
    "ms-python.python",              // Python 支持
    "ms-python.pylint",              // 代码检查
    "ms-python.black-formatter",     // 代码格式化
    "ms-python.mypy-type-checker",   // 类型检查
    "ms-vscode.vscode-json",         // JSON 支持
    "redhat.vscode-yaml",            // YAML 支持
    "ms-vscode.vscode-sqlite",       // SQLite 查看器
    "ckolkman.vscode-postgres"       // PostgreSQL 支持
  ]
}
```

**配置文件** (`.vscode/settings.json`)：
```json
{
  "python.defaultInterpreterPath": "./sqlmodel-env/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=88"],
  "python.typeChecking": "strict",
  "files.associations": {
    "*.py": "python"
  }
}
```

#### PyCharm

**配置步骤**：
1. 设置 Python 解释器为虚拟环境
2. 启用类型检查
3. 配置代码格式化工具
4. 安装数据库插件

#### Jupyter Notebook

```bash
# 安装 Jupyter
pip install jupyter ipykernel

# 注册虚拟环境内核
python -m ipykernel install --user --name=sqlmodel-env

# 启动 Jupyter
jupyter notebook
```

### 5.2 代码质量工具

#### Black（代码格式化）

```bash
# 安装
pip install black

# 使用
black your_file.py
black .  # 格式化所有文件
```

配置文件 (`pyproject.toml`)：
```toml
[tool.black]
line-length = 88
target-version = ['py310']
include = '\.pyi?$'
extend-exclude = '''
(
  /(
      \.eggs
    | \.git
    | \.venv
    | build
    | dist
  )/
)
'''
```

#### MyPy（类型检查）

```bash
# 安装
pip install mypy

# 使用
mypy your_file.py
mypy .  # 检查所有文件
```

配置文件 (`mypy.ini`)：
```ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_decorators = True
no_implicit_optional = True
warn_redundant_casts = True
warn_unused_ignores = True
warn_no_return = True
warn_unreachable = True
strict_equality = True

[mypy-sqlmodel.*]
ignore_missing_imports = True
```

#### Pre-commit（Git 钩子）

```bash
# 安装
pip install pre-commit

# 初始化
pre-commit install
```

配置文件 (`.pre-commit-config.yaml`)：
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.10.1
    hooks:
      - id: black
        language_version: python3.10

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        additional_dependencies: [sqlmodel]
```

---

## 6. 第一个 SQLModel 程序

### 6.1 项目结构

```
sqlmodel-tutorial/
├── .env                    # 环境变量
├── .gitignore             # Git 忽略文件
├── requirements.txt       # 依赖列表
├── README.md             # 项目说明
├── config/
│   ├── __init__.py
│   └── database.py       # 数据库配置
├── models/
│   ├── __init__.py
│   └── hero.py          # 模型定义
├── main.py              # 主程序
└── tests/
    ├── __init__.py
    └── test_hero.py     # 测试文件
```

### 6.2 数据库配置模块

```python
# config/database.py
from sqlmodel import create_engine, SQLModel, Session
from typing import Generator
import os

# 数据库 URL（默认使用 SQLite）
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tutorial.db")

# 创建数据库引擎
engine = create_engine(
    DATABASE_URL,
    echo=True,  # 开发时显示 SQL 语句
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

def create_db_and_tables():
    """创建数据库表"""
    SQLModel.metadata.create_all(engine)
    print("✅ 数据库表创建成功")

def get_session() -> Generator[Session, None, None]:
    """获取数据库会话"""
    with Session(engine) as session:
        yield session
```

### 6.3 模型定义

```python
# models/hero.py
from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime

class HeroBase(SQLModel):
    """英雄基础模型（共享字段）"""
    name: str = Field(max_length=50, description="英雄名称")
    secret_name: str = Field(description="真实姓名")
    age: Optional[int] = Field(default=None, ge=0, le=200, description="年龄")

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
```

### 6.4 主程序

```python
# main.py
from typing import List
from sqlmodel import Session, select
from config.database import create_db_and_tables, get_session
from models.hero import Hero, HeroCreate

def create_hero(session: Session, hero_data: HeroCreate) -> Hero:
    """创建英雄"""
    hero = Hero.from_orm(hero_data)
    session.add(hero)
    session.commit()
    session.refresh(hero)
    print(f"✅ 创建英雄成功: {hero.name}")
    return hero

def get_heroes(session: Session) -> List[Hero]:
    """获取所有英雄"""
    statement = select(Hero)
    heroes = session.exec(statement).all()
    print(f"📋 找到 {len(heroes)} 个英雄")
    return heroes

def get_hero_by_id(session: Session, hero_id: int) -> Hero | None:
    """根据 ID 获取英雄"""
    hero = session.get(Hero, hero_id)
    if hero:
        print(f"🔍 找到英雄: {hero.name}")
    else:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
    return hero

def update_hero(session: Session, hero_id: int, hero_data: dict) -> Hero | None:
    """更新英雄信息"""
    hero = session.get(Hero, hero_id)
    if not hero:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
        return None
    
    for key, value in hero_data.items():
        if hasattr(hero, key) and value is not None:
            setattr(hero, key, value)
    
    session.add(hero)
    session.commit()
    session.refresh(hero)
    print(f"✅ 更新英雄成功: {hero.name}")
    return hero

def delete_hero(session: Session, hero_id: int) -> bool:
    """删除英雄"""
    hero = session.get(Hero, hero_id)
    if not hero:
        print(f"❌ 未找到 ID 为 {hero_id} 的英雄")
        return False
    
    session.delete(hero)
    session.commit()
    print(f"🗑️ 删除英雄成功: {hero.name}")
    return True

def main():
    """主函数 - 演示 CRUD 操作"""
    print("🚀 SQLModel 教程 - 第一个程序")
    print("=" * 40)
    
    # 创建数据库表
    create_db_and_tables()
    
    # 获取数据库会话
    session_gen = get_session()
    session = next(session_gen)
    
    try:
        # 1. 创建英雄
        print("\n1️⃣ 创建英雄")
        hero1_data = HeroCreate(
            name="Spider-Man",
            secret_name="Peter Parker",
            age=25
        )
        hero1 = create_hero(session, hero1_data)
        
        hero2_data = HeroCreate(
            name="Iron Man",
            secret_name="Tony Stark",
            age=45
        )
        hero2 = create_hero(session, hero2_data)
        
        # 2. 查询所有英雄
        print("\n2️⃣ 查询所有英雄")
        all_heroes = get_heroes(session)
        for hero in all_heroes:
            print(f"  - {hero.name} ({hero.secret_name}), 年龄: {hero.age}")
        
        # 3. 根据 ID 查询英雄
        print("\n3️⃣ 根据 ID 查询英雄")
        hero = get_hero_by_id(session, 1)
        if hero:
            print(f"  英雄详情: {hero.name}, 创建时间: {hero.created_at}")
        
        # 4. 更新英雄信息
        print("\n4️⃣ 更新英雄信息")
        updated_hero = update_hero(session, 1, {"age": 26})
        if updated_hero:
            print(f"  更新后年龄: {updated_hero.age}")
        
        # 5. 删除英雄
        print("\n5️⃣ 删除英雄")
        delete_success = delete_hero(session, 2)
        
        # 6. 再次查询验证
        print("\n6️⃣ 验证删除结果")
        remaining_heroes = get_heroes(session)
        for hero in remaining_heroes:
            print(f"  - {hero.name} ({hero.secret_name})")
            
    except Exception as e:
        print(f"❌ 程序执行出错: {e}")
        session.rollback()
    finally:
        session.close()
        print("\n🎉 程序执行完成")

if __name__ == "__main__":
    main()
```

### 6.5 运行程序

```bash
# 确保虚拟环境已激活
(sqlmodel-env) $ python main.py
```

**预期输出**：
```
🚀 SQLModel 教程 - 第一个程序
========================================
✅ 数据库表创建成功

1️⃣ 创建英雄
✅ 创建英雄成功: Spider-Man
✅ 创建英雄成功: Iron Man

2️⃣ 查询所有英雄
📋 找到 2 个英雄
  - Spider-Man (Peter Parker), 年龄: 25
  - Iron Man (Tony Stark), 年龄: 45

3️⃣ 根据 ID 查询英雄
🔍 找到英雄: Spider-Man
  英雄详情: Spider-Man, 创建时间: 2024-12-01 10:30:45.123456

4️⃣ 更新英雄信息
✅ 更新英雄成功: Spider-Man
  更新后年龄: 26

5️⃣ 删除英雄
🗑️ 删除英雄成功: Iron Man

6️⃣ 验证删除结果
📋 找到 1 个英雄
  - Spider-Man (Peter Parker)

🎉 程序执行完成
```

---

## 7. 常见问题与解决方案

### 7.1 安装问题

#### 问题 1：pip 安装失败

```bash
# 错误信息
ERROR: Could not find a version that satisfies the requirement sqlmodel

# 解决方案
# 1. 升级 pip
pip install --upgrade pip

# 2. 使用国内镜像
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple sqlmodel

# 3. 检查 Python 版本
python --version  # 确保是 3.7+
```

#### 问题 2：数据库驱动安装失败

```bash
# PostgreSQL 驱动问题
# 错误: Microsoft Visual C++ 14.0 is required

# Windows 解决方案
# 1. 安装 Visual Studio Build Tools
# 2. 或使用预编译版本
pip install psycopg2-binary

# macOS 解决方案
brew install postgresql
pip install psycopg2-binary

# Linux 解决方案
sudo apt-get install libpq-dev python3-dev
pip install psycopg2-binary
```

### 7.2 数据库连接问题

#### 问题 1：SQLite 权限错误

```python
# 错误信息
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file

# 解决方案
import os

# 确保目录存在
db_dir = os.path.dirname("./data/tutorial.db")
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

# 使用绝对路径
DATABASE_URL = f"sqlite:///{os.path.abspath('./data/tutorial.db')}"
```

#### 问题 2：PostgreSQL 连接被拒绝

```python
# 错误信息
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) connection to server at "localhost" (127.0.0.1), port 5432 failed

# 解决方案检查清单
# 1. 确认 PostgreSQL 服务运行
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # macOS

# 2. 检查端口是否开放
netstat -an | grep 5432

# 3. 检查防火墙设置
sudo ufw status  # Ubuntu

# 4. 验证用户权限
psql -U username -d database_name -h localhost
```

### 7.3 代码问题

#### 问题 1：导入错误

```python
# 错误信息
ModuleNotFoundError: No module named 'sqlmodel'

# 解决方案
# 1. 确认虚拟环境已激活
which python  # 应该指向虚拟环境

# 2. 重新安装
pip uninstall sqlmodel
pip install sqlmodel

# 3. 检查 PYTHONPATH
echo $PYTHONPATH
```

#### 问题 2：类型检查错误

```python
# MyPy 错误
error: Cannot determine type of 'table'

# 解决方案
# 1. 更新 MyPy 配置
# mypy.ini
[mypy-sqlmodel.*]
ignore_missing_imports = True

# 2. 或在代码中忽略
from sqlmodel import SQLModel  # type: ignore
```

### 7.4 性能问题

#### 问题 1：查询速度慢

```python
# 问题代码
for hero in heroes:
    print(hero.team.name)  # N+1 查询问题

# 解决方案：使用 joinedload
from sqlalchemy.orm import selectinload

statement = select(Hero).options(selectinload(Hero.team))
heroes = session.exec(statement).all()
```

#### 问题 2：内存占用过高

```python
# 问题代码
all_heroes = session.exec(select(Hero)).all()  # 加载所有数据到内存

# 解决方案：使用分页
from sqlmodel import select

def get_heroes_paginated(session: Session, page: int = 1, size: int = 100):
    offset = (page - 1) * size
    statement = select(Hero).offset(offset).limit(size)
    return session.exec(statement).all()
```

---

## 8. 验证安装

### 8.1 环境检查脚本

```python
# check_environment.py
import sys
import subprocess
from typing import List, Tuple

def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本"""
    version = sys.version_info
    if version >= (3, 7):
        return True, f"✅ Python {version.major}.{version.minor}.{version.micro}"
    else:
        return False, f"❌ Python {version.major}.{version.minor}.{version.micro} (需要 3.7+)"

def check_package(package_name: str) -> Tuple[bool, str]:
    """检查包是否安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {package_name}; print({package_name}.__version__)"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"✅ {package_name} {version}"
        else:
            return False, f"❌ {package_name} 未安装"
    except Exception as e:
        return False, f"❌ {package_name} 检查失败: {e}"

def check_database_connection(database_url: str) -> Tuple[bool, str]:
    """检查数据库连接"""
    try:
        from sqlmodel import create_engine
        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True, f"✅ 数据库连接成功: {database_url}"
    except Exception as e:
        return False, f"❌ 数据库连接失败: {e}"

def main():
    """主检查函数"""
    print("🔍 SQLModel 环境检查")
    print("=" * 40)
    
    checks = [
        ("Python 版本", lambda: check_python_version()),
        ("SQLModel", lambda: check_package("sqlmodel")),
        ("FastAPI", lambda: check_package("fastapi")),
        ("Uvicorn", lambda: check_package("uvicorn")),
        ("Pytest", lambda: check_package("pytest")),
        ("SQLite 连接", lambda: check_database_connection("sqlite:///test.db")),
    ]
    
    all_passed = True
    for name, check_func in checks:
        try:
            passed, message = check_func()
            print(f"{name}: {message}")
            if not passed:
                all_passed = False
        except Exception as e:
            print(f"{name}: ❌ 检查失败: {e}")
            all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("🎉 所有检查通过！环境配置正确。")
    else:
        print("⚠️ 部分检查失败，请根据上述信息修复问题。")

if __name__ == "__main__":
    main()
```

运行检查：
```bash
(sqlmodel-env) $ python check_environment.py
```

### 8.2 功能测试脚本

```python
# test_functionality.py
from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
import tempfile
import os

class TestHero(SQLModel, table=True):
    """测试用英雄模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    power: str

def test_basic_functionality():
    """测试基础功能"""
    print("🧪 测试 SQLModel 基础功能")
    
    # 创建临时数据库
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    
    try:
        # 创建引擎和表
        engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(engine)
        print("✅ 数据库表创建成功")
        
        # 测试 CRUD 操作
        with Session(engine) as session:
            # Create
            hero = TestHero(name="Test Hero", power="Testing")
            session.add(hero)
            session.commit()
            session.refresh(hero)
            print(f"✅ 创建记录成功: ID {hero.id}")
            
            # Read
            statement = select(TestHero).where(TestHero.name == "Test Hero")
            found_hero = session.exec(statement).first()
            assert found_hero is not None
            print(f"✅ 查询记录成功: {found_hero.name}")
            
            # Update
            found_hero.power = "Super Testing"
            session.add(found_hero)
            session.commit()
            print("✅ 更新记录成功")
            
            # Delete
            session.delete(found_hero)
            session.commit()
            print("✅ 删除记录成功")
        
        print("🎉 所有功能测试通过！")
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        raise
    finally:
        # 清理临时文件
        if os.path.exists(db_path):
            os.unlink(db_path)

if __name__ == "__main__":
    test_basic_functionality()
```

---

## 9. 总结与下一步

### 9.1 本章要点回顾

✅ **环境配置**：Python 3.7+、虚拟环境、SQLModel 安装  
✅ **数据库选择**：SQLite（入门）、PostgreSQL（生产）、MySQL（Web）  
✅ **开发工具**：VS Code、PyCharm、Jupyter、代码质量工具  
✅ **第一个程序**：完整的 CRUD 操作示例  
✅ **问题解决**：常见安装和配置问题的解决方案  

### 9.2 环境检查清单

在继续下一章之前，请确保：

- [ ] Python 3.7+ 已安装并可正常使用
- [ ] 虚拟环境已创建并激活
- [ ] SQLModel 及相关依赖已安装
- [ ] 数据库（至少 SQLite）可正常连接
- [ ] 开发工具已配置并支持类型检查
- [ ] 第一个程序可以成功运行
- [ ] 环境检查脚本全部通过

### 9.3 下一步学习

🎯 **下一章预告**：[03-first-model.md](./03-first-model.md)  
在下一章中，我们将深入学习：
- 模型类的详细定义
- 字段类型和约束
- 表配置和自定义
- 数据验证机制
- 模型继承和组合

### 9.4 实践建议

#### 🔄 日常开发流程
```bash
# 1. 激活虚拟环境
source sqlmodel-env/bin/activate

# 2. 更新依赖（定期）
pip install --upgrade sqlmodel

# 3. 运行代码质量检查
black .
mypy .

# 4. 运行测试
pytest

# 5. 提交代码
git add .
git commit -m "feat: add new feature"
```

#### 📚 扩展学习
- 阅读 SQLModel 官方文档
- 学习 SQLAlchemy 核心概念
- 了解 Pydantic 数据验证
- 实践不同数据库的使用

---

**📚 相关资源**
- [Python 官方文档](https://docs.python.org/3/)
- [SQLModel 官方文档](https://sqlmodel.fastapi.org.cn/)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)
- [VS Code Python 扩展](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

**🔗 导航**
- [⬅️ 上一章：SQLModel 介绍与核心概念](./01-introduction-and-concepts.md)
- [➡️ 下一章：第一个 SQLModel 模型](./03-first-model.md)
- [🏠 返回目录](./README.md)

---

**最后更新**：2024年12月  
**版本**：v1.0  
**作者**：SQLModel 中文教程团队