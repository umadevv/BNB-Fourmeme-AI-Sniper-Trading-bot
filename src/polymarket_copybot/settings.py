from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mode: str = Field(default="paper", alias="COPYBOT_MODE")
    log_level: str = Field(default="INFO", alias="COPYBOT_LOG_LEVEL")

    leader_wallet: str | None = Field(default=None, alias="LEADER_WALLET")
    poll_interval_seconds: int = Field(default=5, alias="POLL_INTERVAL_SECONDS")
    data_api_base: str = Field(default="https://data-api.polymarket.com", alias="DATA_API_BASE")
    leader_state_path: str = Field(default=".copybot_state.json", alias="LEADER_STATE_PATH")
    # If no state exists yet, start at "now" (do not replay history).
    leader_start_from_now: bool = Field(default=True, alias="LEADER_START_FROM_NOW")

    min_usd_per_trade: float = Field(default=0.0, alias="MIN_USD_PER_TRADE")
    max_usd_per_trade: float = Field(default=25.0, alias="MAX_USD_PER_TRADE")
    max_total_usd_exposure: float = Field(default=200.0, alias="MAX_TOTAL_USD_EXPOSURE")
    copy_ratio: float = Field(default=1.0, alias="COPY_RATIO")

    polygon_key: str | None = Field(default=None, alias="POLYGON_KEY")
    sig_type: int = Field(default=0, alias="SIG_TYPE")
    proxy_address: str | None = Field(default=None, alias="PROXY_ADDRESS")

    fok_max_retries: int = Field(default=5, alias="FOK_MAX_RETRIES")
    fok_retry_delay_s: float = Field(default=0.5, alias="FOK_RETRY_DELAY_S")

    polymarket_api_base: str = Field(default="https://clob.polymarket.com", alias="POLYMARKET_API_BASE")
    polymarket_api_key: str | None = Field(default=None, alias="POLYMARKET_API_KEY")
    polymarket_api_secret: str | None = Field(default=None, alias="POLYMARKET_API_SECRET")


def load_settings() -> Settings:
    return Settings()

