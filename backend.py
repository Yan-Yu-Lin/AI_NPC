# backend.py
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Union, Literal, List, Optional, Dict, Any, Tuple
import json
import os
import glob
import asyncio
from dataclasses import dataclass, field as dataclass_field
import heapq

client = OpenAI()

# 設定全局變量使 NPC 類可以訪問
world_system = None

def get_world_system():
    global world_system
    if world_system is None:
        world_system = AI_System()
    return world_system

#NOTE: Item

# 定義基礎 Item 類

class Item(BaseModel):
    name: str
    description: str
    # Simpler interaction definition:
    # - If value is None: no parameters needed
    # - If value is dict: specifies required parameters and their types
    properties: Dict[str, Any] = {}
    position: Optional[Tuple[int, int]] = None  # 允許 None，代表未指定
    size: Optional[Tuple[int, int]] = None      # 允許 None，代表未指定


#NOTE: Space 空間 class

# 對話事件資料結構
class ConversationEvent(BaseModel):
    priority: int = Field(..., description="事件優先級，數字越小優先處理")
    timestamp: float = Field(..., description="事件產生的時間戳")
    speaker: str = Field(..., description="發話者名稱")
    target: str = Field(..., description="目標 NPC 名稱")
    message: str = Field(..., description="對話內容")
    extra: dict = Field(default_factory=dict, description="額外資訊")

    def __lt__(self, other):
        # heapq 需要 __lt__ 來比較優先級
        if not isinstance(other, ConversationEvent):
            return NotImplemented
        # 先比 priority，再比 timestamp
        return (self.priority, self.timestamp) < (other.priority, other.timestamp)

class ConversationManager(BaseModel):
    space_name: str = Field(..., description="空間名稱")
    queue: list = Field(default_factory=list, description="對話事件的優先佇列（heapq）")
    
    # _lock 和 _running 屬於 runtime 狀態，不序列化
    # 用 __init__ 動態初始化
    def __init__(self, **data):
        super().__init__(**data)
        self._lock = asyncio.Lock()
        self._running = False

    async def add_conversation(self, event: ConversationEvent):  # Add event to queue
        async with self._lock:  # Thread-safe
            heapq.heappush(self.queue, event)   # Add event to priority queue

    async def run(self):  # Run the event loop
        self._running = True
        while self._running:
            await asyncio.sleep(0)  # yield control
            event = None
            async with self._lock:  # Thread-safe
                if self.queue:
                    event = heapq.heappop(self.queue)
            if event:
                await self.handle_event(event)
            else:
                await asyncio.sleep(0.05)  # idle

    async def handle_event(self, event: ConversationEvent):  # Handle a single event
        print(f"[Space: {self.space_name}] {event.speaker} 對 {event.target} 說: {event.message}")

    def stop(self):  # Stop the event loop
        self._running = False

class Space(BaseModel):
    name: str  # Space name, e.g., "kitchen" or "living_room"
    description: str  # Description of the space
    connected_spaces: List["Space"] = []  # Connected spaces (bidirectional relationships)
    items: List["Item"] = []  # Items in the space
    npcs: List["NPC"] = Field(default_factory=list)  # NPCs currently in the space
    display_pos: Tuple[int, int] = (0, 0)  # for pygame display
    display_size: Tuple[int, int] = (0, 0)  # for pygame display
    conversation_manager: Optional["ConversationManager"] = None

    model_config = {"arbitrary_types_allowed": True}

    def biconnect(self, other_space: "Space") -> None:
        """
        Establish a bidirectional connection between this space and another space.
        """
        if other_space not in self.connected_spaces:
            self.connected_spaces.append(other_space)
        if self not in other_space.connected_spaces:
            other_space.connected_spaces.append(self)

    def __str__(self) -> str:
        """
        Returns a string representation of the space, including its connections, items, and NPCs.
        """
        connected = ", ".join([space.name for space in self.connected_spaces]) if self.connected_spaces else "none"
        items = ", ".join([item.name for item in self.items]) if self.items else "none"
        npcs = ", ".join([npc.name for npc in self.npcs]) if self.npcs else "none"
        return (
            f"Space Name: {self.name}\n"
            f"Description: {self.description}\n"
            f"Connected Spaces: {connected}\n"
            f"Items in Space: {items}\n"
            f"NPCs in Space: {npcs}"
        )

#NOTE: Define Inventory
# Inventory 類
class Inventory(BaseModel):
    items: List[Item] = []  # 存放物品的列表
    capacity: Optional[int] = None  # 容量限制（可選）

    def add_item(self, item: Item) -> str:
        """
        將物品添加到 Inventory。
        """
        if self.capacity is not None and len(self.items) >= self.capacity:
            return f"Cannot add {item.name}. Inventory is full."
        self.items.append(item)
        return f"Added {item.name} to inventory."
    def remove_item(self, item_name: str) -> str:
        """
        根據物品名稱從 Inventory 中移除物品。
        """
        for i, item in enumerate(self.items):
            if item.name == item_name:
                removed_item = self.items.pop(i)
                return f"Removed {removed_item.name} from inventory."
        return f"Item with name '{item_name}' not found in inventory."


    def has_item(self, item_name: str) -> bool:
        """
        檢查 Inventory 中是否有指定名稱的物品。
        """
        return any(item.name == item_name for item in self.items)

    def list_items(self) -> str:
        """
        列出 Inventory 中的所有物品。
        """
        if not self.items:
            return "Inventory is empty."
        return "\n".join([f"- {item.name}: {item.description}" for item in self.items])

#NOTE: Define NPC
## 定義 NPC 類

