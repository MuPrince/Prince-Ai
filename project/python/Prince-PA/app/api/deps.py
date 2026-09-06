from app.core.database import SessionLocal


def get_session_factory():
    """供后台任务与流式生成获取独立 Session 工厂。"""
    return SessionLocal
