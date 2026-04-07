from pydantic import BaseModel, ConfigDict, Field


class PostRequest(BaseModel):
    """Тело от бота: достаточно text (+ model); остальное для логов и трассировки."""

    model_config = ConfigDict(extra="ignore")

    text: str
    model: str = "qwen2.5:7b"
    id: int | None = Field(default=None, description="ID записи в SQLite бота")
    chat_id: int | None = None
    chat_title: str | None = None
    channel_username: str | None = Field(
        default=None,
        description="Публичный username канала без @ — контекст для organization",
    )
    message_id: int | None = None
    url: str | None = None
    system_prompt: str | None = Field(
        default=None,
        description=(
            "Если поле передано (в т.ч. пустая строка), подставляется вместо встроенного SYSTEM_PROMPT API; "
            "если ключ не отправлять — используется дефолтный промпт на сервере."
        ),
    )

