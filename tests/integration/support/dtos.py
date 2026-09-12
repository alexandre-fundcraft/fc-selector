"""Reusable DTOs and selector definitions for integration contracts."""

from dataclasses import dataclass
from typing import Optional

from fc_selector.core.dtos import UNSET, BaseODataDTO
from fc_selector.django.selector import ODataSelector
from tests.integration.support.models import ODataModelWithFK

# --- DTOs ---


@dataclass
class FKTargetDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET
    code: str = UNSET


@dataclass
class ModelWithFKDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    value: int = UNSET
    target: Optional[FKTargetDTO] = UNSET
    second_target: Optional[FKTargetDTO] = UNSET


@dataclass
class M2MTargetDTO(BaseODataDTO):
    id: int = UNSET
    name: str = UNSET


@dataclass
class GrandChildDTO(BaseODataDTO):
    id: int = UNSET
    note: str = UNSET


@dataclass
class ChildDTO(BaseODataDTO):
    id: int = UNSET
    label: str = UNSET
    score: int = UNSET
    category: Optional[M2MTargetDTO] = UNSET
    grandchildren: list[GrandChildDTO] = UNSET


@dataclass
class ParentWithRelationsDTO(BaseODataDTO):
    id: int = UNSET
    title: str = UNSET
    value: int = UNSET
    target: Optional[FKTargetDTO] = UNSET
    children: list[ChildDTO] = UNSET
    tags: list[M2MTargetDTO] = UNSET


# --- Selectors ---


class FKSelector(ODataSelector):
    class Meta:
        model = ODataModelWithFK
        dto_class = ModelWithFKDTO
        expandable_fields = {
            "target": FKTargetDTO,
            "second_target": FKTargetDTO,
        }
