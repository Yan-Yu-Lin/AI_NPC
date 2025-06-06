"""
Space Model - 空間資料模型

定義遊戲中的空間/房間，專注於邏輯結構而非顯示。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .item import Item
    from .npc import NPC


class Space(BaseModel):
    """
    空間類別
    
    代表遊戲世界中的一個空間或房間。
    """
    name: str
    description: str
    connected_spaces: List["Space"] = Field(default_factory=list)
    items: List["Item"] = Field(default_factory=list)
    npcs: List["NPC"] = Field(default_factory=list)
    
    # 空間屬性
    space_type: str = "room"  # room, outdoor, corridor, etc.
    capacity: int = 10  # 最大容納物品數
    is_accessible: bool = True
    ambient_sound: Optional[str] = None
    
    model_config = {"arbitrary_types_allowed": True}
    
    def biconnect(self, other_space: "Space") -> None:
        """
        建立雙向連接
        
        Args:
            other_space: 要連接的空間
        """
        if other_space not in self.connected_spaces:
            self.connected_spaces.append(other_space)
        if self not in other_space.connected_spaces:
            other_space.connected_spaces.append(self)
    
    def add_item(self, item: "Item") -> bool:
        """
        添加物品到空間
        
        Args:
            item: 要添加的物品
            
        Returns:
            是否成功添加
        """
        if len(self.items) >= self.capacity:
            return False
        
        if item not in self.items:
            self.items.append(item)
            return True
        return False
    
    def remove_item(self, item_name: str) -> Optional["Item"]:
        """
        從空間移除物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            被移除的物品，如果沒找到則返回 None
        """
        for i, item in enumerate(self.items):
            if item.name == item_name:
                return self.items.pop(i)
        return None
    
    def add_npc(self, npc: "NPC") -> None:
        """添加 NPC 到空間"""
        if npc not in self.npcs:
            self.npcs.append(npc)
    
    def remove_npc(self, npc: "NPC") -> None:
        """從空間移除 NPC"""
        if npc in self.npcs:
            self.npcs.remove(npc)
    
    def get_connected_space_names(self) -> List[str]:
        """獲取所有連接空間的名稱"""
        return [space.name for space in self.connected_spaces]
    
    def get_items_names(self) -> List[str]:
        """獲取所有物品的名稱"""
        return [item.name for item in self.items]
    
    def get_npcs_names(self) -> List[str]:
        """獲取所有 NPC 的名稱"""
        return [npc.name for npc in self.npcs]
    
    def __str__(self) -> str:
        connected = ", ".join(self.get_connected_space_names()) if self.connected_spaces else "none"
        items_str = ", ".join(self.get_items_names()) if self.items else "none"
        npcs_str = ", ".join(self.get_npcs_names()) if self.npcs else "none"
        return (
            f"Space Name: {self.name}\n"
            f"Description: {self.description}\n"
            f"Type: {self.space_type}\n"
            f"Connected Spaces: {connected}\n"
            f"Items in Space: {items_str}\n"
            f"NPCs in Space: {npcs_str}"
        )