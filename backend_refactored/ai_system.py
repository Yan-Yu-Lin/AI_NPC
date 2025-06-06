"""
AI System - 核心 AI 系統

這是重構後的 AI 系統，專注於純 AI 邏輯，不包含任何顯示相關程式碼。
實作了 interfaces.py 中定義的 BackendAPI 介面。
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from pydantic import BaseModel, Field

from interfaces import (
    BackendAPI, 
    NPCDisplayData, ItemDisplayData, SpaceDisplayData, WorldDisplayData,
    UserInput, AIResponse, HistoryData, HistoryEntry,
    NPCNotFoundError, InvalidInputError, AIProcessingError,
    NPCState, Position, Size
)
from .models import Space, Item, NPC, Inventory
from .world_manager import WorldManager
from .npc_manager import NPCManager
from .interaction_processor import InteractionProcessor
from .utils.time_manager import TimeManager

# 設定 logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AI_System(BaseModel, BackendAPI):
    """
    核心 AI 系統類別
    
    管理整個 AI 系統的運作，包括 NPC、世界狀態和互動處理。
    實作 BackendAPI 介面以提供清晰的前後端分離。
    """
    
    # 配置
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # 核心組件
    world_manager: WorldManager = Field(default_factory=WorldManager)
    npc_manager: NPCManager = Field(default_factory=NPCManager)
    interaction_processor: InteractionProcessor = Field(default_factory=InteractionProcessor)
    time_manager: TimeManager = Field(default_factory=TimeManager)
    
    # 系統狀態
    is_initialized: bool = False
    active_npc_id: Optional[str] = None
    
    # 世界資料
    world_name: str = "未知世界"
    world_description: str = ""
    
    def initialize(self, world_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        初始化 AI 系統
        
        Args:
            world_data: 世界資料（可選）
            
        Returns:
            是否成功初始化
        """
        try:
            logger.info("Initializing AI System...")
            
            # 初始化各個管理器
            self.world_manager.initialize()
            self.npc_manager.initialize()
            self.interaction_processor.initialize(self)
            self.time_manager.initialize()
            
            # 如果提供了世界資料，載入它
            if world_data:
                self.load_world(world_data)
            
            self.is_initialized = True
            logger.info("AI System initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AI System: {e}")
            raise AIProcessingError(f"初始化失敗: {str(e)}")
    
    def load_world(self, world_data: Dict[str, Any]):
        """
        載入世界資料
        
        Args:
            world_data: 包含世界資料的字典
        """
        try:
            self.world_name = world_data.get("world_name", "未知世界")
            self.world_description = world_data.get("description", "")
            
            # 載入空間
            spaces_data = world_data.get("spaces_data", {})
            for space_name, space_info in spaces_data.items():
                self.world_manager.add_space(Space(**space_info))
            
            # 載入物品
            items_data = world_data.get("items_data", {})
            for item_name, item_info in items_data.items():
                self.world_manager.add_item(Item(**item_info))
            
            # 載入 NPC
            npcs_data = world_data.get("npcs_data", {})
            for npc_name, npc_info in npcs_data.items():
                # 建立 NPC 的物品欄
                inventory_data = npc_info.get("inventory", {})
                inventory = Inventory(**inventory_data)
                
                # 找到 NPC 的起始空間
                starting_space_name = npc_info.get("starting_space")
                starting_space = self.world_manager.get_space(starting_space_name)
                if not starting_space:
                    logger.warning(f"Starting space '{starting_space_name}' not found for NPC '{npc_name}'")
                    continue
                
                # 建立 NPC
                npc = NPC(
                    name=npc_name,
                    description=npc_info.get("description", ""),
                    current_space=starting_space,
                    inventory=inventory,
                    position=tuple(npc_info.get("position", [0, 0]))
                )
                
                self.npc_manager.add_npc(npc)
                starting_space.add_npc(npc)
            
            # 建立空間連接
            for space_name, space_info in spaces_data.items():
                space = self.world_manager.get_space(space_name)
                if space:
                    for connected_name in space_info.get("connected_spaces", []):
                        connected_space = self.world_manager.get_space(connected_name)
                        if connected_space:
                            space.biconnect(connected_space)
            
            logger.info(f"World '{self.world_name}' loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading world: {e}")
            raise
    
    def process_tick(self) -> bool:
        """
        處理一個遊戲 tick
        
        Returns:
            是否成功處理
        """
        try:
            # 更新時間
            self.time_manager.advance_time()
            
            # 處理世界更新
            self.world_manager.update()
            
            # 處理待處理的互動
            self.interaction_processor.process_pending_interactions()
            
            return True
            
        except Exception as e:
            logger.error(f"Error in process_tick: {e}")
            return False
    
    # ========== BackendAPI 介面實作 ==========
    
    def get_world_display_data(self) -> WorldDisplayData:
        """獲取世界顯示資料"""
        spaces = []
        items = []
        npcs = []
        
        # 收集空間資料
        for space in self.world_manager.get_all_spaces():
            spaces.append(SpaceDisplayData(
                id=space.name,
                name=space.name,
                description=space.description,
                position=Position(0, 0),  # 需要位置管理系統
                size=Size(100, 100),  # 需要大小管理系統
                connected_space_ids=[s.name for s in space.connected_spaces]
            ))
            
            # 收集該空間的物品
            for item in space.items:
                if item.position:
                    items.append(ItemDisplayData(
                        id=item.name,
                        name=item.name,
                        description=item.description,
                        position=Position(item.position[0], item.position[1]),
                        size=Size(item.size[0], item.size[1]) if item.size else None,
                        space_id=space.name
                    ))
        
        # 收集 NPC 資料
        for npc in self.npc_manager.get_all_npcs():
            npc_state = NPCState.THINKING if npc.current_state == "thinking" else NPCState.IDLE
            npcs.append(NPCDisplayData(
                id=npc.name,
                name=npc.name,
                description=npc.description,
                position=Position(npc.position[0], npc.position[1]) if npc.position else Position(0, 0),
                state=npc_state,
                current_space_id=npc.current_space.name,
                inventory_count=npc.inventory.get_item_count()
            ))
        
        return WorldDisplayData(
            world_name=self.world_name,
            current_time=self.time_manager.get_formatted_time(),
            day_count=self.time_manager.world_day,
            weather=self.time_manager.weather,
            spaces=spaces,
            items=items,
            npcs=npcs
        )
    
    def get_npc_display_data(self, npc_id: str) -> NPCDisplayData:
        """獲取特定 NPC 的顯示資料"""
        npc = self.npc_manager.get_npc(npc_id)
        if not npc:
            raise NPCNotFoundError(f"NPC '{npc_id}' not found")
        
        npc_state = NPCState.THINKING if npc.current_state == "thinking" else NPCState.IDLE
        
        return NPCDisplayData(
            id=npc.name,
            name=npc.name,
            description=npc.description,
            position=Position(npc.position[0], npc.position[1]) if npc.position else Position(0, 0),
            state=npc_state,
            current_space_id=npc.current_space.name,
            inventory_count=npc.inventory.get_item_count()
        )
    
    def process_user_input(self, user_input: UserInput) -> AIResponse:
        """處理使用者輸入"""
        try:
            npc = self.npc_manager.get_npc(user_input.npc_id)
            if not npc:
                raise NPCNotFoundError(f"NPC '{user_input.npc_id}' not found")
            
            # 處理輸入
            result = npc.process_tick(user_input.content, self)
            
            return AIResponse(
                npc_id=user_input.npc_id,
                response_type="text",
                content=result,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            raise AIProcessingError(str(e))
    
    def trigger_npc_action(self, npc_id: str) -> AIResponse:
        """觸發 NPC 自主行動"""
        try:
            npc = self.npc_manager.get_npc(npc_id)
            if not npc:
                raise NPCNotFoundError(f"NPC '{npc_id}' not found")
            
            # 觸發 NPC 思考
            result = npc.process_tick(None, self)
            
            return AIResponse(
                npc_id=npc_id,
                response_type="action",
                content=result,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error triggering NPC action: {e}")
            raise AIProcessingError(str(e))
    
    def get_npc_history(self, npc_id: str) -> HistoryData:
        """獲取 NPC 的歷史記錄"""
        npc = self.npc_manager.get_npc(npc_id)
        if not npc:
            raise NPCNotFoundError(f"NPC '{npc_id}' not found")
        
        entries = []
        for msg in npc.history:
            entries.append(HistoryEntry(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp", "")
            ))
        
        return HistoryData(
            npc_id=npc_id,
            entries=entries,
            total_count=len(entries)
        )
    
    def save_world(self, filepath: str) -> bool:
        """儲存世界狀態"""
        try:
            world_data = {
                "world_name": self.world_name,
                "description": self.world_description,
                "time": self.time_manager.to_dict(),
                "spaces_data": self.world_manager.to_dict()["spaces"],
                "items_data": self.world_manager.to_dict()["items"],
                "npcs_data": self.npc_manager.to_dict()
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(world_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"World saved to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving world: {e}")
            return False
    
    def set_active_npc(self, npc_id: str):
        """設定活躍的 NPC"""
        if self.npc_manager.get_npc(npc_id):
            self.active_npc_id = npc_id
        else:
            raise NPCNotFoundError(f"NPC '{npc_id}' not found")
    
    # ========== InteractionProcessor 需要的方法 ==========
    
    def process_interaction(self, npc: NPC, target_item: str, 
                           inventory_items: List[str], interaction_type: str) -> str:
        """
        處理 NPC 與物品的互動
        
        這個方法會被 InteractionProcessor 呼叫
        """
        return self.interaction_processor.process_interaction(
            npc, target_item, inventory_items, interaction_type
        )