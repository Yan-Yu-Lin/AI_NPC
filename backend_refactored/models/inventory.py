"""
Inventory Model - 物品欄資料模型

管理 NPC 或其他實體的物品欄。
"""

from pydantic import BaseModel, Field
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .item import Item


class Inventory(BaseModel):
    """
    物品欄類別
    
    管理物品的儲存和操作。
    """
    items: List["Item"] = Field(default_factory=list)
    capacity: Optional[int] = None  # None 表示無限容量
    
    def add_item(self, item: "Item") -> str:
        """
        添加物品到物品欄
        
        Args:
            item: 要添加的物品
            
        Returns:
            操作結果訊息
        """
        if self.capacity is not None and len(self.items) >= self.capacity:
            return f"無法添加 {item.name}。物品欄已滿。"
        
        self.items.append(item)
        return f"已將 {item.name} 添加到物品欄。"
    
    def remove_item(self, item_name: str) -> str:
        """
        從物品欄移除物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            操作結果訊息
        """
        for i, item in enumerate(self.items):
            if item.name == item_name:
                removed_item = self.items.pop(i)
                return f"已從物品欄移除 {removed_item.name}。"
        return f"物品欄中找不到名為 '{item_name}' 的物品。"
    
    def has_item(self, item_name: str) -> bool:
        """
        檢查是否擁有特定物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            是否擁有該物品
        """
        return any(item.name == item_name for item in self.items)
    
    def get_item(self, item_name: str) -> Optional["Item"]:
        """
        獲取特定物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            物品實例，如果沒找到則返回 None
        """
        for item in self.items:
            if item.name == item_name:
                return item
        return None
    
    def list_items(self) -> str:
        """
        列出所有物品
        
        Returns:
            物品清單的文字描述
        """
        if not self.items:
            return "物品欄是空的。"
        return "\n".join([f"- {item.name}: {item.description}" for item in self.items])
    
    def get_item_names(self) -> List[str]:
        """
        獲取所有物品名稱
        
        Returns:
            物品名稱列表
        """
        return [item.name for item in self.items]
    
    def get_item_count(self) -> int:
        """獲取物品數量"""
        return len(self.items)
    
    def is_full(self) -> bool:
        """檢查物品欄是否已滿"""
        if self.capacity is None:
            return False
        return len(self.items) >= self.capacity
    
    def get_available_space(self) -> Optional[int]:
        """
        獲取剩餘空間
        
        Returns:
            剩餘空間數量，如果無限容量則返回 None
        """
        if self.capacity is None:
            return None
        return self.capacity - len(self.items)