from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel


class AccountRegisterReq(BaseModel):
    username: str
    password: str
    bind_current_visitor: bool = True


class AccountLoginReq(BaseModel):
    username: str
    password: str


class AccountPasswordChangeReq(BaseModel):
    current_password: str
    new_password: str


class AccountBindVisitorReq(BaseModel):
    conflict_strategy: str = "keep_account"


def build_account_router(*, account_auth, get_identity, require_account, append_audit_log):
    router = APIRouter()

    def _build_capabilities(identity: Dict[str, Any]) -> Dict[str, Any]:
        is_account = identity.get("auth_mode") == "account" and bool(identity.get("account"))
        return {
            "can_play_as_visitor": True,
            "can_edit_local_content": True,
            "can_save_local_mods": True,
            "can_download_workshop_mods": True,
            "can_publish_workshop_mods": is_account,
            "can_manage_account_security": is_account,
            "can_manage_sessions": is_account,
        }

    @router.post("/api/account/register")
    def register_account(
        req: AccountRegisterReq,
        identity: Dict[str, Any] = get_identity,
    ):
        visitor_id = str(identity.get("visitor_id", "") or "")
        bind_visitor_id = visitor_id if req.bind_current_visitor else ""
        account = account_auth.register(req.username, req.password, bind_visitor_id=bind_visitor_id)
        append_audit_log(
            account["account_id"],
            "account_register",
            "ok",
            req.username,
            {"bound_visitor_id": bind_visitor_id},
        )
        return {
            "status": "success",
            "data": {
                "account": account,
                "bound_visitor_id": bind_visitor_id,
            },
        }

    @router.post("/api/account/login")
    def login_account(req: AccountLoginReq):
        session = account_auth.login(req.username, req.password)
        account = session.get("account", {}) if isinstance(session, dict) else {}
        append_audit_log(
            str(account.get("account_id", "") or "default"),
            "account_login",
            "ok",
            req.username,
            {},
        )
        return {"status": "success", "data": session}

    @router.get("/api/account/me")
    def account_me(identity: Dict[str, Any] = get_identity):
        if identity.get("auth_mode") == "account" and identity.get("account"):
            return {
                "status": "success",
                "data": {
                    "auth_mode": "account",
                    "user_id": identity.get("user_id"),
                    "visitor_id": identity.get("visitor_id"),
                    "token": identity.get("token"),
                    "account": identity.get("account"),
                    "capabilities": _build_capabilities(identity),
                },
            }
        return {
            "status": "success",
            "data": {
                "auth_mode": "visitor",
                "user_id": identity.get("user_id"),
                "visitor_id": identity.get("visitor_id"),
                "account": None,
                "capabilities": _build_capabilities(identity),
            },
        }

    @router.post("/api/account/change_password")
    def change_password(
        req: AccountPasswordChangeReq,
        account_session: Dict[str, Any] = require_account,
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        updated_account = account_auth.change_password(account_id, req.current_password, req.new_password)
        append_audit_log(account_id, "account_change_password", "ok", str(account.get("username", "") or ""), {})
        return {"status": "success", "data": {"account": updated_account}}

    @router.post("/api/account/bind_current_visitor")
    def bind_current_visitor(
        req: Optional[AccountBindVisitorReq] = None,
        identity: Dict[str, Any] = get_identity,
        account_session: Dict[str, Any] = require_account,
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        visitor_id = str(identity.get("visitor_id", "") or "")
        conflict_strategy = str((req.dict() if req else {}).get("conflict_strategy", "keep_account") or "keep_account")
        result = account_auth.bind_visitor(account_id, visitor_id, conflict_strategy=conflict_strategy)
        append_audit_log(
            account_id,
            "account_bind_visitor",
            "ok",
            str(account.get("username", "") or ""),
            {
                "visitor_id": visitor_id,
                "migrated": result.get("migrated", False),
                "strategy": conflict_strategy,
            },
        )
        return {"status": "success", "data": result}

    @router.get("/api/account/visitor_binding_preview")
    def preview_bind_current_visitor(
        identity: Dict[str, Any] = get_identity,
        account_session: Dict[str, Any] = require_account,
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        visitor_id = str(identity.get("visitor_id", "") or "")
        result = account_auth.preview_bind_visitor(account_id, visitor_id)
        return {"status": "success", "data": result}

    @router.get("/api/account/sessions")
    def list_account_sessions(
        account_session: Dict[str, Any] = require_account,
        x_account_token: Optional[str] = Header(None),
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        data = account_auth.list_sessions(account_id, current_token=str(x_account_token or ""))
        return {"status": "success", "data": data}

    @router.post("/api/account/logout_others")
    def logout_other_sessions(
        account_session: Dict[str, Any] = require_account,
        x_account_token: Optional[str] = Header(None),
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        result = account_auth.revoke_other_sessions(account_id, current_token=str(x_account_token or ""))
        append_audit_log(
            account_id,
            "account_logout_others",
            "ok",
            str(account.get("username", "") or ""),
            {"count": result.get("count", 0)},
        )
        return {"status": "success", "data": result}

    @router.post("/api/account/revoke_session/{session_id}")
    def revoke_account_session(
        session_id: str,
        account_session: Dict[str, Any] = require_account,
        x_account_token: Optional[str] = Header(None),
    ):
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_id = str(account.get("account_id", "") or "")
        result = account_auth.revoke_session(account_id, session_id, current_token=str(x_account_token or ""))
        append_audit_log(
            account_id,
            "account_revoke_session",
            "ok",
            str(account.get("username", "") or ""),
            {"session_id": session_id},
        )
        return {"status": "success", "data": result}

    @router.post("/api/account/logout")
    def logout_account(
        account_session: Dict[str, Any] = require_account,
        x_account_token: Optional[str] = Header(None),
    ):
        token = str(x_account_token or account_session.get("token", "") or "").strip()
        account = account_session.get("account", {}) if isinstance(account_session, dict) else {}
        account_auth.revoke(token)
        append_audit_log(
            str(account.get("account_id", "") or "default"),
            "account_logout",
            "ok",
            str(account.get("username", "") or ""),
            {},
        )
        return {"status": "success"}

    return router
