from pathlib import Path
from pydantic_settings import BaseSettings


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"


# ── Embedding inference (single source of truth) ──
# Free functions so both the global Settings object and per-user resolved
# configs compute backend/model/path identically.

def embedding_mode_of(backend: str, api_base: str, api_key: str) -> str:
    if backend:
        b = backend.strip().lower()
        if b in {"api", "local"}:
            return b
        raise ValueError("EMBEDDING_BACKEND must be 'api' or 'local'")
    if api_base or api_key:
        return "api"
    return "local"


def embedding_api_model_of(api_model: str, deprecated_model: str = "") -> str:
    return api_model or deprecated_model or DEFAULT_EMBEDDING_MODEL


def embedding_local_model_of(local_model: str, deprecated_model: str = "") -> str:
    return local_model or deprecated_model or DEFAULT_EMBEDDING_MODEL


def embedding_local_path_of(
    local_path: str, local_model: str, base_dir: Path, deprecated_model: str = ""
) -> "Path | None":
    if local_path:
        return Path(local_path).expanduser()
    bundled_path = base_dir / "data" / "models" / "bge-m3"
    if embedding_local_model_of(local_model, deprecated_model) == DEFAULT_EMBEDDING_MODEL and bundled_path.exists():
        return bundled_path
    return None


def embedding_target_of(
    backend: str, api_base: str, api_key: str, api_model: str,
    local_model: str, local_path: str, base_dir: Path, deprecated_model: str = "",
) -> str:
    """Identity string for an embedding config — also used as the cache/rebuild signature."""
    if embedding_mode_of(backend, api_base, api_key) == "api":
        return embedding_api_model_of(api_model, deprecated_model)
    path = embedding_local_path_of(local_path, local_model, base_dir, deprecated_model)
    if path is not None:
        return str(path)
    return embedding_local_model_of(local_model, deprecated_model)


class Settings(BaseSettings):
    # LLM (OpenAI-compatible proxy)
    api_base: str = ""
    api_key: str = ""
    model: str = ""
    temperature: float = 0.7

    # Embedding — explicit backend + separate config for API/local modes
    embedding_backend: str = ""  # api | local; empty keeps legacy inference
    embedding_api_base: str = ""
    embedding_api_key: str = ""
    embedding_api_model: str = ""
    local_embedding_model: str = ""
    local_embedding_path: str = ""
    embedding_model: str = ""  # deprecated fallback for EMBEDDING_MODEL

    # DashScope ASR (speech-to-text, batch transcription)
    dashscope_api_key: str = ""

    # Copilot — 独立 LLM 配置（可选，不填则 fallback 到主 LLM）
    copilot_api_base: str = ""
    copilot_api_key: str = ""
    copilot_model: str = ""
    copilot_temperature: float = 0.3  # Copilot 场景偏确定性

    # Copilot — 腾讯云 VPR 声纹识别（可选，未配置时自动回退手动按钮模式）
    # 允许在用户 settings.json 中覆盖，此处为全局兜底
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    tencent_vpr_app_id: str = ""

    # Copilot — Tavily Web Search
    tavily_api_key: str = ""

    # Alibaba Cloud OSS (only long-audio filetrans needs a public URL;
    # short audio goes through base64 sync chat/completions, no OSS required).
    aliyun_oss_access_key_id: str = ""
    aliyun_oss_access_key_secret: str = ""
    aliyun_oss_bucket: str = ""
    aliyun_oss_endpoint: str = ""  # e.g. "oss-cn-shanghai.aliyuncs.com"

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    resume_path: Path = Path(__file__).resolve().parent.parent / "data" / "resume"
    knowledge_path: Path = Path(__file__).resolve().parent.parent / "data" / "knowledge"
    high_freq_path: Path = Path(__file__).resolve().parent.parent / "data" / "high_freq"
    db_path: Path = Path(__file__).resolve().parent.parent / "data" / "interviews.db"

    # Auth
    jwt_secret: str = "change-me-in-production"
    default_email: str = "admin@techspar.local"
    default_password: str = "admin123"
    default_name: str = "Admin"
    allow_registration: bool = False

    # Interview settings
    max_questions_per_phase: int = 5
    max_drill_questions: int = 15

    def user_data_dir(self, user_id: str) -> Path:
        return self.base_dir / "data" / "users" / user_id

    def user_profile_dir(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "profile"

    def user_resume_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "resume"

    def user_knowledge_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "knowledge"

    def user_high_freq_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "high_freq"

    def user_topics_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "topics.json"

    def user_index_cache_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / ".index_cache"

    def user_settings_path(self, user_id: str) -> Path:
        return self.user_data_dir(user_id) / "settings.json"

    def user_provider_path(self, user_id: str) -> Path:
        """Per-user LLM/Embedding provider overrides."""
        return self.user_data_dir(user_id) / "provider.json"

    @property
    def effective_dashscope_api_key(self) -> str:
        """DashScope API key, with fallback to COPILOT_API_KEY when the Copilot
        LLM is already pointed at DashScope's OpenAI-compatible endpoint.

        Lets users reuse a single DashScope account key across LLM + ASR
        without forcing them to duplicate it into two env vars.
        """
        if self.dashscope_api_key:
            return self.dashscope_api_key
        if self.copilot_api_key and "dashscope.aliyuncs.com" in (self.copilot_api_base or ""):
            return self.copilot_api_key
        return ""

    def embedding_backend_mode(self) -> str:
        return embedding_mode_of(self.embedding_backend, self.embedding_api_base, self.embedding_api_key)

    def embedding_api_model_name(self) -> str:
        return embedding_api_model_of(self.embedding_api_model, self.embedding_model)

    def local_embedding_model_name(self) -> str:
        return embedding_local_model_of(self.local_embedding_model, self.embedding_model)

    def local_embedding_model_path(self) -> Path | None:
        return embedding_local_path_of(
            self.local_embedding_path, self.local_embedding_model, self.base_dir, self.embedding_model
        )

    def active_embedding_target(self) -> str:
        return embedding_target_of(
            self.embedding_backend, self.embedding_api_base, self.embedding_api_key,
            self.embedding_api_model, self.local_embedding_model, self.local_embedding_path,
            self.base_dir, self.embedding_model,
        )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
