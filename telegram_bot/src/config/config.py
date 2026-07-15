import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _openrouter_api_key() -> str | None:
    key = os.getenv("OPENROUTER_API_KEY")
    if key and not os.getenv("OPENAI_API_KEY"):
        # Some langchain-openai versions validate OpenAI credentials even when a
        # custom OpenRouter base_url is used.
        os.environ["OPENAI_API_KEY"] = key
    return key


def _service_url(prefix: str, default_host: str, default_port: str, default_path: str = "") -> str:
    explicit = os.getenv(f"{prefix}_URL")
    if explicit:
        return explicit
    host = os.getenv(f"{prefix}_HOST", default_host)
    port = os.getenv(f"{prefix}_PORT", default_port)
    path = os.getenv(f"{prefix}_PATH", default_path)
    return f"http://{host}:{port}{path}"


class Config:
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    OPENROUTER_API_KEY = _openrouter_api_key()
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "gpt-4-turbo-preview")
    BUDGET_API_BASE_URL = _service_url("BUDGET_API", "localhost", "8000")
    # Streamable-HTTP endpoint of the Budget Planner MCP server
    MCP_SERVER_URL = _service_url("MCP_SERVER", "localhost", "8001", "/mcp")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @staticmethod
    def validate():
        placeholder_values = {
            "your_bot_token_here",
            "your_telegram_bot_token_here",
            "your_api_key_here",
            "your_openrouter_api_key_here",
        }
        if not Config.TELEGRAM_BOT_TOKEN or Config.TELEGRAM_BOT_TOKEN in placeholder_values:
            raise ValueError("TELEGRAM_BOT_TOKEN is not set")
        if not Config.OPENROUTER_API_KEY or Config.OPENROUTER_API_KEY in placeholder_values:
            raise ValueError("OPENROUTER_API_KEY is not set")
