"""
Item Model - 物品資料模型

定義遊戲中的物品，專注於邏輯屬性而非顯示屬性。
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, Tuple


class Item(BaseModel):
    """
    物品基礎類別
    
    包含物品的核心屬性，不包含任何顯示相關的屬性。
    """
    name: str
    description: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Tuple[int, int]] = None  # 邏輯位置，用於AI計算距離等
    size: Optional[Tuple[int, int]] = None      # 邏輯大小，用於空間計算
    
    # 物品狀態屬性
    is_consumable: bool = False
    is_interactive: bool = True
    current_state: str = "normal"  # normal, damaged, broken, etc.
    
    def interact(self, action: str) -> str:
        """
        處理物品互動
        
        Args:
            action: 互動動作類型
            
        Returns:
            互動結果描述
        """
        # 這裡可以根據 action 和 properties 處理不同的互動
        return f"{self.name} 被 {action} 了。"
    
    def update_state(self, new_state: str):
        """更新物品狀態"""
        self.current_state = new_state
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "position": self.position,
            "size": self.size,
            "is_consumable": self.is_consumable,
            "is_interactive": self.is_interactive,
            "current_state": self.current_state
        }