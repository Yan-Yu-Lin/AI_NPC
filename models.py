from typing import List, Optional, Dict, Any, Union, Literal, Tuple
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI()
world_system = None  # 由主程式初始化

# Item 類
class Item(BaseModel):
    name: str
    description: str
    properties: Dict[str, Any] = {}

# Inventory 類
class Inventory(BaseModel):
    items: List[Item] = []
    capacity: Optional[int] = None

    def add_item(self, item: Item) -> str:
        if self.capacity is not None and len(self.items) >= self.capacity:
            return f"Cannot add {item.name}. Inventory is full."
        self.items.append(item)
        return f"Added {item.name} to inventory."
    def remove_item(self, item_name: str) -> str:
        for i, item in enumerate(self.items):
            if item.name == item_name:
                removed_item = self.items.pop(i)
                return f"Removed {removed_item.name} from inventory."
        return f"Item with name '{item_name}' not found in inventory."
    def has_item(self, item_name: str) -> bool:
        return any(item.name == item_name for item in self.items)
    def list_items(self) -> str:
        if not self.items:
            return "Inventory is empty."
        return "\n".join([f"- {item.name}: {item.description}" for item in self.items])

# Space 類
class Space(BaseModel):
    name: str
    description: str
    connected_spaces: List["Space"] = []
    items: List["Item"] = []
    npcs: List["NPC"] = Field(default_factory=list)
    display_pos: Tuple[int, int] = (0, 0)  # for pygame display
    display_size: Tuple[int, int] = (0, 0)  # for pygame display

    def biconnect(self, other_space: "Space") -> None:
        if other_space not in self.connected_spaces:
            self.connected_spaces.append(other_space)
        if self not in other_space.connected_spaces:
            other_space.connected_spaces.append(self)
    def __str__(self) -> str:
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

# NPC 類
class NPC(BaseModel):
    name: str
    description: str
    current_space: Space
    inventory: Inventory
    history: List[Dict[str, str]] = []
    first_tick: bool = True
    display_color: Tuple[int, int, int] = (0, 0, 0)  # for pygame display
    display_pos: Tuple[int, int] = (0, 0)  # for pygame display
    radius: int = 24  # for pygame display
    position: Tuple[int, int] = (0, 0)  # for movement/animation
    move_target: Optional[list] = None  # 目標座標
    move_speed: float = 6  # 每幀移動速度
    # 其他行為欄位略

    def __init__(self, **data):
        super().__init__(**data)
        # 初始化時自動同步 position 與 display_pos
        if hasattr(self, 'display_pos'):
            self.position = list(self.display_pos)

    def update_schema(self):
        valid_spaces = [space.name for space in self.current_space.connected_spaces]
        valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
        available_items = [item.name for item in self.current_space.items + self.inventory.items]
        class EnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: Literal[*valid_spaces] if valid_spaces else str = Field(description="移動到的空間名稱")
        class TalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: Literal[*valid_npcs] if valid_npcs else str = Field(description="對話對象的名稱")
            dialogue: str = Field(description="想要說的話")
        class InteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            interact_with: Literal[*available_items] if available_items else str = Field(description="要互動的物品名稱")
            how_to_interact: str = Field(description="詳細描述如何與物品互動。請使用描述性語言，清楚說明你想要如何使用或操作這個物品。")
        class GeneralResponse(BaseModel):
            self_talk_reasoning: str = Field(description="你對當前情況的思考和分析")
            action: Optional[Union[
                EnterSpaceAction,
                InteractItemAction,
                TalkToNPCAction
            ]] = Field(None, description="你想要執行的動作")
        return GeneralResponse

    def add_space_to_history(self):
        self.history.append({"role": "system", "content": str(self.current_space)})

    def print_current_schema(self):
        try:
            print("\n=== GeneralResponse Schema ===")
            schema = self.update_schema().model_json_schema()
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
            print(f"Current space: {self.current_space.name}")
            print(f"Available items: {[item.name for item in self.current_space.items + self.inventory.items]}")
            print(f"Available NPCs: {[npc.name for npc in self.current_space.npcs if npc != self]}")

    def move_to_space(self, target_space_name: str) -> str:
        target_space_name = target_space_name.lower()
        for connected_space in self.current_space.connected_spaces:
            if connected_space.name.lower() == target_space_name:
                if self in self.current_space.npcs:
                    self.current_space.npcs.remove(self)
                connected_space.npcs.append(self)
                self.current_space = connected_space
                self.add_space_to_history()
                return f"Moved to {connected_space.name}.\n{str(connected_space)}"
        return f"Cannot move to {target_space_name}. It is not connected to {self.current_space.name}."

    def process_tick(self, user_input: Optional[str] = None, move_callback=None):
        GeneralResponse = self.update_schema()
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
        reasoning_content = f"self_talk_reasoning='{response.self_talk_reasoning}'"
        last_reasoning_content = response.self_talk_reasoning
        self.history.append({"role": "assistant", "content": reasoning_content})
        # 讓聊天氣泡顯示這一行
        last_reasoning = last_reasoning_content
        if not response.action:
            print("No action taken")
            return last_reasoning
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
        if not response.action:
            print("No action taken")
            return last_reasoning
        action = response.action
        result = ""
        if hasattr(action, "action_type"):
            if action.action_type == "interact_item":
                if move_callback:
                    move_callback(self, action.interact_with)
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
        return last_reasoning

    def talk_to_npc(self, target_npc_name: str, dialogue: str) -> str:
        target_npc = None
        for npc in self.current_space.npcs:
            if npc.name.lower() == target_npc_name.lower() and npc != self:
                target_npc = npc
                break
        if target_npc is None:
            return f"Cannot find NPC '{target_npc_name}' in the current space."
        return f"{self.name} says to {target_npc.name}: \"{dialogue}\""

