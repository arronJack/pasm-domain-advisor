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


__all__ = [
    "REGISTRY", "register", "get", "list_ids",
    "douyin_pet_store", "cross_border_ecom", "food_business_license",
]
