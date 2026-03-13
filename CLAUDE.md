# CLAUDE.md

## Project Overview

**PII Masking Proxy** — an async FastAPI service that intercepts LLM requests, detects and masks Russian PII (INN, SNILS, Passport, Phone, Email, OGRN, PERSON, etc.) before forwarding to the LLM, then restores original values in the response.

**Flow:** Request → Detect PII → Mask with placeholders → Forward to LLM → Demask response → Return to client

## Structure

```
pii_proxy/
├── app/
│   ├── main.py              # FastAPI app, /v1/chat/completions endpoint
│   ├── config.py            # Pydantic Settings (env vars)
│   ├── models/schemas.py    # Request/response Pydantic models
│   ├── detection/
│   │   ├── base.py          # PIISpan dataclass, Detector protocol
│   │   ├── pipeline.py      # Runs detectors in parallel, merges results
│   │   ├── regex_detector.py# Regex + checksum validation, context boosting
│   │   ├── triton_ner.py    # Optional RuBERT NER via Triton gRPC
│   │   └── merger.py        # Span conflict resolution (higher conf wins)
│   ├── masking/
│   │   ├── masker.py        # Replaces spans with [TYPE_N] placeholders
│   │   └── vault.py         # Session-based TTL store: placeholder→original
│   └── llm/
│       ├── client.py        # Async httpx client, streaming SSE support
│       └── demasker.py      # Reverses placeholders; StreamingDemasker buffers tokens
└── tests/                   # pytest + pytest-asyncio
```

## Tech Stack

- **Python 3.11+**, FastAPI, Uvicorn, Pydantic v2, httpx
- **Triton Inference Server** (optional) — RuBERT NER model via gRPC
- **HuggingFace Transformers** — ruBERT tokenizer
- Docker + Docker Compose (Triton on :8001, proxy on :9000, Redis on :6379)

## Commands

```bash
# Install (from pii_proxy/)
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 9000

# Docker
docker-compose up
```

## Key Config (env vars)

| Variable | Default | Description |
|---|---|---|
| `TRITON_URL` | `localhost:8001` | Triton gRPC endpoint |
| `LLM_BASE_URL` | `http://localhost:8000/v1` | Upstream LLM |
| `LLM_API_KEY` | `EMPTY` | Bearer token |
| `VAULT_TTL` | `3600` | Session mapping TTL (seconds) |
| `NER_CONFIDENCE_THRESHOLD` | `0.7` | Min NER confidence |
| `REGEX_BASE_CONFIDENCE` | `0.4` | Regex match without context keyword |
| `REGEX_CONTEXT_CONFIDENCE` | `0.99` | Regex match with context keyword |

## Logging Requirements

All code must include thorough logging for debuggability:
- Use Python's `logging` module (`logger = logging.getLogger(__name__)`) in every module
- Log at `ERROR` level with `exc_info=True` for all caught exceptions — never silently swallow errors with bare `pass` or `except: pass`
- Log at `INFO` level for significant state changes: startup/shutdown, connections established/lost, configuration loaded, external service status
- Log at `DEBUG` level for request/response details, detection results, masking operations, and other per-request data useful for troubleshooting
- Always include relevant context in log messages (session IDs, request IDs, entity counts, endpoint URLs, etc.)
- When integrating with external services (Triton, LLM, Redis), log connection attempts, failures, and fallback behavior

## Architecture Notes

- **Detection** runs regex + NER in parallel; `SpanMerger` resolves overlaps (higher confidence wins, NER preferred over regex for same span)
- **Triton NER** is optional — if unavailable, falls back to regex-only silently
- **SessionVault** is in-memory with TTL; `session_id` in request body scopes the placeholder mappings
- **StreamingDemasker** buffers up to 50 chars to handle placeholders split across SSE tokens
- Regex patterns include Luhn-style checksum validation for INN and SNILS
- Context keywords (e.g., "ИНН", "паспорт") boost regex confidence from 0.4 → 0.99
