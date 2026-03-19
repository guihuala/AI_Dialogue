import json
import os
import time
import uuid
import argparse
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional

# Avoid noisy HuggingFace tokenizers fork-parallelism warning during benchmark runs.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_PATH = os.path.join(BASE_DIR, "data", "test_report.md")
API_BASE = "http://127.0.0.1:8000"


def _http_json(
    method: str,
    path: str,
    body: Optional[Dict[str, Any]] = None,
    visitor_id: Optional[str] = None,
    timeout: float = 60.0
) -> Dict[str, Any]:
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if visitor_id:
        headers["X-Visitor-Id"] = visitor_id
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url=url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
            if not text.strip():
                return {}
            return json.loads(text)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {raw}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"{method} {path} -> Network error: {e}") from e


def _shorten(text: str, limit: int = 140) -> str:
    if not text:
        return ""
    one_line = " ".join(str(text).split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 1] + "…"


def _set_mode(visitor_id: str, dialogue_mode: str, latency_mode: str = "balanced") -> None:
    _http_json(
        "POST",
        "/api/system/settings",
        {
            "dialogue_mode": dialogue_mode,
            "latency_mode": latency_mode
        },
        visitor_id=visitor_id,
        timeout=30.0
    )


def _run_one_mode(dialogue_mode: str) -> Dict[str, Any]:
    visitor_id = f"bench-{dialogue_mode}-{uuid.uuid4()}"
    _set_mode(visitor_id, dialogue_mode, latency_mode="balanced")

    roommates = ["tang_mengqi", "lin_sa", "li_yinuo"]
    start_body = {
        "roommates": roommates,
        "save_id": "slot_bench"
    }

    t0 = time.perf_counter()
    start_res = _http_json("POST", "/api/game/start", start_body, visitor_id=visitor_id, timeout=120.0)
    start_elapsed = time.perf_counter() - t0

    start_options = start_res.get("next_options") or []
    first_choice = start_options[0] if start_options else "继续剧情..."

    turn_body = {
        "choice": first_choice,
        "active_roommates": start_res.get("active_roommates") or roommates,
        "current_evt_id": start_res.get("current_evt_id", ""),
        "is_transition": (first_choice == "继续剧情..." or bool(start_res.get("is_end"))),
        "chapter": int(start_res.get("chapter", 1)),
        "turn": int(start_res.get("turn", 1)),
        "san": int(start_res.get("san", 100)),
        "money": float(start_res.get("money", 2000)),
        "gpa": float(start_res.get("gpa", 4.0)),
        "hygiene": int(start_res.get("hygiene", 100)),
        "reputation": int(start_res.get("reputation", 100)),
        "arg_count": int(start_res.get("arg_count", 0)),
        "affinity": start_res.get("affinity", {}),
        "wechat_data_list": [],
        "save_id": "slot_bench"
    }

    t1 = time.perf_counter()
    turn_res = _http_json("POST", "/api/game/turn", turn_body, visitor_id=visitor_id, timeout=120.0)
    turn_elapsed = time.perf_counter() - t1

    monitor = _http_json("GET", "/api/game/monitor", None, visitor_id=visitor_id, timeout=30.0)
    prefetch_stats = monitor.get("prefetch_stats", {})

    return {
        "mode": dialogue_mode,
        "visitor_id": visitor_id,
        "start_elapsed": round(start_elapsed, 3),
        "turn_elapsed": round(turn_elapsed, 3),
        "start_evt": start_res.get("current_evt_id", ""),
        "turn_evt": turn_res.get("current_evt_id", ""),
        "start_is_end": bool(start_res.get("is_end", False)),
        "turn_is_end": bool(turn_res.get("is_end", False)),
        "choice": first_choice,
        "start_text": _shorten(start_res.get("display_text", "")),
        "turn_text": _shorten(turn_res.get("display_text", "")),
        "start_options": start_options[:3],
        "turn_options": (turn_res.get("next_options") or [])[:3],
        "cache_hit_rate": prefetch_stats.get("cache_hit_rate"),
        "recent_cache_hit_rate": prefetch_stats.get("recent_cache_hit_rate"),
        "recent_fallback_rate": prefetch_stats.get("recent_fallback_rate"),
        "fallback_streak": prefetch_stats.get("fallback_streak"),
    }


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return -1.0
    arr = sorted(values)
    if len(arr) == 1:
        return float(arr[0])
    idx = int(round((len(arr) - 1) * p))
    return float(arr[max(0, min(len(arr) - 1, idx))])


