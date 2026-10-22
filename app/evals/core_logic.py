"""
核心评估/测试辅助逻辑。

该模块把 XP、升级、掉落和 JSON 解析等规则从大函数中抽离，
便于单元测试、评估脚本复用和后续门禁统计。
"""
from __future__ import annotations

import json
import random
import uuid
from datetime import datetime
from typing import Any, Callable

from app.config import config


def calculate_xp_reward(difficulty: str | None, is_challenge: bool = False) -> int:
    """根据难度和挑战标记计算单次任务 XP。"""
    difficulty_key = (difficulty or "medium").lower()
    xp_multiplier = config.DIFFICULTY_MULTIPLIER.get(difficulty_key, 1.0)
    if is_challenge:
        xp_multiplier *= 1.5
    return int(config.BASE_XP_PER_TASK * xp_multiplier)


def calculate_drop_rate(task_dict: dict, streak_days: int = 0) -> float:
    """计算最终掉落率，供奖励逻辑和性能评估复用。"""
    base_drop_rate = config.DROP_RATE_BASE
    difficulty = (task_dict.get("difficulty") or "").lower()

    if difficulty == "hard":
        base_drop_rate += 0.05
    elif difficulty == "epic":
        base_drop_rate += 0.15

    if task_dict.get("is_challenge"):
        base_drop_rate += 0.10

    base_drop_rate += max(0, streak_days) * 0.02
    # 对上限做裁剪，避免极端 streak 让概率失真。
    return max(0.0, min(base_drop_rate, 1.0))


def roll_drop_rarity(
    rng_random: Callable[[], float] | None = None,
) -> str:
    """根据固定稀有度分布抽样，便于通过 mock 精准测边界。"""
    rng_random = rng_random or random.random
    roll = rng_random()
    if roll < 0.60:
        return "common"
    if roll < 0.85:
        return "rare"
    if roll < 0.97:
        return "epic"
    return "legendary"


def calculate_drop(
    task_dict: dict,
    profile_dict: dict,
    reward_pool: list[dict],
    *,
    rng_random: Callable[[], float] | None = None,
    rng_choice: Callable[[list[dict]], dict] | None = None,
    now_factory: Callable[[], datetime] | None = None,
) -> dict | None:
    """统一掉落计算逻辑，支持在测试中注入可控随机数。"""
    rng_random = rng_random or random.random
    rng_choice = rng_choice or random.choice
    now_factory = now_factory or datetime.now

    drop_rate = calculate_drop_rate(task_dict, profile_dict.get("streak_days", 0))
    if rng_random() > drop_rate:
        return None

    rarity = roll_drop_rarity(rng_random)
    available = [reward for reward in reward_pool if reward.get("rarity") == rarity]
    if not available:
        available = reward_pool

    chosen = rng_choice(available)
    return {
        "id": str(uuid.uuid4()),
        "name": chosen["name"],
        "description": chosen["description"],
        "reward_type": chosen["type"],
        "value": chosen["value"],
        "rarity": rarity,
        "obtained_at": now_factory().isoformat(),
    }


def apply_xp_to_profile(profile_dict: dict, xp_earned: int) -> tuple[dict, bool]:
    """更新用户经验和等级，返回更新后的 profile 与是否升级。"""
    updated = dict(profile_dict)
    old_level = updated.get("level", 1)
    updated["current_xp"] = updated.get("current_xp", 0) + xp_earned
    updated["total_xp"] = updated.get("total_xp", 0) + xp_earned

    xp_to_next = updated.get("xp_to_next_level", 1000)
    while updated["current_xp"] >= xp_to_next:
        updated["current_xp"] -= xp_to_next
        updated["level"] = updated.get("level", 1) + 1
        xp_to_next = int(xp_to_next * 1.2)

    updated["xp_to_next_level"] = xp_to_next
    return updated, updated.get("level", 1) > old_level


def safe_json_loads(raw_content: str | None, fallback: dict[str, Any]) -> dict[str, Any]:
    """统一 JSON 解析容错，避免各 Agent 重复写同类 fallback。"""
    try:
        parsed = json.loads((raw_content or "").strip())
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return dict(fallback)
