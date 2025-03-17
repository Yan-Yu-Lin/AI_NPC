"""
NPC類
處理NPC的行為和狀態
"""

import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple

from openai import OpenAI

# 初始化OpenAI客戶端
client = OpenAI()

# 導入相關模塊
from core.base_models import BaseEntity
from spaces.space import Space
from inventory.inventory import Inventory

class NPC(BaseEntity):
    """
    表示遊戲中的NPC（非玩家角色）。
    處理NPC的行為、狀態和交互。
    """
    
    def __init__(self, name: str, description: str, personality: str = None, knowledge: Dict[str, str] = None):
        """
        初始化一個新的NPC。
        
        Args:
            name: NPC的名稱
            description: NPC的描述
            personality: NPC的性格描述
            knowledge: NPC擁有的知識
        """
        super().__init__(name, description)
        self.personality = personality or "友好且樂於助人"
        self.knowledge = knowledge or {}
        self.current_space = None
        self.inventory = Inventory()
        self.history = []
        
        # 添加初始系統提示
        self.history.append({
            "role": "system",
            "content": f"你是 {name}。{description}。你的性格：{self.personality}。在每一步，考慮你已知的信息，你能採取的行動，並選擇做出最好的決定。"
        })
        
        # 跟踪這是否是第一個tick
        self.first_tick = True
    
    def update_schema(self):
        """
        根據NPC的當前狀態動態生成模式。
        返回帶有適當動作模式的GeneralResponse模型。
        """
        # 獲取當前可用的空間名稱
        valid_spaces = [space.name for space in self.current_space.connected_spaces]
        
        # 獲取當前空間中的NPC名稱（排除自己）
        valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
        
        # 獲取當前空間中的物品及其互動方式
        space_items = {}
        for item in self.current_space.items:
            space_items[item.name] = item.interactions
        
        # 獲取庫存中的物品及其互動方式
        inventory_items = {}
        for item in self.inventory.items:
            inventory_items[item.name] = item.interactions
        
        # 合併所有可用物品
        all_items = {**space_items, **inventory_items}
        
        # 創建動態模式
        schema = {
            "type": "object",
            "properties": {
                "self_talk_reasoning": {
                    "type": "string",
                    "description": "你對接下來該做什麼的內部推理"
                },
                "action": {
                    "type": "object",
                    "oneOf": []
                }
            },
            "required": ["self_talk_reasoning", "action"]
        }
        
        # 添加進入空間的動作模式
        if valid_spaces:
            enter_space_schema = {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["enter_space"]},
                    "target_space": {"type": "string", "enum": valid_spaces}
                },
                "required": ["action_type", "target_space"]
            }
            schema["properties"]["action"]["oneOf"].append(enter_space_schema)
        
        # 添加與NPC交談的動作模式
        if valid_npcs:
            talk_to_npc_schema = {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["talk_to_npc"]},
                    "target_npc": {"type": "string", "enum": valid_npcs},
                    "dialogue": {"type": "string"}
                },
                "required": ["action_type", "target_npc", "dialogue"]
            }
            schema["properties"]["action"]["oneOf"].append(talk_to_npc_schema)
        
        # 添加與物品互動的動作模式 - 使與demo_preview_alpha_nighty_RC2.py更一致
        if all_items:
            # 為每個物品創建互動選項
            item_interaction_options = {}
            for item_name, interactions in all_items.items():
                interaction_schema = {}
                for interaction_name, params in interactions.items():
                    if params:
                        param_props = {}
                        for param_name, param_type in params.items():
                            # 簡化參數類型處理
                            param_schema_type = "string"  # 預設為字符串
                            if param_type == int:
                                param_schema_type = "integer"
                            elif param_type == bool:
                                param_schema_type = "boolean"
                            elif param_type == float:
                                param_schema_type = "number"
                            
                            param_props[param_name] = {"type": param_schema_type}
                        
                        interaction_schema[interaction_name] = {"type": "object", "properties": param_props}
                    else:
                        interaction_schema[interaction_name] = {"type": "null"}
                
                item_interaction_options[item_name] = interaction_schema
            
            # 創建物品互動的主模式
            interact_item_schema = {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["interact_item"]},
                    "target_item": {"type": "object"}
                },
                "required": ["action_type", "target_item"]
            }
            
            # 為每個物品添加可能的互動
            item_properties = {}
            for item_name, interactions in item_interaction_options.items():
                item_properties[item_name] = {
                    "type": "object",
                    "properties": interactions,
                    "additionalProperties": False
                }
            
            interact_item_schema["properties"]["target_item"]["properties"] = item_properties
            interact_item_schema["properties"]["target_item"]["additionalProperties"] = False
            
            schema["properties"]["action"]["oneOf"].append(interact_item_schema)
        
        return schema
    
    def add_space_to_history(self):
        """
        將當前空間的信息（通過__str__）添加到NPC的歷史記錄中。
        """
        space_info = str(self.current_space)
        self.history.append({"role": "system", "content": space_info})
    
    def print_current_schema(self):
        """
        打印AI工作的實際模式
        """
        schema = self.update_schema()
        print(json.dumps(schema, indent=2))
    
    def move_to_space(self, target_space_name: str):
        """
        如果有效，將NPC移動到連接的空間，並更新空間的NPC列表。
        """
        # 檢查目標空間是否與當前空間相連
        target_space = None
        for space in self.current_space.connected_spaces:
            if space.name == target_space_name:
                target_space = space
                break
        
        if not target_space:
            return f"{self.name} 嘗試前往 {target_space_name}，但無法到達。"
        
        # 從當前空間的NPC列表中移除
        if self in self.current_space.npcs:
            self.current_space.npcs.remove(self)
        
        # 移動到新空間並添加到其NPC列表中
        self.current_space = target_space
        if self not in self.current_space.npcs:
            self.current_space.npcs.append(self)
        
        return f"{self.name} 前往了 {self.current_space.name}。"
    
    def process_tick(self, user_input: Optional[str] = None):
        """
        處理NPC行為的單個時間單位。
        
        Args:
            user_input: 來自用戶的可選輸入
            
        Returns:
            描述NPC行動結果的字符串
        """
        # 第一個tick時，添加初始空間信息
        if self.first_tick:
            self.add_space_to_history()
            self.first_tick = False
        
        # 如果有用戶輸入，將其添加到歷史記錄
        if user_input:
            self.history.append({"role": "user", "content": user_input})
        
        # 獲取當前模式
        schema = self.update_schema()
        
        # 使用OpenAI API獲取NPC的下一步行動
        try:
            # 添加調試輸出
            print("\n=== AI 請求 ===")
            print(f"模型: gpt-4o-2024-11-20")
            print(f"歷史記錄長度: {len(self.history)}")
            print("=================\n")
            
            response = client.chat.completions.create(
                model="gpt-4o-2024-11-20",
                messages=self.history,
                functions=[{"name": "decide_action", "parameters": schema}],
                function_call={"name": "decide_action"}
            )
            
            # 解析響應
            function_args = json.loads(response.choices[0].message.function_call.arguments)
            
            # 添加調試輸出
            print("\n=== AI 回應 ===")
            print(json.dumps(function_args, indent=2, ensure_ascii=False))
            print("=================\n")
            
            # 將AI的思考過程添加到歷史記錄
            reasoning = function_args.get("self_talk_reasoning", "")
            self.history.append({
                "role": "assistant", 
                "content": f"思考: {reasoning}"
            })
            
            # 處理不同類型的動作
            action_data = function_args.get("action", {})
            
            # 如果沒有動作
            if not action_data:
                self.history.append({"role": "system", "content": "沒有採取任何動作。"})
                return "沒有發生任何事情。"
            
            action_type = action_data.get("action_type")
            result = ""
            
            try:
                if action_type == "enter_space":
                    # 移動到新空間
                    target_space = action_data.get("target_space")
                    result = self.move_to_space(target_space)
                    # 添加新空間信息到歷史記錄
                    self.add_space_to_history()
                
                elif action_type == "talk_to_npc":
                    # 與其他NPC交談
                    target_npc = action_data.get("target_npc")
                    dialogue = action_data.get("dialogue")
                    result = self.talk_to_npc(target_npc, dialogue)
                
                elif action_type == "interact_item":
                    # 與物品互動 - 使用與demo_preview_alpha_nighty_RC2.py相同的參數格式
                    target_item = action_data.get("target_item", {})
                    
                    # 構建與demo_preview_alpha_nighty_RC2.py兼容的參數格式
                    # 示例結構: {"書": {"閱讀": None}} 或 {"日記": {"寫入": {"content": "日記內容"}}}
                    item_name = list(target_item.keys())[0] if target_item else ""
                    
                    if item_name:
                        interaction_data = target_item[item_name]
                        result = self.interact_with_item({item_name: interaction_data})
                    else:
                        result = f"{self.name} 嘗試與物品互動，但未指定物品。"
                
                else:
                    result = f"{self.name} 正在思考..."
            
            except Exception as inner_e:
                import traceback
                tb = traceback.format_exc()
                print(f"處理動作時出錯，動作類型: {action_type}, 錯誤: {str(inner_e)}\n{tb}")
                result = f"處理動作時出錯: {str(inner_e)}"
            
            # 將結果添加到歷史記錄
            self.history.append({"role": "system", "content": result})
            
            # 添加調試輸出
            print("\n=== 動作結果 ===")
            print(result)
            print("=================\n")
            
            return result
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"處理NPC行為時出錯: {str(e)}\n{tb}")
            return f"處理NPC行為時出錯: {str(e)}"
    
    def talk_to_npc(self, target_npc_name: str, dialogue: str) -> str:
        """
        與當前空間中的另一個NPC交談。
        返回對話結果。
        """
        # 尋找目標NPC
        target_npc = None
        for npc in self.current_space.npcs:
            if npc.name == target_npc_name:
                target_npc = npc
                break
        
        if not target_npc:
            return f"{self.name} 嘗試與 {target_npc_name} 交談，但他們不在這裡。"
        
        # 將對話添加到目標NPC的歷史記錄中，以便他們可以回應
        target_npc.history.append({
            "role": "user", 
            "content": f"{self.name} 對你說: {dialogue}"
        })
        
        # 取得回應
        response = target_npc.process_tick()
        
        return f"{self.name} 對 {target_npc_name} 說: \"{dialogue}\"\n{response}"
    
    def interact_with_item(self, action_data: Dict[str, Dict[str, Optional[Dict[str, Any]]]]) -> str:
        """
        與物品互動。
        
        Args:
            action_data: 物品互動數據，如 {"書": {"閱讀": None}} 或 {"日記": {"寫入": {"content": "今天天氣很好"}}}
            
        Returns:
            互動結果的描述
        """
        try:
            # 從action_data提取物品名稱和互動類型
            if not action_data or not isinstance(action_data, dict):
                return f"{self.name} 嘗試與物品互動，但提供的數據無效。"
            
            # 獲取物品名稱
            item_name = list(action_data.keys())[0]
            
            # 檢查物品是否存在（在當前空間或庫存中）
            item = None
            for i in self.current_space.items:
                if i.name == item_name:
                    item = i
                    break
            
            if not item:
                for i in self.inventory.items:
                    if i.name == item_name:
                        item = i
                        break
            
            if not item:
                return f"{self.name} 嘗試與 {item_name} 互動，但找不到該物品。"
            
            # 獲取互動類型和參數
            interaction_dict = action_data[item_name]
            if not interaction_dict:
                return f"{self.name} 看著 {item_name}，但沒有採取任何行動。"
            
            interaction_type = list(interaction_dict.keys())[0]
            interaction_params = interaction_dict[interaction_type]
            
            # 檢查互動類型是否有效
            if interaction_type not in item.interactions:
                return f"{self.name} 嘗試 {interaction_type} {item_name}，但這種互動不可行。"
            
            # 執行互動
            parameter_content = None
            if interaction_params and isinstance(interaction_params, dict) and "content" in interaction_params:
                parameter_content = interaction_params["content"]
            
            # 不同類型的互動可以有不同的實現
            if interaction_type == "拿取":
                # 將物品從當前空間轉移到庫存
                self.current_space.items.remove(item)
                self.inventory.add_item(item)
                return f"{self.name} 拿取了 {item_name}。"
            
            elif interaction_type == "放置":
                # 將物品從庫存轉移到當前空間
                self.inventory.remove_item(item.name)
                self.current_space.items.append(item)
                return f"{self.name} 將 {item_name} 放在了 {self.current_space.name}。"
            
            elif interaction_type == "使用":
                action = "使用"
                result = f"{self.name} {action}了 {item_name}"
                if parameter_content:
                    result += f"，{parameter_content}"
                return result + "。"
            
            elif interaction_type == "閱讀":
                # 閱讀物品上的文字
                if hasattr(item, "content") and item.content:
                    return f"{self.name} 閱讀了 {item_name}:\n\"{item.content}\""
                else:
                    return f"{self.name} 嘗試閱讀 {item_name}，但上面沒有任何文字。"
            
            elif interaction_type == "觀察":
                # 觀察物品
                return f"{self.name} 仔細觀察了 {item_name}。\n{item.description}"
            
            elif interaction_type == "寫入":
                # 更新內容
                if parameter_content:
                    item.content = parameter_content
                    return f"{self.name} 寫在了 {item_name} 上:\n\"{parameter_content}\""
                else:
                    return f"{self.name} 嘗試在 {item_name} 上寫東西，但沒有想到要寫什麼。"
            
            else:
                # 一般互動
                action = interaction_type
                result = f"{self.name} {action}了 {item_name}"
                if parameter_content:
                    result += f"，{parameter_content}"
                return result + "。"
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"物品互動錯誤: {str(e)}\n{tb}")
            return f"與物品互動時發生錯誤: {str(e)}"
    
    def __str__(self):
        """返回NPC的字符串表示"""
        inventory_str = ""
        if self.inventory.items:
            items_str = ", ".join([item.name for item in self.inventory.items])
            inventory_str = f"\n持有物品: {items_str}"
        
        return f"{self.name}: {self.description}{inventory_str}"
