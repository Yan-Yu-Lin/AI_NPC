"""
庫存類
管理實體可持有的物品
"""

from typing import Dict, List, Optional, Any


class Inventory:
    """
    表示實體（如NPC）的庫存。
    管理庫存中的物品。
    """
    
    def __init__(self, max_capacity: int = 10):
        """
        初始化一個新的庫存。
        
        Args:
            max_capacity: 庫存的最大容量
        """
        self.items = []  # 庫存中的物品列表
        self.max_capacity = max_capacity
    
    def add_item(self, item):
        """
        添加物品到庫存。
        
        Args:
            item: 要添加的物品
            
        Returns:
            成功添加返回True，否則返回False
        """
        if len(self.items) >= self.max_capacity:
            return False
        
        self.items.append(item)
        return True
    
    def remove_item(self, item_name: str):
        """
        從庫存中移除指定名稱的物品。
        
        Args:
            item_name: 要移除的物品名稱
            
        Returns:
            被移除的物品，如果未找到則返回None
        """
        for i, item in enumerate(self.items):
            if item.name == item_name:
                return self.items.pop(i)
        
        return None
    
    def get_item(self, item_name: str):
        """
        獲取庫存中指定名稱的物品，但不從庫存中移除。
        
        Args:
            item_name: 要獲取的物品名稱
            
        Returns:
            找到的物品，如果未找到則返回None
        """
        for item in self.items:
            if item.name == item_name:
                return item
        
        return None
    
    def __str__(self) -> str:
        """返回庫存的字符串表示"""
        if not self.items:
            return "空的庫存"
        
        items_str = ", ".join([item.name for item in self.items])
        return f"庫存: {items_str}"
