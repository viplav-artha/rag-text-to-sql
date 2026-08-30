import os

from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse


load_dotenv()


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name, default)
    if value is None:
        return None
    return value.strip()


def _env_float(name: str, default: float) -> float:
    value = _env(name)
    if value in (None, ""):
        return default
    return float(value)


def get_llm():
    model_id = _env("BEDROCK_CHAT_MODEL_ID", "us.amazon.nova-pro-v1:0")
    region = _env("BEDROCK_REGION") or _env("AWS_REGION", "us-east-1")
    profile = _env("AWS_PROFILE", "Artha-stg-dev")

    if not model_id:
        raise ValueError("BEDROCK_CHAT_MODEL_ID not configured")
    if not region:
        raise ValueError("BEDROCK_REGION or AWS_REGION not configured")

    # Pass credentials_profile_name so Bedrock uses your active AWS SSO profile
    kwargs = {
        "model": model_id,
        "region_name": region,
        "temperature": _env_float("LLM_TEMPERATURE", 0),
    }

    if profile:
        kwargs["credentials_profile_name"] = profile

    return ChatBedrockConverse(**kwargs)
