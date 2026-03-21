import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException

from src.core.config import DATA_ROOT

load_dotenv()


class AccountAuthManager:
    USERNAME_RE = re.compile(r"^[A-Za-z0-9_\-]{3,32}$")

    def __init__(self):
        self.ttl_seconds = int(os.getenv("ACCOUNT_SESSION_TTL_SECONDS", "2592000") or "2592000")
        self.accounts_root = os.path.join(DATA_ROOT, "accounts")
        self.accounts_by_id_dir = os.path.join(self.accounts_root, "by_id")
        self.sessions_dir = os.path.join(self.accounts_root, "sessions")
        self.index_path = os.path.join(self.accounts_root, "index.json")
        self._lock = threading.Lock()
        os.makedirs(self.accounts_by_id_dir, exist_ok=True)
        os.makedirs(self.sessions_dir, exist_ok=True)

    def _now(self) -> datetime:
        return datetime.now()

    def _now_str(self) -> str:
        return self._now().strftime("%Y-%m-%d %H:%M:%S")

    def _read_json(self, path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data
        except Exception:
            return default

    def _write_json(self, path: str, data: Any) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_index(self) -> Dict[str, str]:
        data = self._read_json(self.index_path, {})
        return data if isinstance(data, dict) else {}

    def _save_index(self, data: Dict[str, str]) -> None:
        self._write_json(self.index_path, data)

    def _account_path(self, account_id: str) -> str:
        return os.path.join(self.accounts_by_id_dir, f"{account_id}.json")

    def _session_path(self, token: str) -> str:
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        return os.path.join(self.sessions_dir, f"{digest}.json")

    def _session_id_from_token(self, token: str) -> str:
        return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()[:16]

    def _user_root(self, user_id: str) -> str:
        return os.path.join(DATA_ROOT, "users", user_id)

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        iterations = 200000
        derived = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, iterations)
        return "pbkdf2_sha256${}${}${}".format(
            iterations,
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(derived).decode("utf-8"),
        )

    def _verify_password(self, password: str, stored: str) -> bool:
        try:
            algorithm, iteration_text, salt_text, hash_text = str(stored or "").split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iteration_text)
            salt = base64.b64decode(salt_text.encode("utf-8"))
            expected = base64.b64decode(hash_text.encode("utf-8"))
            actual = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, iterations)
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False

    def _merge_dirs_with_report(
        self,
        source_dir: str,
        target_dir: str,
        *,
        conflict_strategy: str,
        report: Dict[str, Any],
        rel_prefix: str = "",
    ) -> None:
        if not os.path.exists(source_dir):
            return
        os.makedirs(target_dir, exist_ok=True)
        for name in os.listdir(source_dir):
            source_path = os.path.join(source_dir, name)
            target_path = os.path.join(target_dir, name)
            rel_path = os.path.join(rel_prefix, name).replace("\\", "/").strip("/")
            if os.path.isdir(source_path):
                self._merge_dirs_with_report(
                    source_path,
                    target_path,
                    conflict_strategy=conflict_strategy,
                    report=report,
                    rel_prefix=rel_path,
                )
                try:
                    os.rmdir(source_path)
                except OSError:
                    pass
                continue

            if not os.path.exists(target_path):
                shutil.move(source_path, target_path)
                report["moved_files"] = int(report.get("moved_files", 0)) + 1
                if len(report.get("moved_examples", [])) < 8:
                    report.setdefault("moved_examples", []).append(rel_path)
                continue

            if conflict_strategy == "overwrite_with_visitor":
                try:
                    os.remove(target_path)
                except FileNotFoundError:
                    pass
                shutil.move(source_path, target_path)
                report["overwritten_files"] = int(report.get("overwritten_files", 0)) + 1
                if len(report.get("overwritten_examples", [])) < 8:
                    report.setdefault("overwritten_examples", []).append(rel_path)
                continue

            report["skipped_conflicts"] = int(report.get("skipped_conflicts", 0)) + 1
            if len(report.get("conflict_examples", [])) < 8:
                report.setdefault("conflict_examples", []).append(rel_path)

        try:
            os.rmdir(source_dir)
        except OSError:
            pass

    def _migrate_visitor_data_with_report(
        self, visitor_id: str, account_id: str, *, conflict_strategy: str = "keep_account"
    ) -> Dict[str, Any]:
        report = {
            "visitor_id": str(visitor_id or "").strip(),
            "account_id": str(account_id or "").strip(),
            "conflict_strategy": conflict_strategy,
            "moved_files": 0,
            "overwritten_files": 0,
            "skipped_conflicts": 0,
            "moved_examples": [],
            "overwritten_examples": [],
            "conflict_examples": [],
        }
        normalized_visitor = str(visitor_id or "").strip()
        if not normalized_visitor or normalized_visitor in {"default", account_id}:
            report["migrated"] = False
            return report
        source_root = self._user_root(normalized_visitor)
        if not os.path.exists(source_root):
            report["migrated"] = False
            return report
        target_root = self._user_root(account_id)
        self._merge_dirs_with_report(
            source_root,
            target_root,
            conflict_strategy=conflict_strategy,
            report=report,
        )
        report["migrated"] = bool(
            int(report.get("moved_files", 0)) > 0 or int(report.get("overwritten_files", 0)) > 0
        )
        return report

    def _migrate_visitor_data(self, visitor_id: str, account_id: str) -> bool:
        report = self._migrate_visitor_data_with_report(visitor_id, account_id, conflict_strategy="keep_account")
        return bool(report.get("migrated"))

    def _summarize_user_root(self, user_id: str) -> Dict[str, Any]:
        root = self._user_root(user_id)
        summary = {
            "exists": os.path.exists(root),
            "library_items": 0,
            "save_files": 0,
            "snapshot_files": 0,
            "prompt_files": 0,
            "event_files": 0,
            "total_files": 0,
        }
        if not os.path.exists(root):
            return summary

        targets = {
            "library_items": os.path.join(root, "library"),
            "save_files": os.path.join(root, "saves"),
            "snapshot_files": os.path.join(root, "snapshots"),
            "prompt_files": os.path.join(root, "prompts"),
            "event_files": os.path.join(root, "events"),
        }
        for key, path in targets.items():
            if not os.path.exists(path):
                continue
            count = 0
            for _, _, files in os.walk(path):
                count += len(files)
            summary[key] = count
            summary["total_files"] += count
        return summary

    def _collect_conflicts(self, visitor_id: str, account_id: str) -> Dict[str, Any]:
        visitor_root = self._user_root(visitor_id)
        account_root = self._user_root(account_id)
        collisions = []
        collisions_count = 0
        if not os.path.exists(visitor_root) or not os.path.exists(account_root):
            return {"count": 0, "examples": []}

        for root, _, files in os.walk(visitor_root):
            for file_name in files:
                source_path = os.path.join(root, file_name)
                relative_path = os.path.relpath(source_path, visitor_root)
                target_path = os.path.join(account_root, relative_path)
                if os.path.exists(target_path):
                    collisions_count += 1
                    if len(collisions) < 8:
                        collisions.append(relative_path.replace("\\", "/"))
        return {"count": collisions_count, "examples": collisions}

    def _build_account_payload(self, account: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "account_id": str(account.get("account_id", "") or ""),
            "username": str(account.get("username", "") or ""),
            "created_at": str(account.get("created_at", "") or ""),
            "updated_at": str(account.get("updated_at", "") or ""),
            "linked_visitor_ids": list(account.get("linked_visitor_ids", []) or []),
        }

    def _save_account(self, account: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(account or {})
        normalized["updated_at"] = self._now_str()
        self._write_json(self._account_path(str(normalized.get("account_id", "") or "")), normalized)
        return normalized

    def _build_session_payload(self, token: str, account: Dict[str, Any], expires_at: datetime) -> Dict[str, Any]:
        return {
            "session_id": self._session_id_from_token(token),
            "token": token,
            "expires_at": expires_at.isoformat(),
            "ttl_seconds": max(0, int((expires_at - self._now()).total_seconds())),
            "account": self._build_account_payload(account),
        }

    def _get_account_by_id(self, account_id: str) -> Optional[Dict[str, Any]]:
        if not account_id:
            return None
        data = self._read_json(self._account_path(account_id), {})
        return data if isinstance(data, dict) and data.get("account_id") else None

    def get_account_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        normalized = str(username or "").strip().lower()
        if not normalized:
            return None
        index = self._load_index()
        account_id = str(index.get(normalized, "") or "")
        return self._get_account_by_id(account_id)

    def register(self, username: str, password: str, bind_visitor_id: str = "") -> Dict[str, Any]:
        normalized_username = str(username or "").strip()
        if not self.USERNAME_RE.match(normalized_username):
            raise HTTPException(status_code=400, detail="用户名需为 3-32 位字母、数字、下划线或中横线")
        if len(str(password or "")) < 6:
            raise HTTPException(status_code=400, detail="密码至少需要 6 位")

        normalized_key = normalized_username.lower()
        with self._lock:
            index = self._load_index()
            if normalized_key in index:
                raise HTTPException(status_code=409, detail="用户名已存在")

            account_id = f"acc_{uuid.uuid4().hex[:8]}"
            linked_visitor_ids = []
            normalized_visitor = str(bind_visitor_id or "").strip()
            if normalized_visitor and normalized_visitor != "default":
                linked_visitor_ids.append(normalized_visitor)

            now = self._now_str()
            account = {
                "account_id": account_id,
                "username": normalized_username,
                "password_hash": self._hash_password(password),
                "created_at": now,
                "updated_at": now,
                "linked_visitor_ids": linked_visitor_ids,
                "active_user_id": account_id,
            }
            self._save_account(account)
            index[normalized_key] = account_id
            self._save_index(index)
            if normalized_visitor and normalized_visitor != "default":
                self._migrate_visitor_data(normalized_visitor, account_id)
        return self._build_account_payload(account)

    def login(self, username: str, password: str) -> Dict[str, Any]:
        account = self.get_account_by_username(username)
        if not account or not self._verify_password(password, str(account.get("password_hash", "") or "")):
            raise HTTPException(status_code=401, detail="用户名或密码不正确")
        token = secrets.token_urlsafe(32)
        expires_at = self._now() + timedelta(seconds=self.ttl_seconds)
        session = {
            "token": token,
            "account_id": str(account.get("account_id", "") or ""),
            "created_at": self._now_str(),
            "expires_at": expires_at.isoformat(),
        }
        with self._lock:
            self._write_json(self._session_path(token), session)
        return self._build_session_payload(token, account, expires_at)

    def get_session(self, token: str) -> Optional[Dict[str, Any]]:
        normalized_token = str(token or "").strip()
        if not normalized_token:
            return None
        path = self._session_path(normalized_token)
        session = self._read_json(path, {})
        if not isinstance(session, dict) or not session.get("account_id"):
            return None
        try:
            expires_at = datetime.fromisoformat(str(session.get("expires_at", "") or ""))
        except Exception:
            expires_at = None
        if not isinstance(expires_at, datetime) or expires_at <= self._now():
            try:
                os.remove(path)
            except Exception:
                pass
            return None
        account = self._get_account_by_id(str(session.get("account_id", "") or ""))
        if not account:
            return None
        return self._build_session_payload(normalized_token, account, expires_at)

    def revoke(self, token: str) -> None:
        normalized_token = str(token or "").strip()
        if not normalized_token:
            return
        try:
            os.remove(self._session_path(normalized_token))
        except FileNotFoundError:
            pass

    def list_sessions(self, account_id: str, current_token: str = "") -> Dict[str, Any]:
        normalized_account_id = str(account_id or "").strip()
        current_session_id = self._session_id_from_token(current_token) if current_token else ""
        rows = []
        now = self._now()
        try:
            file_names = os.listdir(self.sessions_dir)
        except Exception:
            file_names = []

        for file_name in file_names:
            if not file_name.endswith(".json"):
                continue
            session_path = os.path.join(self.sessions_dir, file_name)
            session = self._read_json(session_path, {})
            if not isinstance(session, dict):
                continue
            if str(session.get("account_id", "") or "") != normalized_account_id:
                continue
            token = str(session.get("token", "") or "")
            if not token:
                continue
            try:
                expires_at = datetime.fromisoformat(str(session.get("expires_at", "") or ""))
            except Exception:
                expires_at = None
            if not isinstance(expires_at, datetime) or expires_at <= now:
                try:
                    os.remove(session_path)
                except Exception:
                    pass
                continue
            rows.append(
                {
                    "session_id": self._session_id_from_token(token),
                    "created_at": str(session.get("created_at", "") or ""),
                    "expires_at": expires_at.isoformat(),
                    "ttl_seconds": max(0, int((expires_at - now).total_seconds())),
                    "is_current": self._session_id_from_token(token) == current_session_id,
                }
            )
        rows.sort(key=lambda item: (not bool(item.get("is_current")), str(item.get("created_at", ""))), reverse=False)
        return {"sessions": rows, "current_session_id": current_session_id}

    def revoke_session(self, account_id: str, session_id: str, current_token: str = "") -> Dict[str, Any]:
        normalized_account_id = str(account_id or "").strip()
        normalized_session_id = str(session_id or "").strip()
        if not normalized_session_id:
            raise HTTPException(status_code=400, detail="缺少会话标识")
        if normalized_session_id == self._session_id_from_token(current_token):
            raise HTTPException(status_code=400, detail="当前登录会话请直接使用退出登录")
        try:
            file_names = os.listdir(self.sessions_dir)
        except Exception:
            file_names = []
        for file_name in file_names:
            if not file_name.endswith(".json"):
                continue
            session_path = os.path.join(self.sessions_dir, file_name)
            session = self._read_json(session_path, {})
            if not isinstance(session, dict):
                continue
            if str(session.get("account_id", "") or "") != normalized_account_id:
                continue
            token = str(session.get("token", "") or "")
            if self._session_id_from_token(token) != normalized_session_id:
                continue
            try:
                os.remove(session_path)
            except FileNotFoundError:
                pass
            return {"revoked_session_id": normalized_session_id}
        raise HTTPException(status_code=404, detail="指定会话不存在")

    def revoke_other_sessions(self, account_id: str, current_token: str = "") -> Dict[str, Any]:
        normalized_account_id = str(account_id or "").strip()
        current_session_id = self._session_id_from_token(current_token) if current_token else ""
        revoked = []
        try:
            file_names = os.listdir(self.sessions_dir)
        except Exception:
            file_names = []
        for file_name in file_names:
            if not file_name.endswith(".json"):
                continue
            session_path = os.path.join(self.sessions_dir, file_name)
            session = self._read_json(session_path, {})
            if not isinstance(session, dict):
                continue
            if str(session.get("account_id", "") or "") != normalized_account_id:
                continue
            token = str(session.get("token", "") or "")
            session_id = self._session_id_from_token(token)
            if session_id == current_session_id:
                continue
            try:
                os.remove(session_path)
                revoked.append(session_id)
            except FileNotFoundError:
                continue
        return {"revoked_session_ids": revoked, "count": len(revoked)}

    def change_password(self, account_id: str, current_password: str, new_password: str) -> Dict[str, Any]:
        if len(str(new_password or "")) < 6:
            raise HTTPException(status_code=400, detail="新密码至少需要 6 位")
        with self._lock:
            account = self._get_account_by_id(account_id)
            if not account:
                raise HTTPException(status_code=404, detail="账户不存在")
            if not self._verify_password(current_password, str(account.get("password_hash", "") or "")):
                raise HTTPException(status_code=401, detail="当前密码不正确")
            account["password_hash"] = self._hash_password(new_password)
            account = self._save_account(account)
        return self._build_account_payload(account)

    def bind_visitor(self, account_id: str, visitor_id: str, conflict_strategy: str = "keep_account") -> Dict[str, Any]:
        normalized_visitor = str(visitor_id or "").strip()
        if not normalized_visitor or normalized_visitor == "default":
            raise HTTPException(status_code=400, detail="当前没有可绑定的访客身份")
        if normalized_visitor == account_id:
            raise HTTPException(status_code=400, detail="当前访客身份已与账户一致")
        strategy = str(conflict_strategy or "keep_account").strip()
        if strategy not in {"keep_account", "overwrite_with_visitor"}:
            raise HTTPException(status_code=400, detail="不支持的冲突处理策略")
        with self._lock:
            account = self._get_account_by_id(account_id)
            if not account:
                raise HTTPException(status_code=404, detail="账户不存在")
            linked_visitors = list(account.get("linked_visitor_ids", []) or [])
            already_linked = normalized_visitor in linked_visitors
            if not already_linked:
                linked_visitors.append(normalized_visitor)
                account["linked_visitor_ids"] = linked_visitors
            migration_report = self._migrate_visitor_data_with_report(
                normalized_visitor,
                account_id,
                conflict_strategy=strategy,
            )
            migrated = bool(migration_report.get("migrated"))
            account = self._save_account(account)
        return {
            "account": self._build_account_payload(account),
            "visitor_id": normalized_visitor,
            "already_linked": already_linked,
            "migrated": migrated,
            "migration_report": migration_report,
        }

    def preview_bind_visitor(self, account_id: str, visitor_id: str) -> Dict[str, Any]:
        normalized_visitor = str(visitor_id or "").strip()
        if not normalized_visitor or normalized_visitor == "default":
            return {
                "visitor_id": "",
                "can_bind": False,
                "reason": "当前没有可绑定的访客身份",
                "visitor_summary": self._summarize_user_root(""),
                "account_summary": self._summarize_user_root(account_id),
                "conflicts": {"count": 0, "examples": []},
                "already_linked": False,
            }
        account = self._get_account_by_id(account_id)
        if not account:
            raise HTTPException(status_code=404, detail="账户不存在")
        linked_visitors = list(account.get("linked_visitor_ids", []) or [])
        return {
            "visitor_id": normalized_visitor,
            "can_bind": normalized_visitor != account_id,
            "reason": "" if normalized_visitor != account_id else "当前访客身份已与账户一致",
            "visitor_summary": self._summarize_user_root(normalized_visitor),
            "account_summary": self._summarize_user_root(account_id),
            "conflicts": self._collect_conflicts(normalized_visitor, account_id),
            "already_linked": normalized_visitor in linked_visitors,
        }

    def resolve_identity(self, x_account_token: Optional[str], x_visitor_id: Optional[str]) -> Dict[str, Any]:
        session = self.get_session(x_account_token or "")
        if session:
            account = session["account"]
            return {
                "auth_mode": "account",
                "user_id": str(account.get("account_id", "") or ""),
                "account": account,
                "visitor_id": str(x_visitor_id or "").strip(),
                "token": str(session.get("token", "") or ""),
            }
        visitor_id = str(x_visitor_id or "").strip() or "default"
        return {
            "auth_mode": "visitor",
            "user_id": visitor_id,
            "account": None,
            "visitor_id": visitor_id,
            "token": "",
        }

    def get_identity(self, x_account_token: Optional[str] = Header(None), x_visitor_id: Optional[str] = Header(None)) -> Dict[str, Any]:
        return self.resolve_identity(x_account_token, x_visitor_id)

    def require_account(self, x_account_token: Optional[str] = Header(None)) -> Dict[str, Any]:
        session = self.get_session(x_account_token or "")
        if not session:
            raise HTTPException(status_code=401, detail="账户登录已失效，请重新登录")
        return session