def _agg_mode(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ok_rows = [r for r in rows if r.get("start_elapsed", -1) >= 0 and r.get("turn_elapsed", -1) >= 0]
    start_vals = [float(r["start_elapsed"]) for r in ok_rows]
    turn_vals = [float(r["turn_elapsed"]) for r in ok_rows]
    return {
        "runs_total": len(rows),
        "runs_ok": len(ok_rows),
        "start_avg": round(sum(start_vals) / len(start_vals), 3) if start_vals else -1,
        "turn_avg": round(sum(turn_vals) / len(turn_vals), 3) if turn_vals else -1,
        "start_p95": round(_percentile(start_vals, 0.95), 3) if start_vals else -1,
        "turn_p95": round(_percentile(turn_vals, 0.95), 3) if turn_vals else -1,
    }


def _write_report(results: List[Dict[str, Any]], repeats: int) -> None:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for r in results:
        grouped.setdefault(r["mode"], []).append(r)

    lines: List[str] = []
    lines.append("# 对话模式速度与文本对比报告")
    lines.append("")
    lines.append(f"- 测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"- API 地址: `{API_BASE}`")
    lines.append("- 场景: `start -> first turn`（同批次对比）")
    lines.append(f"- 每种模式轮次: `{repeats}`")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 模式 | 轮次(成功/总数) | start均值(s) | startP95(s) | turn均值(s) | turnP95(s) |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for mode in ["single_dm", "npc_dm"]:
        rows = grouped.get(mode, [])
        agg = _agg_mode(rows)
        lines.append(
            f"| `{mode}` | {agg['runs_ok']}/{agg['runs_total']} | "
            f"{agg['start_avg']} | {agg['start_p95']} | {agg['turn_avg']} | {agg['turn_p95']} |"
        )

    lines.append("")
    lines.append("## 单次明细")
    lines.append("")
    lines.append("| 模式 | run | start耗时(s) | turn耗时(s) | start事件 | turn事件 | cache_hit_rate | recent_cache_hit_rate | recent_fallback_rate |")
    lines.append("|---|---:|---:|---:|---|---|---:|---:|---:|")
    for idx, r in enumerate(results, 1):
        lines.append(
            f"| `{r['mode']}` | {r.get('run_index', idx)} | "
            f"{r['start_elapsed']:.3f} | {r['turn_elapsed']:.3f} | "
            f"`{r['start_evt']}` | `{r['turn_evt']}` | "
            f"{r['cache_hit_rate'] if r['cache_hit_rate'] is not None else '-'} | "
            f"{r['recent_cache_hit_rate'] if r['recent_cache_hit_rate'] is not None else '-'} | "
            f"{r['recent_fallback_rate'] if r['recent_fallback_rate'] is not None else '-'} |"
        )
    lines.append("")
    lines.append("## 文本样本")
    lines.append("")
    for r in results:
        lines.append(f"### 模式: `{r['mode']}`")
        lines.append(f"- Visitor: `{r['visitor_id']}`")
        lines.append(f"- 首次选项: `{r['choice']}`")
        lines.append(f"- Start文本: `{r['start_text']}`")
        lines.append(f"- Turn文本: `{r['turn_text']}`")
        lines.append(f"- Start可选项: `{r['start_options']}`")
        lines.append(f"- Turn可选项: `{r['turn_options']}`")
        lines.append(f"- Fallback连续次数: `{r['fallback_streak']}`")
        lines.append("")

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main() -> None:
    global API_BASE
    parser = argparse.ArgumentParser(description="Benchmark dialogue modes via API")
    parser.add_argument("--repeats", type=int, default=3, help="runs per mode")
    parser.add_argument("--api-base", type=str, default=API_BASE, help="API base URL, e.g. http://127.0.0.1:8000")
    args = parser.parse_args()

    API_BASE = args.api_base.rstrip("/")

    repeats = max(1, int(args.repeats))
    modes = ["single_dm", "npc_dm"]
    print("🚀 开始模式对比测试：", ", ".join(modes))
    print(f"⚠️ 请确认后端服务已启动： {API_BASE}")
    print(f"🔁 每种模式轮次: {repeats}")

    results: List[Dict[str, Any]] = []
    for mode in modes:
        print(f"\n--- 测试模式: {mode} ---")
        for run_idx in range(1, repeats + 1):
            try:
                r = _run_one_mode(mode)
                r["run_index"] = run_idx
                results.append(r)
                print(
                    f"[{mode}#{run_idx}] start={r['start_elapsed']:.3f}s "
                    f"turn={r['turn_elapsed']:.3f}s evt={r['turn_evt']}"
                )
            except Exception as e:
                print(f"❌ 模式 {mode} 第 {run_idx} 轮失败: {e}")
                results.append({
                    "mode": mode,
                    "run_index": run_idx,
                    "visitor_id": "-",
                    "start_elapsed": -1.0,
                    "turn_elapsed": -1.0,
                    "start_evt": "-",
                    "turn_evt": "-",
                    "start_is_end": False,
                    "turn_is_end": False,
                    "choice": "-",
                    "start_text": str(e),
                    "turn_text": "",
                    "start_options": [],
                    "turn_options": [],
                    "cache_hit_rate": None,
                    "recent_cache_hit_rate": None,
                    "recent_fallback_rate": None,
                    "fallback_streak": None
                })

    _write_report(results, repeats)
    print(f"\n✅ 对比完成，报告已写入: {REPORT_PATH}")


if __name__ == "__main__":
    main()