class NPC(BaseModel):
    name: str
    description: str
    current_space: "Space"
    inventory: "Inventory"
    history: List[Dict[str, str]] = []
    first_tick: bool = True
    display_color: Optional[Tuple[int, int, int]] = None
    radius: Optional[int] = None
    position: Optional[Tuple[int, int]] = None
    display_pos: Optional[Tuple[int, int]] = None

    # Initial schema definitions
    class EnterSpaceAction(BaseModel):
        action_type: Literal["enter_space"]
        target_space: str = Field(description="Space to move to")

    class TalkToNPCAction(BaseModel):
        action_type: Literal["talk_to_npc"]
        target_npc: str = Field(description="NPC to talk to")
        dialogue: str
    
    # 新的物品互動模式
    class InteractItemAction(BaseModel):
        action_type: Literal["interact_item"]
        interact_with: str = Field(description="要互動的物品名稱")
        how_to_interact: str = Field(description="詳細描述如何與物品互動")

    class GeneralResponse(BaseModel):
        self_talk_reasoning: str
        action: Optional[Union[
            "NPC.EnterSpaceAction", 
            "NPC.InteractItemAction", 
            "NPC.TalkToNPCAction"
        ]] = None

    def update_schema(self):
        """
        根據 NPC 當前狀態動態生成模式結構。
        返回適當的 GeneralResponse 模型。
        """
        # 獲取當前狀態的有效選項
        valid_spaces = [space.name for space in self.current_space.connected_spaces]
        valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
        available_items = [item.name for item in self.current_space.items + self.inventory.items]
        inventory_items = [item.name for item in self.inventory.items]

        # 定義空間移動操作
        class EnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: Literal[*valid_spaces] if valid_spaces else str = Field(description="移動到的空間名稱")

        # 定義與 NPC 對話操作
        class TalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: Literal[*valid_npcs] if valid_npcs else str = Field(description="對話對象的名稱")
            dialogue: str = Field(description="想要說的話")

        # 定義物品互動操作（統一單一物品和多物品互動）
        class InteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            #TODO: target_item should be available_items in space + inventory_items
            target_item: Literal[*available_items] if available_items else str = Field(description="主要目標物品名稱，NPC 將移動到此物品位置進行互動，可以是空間中或庫存中的物品。例如：與「鍋子」互動進行烹飪，或與「樹」互動進行砍伐。")
            inventory_item_1: Optional[Literal[*inventory_items] if inventory_items else str] = Field(None, description="庫存中的第一個輔助物品名稱（可選）。例如：烹飪時使用「雞肉」作為食材，或組裝時使用「螺絲」。")
            inventory_item_2: Optional[Literal[*inventory_items] if inventory_items else str] = Field(None, description="庫存中的第二個輔助物品名稱（可選）。例如：烹飪時使用「蔬菜」作為食材，或組裝時使用「螺絲起子」。")
            inventory_item_3: Optional[Literal[*inventory_items] if inventory_items else str] = Field(None, description="庫存中的第三個輔助物品名稱（可選）。例如：烹飪時使用「調味料」作為食材。")
            inventory_item_4: Optional[Literal[*inventory_items] if inventory_items else str] = Field(None, description="庫存中的第四個輔助物品名稱（可選）。例如：烹飪時使用「油」作為食材。")
            inventory_item_5: Optional[Literal[*inventory_items] if inventory_items else str] = Field(None, description="庫存中的第五個輔助物品名稱（可選）。例如：烹飪時使用「鹽」作為食材。")
            how_to_interact: str = Field(description="""
            詳細描述如何與這些物品互動。請使用描述性語言，清楚說明你想要如何使用或操作這些物品。以下是一些可能的互動方式和場景：
            
            1. 拆解物品：你可以將物品拆解成零件或材料，系統會刪除原物品並創建新物品。例如：「我要用工具拆解這台舊電腦，取出電路板和硬盤。」（target_item: 舊電腦，inventory_item_1: 螺絲起子）
            2. 烹飪：你可以使用鍋子或烤箱（作為 target_item）與庫存中的多個食材進行烹飪，系統會刪除食材並創建新的料理。例如：「我要用鍋子烹飪雞肉和蔬菜，製作一盤炒雞肉。」（target_item: 鍋子，inventory_item_1: 雞肉，inventory_item_2: 蔬菜）
            3. 從儲存空間取出物品：你可以與冰箱、櫃子或工作台（作為 target_item）互動，從中取出物品，系統會創建新物品。例如：「我要從冰箱中拿出一瓶飲料和一些食材。」（target_item: 冰箱）
            4. 砍伐或採集：你可以與樹木、岩石或其他資源（作為 target_item）互動，進行砍伐或採集，系統會刪除原物品並創建新材料。例如：「我要用斧頭砍倒這棵樹，獲取木材和樹枝。」（target_item: 樹，inventory_item_1: 斧頭）
            5. 組裝或合成：你可以使用工具或工作台（作為 target_item）與庫存中的零件或材料進行組裝，系統會刪除材料並創建新物品。例如：「我要在工作台上用螺絲和木板組裝一個木架。」（target_item: 工作台，inventory_item_1: 螺絲，inventory_item_2: 木板）
            6. 使用物品：你可以簡單地使用物品而不改變其狀態，系統可能只更新物品描述。例如：「我要用電腦上網查資料。」（target_item: 電腦）
            
            請根據你的意圖和物品的性質，詳細描述你的行為，系統將根據你的描述執行相應的操作。
            """)

        # 頂層響應
        class GeneralResponse(BaseModel):
            self_talk_reasoning: str = Field(description="你對當前情況的思考和分析")
            action: Optional[Union[
                EnterSpaceAction,
                TalkToNPCAction,
                InteractItemAction
            ]] = Field(None, description="""
            你想要執行的動作。請根據你的意圖選擇適當的行動類別：
            
            1. EnterSpaceAction：用於移動到另一個空間，例如：「我要去廚房。」此行動適用於需要在不同空間之間移動的情況，系統會將你移動到目標空間並更新你的位置。
            
            2. TalkToNPCAction：用於與其他 NPC 進行對話，例如：「我要和 John 談談今天的計劃。」此行動適用於社交互動，系統會記錄你的對話內容並可能觸發其他 NPC 的回應。
            
            3. InteractItemAction：用於與物品進行互動，涵蓋了多種可能性，從簡單的使用到複雜的合成。此行動適用於任何涉及物品的操作，包括但不限於：
            - 拆解物品：將物品分解成零件或材料，例如：「我要拆解這台舊電腦。」系統會刪除原物品並創建新物品（如電路板、硬盤）。
            - 烹飪：使用鍋子或烤箱與多個食材進行烹飪，例如：「我要用鍋子烹飪雞肉和蔬菜。」系統會刪除食材並創建新料理（如炒雞肉）。
            - 從儲存空間取出物品：從冰箱、櫃子或工作台中取出物品，例如：「我要從冰箱拿飲料。」系統會創建新物品（如飲料）。
            - 砍伐或採集：砍伐樹木或採集資源，例如：「我要用斧頭砍樹。」系統會刪除樹並創建新材料（如木材、樹枝）。
            - 組裝或合成：使用工具或工作台與零件進行組裝，例如：「我要用螺絲和木板組裝木架。」系統會刪除材料並創建新物品（如木架）。
            - 使用物品：簡單使用物品而不改變其狀態，例如：「我要用電腦上網。」系統可能只更新物品描述或不做改變。
            請在 how_to_interact 欄位中詳細描述你的意圖，系統將根據你的描述執行相應操作。
            """)
        
        return GeneralResponse

    def add_space_to_history(self):
        """
        將當前空間的信息（通過 __str__）附加到 NPC 的歷史記錄中。
        """
        self.history.append({"role": "system", "content": str(self.current_space)})

    def print_current_schema(self):
        """
        打印 AI 使用的實際模式結構
        """
        try:
            print("\n=== GeneralResponse Schema ===")
            schema = self.update_schema().model_json_schema()
            # 使用縮進使其更易讀
            import json
            print(json.dumps(schema, indent=2))
            print("=== GeneralResponse Schema END ===\n")

            if self.current_space.connected_spaces:
                print("=== EnterSpaceAction Schema ===")
                schema = self.EnterSpaceAction.model_json_schema()
                print(json.dumps(schema, indent=2))
                print("=== EnterSpaceAction Schema END ===\n")

            print("=== InteractItemAction Schema ===")
            schema = self.InteractItemAction.model_json_schema()
            print(json.dumps(schema, indent=2))
            print("=== InteractItemAction Schema END ===\n")

            valid_npcs = [npc for npc in self.current_space.npcs if npc != self]
            if valid_npcs:
                print("=== TalkToNPCAction Schema ===")
                schema = self.TalkToNPCAction.model_json_schema()
                print(json.dumps(schema, indent=2))
                print("=== TalkToNPCAction Schema END ===\n")
        except Exception as e:
            print(f"Error printing schema: {str(e)}")
            # 打印額外的調試信息
            print(f"Current space: {self.current_space.name}")
            print(f"Available items: {[item.name for item in self.current_space.items + self.inventory.items]}")
            print(f"Available NPCs: {[npc.name for npc in self.current_space.npcs if npc != self]}")

    def move_to_space(self, target_space_name: str) -> str:
        """
        將 NPC 移動到連接的空間，並更新空間的 NPC 列表。
        """
        target_space_name = target_space_name.lower()

        # Check if the target space is in the connected spaces of the current space
        for connected_space in self.current_space.connected_spaces:
            if connected_space.name.lower() == target_space_name:
                # Remove the NPC from the current space's NPC list
                if self in self.current_space.npcs:
                    self.current_space.npcs.remove(self)

                # Add the NPC to the target space's NPC list
                connected_space.npcs.append(self)

                # Move to the target space
                self.current_space = connected_space

                # Add the target space's information to history
                self.add_space_to_history()

                # Return the target space's description
                return f"Moved to {connected_space.name}.\n{str(connected_space)}"

        # If the target space is not connected, return an error message
        return f"Cannot move to {target_space_name}. It is not connected to {self.current_space.name}."


    def process_tick(self, user_input: Optional[str] = None):
        """
        Process a single tick of the NPC's behavior.
        
        Args:
            user_input: Optional input from the user
            
        Returns:
            A string describing the result of the NPC's action
        """
        global world_system
        if world_system is None:
            from backend import AI_System
            world_system = AI_System()
        # Get the dynamically generated schema
        GeneralResponse = self.update_schema()
        
        # History and AI call
        if self.first_tick:
            self.add_space_to_history()
            self.first_tick = False
        if user_input:
            self.history.append({"role": "user", "content": f"User: {user_input}"})

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=self.history,
            response_format=GeneralResponse
        )
        response = completion.choices[0].message.parsed

        print("\n=== AI Response ===")
        print(response)
        print("==================\n")

        # Handle the action
        if not response.action:
            # If no action, append reasoning only
            memory = f"{response.self_talk_reasoning}\n沒有執行動作"
            self.history.append({"role": "assistant", "content": memory})
            return memory

        action = response.action
        result = ""
        
        # Process the action based on its type
        if hasattr(action, "action_type"):
            if action.action_type == "interact_item":
                # 使用統一的互動系統處理物品互動（支援單一物品和多物品）
                target_item = action.target_item
                
                # 安全地獲取庫存物品，使用 getattr 避免屬性不存在的問題
                inventory_items = []
                for i in range(1, 6):
                    item_attr = f"inventory_item_{i}"
                    item = getattr(action, item_attr, None)
                    if item:
                        inventory_items.append(item)
                
                result = world_system.process_interaction(
                    self,
                    target_item,
                    inventory_items,
                    action.how_to_interact
                )
            elif action.action_type == "enter_space":
                result = self.move_to_space(action.target_space)
            elif action.action_type == "talk_to_npc":
                result = self.talk_to_npc(action.target_npc, action.dialogue)
            else:
                result = f"Unknown action type: {action.action_type}"
        else:
            result = "Action has no type specified."

        # Append reasoning, how_to_interact or dialogue (if applicable), and result to history as assistant
        memory = f"{response.self_talk_reasoning}"
        if action.action_type == "interact_item":
            memory += f"\n{action.how_to_interact}"
        elif action.action_type == "talk_to_npc":
            memory += f"\n對 {action.target_npc} 說: {action.dialogue}"
        elif action.action_type == "enter_space":
            memory += f"\n我要移動到 {action.target_space}"
        memory += f"\n結果: {result}"
        self.history.append({"role": "assistant", "content": memory})
        
        print("\n=== Action Result ===")
        print(result)
        print("===================\n")
        
        # Return the complete result including reasoning, how_to_interact or dialogue (if applicable), and result
        return memory

    def talk_to_npc(self, target_npc_name: str, dialogue: str) -> str:
        """
        Handle talking to another NPC in the same space.
        
        Args:
            target_npc_name: The name of the NPC to talk to
            dialogue: What to say to the NPC
            
        Returns:
            A string describing the result of the conversation
        """
        # Find the target NPC in the current space
        target_npc = None
        for npc in self.current_space.npcs:
            if npc.name.lower() == target_npc_name.lower() and npc != self:
                target_npc = npc
                break
        
        if target_npc is None:
            return f"Cannot find NPC '{target_npc_name}' in the current space."
        
        # In a more complex implementation, you might want to pass the dialogue to the target NPC
        # and get a response back. For now, we'll just return a simple message.
        return f"{self.name} says to {target_npc.name}: \"{dialogue}\""

    async def async_talk_to_npc(self, target_npc_name: str, dialogue: str, priority: int = 10):
        """
        將對話事件丟到空間的對話管理器（asyncio 版本，帶優先級）。
        """
        import time
        event = ConversationEvent(
            priority=priority,
            timestamp=time.time(),
            speaker=self.name,
            target=target_npc_name,
            message=dialogue
        )
        if self.current_space.conversation_manager:
            await self.current_space.conversation_manager.add_conversation(event)
        else:
            print(f"[警告] 空間 {self.current_space.name} 沒有對話管理器！")

