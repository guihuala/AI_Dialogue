import hmac
import os
import secrets
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException

load_dotenv()


class AdminAuthManager:
    def __init__(self):
        self.password = (os.getenv("ADMIN_PASSWORD") or "").strip()
        self.openclaw_token = (os.getenv("OPENCLAW_BOT_TOKEN") or "").strip()
        self.ttl_seconds = int(os.getenv("ADMIN_SESSION_TTL_SECONDS", "43200") or "43200")
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _now(self) -> datetime:
        return datetime.now()

    def _purge_expired(self):
        now = self._now()
        expired = []
        for token, session in self._sessions.items():
            expires_at = session.get("expires_at")
            if not isinstance(expires_at, datetime) or expires_at <= now:
                expired.append(token)
        for token in expired:
            self._sessions.pop(token, None)

    def _build_session_payload(self, token: str, session: Dict[str, Any]) -> Dict[str, Any]:
        expires_at = session["expires_at"]
        return {
            "token": token,
            "expires_at": expires_at.isoformat(),
            "ttl_seconds": max(0, int((expires_at - self._now()).total_seconds())),
        }

    def verify_password(self, password: str) -> bool:
        if not self.password:
            return False
        return hmac.compare_digest(password or "", self.password)

    def login(self, password: str) -> Dict[str, Any]:
        if not self.password:
            raise HTTPException(status_code=503, detail="管理员口令未配置，请设置 ADMIN_PASSWORD")
        if not self.verify_password(password):
            raise HTTPException(status_code=401, detail="口令不正确")

        token = secrets.token_urlsafe(32)
        expires_at = self._now() + timedelta(seconds=self.ttl_seconds)
        session = {"expires_at": expires_at}
        with self._lock:
            self._purge_expired()
            self._sessions[token] = session
        return self._build_session_payload(token, session)

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        with self._lock:
            self._purge_expired()
            session = self._sessions.get(token)
            if not session:
                return None
            return self._build_session_payload(token, session)

    def revoke(self, token: str):
        if not token:
            return
        with self._lock:
            self._sessions.pop(token, None)

    def require_admin(self, x_admin_token: Optional[str] = Header(None)) -> Dict[str, Any]:
        session = self.get_session(x_admin_token or "")
        if not session:
            raise HTTPException(status_code=401, detail="管理员登录已失效，请重新验证")
        return {**session, "role": "admin", "actor_type": "admin"}

    def require_openclaw_bot(self, x_openclaw_token: Optional[str] = Header(None)) -> Dict[str, Any]:
        if not self.openclaw_token:
            raise HTTPException(status_code=503, detail="OPENCLAW_BOT_TOKEN 未配置")
        token = (x_openclaw_token or "").strip()
        if not token or not hmac.compare_digest(token, self.openclaw_token):
            raise HTTPException(status_code=401, detail="OpenClaw token 无效")
        return {
            "role": "openclaw_bot",
            "actor_type": "bot",
            "bot_id": "openclaw_bot",
            "expires_at": "",
            "ttl_seconds": 0,
        }
