from fastapi import APIRouter, Depends
from app.core.deps import get_current_active_user
from app.models.user import User
import hashlib, hmac, base64, httpx
from urllib.parse import urlencode
from collections import OrderedDict

router = APIRouter(prefix="/zadarma", tags=["zadarma"])

ZADARMA_KEY = "2e4fdd0e35870bbf4621"
ZADARMA_SECRET = "e058b4bbe3d240c1abd4"
ZADARMA_SIP = "280175"


def zadarma_auth(method: str, params: dict = {}) -> str:
    params_string = urlencode(OrderedDict(sorted(params.items()))) if params else ""
    md5_params = hashlib.md5(params_string.encode('utf8')).hexdigest()
    data = method + params_string + md5_params
    hmac_h = hmac.new(ZADARMA_SECRET.encode('utf8'), data.encode('utf8'), hashlib.sha1)
    sign = base64.b64encode(hmac_h.hexdigest().encode('utf8')).decode()
    return f"{ZADARMA_KEY}:{sign}"


async def zadarma_get(method: str, params: dict = {}) -> dict:
    auth = zadarma_auth(method, params)
    params_str = urlencode(OrderedDict(sorted(params.items()))) if params else ""
    url = f"https://api.zadarma.com{method}"
    if params_str:
        url += f"?{params_str}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers={"Authorization": auth})
        return r.json()


@router.get("/webrtc_key")
async def get_webrtc_key(
    current_user: User = Depends(get_current_active_user),
):
    """Получить ключ для WebRTC виджета."""
    try:
        data = await zadarma_get("/v1/webrtc/get_key", {"sip": ZADARMA_SIP})
        return {"key": data.get("key", ""), "sip": ZADARMA_SIP}
    except Exception as e:
        return {"key": "", "sip": ZADARMA_SIP, "error": str(e)}
