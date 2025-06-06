"""
World Manager - 世界狀態管理器

管理遊戲世界的空間、物品和整體狀態。
"""

from typing import Dict, List, Optional, Any
import logging

from .models import Space, Item

logger = logging.getLogger(__name__)


class WorldManager:
    """
    世界管理器
    
    負責管理所有空間、物品和世界狀態。
    """
    
    def __init__(self):
        """初始化世界管理器"""
        self.spaces: Dict[str, Space] = {}
        self.items: Dict[str, Item] = {}
        self.global_state: Dict[str, Any] = {}
        
    def initialize(self):
        """初始化世界管理器"""
        logger.info("WorldManager initialized")
        
    def add_space(self, space: Space) -> bool:
        """
        添加空間到世界
        
        Args:
            space: 要添加的空間
            
        Returns:
            是否成功添加
        """
        if space.name in self.spaces:
            logger.warning(f"Space '{space.name}' already exists")
            return False
        
        self.spaces[space.name] = space
        logger.info(f"Added space '{space.name}' to world")
        return True
    
    def remove_space(self, space_name: str) -> bool:
        """
        從世界移除空間
        
        Args:
            space_name: 空間名稱
            
        Returns:
            是否成功移除
        """
        if space_name not in self.spaces:
            return False
        
        space = self.spaces[space_name]
        
        # 斷開所有連接
        for connected in space.connected_spaces:
            connected.connected_spaces.remove(space)
        
        del self.spaces[space_name]
        logger.info(f"Removed space '{space_name}' from world")
        return True
    
    def get_space(self, space_name: str) -> Optional[Space]:
        """
        獲取空間
        
        Args:
            space_name: 空間名稱
            
        Returns:
            空間實例，如果不存在則返回 None
        """
        return self.spaces.get(space_name)
    
    def get_all_spaces(self) -> List[Space]:
        """獲取所有空間"""
        return list(self.spaces.values())
    
    def add_item(self, item: Item) -> bool:
        """
        添加物品到世界
        
        Args:
            item: 要添加的物品
            
        Returns:
            是否成功添加
        """
        if item.name in self.items:
            logger.warning(f"Item '{item.name}' already exists")
            return False
        
        self.items[item.name] = item
        logger.info(f"Added item '{item.name}' to world")
        return True
    
    def remove_item(self, item_name: str) -> bool:
        """
        從世界移除物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            是否成功移除
        """
        if item_name not in self.items:
            return False
        
        # 從所有空間移除該物品
        for space in self.spaces.values():
            space.remove_item(item_name)
        
        del self.items[item_name]
        logger.info(f"Removed item '{item_name}' from world")
        return True
    
    def get_item(self, item_name: str) -> Optional[Item]:
        """
        獲取物品
        
        Args:
            item_name: 物品名稱
            
        Returns:
            物品實例，如果不存在則返回 None
        """
        return self.items.get(item_name)
    
    def find_item_in_world(self, item_name: str) -> Optional[Space]:
        """
        在世界中尋找物品所在的空間
        
        Args:
            item_name: 物品名稱
            
        Returns:
            包含該物品的空間，如果沒找到則返回 None
        """
        for space in self.spaces.values():
            for item in space.items:
                if item.name == item_name:
                    return space
        return None
    
    def move_item(self, item_name: str, from_space: str, to_space: str) -> bool:
        """
        在空間之間移動物品
        
        Args:
            item_name: 物品名稱
            from_space: 來源空間名稱
            to_space: 目標空間名稱
            
        Returns:
            是否成功移動
        """
        source = self.get_space(from_space)
        target = self.get_space(to_space)
        
        if not source or not target:
            return False
        
        item = source.remove_item(item_name)
        if not item:
            return False
        
        return target.add_item(item)
    
    def update(self):
        """更新世界狀態"""
        # 這裡可以添加世界的週期性更新邏輯
        # 例如：物品狀態變化、環境變化等
        pass
    
    def get_global_state(self, key: str) -> Any:
        """獲取全域狀態值"""
        return self.global_state.get(key)
    
    def set_global_state(self, key: str, value: Any):
        """設定全域狀態值"""
        self.global_state[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            包含世界資料的字典
        """
        return {
            "spaces": {name: space.model_dump() for name, space in self.spaces.items()},
            "items": {name: item.to_dict() for name, item in self.items.items()},
            "global_state": self.global_state
        }