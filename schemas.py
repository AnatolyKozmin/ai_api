from pydantic import BaseModel


class PostRequest(BaseModel):
    text: str
    model: str = 'qwen3:8b'

