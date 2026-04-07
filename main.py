import logging
import os
import re
import json
from pathlib import Path
from typing import Annotated

import requests
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException

load_dotenv(Path(__file__).resolve().parent / ".env")

from logging_config import setup_logging
from schemas import PostRequest
from sheets import append_vacancy_row

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title='CT AI API')


def _ingest_secret_expected() -> str:
    return os.environ.get("INGEST_SECRET", "").strip()


async def verify_ingest_secret(
    x_ingest_secret: Annotated[str | None, Header(alias="X-Ingest-Secret")] = None,
) -> None:
    """Если задан INGEST_SECRET в окружении API — требуем такой же заголовок от бота."""
    expected = _ingest_secret_expected()
    if not expected:
        return
    if not x_ingest_secret or x_ingest_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ingest-Secret")

SYSTEM_PROMPT = """
Ты изучаешь текст из Telegram‑поста. Твоя задача определить, является ли этот пост
вакансией на стажировку или на работу. Если это текст о вакансии, в нём должна быть 
информация о том, на какую должность берут, какой график, какая заработная плата и т.п.

Если пост **не является вакансией** (например, объявление, реклама, несвязный текст),
выведи пустой JSON‑объект: `{}`.

Если пост **вакансия**, то выведи **строго** следующий JSON‑объект.
Ключи и их смысл:
- organization: Организация (название компании, студии, агентства, команды и т.п.).
- division: Подразделение внутри организации (если указано).
- vacancy_type: Тип вакансии — «стажировка» или «работа».
- role: Вакансия (должность, позиция, специальность).
- field: Сфера (например, IT, дизайн, маркетинг, бэкенд‑разработка, продажи и т.п.).
- salary: ЗП (заработная плата, указать диапазон или фиксированную сумму, валюту).
- schedule: График (например, 5/2, 2/2, с 9:00 до 18:00, 36 часов в неделю и т.п.).
- format: Формат работы (офис, частичный офис, полностью удалённо и т.п.).
- description: Описание вакансии (кратко своими словами, ключевые обязанности и требования).
- employment_format: Формат трудоустройства (например, ТК РФ, самозанятость, гражданско‑правовой договор, нетрудоустройства / стажировка без ТК и т.п.).
- feature1: Особенность 1 (например, бесплатное обучение, бонусы, компенсация питания, обучение за счёт компании).
- feature2: Особенность 2 (например, перспективы карьеры, менторство, возможность удалённой работы после стажировки).
- feature3: Особенность 3 (любой вид особенности который не подошёл под первые две)
Выведи **только валидный JSON**. Не добавляй никаких пояснений, комментариев, markdown, текста вокруг JSON.
Если какое‑то поле неизвестно, поставь вместо него пустую строку, но не удаляй ключ.

Перед текстом поста может быть блок «Контекст источника» с username и названием Telegram‑канала.
Если в тексте поста организация‑работодатель не указана, используй этот контекст: для канала одной компании
заполни organization названием бренда, выводимым из названия канала и/или @username (без выдумывания —
если нельзя уверенно сопоставить с компанией, оставь organization пустым); если канал по смыслу агрегирует
чужие вакансии и работодатель в посте не назван — organization оставь пустым.

Пример ответа:
{
  "organization": "С科技",
  "division": "",
  "vacancy_type": "работа",
  "role": "Python-разработчик",
  "field": "IT / разработка",
  "salary": "150–200k ₽",
  "schedule": "5/2, с 9:00 до 18:00",
  "format": "офис",
  "description": "Разработка и поддержка внутренних сервисов на Python, работа с командой...",
  "employment_format": "ТК РФ",
  "feature1": "Компенсация питания",
  "feature2": "Обучение за счёт компании",
  "feature3": "Полный пакет ДМС"
}
"""


