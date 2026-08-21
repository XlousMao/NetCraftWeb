"""模型包：统一导出所有 ORM 模型，确保 Base.metadata 完整。"""

from app.models.activity import Activity, ActivityRecord
from app.models.dungeon import (
    Dungeon,
    DungeonConsumption,
    DungeonLoot,
    DungeonRepair,
    DungeonRun,
)
from app.models.equipment import Equipment, EquipmentRepairRequirement
from app.models.item import Item, ItemImage, ItemPriceHistory, ItemRelation
from app.models.recipe import (
    ProductionRecord,
    Recipe,
    RecipeMaterial,
    RecipeOutput,
)

__all__ = [
    "Item",
    "ItemImage",
    "ItemPriceHistory",
    "ItemRelation",
    "Dungeon",
    "DungeonRun",
    "DungeonLoot",
    "DungeonConsumption",
    "DungeonRepair",
    "Equipment",
    "EquipmentRepairRequirement",
    "Recipe",
    "RecipeMaterial",
    "RecipeOutput",
    "ProductionRecord",
    "Activity",
    "ActivityRecord",
]