#NOTE: Loading world & Saving


def load_world_from_json(file_path: str) -> Dict[str, Any]:
    """
    Load world data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing the world data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: World file not found at {file_path}")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
        return {}

def build_world_from_data(world_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    從加載的 JSON 數據構建世界對象。
    
    Args:
        world_data: 包含世界數據的字典
        
    Returns:
        包含構建的世界對象的字典
    """
    if not world_data:
        print("錯誤: 未提供世界數據")
        return {}

    # 初始化空集合
    spaces_dict = {}
    items_dict = {}
    npcs_dict = {}
    
    # 第一步: 創建所有空間（不含連接）
    for space_data in world_data.get("spaces", []):
        spaces_dict[space_data["name"]] = Space(
            name = space_data["name"],
            description = space_data["description"],
            connected_spaces = [],  # 後續連接
            items = [],  # 後續添加物品
            npcs = [],  # 後續添加 NPC
            display_pos = tuple(space_data["space_positions"]),
            display_size = tuple(space_data["space_size"]),
            conversation_manager = ConversationManager(space_name=space_data["name"])
        )
    
    # 第二步: 創建所有物品
    for item_data in world_data.get("items", []):
        # 使用簡化的 Item 類創建物品（沒有 interactions 欄位）
        items_dict[item_data["name"]] = Item(
            name = item_data["name"],
            description = item_data["description"],
            properties = item_data.get("properties", {}),
            position = tuple(item_data["position"]),
            size = tuple(item_data["size"])
        )
    
    # 第三步: 連接空間並向空間添加物品
    for space_data in world_data.get("spaces", []):
        space = spaces_dict[space_data["name"]]
        
        # 連接空間
        for connected_space_name in space_data["connected_spaces"]:
            if connected_space_name in spaces_dict:
                connected_space = spaces_dict[connected_space_name]
                # 使用 biconnect 建立雙向連接
                space.biconnect(connected_space)
        
        # 向空間添加物品
        for item_name in space_data["items"]:
            if item_name in items_dict:
                space.items.append(items_dict[item_name])
    
    # 第四步: 創建 NPC 並放入空間
    for npc_data in world_data.get("npcs", []):
        # 為 NPC 創建庫存
        inventory = Inventory(items=[])
        
        # 如果指定了庫存物品，則添加到庫存中
        for item_name in npc_data.get("inventory", []):
            if item_name in items_dict:
                inventory.add_item(items_dict[item_name])
        
        # 獲取起始空間
        starting_space_name = npc_data.get("starting_space")
        starting_space = spaces_dict.get(starting_space_name)
        
        if starting_space:
            # 計算 NPC 初始位置
            if "position" in npc_data and npc_data["position"] is not None:
                npc_pos = tuple(npc_data["position"])
            else:
                # 預設在空間中央
                npc_pos = (
                    starting_space.display_pos[0] + starting_space.display_size[0] // 2,
                    starting_space.display_pos[1] + starting_space.display_size[1] // 2
                )
            # 創建 NPC
            npc = NPC(
                name = npc_data["name"],
                description = npc_data["description"],
                current_space = starting_space,
                inventory = inventory,
                history = npc_data.get("history", []),
                display_pos = tuple(npc_pos),
                position = tuple(npc_pos)
            )
            
            # 將 NPC 添加到其起始空間
            starting_space.npcs.append(npc)
            
            # 將 NPC 存儲在字典中
            npcs_dict[npc_data["name"]] = npc
    
    return {
        "world_name": world_data.get("world_name", "未知世界"),
        "description": world_data.get("description", ""),
        "spaces": spaces_dict,
        "items": items_dict,  # 確保總是有 'items' key
        "npcs": npcs_dict
    }

# New function to list available worlds
def list_available_worlds():
    """
    Scan the 'worlds' folder and return a list of available world files.
    
    Returns:
        List of world filenames (without path)
    """
    # Make sure the worlds directory exists
    if not os.path.exists("worlds"):
        print("Creating 'worlds' directory...")
        os.makedirs("worlds")
        return []
    
    # Get all JSON files in the worlds directory
    world_files = glob.glob(os.path.join("worlds", "*.json"))
    
    # Extract just the filenames without the path
    return [os.path.basename(file) for file in world_files]

def select_world():
    """
    Prompt the user to select a world from the available options.
    
    Returns:
        Path to the selected world file
    """
    available_worlds = list_available_worlds()
    
    if not available_worlds:
        print("No world files found in the 'worlds' directory.")
        print("Please add world JSON files to the 'worlds' directory and restart.")
        exit(1)
    
    print("\n=== Available Worlds ===")
    for i, world_file in enumerate(available_worlds, 1):
        print(f"{i}. {world_file}")
    print("=======================\n")
    
    while True:
        user_input = input("Enter world name or number to load (partial name is OK): ").strip()
        
        # Check if input is a number
        if user_input.isdigit():
            index = int(user_input) - 1
            if 0 <= index < len(available_worlds):
                selected_world = available_worlds[index]
                break
            else:
                print(f"Invalid number. Please enter a number between 1 and {len(available_worlds)}.")
        else:
            # Try to match partial name
            matches = [world for world in available_worlds if user_input.lower() in world.lower()]
            
            if len(matches) == 1:
                selected_world = matches[0]
                break
            elif len(matches) > 1:
                print("Multiple matches found:")
                for i, match in enumerate(matches, 1):
                    print(f"{i}. {match}")
                continue
            else:
                print("No matching world found. Please try again.")
    
    print(f"Loading world: {selected_world}")
    return os.path.join("worlds", selected_world)

def save_world_to_json(world: Dict[str, Any], file_path: str) -> bool:
    """
    將當前世界狀態保存到 JSON 文件。
    
    Args:
        world: 包含世界對象的字典
        file_path: 保存 JSON 文件的路徑
        
    Returns:
        保存成功返回 True，否則返回 False
    """
    try:
        # 創建一個字典來保存序列化的世界數據
        world_data = {
            "world_name": world.get("world_name", "未知世界"),
            "description": world.get("description", ""),
            "spaces": [],
            "items": [],
            "npcs": []
        }
        
        # 序列化空間
        for space_name, space in world["spaces"].items():
            space_data = {
                "name": space.name,
                "description": space.description,
                "connected_spaces": [connected.name for connected in space.connected_spaces],
                "items": [item.name for item in space.items]
                # NPC 單獨處理
            }
            world_data["spaces"].append(space_data)
        
        # 序列化物品 - 簡化版本，不包含 interactions
        for item_name, item in world["items"].items():
            item_data = {
                "name": item.name,
                "description": item.description,
                "properties": item.properties
            }
            world_data["items"].append(item_data)
        
        # 序列化 NPC
        for npc_name, npc in world["npcs"].items():
            npc_data = {
                "name": npc.name,
                "description": npc.description,
                "starting_space": npc.current_space.name,
                "inventory": [item.name for item in npc.inventory.items],
                "history": npc.history  # 保存 NPC 的記憶/歷史記錄
            }
            world_data["npcs"].append(npc_data)
        
        # 寫入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, indent=2, ensure_ascii=False)
        
        print(f"成功保存世界至 {file_path}")
        return True
    
    except Exception as e:
        print(f"保存世界時出錯: {str(e)}")
        return False

def prompt_for_save_location(original_file_path: str) -> str:
    """
    Prompt the user for where to save the world.
    
    Args:
        original_file_path: The path of the originally loaded world file
        
    Returns:
        Path where to save the world
    """
    print("\n=== Save World ===")
    print("Enter a new filename to save as a new world, or")
    print("Press Enter to overwrite the current world file.")
    print(f"Current file: {os.path.basename(original_file_path)}")
    
    user_input = input("Save as (leave blank to overwrite): ").strip()
    
    if not user_input:
        # Overwrite the original file
        return original_file_path
    
    # Check if the user provided a .json extension
    if not user_input.lower().endswith('.json'):
        user_input += '.json'
    
    # Return the new file path
    return os.path.join("worlds", user_input)

