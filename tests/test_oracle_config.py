from pathlib import Path

import pytest

from wealthy_api.config import Settings
from wealthy_api.database import get_database_url, get_oracle_connect_args


def test_oracle_connection_uses_wallet_and_tns_alias(tmp_path: Path) -> None:
    (tmp_path / "tnsnames.ora").touch()
    (tmp_path / "ewallet.pem").touch()
    settings = Settings(
        _env_file=None,
        oracle_user="wealthy_app",
        oracle_password="local-test-password",
        oracle_dsn="e7h50o2uobc0nl1q_medium",
        oracle_wallet_location=str(tmp_path),
        oracle_wallet_password="local-wallet-password",
    )

    url = get_database_url()
    connect_args = get_oracle_connect_args(settings)

    assert url.drivername == "oracle+oracledb"
    assert "local-test-password" not in str(url)
    assert connect_args["dsn"] == "e7h50o2uobc0nl1q_medium"
    assert connect_args["config_dir"] == str(tmp_path)
    assert connect_args["wallet_location"] == str(tmp_path)
    assert connect_args["wallet_password"] == "local-wallet-password"


def test_oracle_wallet_password_can_be_omitted(tmp_path: Path) -> None:
    (tmp_path / "tnsnames.ora").touch()
    (tmp_path / "ewallet.pem").touch()
    settings = Settings(
        _env_file=None,
        oracle_user="wealthy_app",
        oracle_password="local-test-password",
        oracle_wallet_location=str(tmp_path),
    )

    connect_args = get_oracle_connect_args(settings)

    assert "wallet_password" not in connect_args


def test_oracle_backend_requires_user_password_and_wallet_path(tmp_path: Path) -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(ValueError, match="WEALTHY_ORACLE_USER"):
        get_oracle_connect_args(settings)


def test_oracle_backend_rejects_missing_wallet_directory() -> None:
    settings = Settings(
        _env_file=None,
        oracle_user="wealthy_app",
        oracle_password="local-test-password",
        oracle_wallet_location="C:/wallet-that-does-not-exist",
    )

    with pytest.raises(ValueError, match="pasta extraída da wallet"):
        get_oracle_connect_args(settings)
