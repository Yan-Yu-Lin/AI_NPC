"""
Interaction Processor - 互動處理器

處理 NPC 與世界的各種互動，包括物品操作、空間互動等。
"""

from typing import List, Optional, Dict, Any, TYPE_CHECKING
from pydantic import BaseModel, Field
from openai import OpenAI
import logging

from .models import Item, NPC

if TYPE_CHECKING:
    from .ai_system import AI_System

logger = logging.getLogger(__name__)
client = OpenAI()


class InteractionProcessor:
    """
    互動處理器
    
    負責處理所有 NPC 與世界的互動邏輯。
    """
    
    def __init__(self):
        """初始化互動處理器"""
        self.ai_system: Optional["AI_System"] = None
        self.pending_interactions: List[Dict[str, Any]] = []
        
    def initialize(self, ai_system: "AI_System"):
        """
        初始化互動處理器
        
        Args:
            ai_system: AI 系統實例
        """
        self.ai_system = ai_system
        logger.info("InteractionProcessor initialized")
    
    def process_interaction(self, npc: NPC, target_item: str, 
                          inventory_items: List[str], interaction_type: str) -> str:
        """
        處理 NPC 與物品的互動
        
        Args:
            npc: 執行互動的 NPC
            target_item: 目標物品名稱
            inventory_items: 使用的物品欄物品
            interaction_type: 互動類型描述
            
        Returns:
            互動結果描述
        """
        try:
            logger.info(f"Processing interaction: {npc.name} -> {target_item}")
            
            # 收集可用物品
            available_items = self._collect_available_items(npc, target_item, inventory_items)
            
            # 生成動態 schema
            GeneralResponse = self._update_schema(available_items, npc.inventory.get_item_names())
            
            # 準備 prompt
            prompt = self._prepare_interaction_prompt(npc, target_item, inventory_items, interaction_type)
            
            # 呼叫 AI 處理互動
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-11-20",
                messages=[{"role": "system", "content": prompt}],
                response_format=GeneralResponse
            )
            
            response = completion.choices[0].message.parsed
            
            # 處理 AI 回應
            result = self._handle_ai_response(response, npc, available_items)
            
            logger.info(f"Interaction result: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in process_interaction: {e}")
            return f"互動失敗: {str(e)}"
    
    def _collect_available_items(self, npc: NPC, target_item: str, 
                               inventory_items: List[str]) -> List[str]:
        """收集本次互動涉及的所有物品"""
        items = [target_item]
        items.extend(inventory_items)
        return list(set(items))  # 去重
    
    def _prepare_interaction_prompt(self, npc: NPC, target_item: str,
                                  inventory_items: List[str], interaction_type: str) -> str:
        """準備互動 prompt"""
        inventory_str = ", ".join(inventory_items) if inventory_items else "無"
        
        return f"""你是一個負責處理物品互動的 AI 系統。

NPC {npc.name} 想要對 {target_item} 執行以下操作：
{interaction_type}

使用的物品欄物品：{inventory_str}

請根據這個互動的邏輯性和合理性，決定：
1. 這個互動是否可能成功
2. 如果成功，會產生什麼結果（創建新物品、修改物品狀態等）
3. 提供詳細的互動結果描述

請考慮物理定律、常識和遊戲世界的邏輯。"""
    
    def _update_schema(self, available_items: List[str], inventory_items: List[str]):
        """動態生成互動 schema"""
        from typing import Literal
        
        # 準備動態類型
        ItemLiteral = Literal[tuple(available_items)] if available_items else str
        InventoryLiteral = Literal[tuple(inventory_items)] if inventory_items else str
        
        class ModifyWorldItemsFunction(BaseModel):
            function_type: Literal["modify_world_items"] = Field("modify_world_items")
            
            # 刪除物品
            delete_item_1: Optional[ItemLiteral] = None
            delete_item_2: Optional[ItemLiteral] = None
            delete_item_3: Optional[ItemLiteral] = None
            
            # 創建物品
            create_item_1_name: Optional[str] = None
            create_item_1_description: Optional[str] = None
            create_item_2_name: Optional[str] = None
            create_item_2_description: Optional[str] = None
        
        class ChangeItemDescriptionFunction(BaseModel):
            function_type: Literal["change_item_description"] = Field("change_item_description")
            item_name: ItemLiteral
            new_description: str
        
        class MoveItemToInventoryFunction(BaseModel):
            function_type: Literal["move_item_to_inventory"] = Field("move_item_to_inventory")
            item_name: ItemLiteral
        
        class MoveItemFromInventoryFunction(BaseModel):
            function_type: Literal["move_item_from_inventory"] = Field("move_item_from_inventory")
            item_name: InventoryLiteral
        
        # 通用回應
        from typing import Union
        
        class GeneralResponse(BaseModel):
            world_observation: str = Field(description="對互動情況的觀察和理解")
            reasoning: str = Field(description="互動邏輯的推理過程")
            success: bool = Field(description="互動是否成功")
            result_description: str = Field(description="互動結果的詳細描述")
            function: Optional[Union[
                ModifyWorldItemsFunction,
                ChangeItemDescriptionFunction,
                MoveItemToInventoryFunction,
                MoveItemFromInventoryFunction
            ]] = None
        
        return GeneralResponse
    
    def _handle_ai_response(self, response: Any, npc: NPC, available_items: List[str]) -> str:
        """處理 AI 回應並執行相應操作"""
        if not response.success:
            return response.result_description
        
        # 如果有函數調用，執行它
        if response.function:
            function_result = self._execute_function(response.function, npc, available_items)
            return f"{response.result_description}\n{function_result}"
        
        return response.result_description
    
    def _execute_function(self, function: Any, npc: NPC, available_items: List[str]) -> str:
        """執行互動函數"""
        function_type = function.function_type
        
        if function_type == "modify_world_items":
            return self._modify_world_items(function, npc, available_items)
        elif function_type == "change_item_description":
            return self._change_item_description(function, npc, available_items)
        elif function_type == "move_item_to_inventory":
            return self._move_item_to_inventory(function, npc, available_items)
        elif function_type == "move_item_from_inventory":
            return self._move_item_from_inventory(function, npc)
        
        return "未知的函數類型"
    
    def _modify_world_items(self, function: Any, npc: NPC, available_items: List[str]) -> str:
        """修改世界物品（刪除/創建）"""
        results = []
        
        # 刪除物品
        for i in range(1, 4):
            item_name = getattr(function, f"delete_item_{i}", None)
            if item_name:
                # 從空間或物品欄移除
                if npc.current_space.remove_item(item_name):
                    results.append(f"從空間移除了 {item_name}")
                elif npc.inventory.has_item(item_name):
                    npc.inventory.remove_item(item_name)
                    results.append(f"從物品欄移除了 {item_name}")
        
        # 創建物品
        for i in range(1, 3):
            item_name = getattr(function, f"create_item_{i}_name", None)
            item_desc = getattr(function, f"create_item_{i}_description", None)
            
            if item_name and item_desc:
                new_item = Item(name=item_name, description=item_desc)
                npc.current_space.add_item(new_item)
                self.ai_system.world_manager.add_item(new_item)
                results.append(f"創建了新物品: {item_name}")
        
        return "\n".join(results) if results else "沒有物品被修改"
    
    def _change_item_description(self, function: Any, npc: NPC, available_items: List[str]) -> str:
        """修改物品描述"""
        item_name = function.item_name
        new_description = function.new_description
        
        # 在世界中尋找物品
        item = self.ai_system.world_manager.get_item(item_name)
        if item:
            item.description = new_description
            return f"{item_name} 的描述已更新"
        
        return f"找不到物品 {item_name}"
    
    def _move_item_to_inventory(self, function: Any, npc: NPC, available_items: List[str]) -> str:
        """將物品移到物品欄"""
        item_name = function.item_name
        
        # 從空間移除物品
        item = npc.current_space.remove_item(item_name)
        if item:
            result = npc.inventory.add_item(item)
            return result
        
        return f"空間中找不到 {item_name}"
    
    def _move_item_from_inventory(self, function: Any, npc: NPC) -> str:
        """從物品欄移出物品"""
        item_name = function.item_name
        
        # 從物品欄獲取物品
        item = npc.inventory.get_item(item_name)
        if item:
            npc.inventory.remove_item(item_name)
            npc.current_space.add_item(item)
            return f"將 {item_name} 放置在 {npc.current_space.name}"
        
        return f"物品欄中找不到 {item_name}"
    
    def add_pending_interaction(self, interaction: Dict[str, Any]):
        """添加待處理的互動"""
        self.pending_interactions.append(interaction)
    
    def process_pending_interactions(self):
        """處理所有待處理的互動"""
        while self.pending_interactions:
            interaction = self.pending_interactions.pop(0)
            # 處理互動
            logger.info(f"Processing pending interaction: {interaction}")
            # 實際處理邏輯...