#NOTE: Main Loop
def SandBox():
    """
    主沙盒函數，處理世界選擇、加載和遊戲循環。
    此函數允許用戶與選定世界中的 NPC 互動。
    """
    # 聲明使用全局變量
    global world_system
    
    # 選擇並加載一個世界
    world_file_path = select_world()
    world_data = load_world_from_json(world_file_path)
    world = build_world_from_data(world_data)

    # 初始化 AI_System 並設置為全局變量
    world_system = AI_System(
        time="中午",
        weather="晴朗",
        history=[]
    )
    world_system.initialize_world(world)
    
    # 打印系統信息
    print(f"世界系統已初始化 - 時間: {world_system.time}, 天氣: {world_system.weather}")
    
    # 獲取世界中的所有 NPC
    npcs = list(world["npcs"].values())
    
    if not npcs:
        print("警告: 此世界中未找到 NPC。模擬將受到限制。")
        print(f"已加載世界: {world['world_name']}")
        print(f"描述: {world['description']}")
        print(f"空間: {', '.join(world['spaces'].keys())}")
        print(f"物品: {', '.join(world['items'].keys())}")
        
        # 沒有 NPC 的簡單循環
        while True:
            print("=====================")
            user_input = input("e -> 退出, i -> 信息: ").strip().lower()
            
            if user_input == "e":
                # 退出前提示保存
                save_path = prompt_for_save_location(world_file_path)
                save_world_to_json(world, save_path)
                print("正在退出...")
                break
            elif user_input == "i":
                print(f"世界: {world['world_name']}")
                print(f"描述: {world['description']}")
                print(f"空間: {', '.join(world['spaces'].keys())}")
                print(f"物品: {', '.join(world['items'].keys())}")
                print(f"時間: {world_system.time}, 天氣: {world_system.weather}")
            else:
                print("沒有可互動的 NPC。嘗試不同的世界或向這個世界添加 NPC。")
    else:
        # 打印世界信息
        print(f"已加載世界: {world['world_name']}")
        print(f"描述: {world['description']}")
        print(f"NPC: {', '.join([npc.name for npc in npcs])}")
        
        # 選擇要關注的 NPC 進行詳細互動
        active_npc_index = 0
        if len(npcs) > 1:
            print("\n=== 可用的 NPC ===")
            for i, npc in enumerate(npcs, 1):
                print(f"{i}. {npc.name} - {npc.description}")
            
            while True:
                npc_choice = input("選擇要關注的 NPC (數字): ").strip()
                if npc_choice.isdigit() and 1 <= int(npc_choice) <= len(npcs):
                    active_npc_index = int(npc_choice) - 1
                    break
                print(f"請輸入 1 到 {len(npcs)} 之間的數字")
        
        active_npc = npcs[active_npc_index]
        print(f"正在關注 NPC: {active_npc.name}")
        
        # 主遊戲循環
        while True:
            print("=====================")
            user_input = input("c -> 繼續, e -> 退出, p -> 打印歷史, s -> 顯示模式, n -> 切換 NPC, w -> 改變天氣和時間: ").strip().lower()

            if user_input == "c":
                # 處理所有 NPC 的 tick，但只顯示活躍 NPC 的結果
                for npc in npcs:
                    result = npc.process_tick()
                    if npc == active_npc:
                        print(f"[{npc.name}] Tick 結果: {result}")
                print()
                print()

            elif user_input == "e":
                # 退出前提示保存
                save_path = prompt_for_save_location(world_file_path)
                save_world_to_json(world, save_path)
                print("正在退出...")
                break

            elif user_input == "p":
                try:
                    from rich.console import Console
                    from rich.panel import Panel
                    
                    console = Console()
                    print(f"{active_npc.name} 的歷史記錄:")
                    
                    # 按連續角色分組消息
                    grouped_messages = []
                    current_group = None
                    
                    for message in active_npc.history:
                        role = message['role']
                        content = message['content']
                        
                        if current_group is None or current_group['role'] != role:
                            # 開始新組
                            current_group = {'role': role, 'contents': [content]}
                            grouped_messages.append(current_group)
                        else:
                            # 添加到現有組
                            current_group['contents'].append(content)
                    
                    # 顯示每個組
                    for group in grouped_messages:
                        role = group['role']
                        contents = group['contents']
                        
                        # 根據角色設置樣式
                        if role == "system":
                            style = "blue"
                            title = "系統"
                        elif role == "assistant":
                            style = "green"
                            title = active_npc.name.upper()
                        elif role == "user":
                            style = "yellow"
                            title = "用戶"
                        else:
                            style = "white"
                            title = role.upper()
                        
                        # 用換行符連接所有內容
                        combined_content = "\n".join(contents)
                        
                        # 創建面板，頂部顯示角色名稱，然後是新行上的內容
                        panel_text = f"{title}:\n{combined_content}"
                        panel = Panel(panel_text, border_style=style)
                        
                        # 打印面板
                        console.print(panel)
                        
                except ImportError:
                    # 如果 rich 未安裝，回退
                    print("為了更好的格式化，安裝 'rich' 庫: pip install rich")
                    print(f"{active_npc.name} 的歷史記錄:")
                    
                    current_role = None
                    role_messages = []
                    
                    for message in active_npc.history:
                        role = message['role']
                        content = message['content']
                        
                        if current_role is None or current_role != role:
                            # 如果有先前角色的消息，則打印
                            if role_messages:
                                print(f"{current_role.upper()}:")
                                for msg in role_messages:
                                    print(f"  {msg}")
                                print()
                            
                            # 開始新角色
                            current_role = role
                            role_messages = [content]
                        else:
                            # 添加到當前角色
                            role_messages.append(content)
                    
                    # 打印最後一組
                    if role_messages:
                        print(f"{current_role.upper()}:")
                        for msg in role_messages:
                            print(f"  {msg}")
                        print()

            elif user_input == "s":
                active_npc.print_current_schema()
                
            elif user_input == "n" and len(npcs) > 1:
                print("\n=== 可用的 NPC ===")
                for i, npc in enumerate(npcs, 1):
                    print(f"{i}. {npc.name} - {npc.description}")
                
                while True:
                    npc_choice = input("選擇要關注的 NPC (數字): ").strip()
                    if npc_choice.isdigit() and 1 <= int(npc_choice) <= len(npcs):
                        active_npc_index = int(npc_choice) - 1
                        active_npc = npcs[active_npc_index]
                        print(f"現在關注: {active_npc.name}")
                        break
                    print(f"請輸入 1 到 {len(npcs)} 之間的數字")
            
            elif user_input == "w":
                # 新增功能：更改世界系統的時間和天氣
                print(f"當前時間: {world_system.time}")
                print(f"當前天氣: {world_system.weather}")
                
                new_time = input("輸入新的時間 (直接按 Enter 保持不變): ").strip()
                if new_time:
                    world_system.time = new_time
                
                new_weather = input("輸入新的天氣 (直接按 Enter 保持不變): ").strip()
                if new_weather:
                    world_system.weather = new_weather
                
                print(f"更新後 - 時間: {world_system.time}, 天氣: {world_system.weather}")

            else:
                # 只處理活躍 NPC 的用戶輸入
                result = active_npc.process_tick(user_input)
                print(f"[{active_npc.name}] Tick 結果: {result}")
                print()
                print()


