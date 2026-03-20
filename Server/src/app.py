from fastapi import FastAPI, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import os
import sys
import concurrent.futures
from fastapi.middleware.cors import CORSMiddleware

# Avoid noisy HuggingFace tokenizers fork-parallelism warning in multi-worker/background contexts.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# 把当前文件的上一级目录加入系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.game_engine import GameEngine
from src.core.config import (
    PROMPTS_DIR, SAVES_DIR, EVENTS_DIR,
    DEFAULT_PROMPTS_DIR, DEFAULT_EVENTS_DIR,
    get_user_saves_dir, get_user_data_root,
    get_user_prompts_dir, get_user_events_dir, get_user_library_dir
)
from src.core.mod_manifest import build_manifest, validate_manifest
from src.core.snapshot_manager import create_snapshot, list_snapshots, load_snapshot, trim_snapshots
from src.routers.admin_router import build_admin_router
from src.routers.system_router import build_system_router
from src.routers.debug_router import build_debug_router
from src.routers.content_router import build_content_router
from src.routers.intervention_router import build_intervention_router
from src.routers.game_router import build_game_router
from src.services.roster_service import get_current_roster, normalize_roster_single_player
from src.services.admin_auth_service import AdminAuthManager
from src.services.state_service import (
    MAX_LIBRARY_ITEMS,
    MAX_LIBRARY_TOTAL_BYTES,
    MAX_SNAPSHOTS_KEEP,
    append_audit_log,
    cleanup_user_storage,
    get_storage_quota_data,
    read_user_state,
    with_user_write_lock,
    write_user_state,
)
from src.services.mod_service import (
    apply_mod_content_atomic,
    build_validation_report,
    package_mod,
    validate_mod_content,
)

TEMP_MIN = 0.2
TEMP_MAX = 1.2
TOKENS_MIN = 300
TOKENS_MAX = 2000

def _clamp(value, vmin, vmax):
    return max(vmin, min(vmax, value))

try:
    from src.core.data_loader import load_all_events
    import src.core.event_script as es
    EVENT_DATABASE = getattr(es, 'EVENT_DATABASE', {})
    EVENT_DATABASE.update(load_all_events(EVENTS_DIR))
except Exception as e:
    print(f"Warning: Failed to load events data: {e}")
    EVENT_DATABASE = {}

# SAVE_DIR is now SAVES_DIR from config.py
SAVE_DIR = SAVES_DIR

# Global shared pool for background tasks (Prefetching, Reflection)
PREFETCH_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=10)

app = FastAPI(title="Roommate Survival Game API")
admin_auth = AdminAuthManager()

@app.on_event("shutdown")
def _shutdown_background_pool():
    try:
        PREFETCH_POOL.shutdown(wait=False, cancel_futures=True)
    except Exception:
        pass

# --- Multi-user Engine Manager ---
engines: Dict[str, GameEngine] = {}

def get_user_id(x_visitor_id: Optional[str] = Header(None)):
    """Extract visitor ID from header, fallback to 'default'"""
    return x_visitor_id or "default"

def get_engine(user_id: str) -> GameEngine:
    """Get or create a GameEngine for a specific user"""
    if user_id not in engines:
        engines[user_id] = GameEngine(user_id)
    return engines[user_id]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any origin for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ==========================================
# 个人模组库 Library 接口
# ==========================================

WORKSHOP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "workshop")
if not os.path.exists(WORKSHOP_DIR):
    os.makedirs(WORKSHOP_DIR)

# ==========================================
# 模块化路由注册
# ==========================================
app.include_router(
    build_system_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
        clamp=_clamp,
        temp_min=TEMP_MIN,
        temp_max=TEMP_MAX,
        tokens_min=TOKENS_MIN,
        tokens_max=TOKENS_MAX,
        prompts_dir=PROMPTS_DIR,
        get_user_prompts_dir=get_user_prompts_dir,
    )
)

app.include_router(
    build_game_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
        get_current_roster=get_current_roster,
        get_user_saves_dir=get_user_saves_dir,
        get_user_library_dir=get_user_library_dir,
        with_user_write_lock=with_user_write_lock,
        append_audit_log=append_audit_log,
        apply_mod_content_atomic=lambda user_id, content: apply_mod_content_atomic(
            user_id, content, normalize_roster_single_player, validate_manifest
        ),
        validate_mod_content=lambda content, manifest=None: validate_mod_content(
            content, normalize_roster_single_player, validate_manifest, manifest
        ),
        package_mod=package_mod,
        read_user_state=read_user_state,
        write_user_state=write_user_state,
        create_snapshot=create_snapshot,
        trim_snapshots=trim_snapshots,
        max_snapshots_keep=MAX_SNAPSHOTS_KEEP,
        clamp=_clamp,
        temp_min=TEMP_MIN,
        temp_max=TEMP_MAX,
        tokens_min=TOKENS_MIN,
        tokens_max=TOKENS_MAX,
        prompts_dir=PROMPTS_DIR,
        default_prompts_dir=DEFAULT_PROMPTS_DIR,
        default_events_dir=DEFAULT_EVENTS_DIR,
        prefetch_pool=PREFETCH_POOL,
    )
)

app.include_router(
    build_admin_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
        get_user_prompts_dir=get_user_prompts_dir,
        get_user_events_dir=get_user_events_dir,
        get_user_library_dir=get_user_library_dir,
        default_prompts_dir=DEFAULT_PROMPTS_DIR,
        default_events_dir=DEFAULT_EVENTS_DIR,
        with_user_write_lock=with_user_write_lock,
        append_audit_log=append_audit_log,
        normalize_roster_single_player=normalize_roster_single_player,
        read_user_state=read_user_state,
        write_user_state=write_user_state,
        build_manifest=build_manifest,
        workshop_dir=WORKSHOP_DIR,
        admin_auth=admin_auth,
        require_admin=Depends(admin_auth.require_admin),
    )
)

app.include_router(
    build_content_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
        get_user_library_dir=get_user_library_dir,
        get_user_data_root=get_user_data_root,
        with_user_write_lock=with_user_write_lock,
        append_audit_log=append_audit_log,
        package_mod=package_mod,
        build_validation_report=lambda content, manifest=None: build_validation_report(
            content, normalize_roster_single_player, validate_manifest, manifest
        ),
        validate_mod_content=lambda content, manifest=None: validate_mod_content(
            content, normalize_roster_single_player, validate_manifest, manifest
        ),
        apply_mod_content_atomic=lambda user_id, content: apply_mod_content_atomic(
            user_id, content, normalize_roster_single_player, validate_manifest
        ),
        read_user_state=read_user_state,
        write_user_state=write_user_state,
        get_storage_quota_data=get_storage_quota_data,
        cleanup_user_storage=cleanup_user_storage,
        list_snapshots=list_snapshots,
        load_snapshot=load_snapshot,
        create_snapshot=create_snapshot,
        trim_snapshots=trim_snapshots,
        build_manifest=build_manifest,
        max_library_items=MAX_LIBRARY_ITEMS,
        max_library_total_bytes=MAX_LIBRARY_TOTAL_BYTES,
        max_snapshots_keep=MAX_SNAPSHOTS_KEEP,
        workshop_dir=WORKSHOP_DIR,
        require_admin=Depends(admin_auth.require_admin),
    )
)

app.include_router(
    build_intervention_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
    )
)

app.include_router(
    build_debug_router(
        get_user_id=Depends(get_user_id),
        get_engine=get_engine,
    )
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