def _post_with_source_context(req: PostRequest) -> str:
    """Текст поста + блок про ТГК для модели."""
    lines: list[str] = []
    if req.channel_username or req.chat_title:
        lines.append("Контекст источника (Telegram-канал):")
        if req.channel_username:
            lines.append(f"- Юзернейм: @{req.channel_username}")
        if req.chat_title:
            lines.append(f"- Название: «{req.chat_title}»")
        lines.append("")
    lines.append("Пост:")
    lines.append(req.text)
    return "\n".join(lines)


def _ollama_full_prompt(req: PostRequest) -> str:
    """
    Сборка промпта для Ollama.

    - system_prompt не задан в запросе (null) — используется встроенный SYSTEM_PROMPT API.
    - system_prompt задан (включая "") — только он как «системная» часть; пустая строка = без системных инструкций,
      в промпт попадает лишь пользовательский блок (контекст канала + пост).
    """
    user_block = _post_with_source_context(req)
    if req.system_prompt is None:
        return f"{SYSTEM_PROMPT}\n\n{user_block}"
    system = req.system_prompt.strip()
    if not system:
        return user_block
    return f"{system}\n\n{user_block}"


@app.post("/parse_post", dependencies=[Depends(verify_ingest_secret)])
async def parse_post(req: PostRequest):
    try:
        logger.info(
            "parse_post job_id=%s chat=%s ch_user=%s msg_id=%s model=%s text_len=%s system=%s",
            req.id,
            req.chat_id,
            req.channel_username,
            req.message_id,
            req.model,
            len(req.text) if req.text else 0,
            "client" if req.system_prompt is not None else "api_default",
        )
        payload = {
            "model": req.model,
            "prompt": _ollama_full_prompt(req),
            "stream": False
        }

        ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
        ollama_timeout = int(os.environ.get("OLLAMA_REQUEST_TIMEOUT", "300"))
        resp = requests.post(
            f"{ollama_base}/api/generate",
            json=payload,
            timeout=ollama_timeout,
        )

        resp.raise_for_status()
        data = resp.json()

        llm_output = data.get("response", "")

        parsed = None

        try:
            parsed = json.loads(llm_output)
        except json.JSONDecodeError as e:
            logger.warning("LLM JSON parse failed: %s", e)
            m = re.search(r"\{.*\}", llm_output, flags=re.DOTALL)
            if m:
                try:
                    parsed = json.loads(m.group(0))
                except json.JSONDecodeError as e2:
                    logger.warning("JSON extract fallback failed: %s", e2)
        
        if not isinstance(parsed, dict):
            parsed = {}

        vacancy_type = parsed.get("vacancy_type", "").strip().lower()
        if vacancy_type not in ["работа", "стажировка", ""]:
            parsed["vacancy_type"] = ""

        sheets_appended = False
        sheets_skipped = False
        sheets_error: str | None = None

        if parsed:
            try:
                ok, sheets_detail = append_vacancy_row(
                    parsed,
                    post_url=req.url,
                    post_text=req.text,
                )
                if ok:
                    sheets_appended = True
                elif sheets_detail == "not_configured":
                    sheets_skipped = True
            except Exception as e:
                msg = str(e)
                r = getattr(e, "response", None)
                if r is not None and getattr(r, "text", None):
                    msg = f"{msg} | {r.text[:800]}"
                sheets_error = msg
                logger.exception("Google Sheets append failed: %s", e)

        logger.info(
            "parse_post ok vacancy_parsed=%s sheets_appended=%s",
            bool(parsed),
            sheets_appended,
        )
        return {
            "success": True,
            "llm_output": llm_output,
            "parsed": parsed,
            "model": req.model,
            "text": req.text,
            "sheets_appended": sheets_appended,
            "sheets_skipped_not_configured": sheets_skipped,
            "sheets_error": sheets_error,
        }
    
    except requests.RequestException as e:
        logger.error("Ollama request failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=502,
            detail=f"Запрос не оч, вот проблема: {str(e)}",
        )

    except Exception as e:
        logger.exception("parse_post failed: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"Ошибочка на сервере: {str(e)}",
        )
    

@app.get('/health_check')
async def health_check():
    return{'status': "norm"}

