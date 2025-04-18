import threading
import time
import json
from typing import Optional
import os
from detecct_item import load_save_data, detect_items_in_space, get_interactive_items

from openai import OpenAI

from npc_manager import NPC

# 初始化OpenAI客戶端
client = OpenAI()

# 指定要使用的模型名稱
GPT_MODEL = "gpt-4.1-mini"  # gpt-4.1-mini 對應的API名稱，若未來官方更名請更新

# 使用者自訂 System Prompt（可於此自訂）
USER_CUSTOM_PROMPT = """你是一個遊戲中的 NPC，請根據遊戲規則與角色個性做出合理行動。"""

class AIThinking:
    def __init__(self, npc, buttons, thinking_lock, space_positions=None, space_size=None):
        self.npc = npc
        self.buttons = buttons if buttons is not None else []
        self.thinking_lock = thinking_lock
        self.thinking_result = ""
        self.thinking = False
        self.mouse_disabled = False
        self.processing_action = False
        self.space_positions = space_positions
        self.space_size = space_size
        self.last_action_time = time.time()
        # 你可以根據需要初始化 space_history、target_pos 等

    def _think_action(self):
        """NPC思考線程"""
        try:
            result = self.process_tick()
            
            # 使用鎖來安全地設置思考結果
            with self.thinking_lock:
                self.thinking_result = result
                self.npc.thinking_result = result  # 更新本地 NPC 的思考結果
                self.mouse_disabled = False
                self.processing_action = False
                self.thinking = False
                
            # ...（其餘你的邏輯不變）...
            # 這裡省略，直接貼你原本的內容即可

        except Exception as e:
            print(f"思考線程出錯: {str(e)}")
            with self.thinking_lock:
                self.mouse_disabled = False
                self.thinking = False
                self.processing_action = False
                

    def process_tick(self, user_input: Optional[str] = None):
        """
        處理NPC行為的單個時間單位。
        
        Args:
            user_input: 來自用戶的可選輸入
            
        Returns:
            描述NPC行動結果的字符串
        """
        # 第一個tick時，添加初始空間信息
        if self.npc.first_tick:
            self.npc.add_space_to_history()
            self.npc.first_tick = False
        
        # 如果有用戶輸入，將其添加到歷史記錄
        if user_input:
            self.npc.history.append({"role": "user", "content": user_input})
        
        # 取得目前 NPC 所在空間
        current_space = self.npc.get_current_space(self.space_positions, self.space_size)
        print(f"目前所在空間: {current_space}")

        if not current_space or current_space == "Unknown":
            current_space = "living_room"

        # 載入 new_save.json
        save_path = os.path.join(os.path.dirname(__file__), "worlds", "new_save.json")  # 載入 save_data
        save_data = load_save_data(save_path)

        # 取得目前空間內所有物品
        # 直接用 detecct_item.py 提供的函式取得可互動物品
        items_in_space = detect_items_in_space(current_space, save_data)
        print("所有物品:", [item.get("name") for item in items_in_space])
        # 只保留有 interactions 且非空的物品，這些才是真正可互動物品
        interactive_items = [item for item in items_in_space if 'interactions' in item and isinstance(item['interactions'], dict) and len(item['interactions']) > 0]
        self.npc.available_items = interactive_items    # 將可互動物品存進 self.npc 或其他屬性，供 AI 判斷使用

        # 獲取當前模式
        schema = self.npc.update_schema()
        
        # 每次都重建完整的 system prompt，包含自訂內容與 schema
        # 直接用 self.npc.available_items 產生物品描述
        def get_item_interaction_desc(item):
            if 'interactions' in item and isinstance(item['interactions'], dict) and item['interactions']:
                actions = list(item['interactions'].keys()) # 取得所有可互動動作
                return f"{item.get('name', '未知物品')}（可{ '、'.join(actions) }）"
            else:
                return item.get('name', '未知物品')
        items_desc = '，'.join([get_item_interaction_desc(item) for item in self.npc.available_items]) # 只取可互動物品
        print(f"可互動物品: {items_desc}")
        
        system_prompt = (
            USER_CUSTOM_PROMPT + "\n"
            "你是一個遊戲中的NPC，你只能進行以下動作: "
            f"{schema['actions']}。\n"
            "你目前所在的空間為: "
            f"{schema['spaces'][0]}。\n"
            f"你可以互動的物品有: {items_desc}。\n"
            "當 action_type 為 'interact_item' 時，必須指定 target_item。\n"
            "你是一個好奇的 NPC，請優先與物品互動，如果沒有物品可互動時再考慮移動空間。\n"
        )
        # 將這個系統提示加入歷史記錄（每次都加）
        self.npc.history.append({"role": "system", "content": system_prompt})
        
        # 使用OpenAI API獲取NPC的下一步行動
        try:
            # 添加調試輸出
            print("\n=== AI 請求 ===")
            print(f"模型: {GPT_MODEL}")
            print(f"歷史記錄長度: {len(self.npc.history)}")
            print("=================\n")

            # 修正：直接使用正確的 function schema
            functions = [
                {
                    "name": "decide_action",
                    "description": "Decides the next action for the NPC.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action_type": {"type": "string"},
                            "target": {"type": "string", "default": ""},
                            "target_space": {"type": "string", "default": ""},
                            "target_npc": {"type": "string", "default": ""},
                            "dialogue": {"type": "string", "default": ""},
                            "target_item": {"type": "string", "default": ""}
                        },
                        "required": ["properties", "action_type", "target_item"]
                    }
                }
            ]

            response = client.chat.completions.create(
                model=GPT_MODEL,
                messages=self.npc.history,
                functions=functions,
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
            self.npc.history.append({
                "role": "assistant", 
                "content": f"思考: {reasoning}"
            })
            
            # 處理不同類型的動作
            action_data = function_args
            print(action_data)

            # 如果沒有動作
            if not action_data:
                self.npc.history.append({"role": "system", "content": "沒有採取任何動作。"})
                return "沒有發生任何事情。"
            
            action_type = function_args.get("action_type", "")
            result = ""
            
            try:
                # 僅允許三種動作: 進入空間、與NPC交談、與物品互動
                if action_type == "enter_space":
                    target_space = function_args.get("target_space", "")
                    self.npc.target_space = target_space
                    result = self.npc.move_to_space(target_space)
                    self.npc.add_space_to_history()
                elif action_type == "talk_to_npc":
                    target_npc = function_args.get("target_npc", "")
                    dialogue = function_args.get("dialogue", "")
                    result = self.npc.talk_to_npc(target_npc, dialogue)
                elif action_type == "interact_item":
                    target_item = function_args.get("target_item", "")  # 互動物品
                    print(f"互動物品: {target_item}")
                    self.npc.item_name = target_item if target_item else ""
                    available_items = getattr(self.npc, "available_items", [])
                    item_list = [item['name'] for item in available_items]
                    if self.npc.item_name:
                        # 假設 interact_with_item 需要 dict 格式
                        result = self.npc.interact_with_item({self.npc.item_name: {}})
                    else:
                        print("未指定互動物品，請檢查 AI 回傳內容")
                else:
                    result = f"{self.npc.name} 正在思考..."
            except Exception as inner_e:
                import traceback
                tb = traceback.format_exc()
                print(tb)
            
            # 將結果添加到歷史記錄
            self.npc.history.append({"role": "system", "content": result})
            
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