#NOTE: AI_System class
class AI_System(BaseModel):
    """
    系統 AI 負責解釋和處理 NPC AI 的互動意圖，
    並根據這些意圖修改世界狀態（創建/刪除物品、修改物品描述等）。
    """
    time: str = "中午"
    weather: str = "晴朗"
    history: List[Dict[str, str]] = []
    world: Dict[str, Any] = {} # 實際使用時會被賦值

    # 注意：以下這些類級別的 schema 定義現在主要作為一個「藍本」或「原始描述的來源」。
    # 實際在 process_interaction 中傳給 LLM 的 schema 將是 update_schema 方法內部重新定義並返回的那個。
    # 這樣做是為了完全遵循您 NPC.update_schema 的模式。

    class ModifyWorldItemsFunction(BaseModel):
        function_type: Literal["modify_world_items"] = Field("modify_world_items", description="固定值，表示這是一個通用的物品修改功能。")
        delete_item_1: Optional[str] = Field(None, description="要刪除的第一個物品的名稱。例如：在烹飪時，這可能是「生雞肉」。如果本次操作不刪除任何物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
        delete_item_2: Optional[str] = Field(None, description="要刪除的第二個物品的名稱。例如：烹飪時decyd的「蔬菜」。如果本次操作不刪除超過一個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
        delete_item_3: Optional[str] = Field(None, description="要刪除的第三個物品的名稱。例如：製作藥水時的「藥草A」。如果本次操作不刪除超過兩個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
        delete_item_4: Optional[str] = Field(None, description="要刪除的第四個物品的名稱。例如：製作複雜裝置時的「零件X」。如果本次操作不刪除超過三個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
        delete_item_5: Optional[str] = Field(None, description="要刪除的第五個物品的名稱。例如：獻祭儀式中消耗的「魔法水晶」。如果本次操作不刪除超過四個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
        create_item_1_name: Optional[str] = Field(None, description="要創建的第一個新物品的名稱。例如：「香煎雞排」。如果本次操作不創建任何物品或不使用此欄位，請保持為 None。")
        create_item_1_description: Optional[str] = Field(None, description="第一個新物品的詳細描述。必須提供如果 create_item_1_name 被指定。例如：「一塊用香料精心烹製，外皮金黃酥脆、肉質鮮嫩多汁的雞排。」")
        create_item_2_name: Optional[str] = Field(None, description="要創建的第二個新物品的名稱。例如：「蔬菜沙拉」。")
        create_item_2_description: Optional[str] = Field(None, description="第二個新物品的詳細描述。例如：「一份由新鮮生菜、番茄、小黃瓜和橄欖組成的清爽沙拉，淋上了特製油醋汁。」")
        create_item_3_name: Optional[str] = Field(None, description="要創建的第三個新物品的名稱。例如：「治療藥水」。")
        create_item_3_description: Optional[str] = Field(None, description="第三個新物品的詳細描述。例如：「一瓶散發著淡淡草藥香氣的紅色藥水，據說能迅速治癒傷口。」")
        create_item_4_name: Optional[str] = Field(None, description="要創建的第四個新物品的名稱。例如：「木柴捆」。")
        create_item_4_description: Optional[str] = Field(None, description="第四個新物品的詳細描述。例如：「一捆由砍伐樹木得到的乾燥木柴，適合用作燃料。」")
        create_item_5_name: Optional[str] = Field(None, description="要創建的第五個新物品的名稱。例如：「精緻的木雕」。")
        create_item_5_description: Optional[str] = Field(None, description="第五個新物品的詳細描述。例如：「一個用優質木材精心雕刻而成的小鳥擺飾，栩栩如生。」")
        # 這裡可以保留 ModifyWorldItemsFunction 的完整描述文字和範例，例如：
        # "這是一個高度通用的物品操作功能..." (內容同前一個版本)
        model_config = {"title": "AI_System_ModifyWorldItemsFunction_Static"} # 區分類名

    class ChangeItemDescriptionFunction(BaseModel):
        function_type: Literal["change_item_description"] = Field("change_item_description", description="固定值，表示這是一個修改物品描述的功能。")
        item_name: str = Field(description="要修改描述的物品名稱。用於物品狀態變化但不需要創建新物品時，例如：物品被使用後狀態改變、物品被修理或損壞。此物品必須是 NPC 正在互動的物品之一。")
        new_description: str = Field(description="物品的新描述，反映其當前狀態。例如：「杯子裡現在裝滿了水」或「手機屏幕有了裂痕」。")
        model_config = {"title": "AI_System_ChangeItemDescriptionFunction_Static"}

    class MoveItemToInventoryFunction(BaseModel):
        function_type: Literal["move_item_to_inventory"] = Field("move_item_to_inventory", description="固定值，表示這是一個將物品從空間移動到 NPC 庫存的功能。")
        item_name: str = Field(description="要移動到 NPC 庫存的物品名稱。用於 NPC 撿起或收集空間中的物品時，例如：撿起地上的鑰匙、從桌上拿起書本。此物品必須是 NPC 正在互動的目標物品(target_item)且位於空間中。")
        model_config = {"title": "AI_System_MoveItemToInventoryFunction_Static"}

    class MoveItemFromInventoryToSpaceFunction(BaseModel):
        function_type: Literal["move_item_from_inventory_to_space"] = Field("move_item_from_inventory_to_space", description="固定值，表示這是一個將物品從 NPC 庫存移動到空間的功能。")
        item_name: str = Field(description="要從 NPC 庫存中取出並放置到空間的物品名稱。用於 NPC 將物品從庫存中拿出並放置在當前空間時，例如：放下背包、擺放物品。此物品必須是 NPC 庫存中的物品之一。")
        model_config = {"title": "AI_System_MoveItemFromInventoryToSpaceFunction_Static"}

    class GeneralResponse(BaseModel):
        reasoning: str = Field(description="...") # 描述同前
        function: Optional[Union[
            "AI_System.ModifyWorldItemsFunction", # 指向類級別的定義以獲取聯合類型提示
            "AI_System.ChangeItemDescriptionFunction",
            "AI_System.MoveItemToInventoryFunction",
            "AI_System.MoveItemFromInventoryToSpaceFunction"
        ]] = Field(None, description="...") # 描述同前
        response_to_AI: str = Field(description="...") # 描述同前
        model_config = {"title": "AI_System_GeneralResponse_Static"}


    def update_schema(self, available_items_for_interaction: List[str], npc_complete_inventory: List[str]):
        """
        根據 NPC 當前互動涉及的物品和其完整庫存，動態生成 AI_System 使用的 GeneralResponse schema。
        所有 schema 結構和描述文字在此方法內重新定義，並直接嵌入動態 Literal。
        
        Args:
            available_items_for_interaction: NPC 本次互動明確涉及的所有物品的名稱列表 (target_item + inventory_items from NPC's action)。
                                             這些是 ModifyWorldItemsFunction 中 delete_item_X,
                                             ChangeItemDescriptionFunction 中 item_name,
                                             以及 MoveItemToInventoryFunction 中 item_name 的有效選項。
            npc_complete_inventory: NPC 完整庫存中所有物品的名稱列表。
                                    這些是 MoveItemFromInventoryToSpaceFunction 中 item_name 的有效選項。
        
        Returns:
            type[GeneralResponse]: 一個在方法內部定義的 GeneralResponse Pydantic 模型類別，
                                   其內嵌的 Function classes 的特定欄位已包含動態 Literal。
        """
        
        # 準備動態 Literal 類型
        # 如果列表為空，Literal[tuple()] 會導致 Pydantic 錯誤或非預期行為。
        # 使用 str 作為備案，並在 prompt 中指導 LLM 此時無有效選項。
        # 或者，如果確定某個 Literal 列表不應為空，則應在更早的邏輯中處理。
        DeleteOrModifyTargetLiteral = Literal[tuple(available_items_for_interaction)] if available_items_for_interaction else str
        MoveFromInventoryLiteral = Literal[tuple(npc_complete_inventory)] if npc_complete_inventory else str

        # --- 在 update_schema 內部重新定義所有 Function Schemas ---

        class ModifyWorldItemsFunction(BaseModel): # 與 AI_System.ModifyWorldItemsFunction 結構和描述相同
            function_type: Literal["modify_world_items"] = Field("modify_world_items", description="固定值，表示這是一個通用的物品修改功能。")
            
            # 應用動態 Literal
            delete_item_1: Optional[DeleteOrModifyTargetLiteral] = Field(None, description="要刪除的第一個物品的名稱。例如：在烹飪時，這可能是「生雞肉」。如果本次操作不刪除任何物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
            delete_item_2: Optional[DeleteOrModifyTargetLiteral] = Field(None, description="要刪除的第二個物品的名稱。例如：烹飪時的「蔬菜」。如果本次操作不刪除超過一個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
            delete_item_3: Optional[DeleteOrModifyTargetLiteral] = Field(None, description="要刪除的第三個物品的名稱。例如：製作藥水時的「藥草A」。如果本次操作不刪除超過兩個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
            delete_item_4: Optional[DeleteOrModifyTargetLiteral] = Field(None, description="要刪除的第四個物品的名稱。例如：製作複雜裝置時的「零件X」。如果本次操作不刪除超過三個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")
            delete_item_5: Optional[DeleteOrModifyTargetLiteral] = Field(None, description="要刪除的第五個物品的名稱。例如：獻祭儀式中消耗的「魔法水晶」。如果本次操作不刪除超過四個物品或不使用此欄位，請保持為 None。物品必須是本次互動明確涉及的物品之一。")

            # 創建部分的描述和結構保持不變
            create_item_1_name: Optional[str] = Field(None, description="要創建的第一個新物品的名稱。例如：「香煎雞排」。如果本次操作不創建任何物品或不使用此欄位，請保持為 None。")
            create_item_1_description: Optional[str] = Field(None, description="第一個新物品的詳細描述。必須提供如果 create_item_1_name 被指定。例如：「一塊用香料精心烹製，外皮金黃酥脆、肉質鮮嫩多汁的雞排。」")
            create_item_2_name: Optional[str] = Field(None, description="要創建的第二個新物品的名稱。例如：「蔬菜沙拉」。")
            create_item_2_description: Optional[str] = Field(None, description="第二個新物品的詳細描述。例如：「一份由新鮮生菜、番茄、小黃瓜和橄欖組成的清爽沙拉，淋上了特製油醋汁。」")
            create_item_3_name: Optional[str] = Field(None, description="要創建的第三個新物品的名稱。例如：「治療藥水」。")
            create_item_3_description: Optional[str] = Field(None, description="第三個新物品的詳細描述。例如：「一瓶散發著淡淡草藥香氣的紅色藥水，據說能迅速治癒傷口。」")
            create_item_4_name: Optional[str] = Field(None, description="要創建的第四個新物品的名稱。例如：「木柴捆」。")
            create_item_4_description: Optional[str] = Field(None, description="第四個新物品的詳細描述。例如：「一捆由砍伐樹木得到的乾燥木柴，適合用作燃料。」")
            create_item_5_name: Optional[str] = Field(None, description="要創建的第五個新物品的名稱。例如：「精緻的木雕」。")
            create_item_5_description: Optional[str] = Field(None, description="第五個新物品的詳細描述。例如：「一個用優質木材精心雕刻而成的小鳥擺飾，栩栩如生。」")
            # 這裡也應包含 ModifyWorldItemsFunction 的完整描述文字和範例 (從 AI_System 類級別複製過來)
            # 例如："這是一個高度通用的物品操作功能..."

        class ChangeItemDescriptionFunction(BaseModel): # 結構和描述相同
            function_type: Literal["change_item_description"] = Field("change_item_description", description="固定值，表示這是一個修改物品描述的功能。")
            # 應用動態 Literal
            item_name: DeleteOrModifyTargetLiteral = Field(description="要修改描述的物品名稱。用於物品狀態變化但不需要創建新物品時，例如：物品被使用後狀態改變、物品被修理或損壞。此物品必須是 NPC 正在互動的物品之一。")
            new_description: str = Field(description="物品的新描述，反映其當前狀態。例如：「杯子裡現在裝滿了水」或「手機屏幕有了裂痕」。")

        class MoveItemToInventoryFunction(BaseModel): # 結構和描述相同
            function_type: Literal["move_item_to_inventory"] = Field("move_item_to_inventory", description="固定值，表示這是一個將物品從空間移動到 NPC 庫存的功能。")
            # 應用動態 Literal
            item_name: DeleteOrModifyTargetLiteral = Field(description="要移動到 NPC 庫存的物品名稱。用於 NPC 撿起或收集空間中的物品時，例如：撿起地上的鑰匙、從桌上拿起書本。此物品必須是 NPC 正在互動的目標物品(target_item)且位於空間中。")

        class MoveItemFromInventoryToSpaceFunction(BaseModel): # 結構和描述相同
            function_type: Literal["move_item_from_inventory_to_space"] = Field("move_item_from_inventory_to_space", description="固定值，表示這是一個將物品從 NPC 庫存移動到空間的功能。")
            # 應用動態 Literal
            item_name: MoveFromInventoryLiteral = Field(description="要從 NPC 庫存中取出並放置到空間的物品名稱。用於 NPC 將物品從庫存中拿出並放置在當前空間時，例如：放下背包、擺放物品。此物品必須是 NPC 庫存中的物品之一。")

        # --- 在 update_schema 內部重新定義 GeneralResponse ---
        class GeneralResponse(BaseModel): # 為了避免與外部 GeneralResponse 命名衝突，或可以就叫 GeneralResponse
            # reasoning, function, response_to_AI 的描述都從 AI_System.GeneralResponse 複製過來
            reasoning: str = Field(description="""
            系統對 NPC 行為的內部分析和思考。請詳細分析 NPC 的互動意圖 (how_to_interact) 以及涉及的物品 (target_item 和 inventory_items)，
            考慮物品的性質、位置和可能的變化，並說明你為什麼選擇接下來的 function (如果有的話)。
            範例思考：
            - NPC 說要「用鐵砧和鐵錘把彎曲的鐵條打直」。目標物品是「鐵砧」，庫存物品是「鐵錘」和「彎曲的鐵條」。這是一個物品轉換的過程。
              我應該使用 ModifyWorldItemsFunction，刪除「彎曲的鐵條」，保留「鐵砧」和「鐵錘」(不刪除它們)，然後創建一個「筆直的鐵條」。
            - NPC 說要「從冰箱裡拿出牛奶和雞蛋」。目標物品是「冰箱」。這是一個從儲存容器獲取物品的行為。
              我應該使用 ModifyWorldItemsFunction，不刪除任何物品 (冰箱本身通常不被消耗)，然後創建「牛奶」和「雞蛋」。
            - NPC 說要「檢查一下這個奇怪的裝置」。目標物品是「奇怪的裝置」。NPC 只是觀察，沒有明確要改變它或產生新東西。
              這種情況下，可能不需要调用任何 function 來改變世界狀態，只需更新物品描述 (如果裝置的狀態因檢查而改變)，或者在 response_to_AI 中描述 NPC 的發現即可。如果只是觀察且物品無變化，則 function 為 None。
            """)
            
            function: Optional[Union[
                ModifyWorldItemsFunction, # 注意：這裡指向的是在 update_schema 內部剛剛定義的 ModifyWorldItemsFunction
                ChangeItemDescriptionFunction,
                MoveItemToInventoryFunction,
                MoveItemFromInventoryToSpaceFunction
            ]] = Field(None, description="""
            根據 NPC 的互動意圖選擇最合適的功能來改變世界狀態。請仔細閱讀每個功能的描述和適用場景：
            
            1.  **ModifyWorldItemsFunction**: 這是最主要和最通用的物品操作功能。
                適用於任何涉及**創建新物品**或**刪除現有物品**的場景 (或者兩者同時發生)。
                - **純粹創建**: NPC 從某處 (如魔法源、容器、NPC的技能) 創造出新物品，而沒有消耗任何現有物品。
                  (所有 `delete_item_X` 欄位為 `None`；至少一個 `create_item_X_name` 被指定)。
                  例：NPC 從「冰箱」拿出「果汁」和「三明治」 -> `ModifyWorldItemsFunction(create_item_1_name="果汁", create_item_2_name="三明治", ...)`
                - **純粹刪除/消耗**: NPC 消耗、摧毀或丟棄物品，而沒有產生任何新物品。
                  (所有 `create_item_X_name` 欄位為 `None`；至少一個 `delete_item_X` 被指定)。
                  例：NPC 吃掉「麵包」 -> `ModifyWorldItemsFunction(delete_item_1="麵包")`
                - **轉換/製作/合成/加工**: NPC 使用一些物品，這些物品被消耗 (刪除)，然後產生了新的物品 (創建)。
                  (同時指定 `delete_item_X` 和 `create_item_X_name` 欄位)。
                  例：NPC 用「木頭」和「釘子」製作「小凳子」 -> `ModifyWorldItemsFunction(delete_item_1="木頭", delete_item_2="釘子", create_item_1_name="小凳子", ...)`
                  例：NPC 砍伐「松樹」得到「松木」和「松果」 -> `ModifyWorldItemsFunction(delete_item_1="松樹", create_item_1_name="松木", create_item_2_name="松果", ...)`
                - **物品替換**: 一個舊物品被一個新物品取代 (通常是狀態的重大改變)。
                  例：NPC 修理「破損的護符」變成「完好的護符」 -> `ModifyWorldItemsFunction(delete_item_1="破損的護符", create_item_1_name="完好的護符", ...)`
                **請注意**: `delete_item_X` 指定的物品必須是 NPC 本次互動明確涉及的物品 (target_item 或 inventory_items)。

            2.  **ChangeItemDescriptionFunction**: 當物品的**狀態發生了變化**，但物品本身沒有被替換、創建或刪除，只是其描述需要更新時使用。
                例：NPC 把「空杯子」裝滿水 -> `ChangeItemDescriptionFunction(item_name="空杯子", new_description="一個裝滿了清水的杯子")`
                例：NPC 使用「電腦」上網後，電腦狀態可能沒有物理變化，但可以更新描述為「一台剛被使用過的電腦，螢幕還微熱」。

            3.  **MoveItemToInventoryFunction**: 當 NPC 從其**當前所處的空間中拾取某個物品**，並將其放入自己的庫存時使用。
                例：NPC 從地上撿起「鑰匙」 -> `MoveItemToInventoryFunction(item_name="鑰匙")`

            4.  **MoveItemFromInventoryToSpaceFunction**: 當 NPC 從**自己的庫存中取出某個物品**，並將其放置到當前所處的空間時使用。
                例：NPC 從背包中拿出「營火工具組」並放置在地上 -> `MoveItemFromInventoryToSpaceFunction(item_name="營火工具組")`
                
            如果 NPC 的行為不直接導致上述任何世界狀態的改變 (例如，NPC 只是在觀察、思考、或與環境進行非物品實體層面的互動)，則 function 欄位應為 `None`。
            """)
            
            response_to_AI: str = Field(description="""
            系統對 NPC 的回應，用自然語言描述 NPC 互動的結果以及世界狀態發生的具體變化。
            請務必生動、具體、且與執行的 function (如果有的話) 的結果保持一致。
            範例：
            - (使用 ModifyWorldItemsFunction 烹飪後): "你巧妙地將生雞肉和蔬菜一起下鍋，隨著一陣翻炒，廚房裡很快彌漫開誘人的香氣。一盤熱騰騰、香噴噴的炒時蔬雞丁就完成了！看起來非常美味。"
            - (使用 ModifyWorldItemsFunction 砍樹後): "你揮動斧頭，伴隨著木屑飛濺和清脆的斷裂聲，那棵松樹應聲倒下。你從中收集到了幾段結實的松木和一些還帶著清香的松果。"
            - (使用 ModifyWorldItemsFunction 從冰箱拿東西後): "你打開冰箱，冷氣撲面而來。你迅速找到了冰涼的牛奶和一盒新鮮的雞蛋，並把它們拿了出來。"
            - (使用 ChangeItemDescriptionFunction 給杯子裝水後): "你將空杯子湊到水龍頭下，清澈的水流注入其中，很快就裝滿了。現在這是一個盛著清水的杯子。"
            - (使用 MoveItemToInventoryFunction 撿起鑰匙後): "你彎下腰，撿起了掉在地上的那把冰冷的黃銅鑰匙，並將它妥善地放進了你的口袋裡。"
            - (如果 function 為 None，NPC 只是觀察): "你仔細地端詳著牆上的那幅古老畫像，畫中人物的眼神似乎帶有一絲神秘，但你並沒有發現任何可以互動的機關或線索。"
            """)

        return GeneralResponse

# --- 以下是 AI_System 其他方法的示意，實際內容待填充 ---
    def process_interaction(self, npc: "NPC", target_item_name: str, inventory_item_names: List[str], how_to_interact: str) -> str:
        """
        處理 NPC 與物品的互動。
        根據 NPC 的意圖、涉及的物品以及當前世界狀態，調用 LLM 來決定如何修改世界，
        並執行相應的操作。

        Args:
            npc: 執行互動的 NPC 物件。
            target_item_name: NPC 主要互動的目標物品的名稱。
            inventory_item_names: NPC 從其庫存中選取用於此次互動的輔助物品的名稱列表。
            how_to_interact: NPC 描述它希望如何與這些物品互動的自然語言字串。

        Returns:
            一個描述互動結果的自然語言字串，將回傳給 NPC。
        """
        global client # 假設 OpenAI client 是全局可用的

        # --- 1. 獲取並驗證互動中涉及的所有物品實體 ---
        target_item_object: Optional["Item"] = None # Forward reference for Item
        item_location_info = ""

        # 首先在 NPC 當前空間查找目標物品
        for item_in_space in npc.current_space.items:
            if item_in_space.name == target_item_name:
                target_item_object = item_in_space
                item_location_info = f"目標物品 '{target_item_name}' 位於空間 '{npc.current_space.name}'。"
                break
        
        if not target_item_object:
            for item_in_inv in npc.inventory.items:
                if item_in_inv.name == target_item_name:
                    target_item_object = item_in_inv
                    item_location_info = f"目標物品 '{target_item_name}' 位於 NPC '{npc.name}' 的庫存中。"
                    break
        
        if not target_item_object:
            return f"系統錯誤：找不到名為 '{target_item_name}' 的目標物品。互動中止。"

        list_of_inventory_item_objects: List["Item"] = [] # Forward reference for Item
        inventory_items_info_lines = []
        if inventory_item_names:
            inventory_items_info_lines.append("NPC 使用的庫存物品：")
            for inv_item_name in inventory_item_names:
                found_inv_item = False
                for item_obj in npc.inventory.items:
                    if item_obj.name == inv_item_name:
                        list_of_inventory_item_objects.append(item_obj)
                        inventory_items_info_lines.append(f"- '{item_obj.name}' (描述：'{item_obj.description}')")
                        found_inv_item = True
                        break
                if not found_inv_item:
                    return f"系統錯誤：NPC '{npc.name}' 的庫存中找不到名為 '{inv_item_name}' 的物品。互動中止。"

        # --- 2. 準備傳遞給 update_schema 的物品名稱列表 ---
        available_items_for_interaction = [target_item_object.name] + [item.name for item in list_of_inventory_item_objects]
        npc_complete_inventory = [item.name for item in npc.inventory.items]

        # --- 3. 動態生成 AI_System 使用的 Schema ---
        # GeneralResponse_For_This_Interaction 就是 self.update_schema 返回的那個在方法內部定義的 GeneralResponse 類
        GeneralResponse_For_This_Interaction = self.update_schema(available_items_for_interaction, npc_complete_inventory)

        # --- 4. 建構詳細的互動上下文 (Context) 給 LLM ---
        context_lines = [
            f"NPC '{npc.name}' (描述：'{npc.description}') 正在嘗試執行以下操作：'{how_to_interact}'.",
            item_location_info,
            f"主要目標物品詳細資訊：'{target_item_object.name}' (描述：'{target_item_object.description}', 屬性：{target_item_object.properties})."
        ]
        context_lines.extend(inventory_items_info_lines) # 加入使用的庫存物品資訊 (如果有的話)
        context_lines.append(f"目前世界時間：{self.time}, 天氣：{self.weather}.")
        # 移除了NPC完整物品庫的列表，因為 schema 的 Literal 已經處理了選擇範圍。
        # 但仍然告知 LLM 本次互動明確涉及的物品，有助於它理解 why 這些物品會出現在 Literal 中。
        context_lines.append(f"本次互動明確涉及的物品有：{', '.join(available_items_for_interaction) if available_items_for_interaction else '無明確目標物品 (可能為純粹的環境互動或無物品技能)' }。請確保你的功能選擇 (如刪除物品) 嚴格基於這些明確涉及的物品。")
        
        interaction_prompt_content = "\\n".join(context_lines)
        
        messages_for_llm = [
            {"role": "system", "content": "你是一個負責根據 NPC 意圖和世界狀態來決定如何修改遊戲世界的 AI 系統。請仔細分析以下提供的完整情境，然後根據你的理解，選擇一個最合適的 `function` 來執行（其參數選項已根據情境被限定），同時提供你的 `reasoning`（思考過程）和給 NPC 的 `response_to_AI`（自然語言回應）。如果 NPC 的意圖不需要改變世界物品狀態（例如只是觀察），則 `function` 應該為 `None`。"},
            {"role": "user", "content": interaction_prompt_content}
        ]
        
        print("\\n=== AI_System 向 LLM 發送的內容 ===")
        print(f"模型: gpt-4o-2024-11-20")
        print(interaction_prompt_content)
        print("================================\\n")

        # --- 5. 呼叫 LLM 並使用動態 Schema 解析回應 ---
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o-2024-11-20", # 使用指定的模型
                messages=messages_for_llm,
                response_format=GeneralResponse_For_This_Interaction # 使用 update_schema 返回的動態類
            )
            ai_system_response = completion.choices[0].message.parsed
        except Exception as e:
            error_msg = f"AI_System在與LLM溝通或解析回應時發生錯誤: {str(e)}"
            print(f"[錯誤] {error_msg}")
            return f"我現在有點糊塗，暫時無法完成 '{how_to_interact}' 這個操作。"

        print("\\n=== AI_System 從 LLM 收到的原始回應 (parsed) ===")
        print(ai_system_response)
        print("===========================================\\n")

        # --- 6. 記錄 AI_System 的思考和給 NPC 的回應到其歷史 ---
        self.history.append({
            "role": "assistant", 
            "content": f"針對NPC '{npc.name}' 的意圖 '{how_to_interact}' (涉及物品: {', '.join(available_items_for_interaction)}):\\n  系統思考: {ai_system_response.reasoning}\\n  計劃給NPC的回應: {ai_system_response.response_to_AI}"
        })

        # --- 7. 處理 AI_System.Function 呼叫 ---
        function_execution_details = "沒有執行功能。"
        if ai_system_response.function:
            try:
                function_execution_details = self._handle_function(ai_system_response.function, npc, available_items_for_interaction)
                self.history.append({
                    "role": "system", 
                    "content": f"系統執行功能 (由NPC '{npc.name}' 觸發，意圖: '{how_to_interact}'):\\n  功能類型: {str(ai_system_response.function.function_type if hasattr(ai_system_response.function, 'function_type') else '未知')}\\n  功能參數: {str(ai_system_response.function.model_dump(exclude_none=True))}\\n  執行結果: {function_execution_details}"
                })
            except Exception as e:
                error_msg = f"AI_System在執行內部功能 '{str(ai_system_response.function.function_type if hasattr(ai_system_response.function, 'function_type') else '未知')}' 時發生錯誤: {str(e)}"
                print(f"[錯誤] {error_msg}")
                self.history.append({"role": "system", "content": f"[錯誤日誌] {error_msg}"})
                return f"我在嘗試 '{how_to_interact}' 的時候遇到了一些內部問題，可能沒有完全成功。"

        # --- 8. 返回給 NPC 的結果 ---
        return ai_system_response.response_to_AI

    def _handle_function(self, function_call: Any, npc: "NPC", available_items_for_interaction: List[str]) -> str:
        """
        根據 LLM 返回的 function_call 物件的類型，分派給相應的內部方法執行世界狀態的修改。

        Args:
            function_call: LLM 選擇的 Function 物件的實例。
                           它將是 AI_System.update_schema 內部定義的某個動態 Function 類別的實例。
            npc: 執行此互動的 NPC 物件。
            available_items_for_interaction: NPC 本次互動明確聲明要使用的所有物品的名稱列表
                                             (target_item + inventory_items from NPC's action)。
                                             用於在具體操作方法中進行額外的合法性驗證。
        Returns:
            一個描述功能執行結果的字串。
        """
        if not function_call: # LLM 可能決定不執行任何 function
            return "沒有功能被執行。"

        # 檢查 function_call 是否真的有 function_type 屬性，以防意外
        if not hasattr(function_call, 'function_type'):
            error_msg = f"收到的 function_call 物件缺少 'function_type' 屬性: {function_call}"
            print(f"[錯誤] {error_msg}")
            return f"系統內部錯誤：功能調用格式不正確。"

        function_type = function_call.function_type
        print(f"[系統日誌] _handle_function 接收到功能類型: {function_type}")
        print(f"[系統日誌] 功能參數: {function_call.model_dump(exclude_none=True)}")


        if function_type == "modify_world_items":
            # 斷言以確保類型正確，雖然 Pydantic 在解析時應該已經保證了
            # 實際上，由於 function_call 是動態類型，這裡的 isinstance 檢查可能不夠直接
            # 我們主要依賴 function_type 字串來判斷
            # if not isinstance(function_call, self.ModifyWorldItemsFunction): # 這裡的 self.ModifyWorldItemsFunction 是靜態藍本
            #     return f"內部錯誤：modify_world_items 功能的類型不匹配。"
            return self._modify_world_items_impl(function_call, npc, available_items_for_interaction)
        
        elif function_type == "change_item_description":
            # if not isinstance(function_call, self.ChangeItemDescriptionFunction):
            #     return f"內部錯誤：change_item_description 功能的類型不匹配。"
            return self._change_item_description_impl(function_call, npc, available_items_for_interaction)
            
        elif function_type == "move_item_to_inventory":
            # if not isinstance(function_call, self.MoveItemToInventoryFunction):
            #     return f"內部錯誤：move_item_to_inventory 功能的類型不匹配。"
            return self._move_item_to_inventory_impl(function_call, npc, available_items_for_interaction)
            
        elif function_type == "move_item_from_inventory_to_space":
            # if not isinstance(function_call, self.MoveItemFromInventoryToSpaceFunction):
            #     return f"內部錯誤：move_item_from_inventory_to_space 功能的類型不匹配。"
            return self._move_item_from_inventory_to_space_impl(function_call, npc) # 此功能的操作對象來自NPC完整庫存，其合法性在schema生成時已限定

        else:
            error_msg = f"未知的 function_type: '{function_type}'"
            print(f"[警告] {error_msg}")
            return error_msg

    def _modify_world_items_impl(self, function_call: Any, npc: "NPC", available_items_for_interaction: List[str]) -> str:
        """
        實現 ModifyWorldItemsFunction 的核心邏輯：處理物品的刪除和創建。

        Args:
            function_call: LLM 返回的、AI_System.update_schema 內部定義的 ModifyWorldItemsFunction 類的實例。
                         它包含了 delete_item_X 和 create_item_X_name/description 等欄位。
            npc: 執行此互動的 NPC 物件。
            available_items_for_interaction: NPC 本次互動明確聲明要使用的所有物品的名稱列表。
                                             用於驗證 delete_item_X 的合法性。
        Returns:
            一個描述物品修改結果的字串。
        """
        results_log = [] # 用於記錄每一步操作的結果，最後匯總

        # --- 1. 處理物品刪除 ---
        items_to_delete_names: List[str] = []
        if hasattr(function_call, 'delete_item_1') and function_call.delete_item_1: items_to_delete_names.append(function_call.delete_item_1)
        if hasattr(function_call, 'delete_item_2') and function_call.delete_item_2: items_to_delete_names.append(function_call.delete_item_2)
        if hasattr(function_call, 'delete_item_3') and function_call.delete_item_3: items_to_delete_names.append(function_call.delete_item_3)
        if hasattr(function_call, 'delete_item_4') and function_call.delete_item_4: items_to_delete_names.append(function_call.delete_item_4)
        if hasattr(function_call, 'delete_item_5') and function_call.delete_item_5: items_to_delete_names.append(function_call.delete_item_5)
        
        successfully_deleted_item_names: List[str] = []

        for item_name_to_delete in items_to_delete_names:
            if not item_name_to_delete: # 以防萬一，雖然 Pydantic Optional 應該處理了
                continue

            # **驗證1：要刪除的物品是否在本次互動明確涉及的物品列表中**
            if item_name_to_delete not in available_items_for_interaction:
                msg = f"警告：AI 試圖刪除未在本次互動中明確指定的物品 '{item_name_to_delete}'。已忽略此刪除操作。"
                print(f"[警告] {msg}")
                results_log.append(msg)
                continue

            deleted_from_where = None
            # 嘗試從 NPC 庫存中刪除
            item_found_in_inventory = False
            for i, item_in_inv in enumerate(npc.inventory.items):
                if item_in_inv.name == item_name_to_delete:
                    npc.inventory.items.pop(i)
                    deleted_from_where = f"NPC '{npc.name}' 的庫存"
                    item_found_in_inventory = True
                    break
            
            # 如果不在 NPC 庫存，嘗試從當前空間刪除
            if not item_found_in_inventory:
                item_found_in_space = False
                for i, item_in_space in enumerate(npc.current_space.items):
                    if item_in_space.name == item_name_to_delete:
                        npc.current_space.items.pop(i)
                        deleted_from_where = f"空間 '{npc.current_space.name}'"
                        item_found_in_space = True
                        break
                
                if not item_found_in_space:
                    msg = f"警告：在嘗試刪除時，未能從 NPC 庫存或當前空間找到物品 '{item_name_to_delete}'（即使它在 available_items_for_interaction 中）。"
                    print(f"[警告] {msg}")
                    results_log.append(msg)
                    continue # 繼續處理下一個要刪除的物品

            # 如果物品成功從某處刪除，也嘗試從全局物品列表 self.world["items"] 中移除
            # 注意：這裡需要更完善的引用計數機制，如果該物品實例還被其他地方引用（例如另一個NPC的庫存），則不應從全局移除。
            # 簡化處理：如果全局字典中有同名物品，就直接刪除。在更複雜的系統中，物品應該有唯一ID。
            if deleted_from_where and item_name_to_delete in self.world.get("items", {}):
                try:
                    del self.world["items"][item_name_to_delete]
                    msg = f"物品 '{item_name_to_delete}' 已成功從 {deleted_from_where} 和全局物品列表中刪除。"
                    print(f"[系統日誌] {msg}")
                    results_log.append(msg)
                    successfully_deleted_item_names.append(item_name_to_delete)
                except KeyError:
                    msg = f"警告：嘗試從全局物品列表刪除 '{item_name_to_delete}' 時發生 KeyError (可能已被其他操作刪除)。"
                    print(f"[警告] {msg}")
                    results_log.append(msg) # 仍然認為從NPC/空間是成功的
                    if item_name_to_delete not in successfully_deleted_item_names: # 避免重複添加
                         successfully_deleted_item_names.append(item_name_to_delete)

            elif deleted_from_where: # 僅從NPC/空間刪除，但全局列表不存在或已刪除
                msg = f"物品 '{item_name_to_delete}' 已成功從 {deleted_from_where} 刪除。"
                print(f"[系統日誌] {msg}")
                results_log.append(msg)
                successfully_deleted_item_names.append(item_name_to_delete)

        # --- 2. 處理物品創建 ---
        items_to_create_details: List[Tuple[Optional[str], Optional[str]]] = []
        if hasattr(function_call, 'create_item_1_name'): items_to_create_details.append((function_call.create_item_1_name, getattr(function_call, 'create_item_1_description', None)))
        if hasattr(function_call, 'create_item_2_name'): items_to_create_details.append((function_call.create_item_2_name, getattr(function_call, 'create_item_2_description', None)))
        if hasattr(function_call, 'create_item_3_name'): items_to_create_details.append((function_call.create_item_3_name, getattr(function_call, 'create_item_3_description', None)))
        if hasattr(function_call, 'create_item_4_name'): items_to_create_details.append((function_call.create_item_4_name, getattr(function_call, 'create_item_4_description', None)))
        if hasattr(function_call, 'create_item_5_name'): items_to_create_details.append((function_call.create_item_5_name, getattr(function_call, 'create_item_5_description', None)))

        successfully_created_item_names: List[str] = []

        for item_name_to_create, item_description in items_to_create_details:
            if item_name_to_create and item_description: # 必須同時有名稱和描述才創建
                # **驗證2：要創建的物品名稱是否已存在於全局？** (簡單的重名檢查，可以根據遊戲設計調整)
                if item_name_to_create in self.world.get("items", {}):
                    # 處理重名：可以選擇創建一個帶後綴的新物品，或直接覆蓋，或報錯。
                    # 這裡選擇報錯並跳過，以保持物品名稱的（假設）唯一性。
                    msg = f"警告：嘗試創建的物品 '{item_name_to_create}' 已存在於世界中。已忽略此創建操作。"
                    print(f"[警告] {msg}")
                    results_log.append(msg)
                    continue

                # 創建新 Item 物件
                # 注意：Item 類的定義需要在 AI_System 之前，或者使用 Forward Reference "Item"
                try:
                    # 假設 Item 類已正確導入或定義
                    from . import Item # 或者根據您的專案結構調整導入
                    new_item = Item(
                        name=item_name_to_create,
                        description=item_description,
                        properties={}, # 可以根據需要從 LLM 的 reasoning 或其他地方獲取 properties
                        # position 和 size 通常在創建時不指定，或由特定邏輯處理
                    )
                except ImportError:
                     return "系統內部錯誤：無法找到 Item 類定義。"
                except Exception as e:
                    return f"系統內部錯誤：創建 Item 物件 '{item_name_to_create}' 時失敗: {e}"


                # 將新物品添加到 NPC 的庫存
                add_result = npc.inventory.add_item(new_item) # Inventory.add_item 應該返回一個描述結果的字串
                
                # 將新物品添加到全局物品列表 self.world["items"]
                if "items" not in self.world: # 確保 self.world["items"] 存在
                    self.world["items"] = {}
                self.world["items"][new_item.name] = new_item
                
                msg = f"新物品 '{new_item.name}' 已成功創建並加入 NPC '{npc.name}' 的庫存 ({add_result.strip('.')})."
                print(f"[系統日誌] {msg}")
                results_log.append(msg)
                successfully_created_item_names.append(new_item.name)
            
            elif item_name_to_create and not item_description:
                msg = f"警告：嘗試創建物品 '{item_name_to_create}' 但缺少描述。已忽略此創建操作。"
                print(f"[警告] {msg}")
                results_log.append(msg)

        # --- 3. 匯總結果 ---
        final_summary_parts = []
        if successfully_deleted_item_names:
            final_summary_parts.append(f"成功刪除了物品：{', '.join(successfully_deleted_item_names)}")
        else:
            final_summary_parts.append("沒有物品被刪除")
        
        if successfully_created_item_names:
            final_summary_parts.append(f"成功創建並將下列物品加入 '{npc.name}' 的庫存：{', '.join(successfully_created_item_names)}")
        else:
            final_summary_parts.append("沒有新物品被創建")
            
        # 如果 results_log 中有其他警告或特定信息，也可以考慮加入到最終返回給 _handle_function 的字串中
        # 例如: detailed_log = " 操作詳情: " + " | ".join(results_log)
        
        return "。 ".join(final_summary_parts) + "。"

    def _change_item_description_impl(self, function_call: Any, npc: "NPC", available_items_for_interaction: List[str]) -> str:
        """
        實現 ChangeItemDescriptionFunction 的具體操作。
        這個方法應該根據 function_call 的具體參數來執行相應的操作。
        例如：修改物品描述、更新物品狀態等。

        Args:
            function_call: LLM 選擇的 Function 物件的實例。
            npc: 執行此互動的 NPC 物件。
            available_items_for_interaction: NPC 本次互動明確聲明要使用的所有物品的名稱列表
                                             (target_item + inventory_items from NPC's action)。
                                             用於在具體操作方法中進行額外的合法性驗證。
        Returns:
            一個描述功能執行結果的字串。
        """
        # 這裡應該實現 ChangeItemDescriptionFunction 的具體操作邏輯
        # 例如：修改物品描述、更新物品狀態等
        return "ChangeItemDescriptionFunction 的具體操作尚未實現。"

    def _move_item_to_inventory_impl(self, function_call: Any, npc: "NPC", available_items_for_interaction: List[str]) -> str:
        """
        實現 MoveItemToInventoryFunction 的具體操作。
        這個方法應該根據 function_call 的具體參數來執行相應的操作。
        例如：將物品從空間移動到 NPC 庫存、從 NPC 庫存中取出物品等。

        Args:
            function_call: LLM 選擇的 Function 物件的實例。
            npc: 執行此互動的 NPC 物件。
            available_items_for_interaction: NPC 本次互動明確聲明要使用的所有物品的名稱列表
                                             (target_item + inventory_items from NPC's action)。
                                             用於在具體操作方法中進行額外的合法性驗證。
        Returns:
            一個描述功能執行結果的字串。
        """
        # 這裡應該實現 MoveItemToInventoryFunction 的具體操作邏輯
        # 例如：將物品從空間移動到 NPC 庫存、從 NPC 庫存中取出物品等
        return "MoveItemToInventoryFunction 的具體操作尚未實現。"

    def _move_item_from_inventory_to_space_impl(self, function_call: Any, npc: "NPC") -> str:
        """
        實現 MoveItemFromInventoryToSpaceFunction 的具體操作。
        這個方法應該根據 function_call 的具體參數來執行相應的操作。
        例如：將物品從 NPC 庫存中取出並放置到空間、從 NPC 庫存中取出物品等。

        Args:
            function_call: LLM 選擇的 Function 物件的實例。
            npc: 執行此互動的 NPC 物件。
        Returns:
            一個描述功能執行結果的字串。
        """
        # 這裡應該實現 MoveItemFromInventoryToSpaceFunction 的具體操作邏輯
        # 例如：將物品從 NPC 庫存中取出並放置到空間、從 NPC 庫存中取出物品等
        return "MoveItemFromInventoryToSpaceFunction 的具體操作尚未實現。"




# Run the sandbox
if __name__ == "__main__":
    SandBox()





#A TODO: List?
#TODO: Implemente a better Multiple NPCs support, like same room serial run with 1 s delay, different room npc.process_tick should run simultaneously, serial vs parallel. The current way seems to be able to achieve this but way to complicated
