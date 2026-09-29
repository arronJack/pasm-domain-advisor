"""领域 profile 注册表（新增领域只需在此登记）。"""
from __future__ import annotations

from typing import Dict

from .douyin_pet_store import PROFILE as douyin_pet_store
from .cross_border_ecom import PROFILE as cross_border_ecom
from .food_business_license import PROFILE as food_business_license
from ..domain_profile import DomainProfile

REGISTRY: Dict[str, DomainProfile] = {
    douyin_pet_store.id: douyin_pet_store,
    cross_border_ecom.id: cross_border_ecom,
    food_business_license.id: food_business_license,
}


def register(profile: DomainProfile) -> None:
    REGISTRY[profile.id] = profile


def get(profile_id: str) -> DomainProfile:
    if profile_id not in REGISTRY:
        raise KeyError("未知 profile：%s（已注册：%s）" % (profile_id, list(REGISTRY)))
    return REGISTRY[profile_id]


def list_ids() -> list:
    return list(REGISTRY)


def match(text: str, min_hits: int = 1):
    """按 match_keywords 给输入打分，返回命中最多的 profile；不达标返回 None。

    打分规则：命中一个关键词计 1 分，同分时用「命中词总长度」衡量具体度
    （"抖音小店" 比 "开店" 更具体）。min_hits 缺省 1——聊天壳用它做
    "领域路由"，宁缺勿滥。
    """
    if not text:
        return None
    best, best_score, best_spec = None, 0, 0
    for prof in REGISTRY.values():
        hits = [kw for kw in prof.match_keywords if kw and kw in text]
        if len(hits) < max(1, min_hits):
            continue
        score, spec = len(hits), sum(len(kw) for kw in hits)
        if score > best_score or (score == best_score and spec > best_spec):
            best, best_score, best_spec = prof, score, spec
    return best


__all__ = [
    "REGISTRY", "register", "get", "list_ids", "match",
    "douyin_pet_store", "cross_border_ecom", "food_business_license",
]
