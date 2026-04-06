from pydantic import BaseModel


class PostRequest(BaseModel):
    text: str
    model: str = "qwen2.5:7b"

