from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Union, Literal, List, Optional, Dict, Any, Annotated
import json
import os
import glob

client = OpenAI()
# 設定全局變量使 NPC 類可以訪問
world_system = None

#NOTE: Item

# 定義基礎 Item 類

class Item(BaseModel):
    name: str
    description: str
    # Simpler interaction definition:
    # - If value is None: no parameters needed
    # - If value is dict: specifies required parameters and their types
    properties: Dict[str, Any] = {}



#NOTE: Space 空間 class

# 定義 Space 類
class Space(BaseModel):
    name: str  # Space name, e.g., "kitchen" or "living_room"
    description: str  # Description of the space
    connected_spaces: List["Space"] = []  # Connected spaces (bidirectional relationships)
    items: List["Item"] = []  # Items in the space
    npcs: List["NPC"] = Field(default_factory=list)  # NPCs currently in the space

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

        # 定義空間移動操作
        class EnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: Literal[*valid_spaces] if valid_spaces else str = Field(description="移動到的空間名稱")

        # 定義與 NPC 對話操作
        class TalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: Literal[*valid_npcs] if valid_npcs else str = Field(description="對話對象的名稱")
            dialogue: str = Field(description="想要說的話")

        # 定義物品互動操作（新版本）
        class InteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            interact_with: Literal[*available_items] if available_items else str = Field(description="要互動的物品名稱")
            how_to_interact: str = Field(description="詳細描述如何與物品互動。請使用描述性語言，清楚說明你想要如何使用或操作這個物品。")

        # 頂層響應
        class GeneralResponse(BaseModel):
            self_talk_reasoning: str = Field(description="你對當前情況的思考和分析")
            action: Optional[Union[
                EnterSpaceAction,
                InteractItemAction,
                TalkToNPCAction
            ]] = Field(None, description="你想要執行的動作")
        
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

        # Add AI's self-reasoning and action to history
        reasoning_content = f"Thinking: {response.self_talk_reasoning}"
        self.history.append({"role": "assistant", "content": reasoning_content})
        
        # Add the attempted action to history if one exists
        if response.action:
            if hasattr(response.action, "action_type"):
                if response.action.action_type == "interact_item":
                    action_content = f"Action: I'm interacting with {response.action.interact_with} by {response.action.how_to_interact}"
                elif response.action.action_type == "enter_space":
                    action_content = f"Action: I'm moving to {response.action.target_space}"
                elif response.action.action_type == "talk_to_npc":
                    action_content = f"Action: I'm talking to {response.action.target_npc} saying: {response.action.dialogue}"
                else:
                    action_content = "Action: Attempting an unknown action type"
            else:
                action_content = "Action: Action has no type specified"
                
            self.history.append({"role": "assistant", "content": action_content})
        
        print("\n=== AI Response ===")
        print(response)
        print("==================\n")

        # Handle the action
        if not response.action:
            print("No action taken")
            return "Nothing happened."

        action = response.action
        result = ""
        
        # Process the action based on its type
        if hasattr(action, "action_type"):
            if action.action_type == "interact_item":
                # 使用新的互動系統處理物品互動
                result = world_system.process_interaction(
                    self, 
                    action.interact_with, 
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

        self.history.append({"role": "system", "content": result})
        print("\n=== Action Result ===")
        print(result)
        print("===================\n")
        return result

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




# Resolve forward references
Space.model_rebuild()





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
            name=space_data["name"],
            description=space_data["description"],
            connected_spaces=[],  # 後續連接
            items=[],  # 後續添加物品
            npcs=[]  # 後續添加 NPC
        )
    
    # 第二步: 創建所有物品
    for item_data in world_data.get("items", []):
        # 使用簡化的 Item 類創建物品（沒有 interactions 欄位）
        items_dict[item_data["name"]] = Item(
            name=item_data["name"],
            description=item_data["description"],
            properties=item_data.get("properties", {})
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
            # 創建 NPC
            npc = NPC(
                name=npc_data["name"],
                description=npc_data["description"],
                current_space=starting_space,
                inventory=inventory,
                history=npc_data.get("history", [])
            )
            
            # 將 NPC 添加到其起始空間
            starting_space.npcs.append(npc)
            
            # 將 NPC 存儲在字典中
            npcs_dict[npc_data["name"]] = npc
    
    return {
        "world_name": world_data.get("world_name", "未知世界"),
        "description": world_data.get("description", ""),
        "spaces": spaces_dict,
        "items": items_dict,
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
    return os.path.join("worlds/maps", user_input)

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
    time: str = "中午"  # 時間描述
    weather: str = "晴朗"  # 天氣描述
    history: List[Dict[str, str]] = []  # 系統歷史記錄
    world: Dict[str, Any] = {}  # 世界狀態的引用
    
    class CreateItemFunction(BaseModel):
        function_type: Literal["create_item"]
        item_name: str = Field(description="新物品的名稱")
        description: str = Field(description="新物品的描述")
        space_name: str = Field(description="物品將被放置的空間名稱")
    
    class DeleteItemFunction(BaseModel):
        function_type: Literal["delete_item"]
        item_name: str = Field(description="要刪除的物品名稱")
        space_name: Optional[str] = Field(None, description="物品所在的空間名稱（如果不在任何 NPC 的庫存中）")
        npc_name: Optional[str] = Field(None, description="持有物品的 NPC 名稱（如果在 NPC 的庫存中）")
    
    class ChangeItemDescriptionFunction(BaseModel):
        function_type: Literal["change_item_description"]
        item_name: str = Field(description="要修改的物品名稱")
        new_description: str = Field(description="物品的新描述")
    
    class DeleteAndCreateNewItemFunction(BaseModel):
        function_type: Literal["delete_and_create_new_item"]
        old_item_name: str = Field(description="要替換的物品名稱")
        new_item_name: str = Field(description="新物品的名稱")
        new_description: str = Field(description="新物品的描述")
        space_name: str = Field(description="物品所在的空間名稱")
    
    class MoveItemToInventoryFunction(BaseModel):
        function_type: Literal["move_item_to_inventory"]
        item_name: str = Field(description="要移動的物品名稱")
        npc_name: str = Field(description="接收物品的 NPC 名稱")
    
    class GeneralResponse(BaseModel):
        reasoning: str = Field(description="系統對 NPC 行為的內部分析和思考")
        response_to_AI: str = Field(description="系統對 NPC 的回應，描述行為結果")
        function: Optional[Union[
            "AI_System.CreateItemFunction",
            "AI_System.DeleteItemFunction",
            "AI_System.ChangeItemDescriptionFunction",
            "AI_System.DeleteAndCreateNewItemFunction",
            "AI_System.MoveItemToInventoryFunction"
        ]] = None
    
    def initialize_world(self, world: Dict[str, Any]):
        """
        初始化系統並儲存世界狀態的引用。
        
        Args:
            world: 包含世界狀態的字典
        """
        self.world = world
    
    def process_interaction(self, npc: "NPC", item_name: str, how_to_interact: str) -> str:
        """
        處理 NPC 與物品的互動。
        
        Args:
            npc: 執行互動的 NPC
            item_name: 互動物品的名稱
            how_to_interact: 描述 NPC 如何與物品互動
            
        Returns:
            互動結果的描述字串
        """
        # 確認物品存在
        target_item = None
        item_location = None
        
        # 檢查 NPC 的庫存
        for item in npc.inventory.items:
            if item.name == item_name:
                target_item = item
                item_location = "inventory"
                break
        
        # 檢查當前空間
        if target_item is None:
            for item in npc.current_space.items:
                if item.name == item_name:
                    target_item = item
                    item_location = "space"
                    break
        
        if target_item is None:
            return f"找不到名為 '{item_name}' 的物品。"
        
        # 準備互動訊息
        interaction_message = {
            "role": "system",
            "content": f"{npc.name} 正在嘗試與 {item_name} 互動：{how_to_interact}\n"
                      f"物品描述: {target_item.description}\n"
                      f"物品位置: {'NPC 的庫存中' if item_location == 'inventory' else '當前空間'}"
        }
        
        # 將互動訊息加入歷史記錄
        self.history.append(interaction_message)
        
        # 使用 AI 來解釋互動並生成響應
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=self.history,
            response_format=self.GeneralResponse
        )
        response = completion.choices[0].message.parsed
        
        # 將 AI 的解釋和響應添加到歷史記錄
        self.history.append({
            "role": "assistant",
            "content": f"系統思考: {response.reasoning}\n回應: {response.response_to_AI}"
        })
        
        # 處理可能的功能調用
        if response.function:
            result = self._handle_function(response.function, npc)
            if result:
                self.history.append({
                    "role": "system",
                    "content": f"系統執行功能: {result}"
                })
        
        return response.response_to_AI
    
    def _handle_function(self, function: Any, npc: "NPC") -> str:
        """
        根據功能類型處理功能調用。
        
        Args:
            function: 要執行的功能
            npc: 觸發功能的 NPC
            
        Returns:
            功能執行結果的描述
        """
        if hasattr(function, "function_type"):
            if function.function_type == "create_item":
                return self._create_item(function.item_name, function.description, function.space_name)
            elif function.function_type == "delete_item":
                return self._delete_item(function.item_name, function.space_name, function.npc_name)
            elif function.function_type == "change_item_description":
                return self._change_item_description(function.item_name, function.new_description)
            elif function.function_type == "delete_and_create_new_item":
                return self._delete_and_create_new_item(
                    function.old_item_name, function.new_item_name, 
                    function.new_description, function.space_name
                )
            elif function.function_type == "move_item_to_inventory":
                return self._move_item_to_inventory(function.item_name, function.npc_name)
        
        return "未知的功能類型。"
    
    def _create_item(self, item_name: str, description: str, space_name: str) -> str:
        """創建新物品並放入指定空間。"""
        space = self.world["spaces"].get(space_name)
        if not space:
            return f"找不到名為 '{space_name}' 的空間。"
        
        # 創建新物品（不再需要 interactions）
        new_item = Item(
            name=item_name,
            description=description,
            properties={}  # 默認空屬性
        )
        
        # 將物品添加到世界物品字典中
        self.world["items"][item_name] = new_item
        
        # 將物品添加到空間
        space.items.append(new_item)
        
        return f"在 {space_name} 創建了新物品: {item_name}"
    
    def _delete_item(self, item_name: str, space_name: Optional[str], npc_name: Optional[str]) -> str:
        """從空間或 NPC 庫存中刪除物品。"""
        # 從空間中刪除
        if space_name:
            space = self.world["spaces"].get(space_name)
            if not space:
                return f"找不到名為 '{space_name}' 的空間。"
            
            for i, item in enumerate(space.items):
                if item.name == item_name:
                    space.items.pop(i)
                    # 如果物品不被任何其他地方引用，則從世界中刪除
                    if item_name in self.world["items"]:
                        del self.world["items"][item_name]
                    return f"從 {space_name} 刪除了物品: {item_name}"
        
        # 從 NPC 庫存中刪除
        if npc_name:
            npc = self.world["npcs"].get(npc_name)
            if not npc:
                return f"找不到名為 '{npc_name}' 的 NPC。"
            
            for i, item in enumerate(npc.inventory.items):
                if item.name == item_name:
                    npc.inventory.items.pop(i)
                    # 如果物品不被任何其他地方引用，則從世界中刪除
                    if item_name in self.world["items"]:
                        del self.world["items"][item_name]
                    return f"從 {npc_name} 的庫存中刪除了物品: {item_name}"
        
        return f"找不到物品 '{item_name}'。"
    
    def _change_item_description(self, item_name: str, new_description: str) -> str:
        """修改物品的描述。"""
        if item_name in self.world["items"]:
            item = self.world["items"][item_name]
            item.description = new_description
            return f"更新了物品 '{item_name}' 的描述。"
        return f"找不到物品 '{item_name}'。"
    
    def _delete_and_create_new_item(self, old_item_name: str, new_item_name: str, 
                                   new_description: str, space_name: str) -> str:
        """刪除舊物品並創建新物品（例如：修復損壞的物品）。"""
        # 刪除舊物品
        delete_result = self._delete_item(old_item_name, space_name, None)
        if "刪除了物品" not in delete_result:
            return f"無法替換物品：{delete_result}"
        
        # 創建新物品
        create_result = self._create_item(new_item_name, new_description, space_name)
        if "創建了新物品" not in create_result:
            return f"刪除了舊物品，但無法創建新物品：{create_result}"
        
        return f"將 '{old_item_name}' 替換為 '{new_item_name}'。"
    
    def _move_item_to_inventory(self, item_name: str, npc_name: str) -> str:
        """將物品從當前空間移動到 NPC 的庫存中。"""
        npc = self.world["npcs"].get(npc_name)
        if not npc:
            return f"找不到名為 '{npc_name}' 的 NPC。"
        
        # 在當前空間中查找物品
        item = None
        for i, space_item in enumerate(npc.current_space.items):
            if space_item.name == item_name:
                item = space_item
                npc.current_space.items.pop(i)
                break
        
        if not item:
            return f"在 {npc.current_space.name} 中找不到物品 '{item_name}'。"
        
        # 將物品添加到 NPC 的庫存
        result = npc.inventory.add_item(item)
        return f"{npc_name} 撿起了 {item_name}。{result}"




# Run the sandbox
if __name__ == "__main__":
    SandBox()