# 解決 forward reference
Space.model_rebuild()
NPC.model_rebuild()

class AI_System(BaseModel):
    time: str = "中午"
    weather: str = "晴朗"
    history: List[Dict[str, str]] = []
    world: Dict[str, Any] = {}

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
        self.world = world

    def process_interaction(self, npc: "NPC", item_name: str, how_to_interact: str) -> str:
        target_item = None
        item_location = None
        for item in npc.inventory.items:
            if item.name == item_name:
                target_item = item
                item_location = "inventory"
                break
        if target_item is None:
            for item in npc.current_space.items:
                if item.name == item_name:
                    target_item = item
                    item_location = "space"
                    break
        if target_item is None:
            return f"找不到名為 '{item_name}' 的物品。"
        interaction_message = {
            "role": "system",
            "content": f"{npc.name} 正在嘗試與 {item_name} 互動：{how_to_interact}\n"
                       f"物品描述: {target_item.description}\n"
                       f"物品位置: {'NPC 的庫存中' if item_location == 'inventory' else '當前空間'}"
        }
        self.history.append(interaction_message)
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-2024-11-20",
            messages=self.history,
            response_format=self.GeneralResponse
        )
        response = completion.choices[0].message.parsed
        self.history.append({
            "role": "assistant",
            "content": f"系統思考: {response.reasoning}\n回應: {response.response_to_AI}"
        })
        if response.function:
            result = self._handle_function(response.function, npc)
            if result:
                self.history.append({
                    "role": "system",
                    "content": f"系統執行功能: {result}"
                })
        return response.response_to_AI

    def _handle_function(self, function: Any, npc: "NPC") -> str:
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
        space = self.world["spaces"].get(space_name)
        if not space:
            return f"找不到名為 '{space_name}' 的空間。"
        new_item = Item(
            name=item_name,
            description=description,
            properties={}
        )
        self.world["items"][item_name] = new_item
        space.items.append(new_item)
        return f"在 {space_name} 創建了新物品: {item_name}"

    def _delete_item(self, item_name: str, space_name: Optional[str], npc_name: Optional[str]) -> str:
        if space_name:
            space = self.world["spaces"].get(space_name)
            if not space:
                return f"找不到名為 '{space_name}' 的空間。"
            for i, item in enumerate(space.items):
                if item.name == item_name:
                    space.items.pop(i)
                    if item_name in self.world["items"]:
                        del self.world["items"][item_name]
                    return f"從 {space_name} 刪除了物品: {item_name}"
        if npc_name:
            npc = self.world["npcs"].get(npc_name)
            if not npc:
                return f"找不到名為 '{npc_name}' 的 NPC。"
            for i, item in enumerate(npc.inventory.items):
                if item.name == item_name:
                    npc.inventory.items.pop(i)
                    if item_name in self.world["items"]:
                        del self.world["items"][item_name]
                    return f"從 {npc_name} 的庫存中刪除了物品: {item_name}"
        return f"找不到物品 '{item_name}'。"

    def _change_item_description(self, item_name: str, new_description: str) -> str:
        if item_name in self.world["items"]:
            item = self.world["items"][item_name]
            item.description = new_description
            return f"更新了物品 '{item_name}' 的描述。"
        return f"找不到物品 '{item_name}'。"

    def _delete_and_create_new_item(self, old_item_name: str, new_item_name: str, new_description: str, space_name: str) -> str:
        delete_result = self._delete_item(old_item_name, space_name, None)
        if "刪除了物品" not in delete_result:
            return f"無法替換物品：{delete_result}"
        create_result = self._create_item(new_item_name, new_description, space_name)
        if "創建了新物品" not in create_result:
            return f"刪除了舊物品，但無法創建新物品：{create_result}"
        return f"將 '{old_item_name}' 替換為 '{new_item_name}'。"

    def _move_item_to_inventory(self, item_name: str, npc_name: str) -> str:
        npc = self.world["npcs"].get(npc_name)
        if not npc:
            return f"找不到名為 '{npc_name}' 的 NPC。"
        item = None
        for i, space_item in enumerate(npc.current_space.items):
            if space_item.name == item_name:
                item = space_item
                npc.current_space.items.pop(i)
                break
        if not item:
            return f"在 {npc.current_space.name} 中找不到物品 '{item_name}'。"
        result = npc.inventory.add_item(item)
        return f"{npc_name} 撿起了 {item_name}。{result}"
