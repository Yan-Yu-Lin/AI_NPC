"""
NPC Manager - NPC 管理器

管理所有 NPC 的建立、更新和互動。
"""

from typing import Dict, List, Optional, Any
import logging

from .models import NPC

logger = logging.getLogger(__name__)


class NPCManager:
    """
    NPC 管理器
    
    負責管理所有 NPC 的生命週期和狀態。
    """
    
    def __init__(self):
        """初始化 NPC 管理器"""
        self.npcs: Dict[str, NPC] = {}
        self.npc_groups: Dict[str, List[str]] = {}  # 群組管理
        
    def initialize(self):
        """初始化 NPC 管理器"""
        logger.info("NPCManager initialized")
    
    def add_npc(self, npc: NPC) -> bool:
        """
        添加 NPC
        
        Args:
            npc: 要添加的 NPC
            
        Returns:
            是否成功添加
        """
        if npc.name in self.npcs:
            logger.warning(f"NPC '{npc.name}' already exists")
            return False
        
        self.npcs[npc.name] = npc
        logger.info(f"Added NPC '{npc.name}'")
        return True
    
    def remove_npc(self, npc_name: str) -> bool:
        """
        移除 NPC
        
        Args:
            npc_name: NPC 名稱
            
        Returns:
            是否成功移除
        """
        if npc_name not in self.npcs:
            return False
        
        npc = self.npcs[npc_name]
        
        # 從當前空間移除
        if npc.current_space:
            npc.current_space.remove_npc(npc)
        
        # 從所有群組移除
        for group_npcs in self.npc_groups.values():
            if npc_name in group_npcs:
                group_npcs.remove(npc_name)
        
        del self.npcs[npc_name]
        logger.info(f"Removed NPC '{npc_name}'")
        return True
    
    def get_npc(self, npc_name: str) -> Optional[NPC]:
        """
        獲取 NPC
        
        Args:
            npc_name: NPC 名稱
            
        Returns:
            NPC 實例，如果不存在則返回 None
        """
        return self.npcs.get(npc_name)
    
    def get_all_npcs(self) -> List[NPC]:
        """獲取所有 NPC"""
        return list(self.npcs.values())
    
    def get_npcs_by_state(self, state: str) -> List[NPC]:
        """
        獲取特定狀態的所有 NPC
        
        Args:
            state: NPC 狀態
            
        Returns:
            符合狀態的 NPC 列表
        """
        return [npc for npc in self.npcs.values() if npc.current_state == state]
    
    def get_npcs_in_space(self, space_name: str) -> List[NPC]:
        """
        獲取特定空間中的所有 NPC
        
        Args:
            space_name: 空間名稱
            
        Returns:
            在該空間中的 NPC 列表
        """
        return [npc for npc in self.npcs.values() 
                if npc.current_space and npc.current_space.name == space_name]
    
    def create_npc_group(self, group_name: str, npc_names: List[str]) -> bool:
        """
        建立 NPC 群組
        
        Args:
            group_name: 群組名稱
            npc_names: NPC 名稱列表
            
        Returns:
            是否成功建立
        """
        # 驗證所有 NPC 都存在
        for npc_name in npc_names:
            if npc_name not in self.npcs:
                logger.warning(f"NPC '{npc_name}' not found for group '{group_name}'")
                return False
        
        self.npc_groups[group_name] = npc_names.copy()
        logger.info(f"Created NPC group '{group_name}' with {len(npc_names)} NPCs")
        return True
    
    def get_group_npcs(self, group_name: str) -> List[NPC]:
        """
        獲取群組中的所有 NPC
        
        Args:
            group_name: 群組名稱
            
        Returns:
            群組中的 NPC 列表
        """
        if group_name not in self.npc_groups:
            return []
        
        return [self.npcs[name] for name in self.npc_groups[group_name] 
                if name in self.npcs]
    
    def update_all_npcs(self):
        """更新所有 NPC 的狀態"""
        for npc in self.npcs.values():
            # 這裡可以添加週期性的 NPC 更新邏輯
            # 例如：目標更新、狀態檢查等
            pass
    
    def process_npc_interactions(self):
        """處理 NPC 之間的互動"""
        # 檢查同一空間內的 NPC 是否有互動
        space_npcs = {}
        
        # 按空間分組 NPC
        for npc in self.npcs.values():
            if npc.current_space:
                space_name = npc.current_space.name
                if space_name not in space_npcs:
                    space_npcs[space_name] = []
                space_npcs[space_name].append(npc)
        
        # 處理每個空間內的潛在互動
        for space_name, npcs in space_npcs.items():
            if len(npcs) > 1:
                # 這裡可以實作 NPC 之間的自動互動邏輯
                pass
    
    def get_npc_stats(self) -> Dict[str, Any]:
        """
        獲取 NPC 統計資訊
        
        Returns:
            包含統計資訊的字典
        """
        states_count = {}
        for npc in self.npcs.values():
            state = npc.current_state
            states_count[state] = states_count.get(state, 0) + 1
        
        return {
            "total_npcs": len(self.npcs),
            "states": states_count,
            "groups": list(self.npc_groups.keys()),
            "active_npcs": len([n for n in self.npcs.values() 
                               if n.current_state != "idle"])
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        轉換為字典格式
        
        Returns:
            包含所有 NPC 資料的字典
        """
        npcs_data = {}
        
        for name, npc in self.npcs.items():
            npcs_data[name] = {
                "name": npc.name,
                "description": npc.description,
                "current_space": npc.current_space.name if npc.current_space else None,
                "inventory": {
                    "items": [item.to_dict() for item in npc.inventory.items],
                    "capacity": npc.inventory.capacity
                },
                "position": npc.position,
                "current_state": npc.current_state,
                "history": npc.history[-10:],  # 只保存最近 10 條歷史
                "personality": npc.personality,
                "goals": npc.goals,
                "current_goal": npc.current_goal
            }
        
        return npcs_data