from typing import Any, Callable


def register_debug_routes(
    app,
    *,
    get_user_id,
    get_engine: Callable[[str], Any],
):
    @app.get("/api/debug/chat_history")
    def get_chat_history(user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine or not hasattr(engine, "mm"):
            return {"status": "error", "message": "Memory module not ready"}
        return {"status": "success", "history": engine.mm.game_history}

    @app.get("/api/debug/state")
    def get_debug_state(user_id: str = get_user_id):
        engine = get_engine(user_id)
        if not engine:
            return {"status": "error", "message": "Engine not ready"}

        recent_events = list(engine.recent_event_ids) if hasattr(engine, "recent_event_ids") else []

        return {
            "status": "success",
            "data": {
                "current_chapter": engine.director.current_chapter if hasattr(engine, "director") else 1,
                "current_turn": engine.director.current_turn if hasattr(engine, "director") else 1,
                "event_count": engine.event_completion_count if hasattr(engine, "event_completion_count") else 0,
                "recent_event_ids": recent_events,
                "roommates": engine.director.active_roommates if hasattr(engine, "director") else [],
            },
        }

    @app.post("/api/debug/clear_cache")
    def clear_engine_cache(user_id: str = get_user_id):
        engine = get_engine(user_id)
        if engine:
            engine.prefetch_futures.clear()
            engine.latest_game_state_cache = None
            return {"status": "success", "message": "Cache cleared for this user"}
        return {"status": "error", "message": "Engine not found"}

