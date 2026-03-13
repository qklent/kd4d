from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from .config import settings
from .detection.merger import SpanMerger
from .detection.pipeline import DetectionPipeline
from .detection.regex_detector import RegexDetector
from .llm.client import LLMClient
from .llm.demasker import StreamingDemasker, demask_text
from .masking.masker import PIIMasker
from .masking.vault import SessionVault
from .models.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ResponseChoice,
    ResponseMessage,
    UsageInfo,
)

# --- Globals initialized at startup ---
detection_pipeline: DetectionPipeline
masker: PIIMasker
vault: SessionVault
llm_client: LLMClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global detection_pipeline, masker, vault, llm_client

    detectors = [RegexDetector(
        base_confidence=settings.regex_base_confidence,
        context_confidence=settings.regex_context_confidence,
        context_window=settings.context_window_chars,
    )]

    # Triton NER is optional — only enable if configured and reachable
    try:
        from .detection.triton_ner import TritonNERDetector

        # BIO label map for dslim/bert-base-NER (CoNLL-2003, 9 labels)
        # See: https://huggingface.co/dslim/bert-base-NER
        label_map = {
            0: "O",
            1: "B-MISC", 2: "I-MISC",
            3: "B-PER",  4: "I-PER",
            5: "B-ORG",  6: "I-ORG",
            7: "B-LOC",  8: "I-LOC",
        }
        ner = TritonNERDetector(
            triton_url=settings.triton_url,
            model_name=settings.triton_model_name,
            tokenizer_name=settings.triton_tokenizer_name,
            label_map=label_map,
            confidence_threshold=settings.ner_confidence_threshold,
        )
        if not await ner.client.is_server_ready():
            raise ConnectionError("Triton server is not ready")
        detectors.append(ner)
    except Exception:
        logger.error("Triton NER unavailable, falling back to regex-only detection", exc_info=True)

    detection_pipeline = DetectionPipeline(detectors=detectors, merger=SpanMerger())
    masker = PIIMasker()
    vault = SessionVault(ttl_seconds=settings.vault_ttl)
    llm_client = LLMClient()

    yield

    await llm_client.close()


app = FastAPI(title="PII Masking Proxy", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    session_id = request.session_id or str(uuid.uuid4())

    masked_messages, combined_mapping = await _mask_messages(request)
    vault.store(session_id, combined_mapping)

    if request.stream:
        return StreamingResponse(
            _stream_and_demask(masked_messages, session_id, request),
            media_type="text/event-stream",
        )

    llm_response = await llm_client.complete(masked_messages, request)

    content = ""
    if llm_response.get("choices"):
        content = llm_response["choices"][0].get("message", {}).get("content", "")
    demasked = demask_text(content, vault.get_mapping(session_id))

    return ChatCompletionResponse(
        id=llm_response.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
        created=llm_response.get("created", int(time.time())),
        model=llm_response.get("model", request.model),
        choices=[
            ResponseChoice(
                message=ResponseMessage(content=demasked),
            )
        ],
        usage=UsageInfo(**llm_response.get("usage", {})),
    )


async def _mask_messages(
    request: ChatCompletionRequest,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    masked_messages: list[dict[str, str]] = []
    combined_mapping: dict[str, str] = {}

    for msg in request.messages:
        spans = await detection_pipeline.detect(msg.content)
        masked_text, mapping = masker.mask(msg.content, spans)
        combined_mapping.update(mapping)
        masked_messages.append({"role": msg.role, "content": masked_text})

    return masked_messages, combined_mapping


async def _stream_and_demask(
    messages: list[dict[str, str]],
    session_id: str,
    request: ChatCompletionRequest,
):
    mapping = vault.get_mapping(session_id)
    demasker = StreamingDemasker(mapping)

    async for chunk in llm_client.stream(messages, request):
        delta_content = _extract_delta_content(chunk)
        if delta_content:
            demasked = demasker.feed(delta_content)
            if demasked:
                yield _format_sse_chunk(chunk, demasked)

    remaining = demasker.finalize()
    if remaining:
        yield _format_sse_final(remaining)

    yield "data: [DONE]\n\n"


def _extract_delta_content(chunk: dict) -> str | None:
    choices = chunk.get("choices", [])
    if not choices:
        return None
    delta = choices[0].get("delta", {})
    return delta.get("content")


def _format_sse_chunk(original_chunk: dict, new_content: str) -> str:
    chunk_copy = dict(original_chunk)
    if chunk_copy.get("choices"):
        chunk_copy["choices"][0]["delta"]["content"] = new_content
    return f"data: {json.dumps(chunk_copy, ensure_ascii=False)}\n\n"


def _format_sse_final(content: str) -> str:
    chunk = {
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "proxy",
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
