"""
基礎模型
提供遊戲中各種元素的基礎類別
"""

from typing import Dict, List, Optional, Any


class BaseEntity:
    """
    遊戲中所有實體的基類。
    提供通用屬性和方法。
    """
    
    def __init__(self, name: str, description: str):
        """
        初始化基礎實體。
        
        Args:
            name: 實體名稱
            description: 實體描述
        """
        self.name = name
        self.description = description
    
    def __str__(self) -> str:
        """返回實體的字符串表示"""
        return f"{self.name}: {self.description}"
