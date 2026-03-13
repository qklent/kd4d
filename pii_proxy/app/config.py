from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    triton_url: str = "localhost:8001"
    triton_model_name: str = "rubert_ner"
    triton_tokenizer_name: str = "ai-forever/ruBert-base"

    llm_base_url: str = "http://localhost:8000/v1"
    llm_api_key: str = "EMPTY"
    llm_timeout: float = 120.0

    vault_ttl: int = 3600

    ner_confidence_threshold: float = 0.7
    regex_base_confidence: float = 0.4
    regex_context_confidence: float = 0.99
    context_window_chars: int = 50

    host: str = "0.0.0.0"
    port: int = 9000

    model_config = {"env_prefix": "", "case_sensitive": False, "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
