from sqlmodel import create_engine

# SQLite 数据库配置
DATABASE_URL = "sqlite:///./test.db"

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    echo = True,
    connect_args={"check_same_thread":False}
)

print("SQLite 数据库配置完成")
print(f"数据库文件位置：{DATABASE_URL}")