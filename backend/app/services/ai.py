"""AI 分析层 —— 输入结构化分析数据，输出可读洞察。

安全原则：AI 只读取分析数据、生成文本，绝不直接修改数据库。
未配置 DEEPSEEK_API_KEY 时降级为本地规则化摘要。
"""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import settings


SYSTEM_PROMPT = (
    "你是 GEAP 游戏经济分析助手。基于后端提供的结构化数据，输出中文分析，"
    "包含：数据摘要、问题定位、可能原因、优化建议。只基于给定数据，不臆测。"
)


def build_analysis_payload(dashboard_data: dict, question: Optional[str] = None) -> dict:
    """从 Dashboard 数据构造发给 AI 的结构化载荷。"""
    week = dashboard_data.get("week", {})
    activities = dashboard_data.get("activities", {})
    return {
        "question": question or "请分析我本周的游戏经济状况，并给出优化建议。",
        "period": f"{week.get('start', '')} ~ {week.get('end', '')}",
        "net_profit": week.get("net_profit", 0),
        "profit_per_hour": week.get("profit_per_hour", 0),
        "gross_value": week.get("total_gross", 0),
        "repair_cost": week.get("total_repair", 0),
        "consumable_cost": week.get("total_consumable", 0),
        "cost_ratio": week.get("cost_ratio", 0),
        "is_loss": week.get("is_loss", False),
        "run_count": week.get("run_count", 0),
        "top_dungeons": dashboard_data.get("top_dungeons", []),
        "top_recipes": dashboard_data.get("top_recipes", []),
        "activity_efficiency": activities.get("activities", []),
        "important_items": dashboard_data.get("important_items", []),
    }


def local_analysis(payload: dict) -> str:
    """本地规则化分析（无 API key 时的降级方案）。"""
    lines: list[str] = []
    net = payload.get("net_profit", 0)
    pph = payload.get("profit_per_hour", 0)
    lines.append("【数据摘要】")
    if net >= 0:
        lines.append(f"本周净利润 {net:,.0f} 金币，每小时约 {pph:,.0f} 金币，处于盈利状态。")
    else:
        lines.append(f"本周净亏损 {abs(net):,.0f} 金币，处于亏损状态。")

    repair = payload.get("repair_cost", 0)
    consumable = payload.get("consumable_cost", 0)
    gross = payload.get("gross_value", 0)
    if gross > 0:
        lines.append(
            f"维修成本 {repair:,.0f}，消耗品 {consumable:,.0f}，"
            f"成本占比 {payload.get('cost_ratio', 0) * 100:.1f}%。"
        )

    top_d = payload.get("top_dungeons", [])
    if top_d:
        best = top_d[0]
        lines.append(f"【问题定位】收益最高的副本是「{best['dungeon_name']}」，净利润 {best['net_profit']:,.0f}。")
        if len(top_d) > 1:
            worst = top_d[-1]
            lines.append(f"收益最低的是「{worst['dungeon_name']}」，净利润 {worst['net_profit']:,.0f}，建议评估是否继续投入时间。")

    acts = payload.get("activity_efficiency", [])
    if acts:
        best_act = acts[0]
        lines.append(f"单位时间收益最高的活动是 {best_act['activity_type']}（{best_act['profit_per_hour']:,.0f}/小时）。")

    lines.append("【优化建议】")
    if payload.get("cost_ratio", 0) > 0.4:
        lines.append("1. 成本占比偏高，优先排查维修与消耗品开销，考虑降低装备维修频率或寻找更便宜的材料。")
    else:
        lines.append("1. 成本占比健康，可将时间优先投入到单位收益更高的副本。")
    if net < 0:
        lines.append("2. 当前处于亏损，建议暂停低收益副本，聚焦高收益活动。")
    else:
        lines.append("2. 保持当前节奏，可将结余资金投入 ROI 较高的配方生产。")

    return "\n".join(lines)


async def generate_analysis(payload: dict) -> dict:
    """生成分析。有 API key 走 DeepSeek，否则本地规则化。"""
    if not settings.DEEPSEEK_API_KEY:
        return {"provider": "local", "content": local_analysis(payload)}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.DEEPSEEK_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": _payload_to_text(payload)},
                    ],
                    "temperature": 0.3,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return {"provider": "deepseek", "content": content}
    except Exception as exc:  # noqa: BLE001
        return {
            "provider": "deepseek-error",
            "content": f"AI 调用失败，已降级为本地分析。\n\n{local_analysis(payload)}",
            "error": str(exc),
        }


def _payload_to_text(payload: dict) -> str:
    import json

    return "以下是我的结构化游戏经济数据（JSON）：\n" + json.dumps(
        payload, ensure_ascii=False, indent=2
    )
