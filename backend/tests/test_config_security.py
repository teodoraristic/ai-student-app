"""Settings validation for production safety."""

import pytest
from pydantic import ValidationError

from backend.config import Settings


class TestProductionJwtSecret:
    def test_production_rejects_default_secret(self) -> None:
        with pytest.raises(ValidationError, match="JWT secret"):
            Settings(app_env="production", jwt_secret="change-me")

    def test_production_rejects_short_secret(self) -> None:
        with pytest.raises(ValidationError, match="JWT secret"):
            Settings(app_env="production", jwt_secret="x" * 31)

    def test_production_accepts_strong_secret(self) -> None:
        s = Settings(app_env="production", jwt_secret="x" * 32)
        assert len(s.jwt_secret) == 32

    def test_development_allows_default_secret(self) -> None:
        s = Settings(app_env="development", jwt_secret="change-me")
        assert s.jwt_secret == "change-me"

    def test_production_env_case_insensitive(self) -> None:
        with pytest.raises(ValidationError):
            Settings(app_env="PRODUCTION", jwt_secret="change-me")
