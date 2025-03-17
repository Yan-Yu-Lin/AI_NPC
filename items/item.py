"""
物品類
表示遊戲中可互動的物品
"""

from typing import Dict, List, Optional, Any

from core.base_models import BaseEntity


class Item(BaseEntity):
    """
    表示遊戲中的物品。
    物品可以被放置、拾取、使用等。
    """
    
    def __init__(self, name: str, description: str, interactions: Dict[str, Optional[Dict[str, type]]] = None):
        """
        初始化一個新的物品。
        
        Args:
            name: 物品名稱
            description: 物品描述
            interactions: 物品可進行的互動及其所需參數
                          例如: {"閱讀": None, "寫入": {"content": str}}
        """
        super().__init__(name, description)
        self.interactions = interactions or {"觀察": None}
        
        # 某些物品可能有內容，如書、紙條等
        self.content = ""

    def add_interaction(self, interaction_name: str, params: Optional[Dict[str, type]] = None):
        """
        添加一個新的互動方式。
        
        Args:
            interaction_name: 互動的名稱，如"閱讀"、"使用"等
            params: 互動所需的參數及其類型，如{"内容": str}
        """
        self.interactions[interaction_name] = params

    def __str__(self) -> str:
        """返回物品的字符串表示"""
        return f"{self.name}: {self.description}"
