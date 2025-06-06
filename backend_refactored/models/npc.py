"""
NPC Model - NPC 資料模型

定義 NPC 的核心邏輯，專注於 AI 行為而非顯示。
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple, Union, Literal, Any, TYPE_CHECKING
from openai import OpenAI
import logging

if TYPE_CHECKING:
    from .space import Space
    from .inventory import Inventory
    from ..ai_system import AI_System

# 設定 logger
logger = logging.getLogger(__name__)

# OpenAI client
client = OpenAI()


class NPC(BaseModel):
    """
    NPC 類別
    
    代表一個具有 AI 能力的非玩家角色。
    """
    name: str
    description: str
    current_space: "Space"
    inventory: "Inventory"
    history: List[Dict[str, str]] = Field(default_factory=list)
    
    # NPC 狀態
    first_tick: bool = True
    current_state: str = "idle"  # idle, thinking, talking, moving, interacting
    
    # 位置和移動相關（邏輯用途）
    position: Optional[Tuple[int, int]] = None
    movement_speed: float = 1.0
    target_position: Optional[Tuple[int, int]] = None
    
    # AI 相關屬性
    personality: Dict[str, Any] = Field(default_factory=dict)
    goals: List[str] = Field(default_factory=list)
    current_goal: Optional[str] = None
    memory_limit: int = 50  # 歷史記錄上限
    
    # 行動定義
    class EnterSpaceAction(BaseModel):
        action_type: Literal["enter_space"]
        target_space: str
    
    class TalkToNPCAction(BaseModel):
        action_type: Literal["talk_to_npc"]
        target_npc: str
        dialogue: str
    
    class InteractItemAction(BaseModel):
        action_type: Literal["interact_item"]
        interact_with: str
        how_to_interact: str
        inventory_item_1: Optional[str] = None
        inventory_item_2: Optional[str] = None
        inventory_item_3: Optional[str] = None
        inventory_item_4: Optional[str] = None
        inventory_item_5: Optional[str] = None
    
    class NPCGeneralResponse(BaseModel):
        npc_observation: str = Field(description="NPC 對當前環境和狀況的觀察")
        self_talk_reasoning: str = Field(description="NPC 的內心想法和推理過程")
        action: Optional[Union[EnterSpaceAction, TalkToNPCAction, InteractItemAction]] = None
    
    def update_schema(self):
        """
        動態更新 AI 的 response schema
        
        Returns:
            更新後的 schema 類別
        """
        # 獲取可用的空間、NPC 和物品
        available_spaces = Literal[tuple(self.current_space.get_connected_space_names())]
        available_npcs = Literal[tuple(self.current_space.get_npcs_names())]
        available_items = Literal[tuple(self.current_space.get_items_names())]
        inventory_items = Literal[tuple(self.inventory.get_item_names())] if self.inventory.items else str
        
        # 動態建立 Action 類別
        class DynamicEnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: available_spaces
        
        class DynamicTalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: available_npcs
            dialogue: str
        
        class DynamicInteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            interact_with: available_items
            how_to_interact: str
            inventory_item_1: Optional[inventory_items] = None
            inventory_item_2: Optional[inventory_items] = None
            inventory_item_3: Optional[inventory_items] = None
            inventory_item_4: Optional[inventory_items] = None
            inventory_item_5: Optional[inventory_items] = None
        
        # 建立可用的 action 類型
        action_types = []
        if self.current_space.connected_spaces:
            action_types.append(DynamicEnterSpaceAction)
        if self.current_space.npcs and len(self.current_space.npcs) > 1:
            action_types.append(DynamicTalkToNPCAction)
        if self.current_space.items:
            action_types.append(DynamicInteractItemAction)
        
        # 動態 Response 類別
        class DynamicNPCResponse(BaseModel):
            npc_observation: str = Field(description="NPC 對當前環境和狀況的觀察")
            self_talk_reasoning: str = Field(description="NPC 的內心想法和推理過程")
            action: Optional[Union[tuple(action_types)]] = None if action_types else None
        
        return DynamicNPCResponse
    
    def add_space_to_history(self):
        """將當前空間資訊加入歷史記錄"""
        space_info = str(self.current_space)
        self.history.append({"role": "system", "content": space_info})
    
    def process_tick(self, user_input: Optional[str] = None, ai_system: Optional["AI_System"] = None):
        """
        處理一個 AI tick
        
        Args:
            user_input: 使用者輸入（如果有）
            ai_system: AI 系統實例
            
        Returns:
            AI 回應結果
        """
        try:
            # 更新 schema
            NPCGeneralResponse = self.update_schema()
            
            # 首次 tick 時加入空間資訊
            if self.first_tick:
                self.add_space_to_history()
                self.first_tick = False
            
            # 加入使用者輸入到歷史
            if user_input:
                self.history.append({"role": "user", "content": f"User: {user_input}"})
            
            # 設定狀態為思考中
            self.current_state = "thinking"
            
            # 呼叫 OpenAI API
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-11-20",
                messages=self.history,
                response_format=NPCGeneralResponse
            )
            response_parsed = completion.choices[0].message.parsed
            
            logger.info(f"NPC {self.name} AI Response: {response_parsed}")
            
            # 處理回應
            if not response_parsed.action:
                memory = f"{response_parsed.self_talk_reasoning}\n沒有執行動作"
                self.history.append({"role": "assistant", "content": memory})
                self.current_state = "idle"
                return memory
            
            # 處理不同類型的動作
            action = response_parsed.action
            result = ""
            
            if hasattr(action, "action_type"):
                if action.action_type == "interact_item" and ai_system:
                    # 收集物品欄物品
                    inventory_items = []
                    for attr in ["inventory_item_1", "inventory_item_2", "inventory_item_3", 
                               "inventory_item_4", "inventory_item_5"]:
                        if hasattr(action, attr) and getattr(action, attr):
                            inventory_items.append(getattr(action, attr))
                    
                    self.current_state = "interacting"
                    result = ai_system.process_interaction(
                        self,
                        action.interact_with,
                        inventory_items,
                        action.how_to_interact
                    )
                
                elif action.action_type == "enter_space":
                    self.current_state = "moving"
                    result = self.move_to_space(action.target_space)
                
                elif action.action_type == "talk_to_npc":
                    self.current_state = "talking"
                    result = self.talk_to_npc(action.target_npc, action.dialogue)
            
            # 更新歷史記錄
            memory = f"{response_parsed.self_talk_reasoning}\n執行動作結果：{result}"
            self.history.append({"role": "assistant", "content": memory})
            
            # 限制歷史記錄長度
            if len(self.history) > self.memory_limit:
                # 保留系統訊息和最新的記錄
                system_messages = [h for h in self.history if h["role"] == "system"][:2]
                recent_messages = self.history[-(self.memory_limit - len(system_messages)):]
                self.history = system_messages + recent_messages
            
            # 恢復狀態
            self.current_state = "idle"
            return memory
            
        except Exception as e:
            logger.error(f"Error in NPC {self.name} process_tick: {e}")
            self.current_state = "idle"
            raise
    
    def move_to_space(self, target_space_name: str) -> str:
        """
        移動到另一個空間
        
        Args:
            target_space_name: 目標空間名稱
            
        Returns:
            移動結果描述
        """
        # 檢查目標空間是否連接
        for space in self.current_space.connected_spaces:
            if space.name == target_space_name:
                # 從當前空間移除
                self.current_space.remove_npc(self)
                # 移動到新空間
                self.current_space = space
                space.add_npc(self)
                # 重置首次 tick 標記
                self.first_tick = True
                return f"{self.name} 移動到了 {target_space_name}。"
        
        return f"無法移動到 {target_space_name}，該空間不可達。"
    
    def talk_to_npc(self, target_npc_name: str, dialogue: str) -> str:
        """
        與另一個 NPC 對話
        
        Args:
            target_npc_name: 目標 NPC 名稱
            dialogue: 對話內容
            
        Returns:
            對話結果
        """
        # 找到目標 NPC
        for npc in self.current_space.npcs:
            if npc.name == target_npc_name and npc != self:
                # 將對話記錄到兩個 NPC 的歷史中
                npc.history.append({
                    "role": "user", 
                    "content": f"{self.name} 對你說: {dialogue}"
                })
                return f"{self.name} 對 {target_npc_name} 說: '{dialogue}'"
        
        return f"找不到名為 {target_npc_name} 的 NPC。"
    
    def get_state_for_display(self) -> Dict[str, Any]:
        """
        獲取用於顯示的狀態資訊
        
        Returns:
            包含顯示所需資訊的字典
        """
        return {
            "id": self.name,  # 使用 name 作為 ID
            "name": self.name,
            "state": self.current_state,
            "position": self.position,
            "current_space": self.current_space.name,
            "inventory_count": self.inventory.get_item_count(),
            "has_goal": self.current_goal is not None
        }