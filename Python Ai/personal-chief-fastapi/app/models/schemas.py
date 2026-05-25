from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    messages: str
    message_id: str
    image_url: Optional[str] = None
