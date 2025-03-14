from typing import Dict, Optional
import orjson

from hibiscus.settings import HibiscusSettings


def save_auth_token(auth_token: str):
    _data = {"token": auth_token}
    orjson.dumps(_data)


def read_auth_token() -> Optional[str]:
    _data: Dict = orjson.loads(HibiscusSettings.credentials_path)  # type: ignore

    try:
        return _data.get("token")
    except Exception:
        pass
    return None