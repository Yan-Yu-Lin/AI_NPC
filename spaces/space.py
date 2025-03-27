"""
空間類
表示遊戲中的位置和環境
"""

from typing import Dict, List, Optional, Any

from core.base_models import BaseEntity


class Space(BaseEntity):
    """
    表示遊戲中的一個空間或位置。
    包含物品、NPCs和到其他空間的連接。
    """
    
    def __init__(self, name: str, description: str):
        """
        初始化一個新的空間。
        
        Args:
            name: 空間名稱
            description: 空間描述
        """
        super().__init__(name, description)
        self.items = []  # 空間中的物品列表
        self.npcs = []  # 空間中的NPC列表
        self.connected_spaces = []  # 與該空間相連的其他空間
    
    def connect_to(self, other_space):
        """
        將此空間與另一個空間相連。
        
        Args:
            other_space: 要連接的空間
        """
        if other_space not in self.connected_spaces:
            self.connected_spaces.append(other_space)
        
        # 確保雙向連接
        if self not in other_space.connected_spaces:
            other_space.connected_spaces.append(self)
    
    def __str__(self) -> str:
        """返回空間的詳細描述，包括物品和NPC"""
        result = [f"空間: {self.name}"]
        result.append(f"描述: {self.description}")
        
        # 添加物品信息
        if self.items:
            result.append("物品:")
            for item in self.items:
                result.append(f" - {item.name}: {item.description}")
        
        # 添加NPC信息
        if self.npcs:
            result.append("人物:")
            for npc in self.npcs:
                result.append(f" - {npc.name}: {npc.description}")
        
        # 添加連接的空間
        if self.connected_spaces:
            result.append("出口:")
            for space in self.connected_spaces:
                result.append(f" - {space.name}")
        
        return "\n".join(result)
