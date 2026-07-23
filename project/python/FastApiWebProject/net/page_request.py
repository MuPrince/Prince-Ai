from fastapi import Query
from pydantic import BaseModel


class PageParams(BaseModel):
    page: int
    pageSize: int

def common_page(
    page: int = Query(0, ge=0),
    page_size: int = Query(10, le=50)
) -> PageParams:
    return PageParams(page=page, pageSize=page_size)