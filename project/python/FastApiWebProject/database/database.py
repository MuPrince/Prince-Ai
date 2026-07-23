from datetime import datetime

from sqlalchemy import DateTime, func, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

ASYNC_DATABASE_URL = "mysql+aiomysql://root:root@localhost:3306/kacha?charset=utf8"

# 创建异步引擎
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,          # 打印SQL语句（生产环境可关闭）
    pool_size=10,
    max_overflow=10,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_session():
    async with AsyncSessionLocal() as session:
        try :
            yield session  #返回会话
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise
        finally:
            await session.close()

class Base(DeclarativeBase):
    # create_time: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    # update_time: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    pass

# 初始化数据库（创建表）
async def init_db():
    async with async_engine.begin() as conn:
        # 删除所有表（谨慎使用，仅用于演示）
        # await conn.run_sync(Base.metadata.drop_all)
        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        result = await conn.execute(text("SELECT 1"))
        print(f"连接成功: {result.scalar()}")
