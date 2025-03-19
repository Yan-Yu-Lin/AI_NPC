# 項目文件合併

目錄: `/Users/linyanyu/Desktop/Coding/python/AI_NPCs`

包含 20 個文件

## __init__.py

```py
from .ai_controller import AIController
from .thought_manager import ThoughtManager
from .decision_manager import DecisionManager
from .memory_manager import MemoryManager
from .movement_manager import MovementManager

__all__ = [
    'AIController',
    'ThoughtManager',
    'DecisionManager',
    'MemoryManager',
    'MovementManager'
]
```

## core/__init__.py

```py

```

## core/base_models.py

```py
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
```

## demo_preview_alpha_nighty_RC2.py

```py
from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Union, Literal, List, Optional, Dict, Any, Annotated
import json
import os
import glob

client = OpenAI()



#NOTE: Item

# 定義基礎 Item 類

class Item(BaseModel):
    name: str
    description: str
    # Simpler interaction definition:
    # - If value is None: no parameters needed
    # - If value is dict: specifies required parameters and their types
    interactions: Dict[str, Optional[Dict[str, type]]]
    properties: Dict[str, Any] = {}

    def interact(self, interaction_type: str, **kwargs) -> str:
        """Handle interactions with parameter validation"""
        if interaction_type not in self.interactions:
            return f"{self.name} cannot be {interaction_type}."

        # Get parameter requirements
        param_requirements = self.interactions[interaction_type]
        
        # If parameters are required, validate them
        if param_requirements:
            if not kwargs:
                return f"{interaction_type} requires parameters: {param_requirements}"
            
            # Validate parameters match requirements
            for param_name, param_type in param_requirements.items():
                if param_name not in kwargs:
                    return f"Missing required parameter: {param_name}"
                if not isinstance(kwargs[param_name], param_type):
                    return f"Invalid type for {param_name}"

        # Call the appropriate method
        method = getattr(self, interaction_type, None)
        if callable(method):
            return method(**kwargs)

        return f"No behavior defined for {interaction_type} on {self.name}."

    # Interaction methods remain the same
    def read(self) -> str:
        content = self.properties.get("content", None)
        if content:
            return f"You read the {self.name}: {content}"
        return f"There is nothing to read in the {self.name}."

    def write(self, content: str) -> str:
        if "content" not in self.properties:
            return f"You cannot write in the {self.name}."
        self.properties["content"] += f"\n{content}"
        return f"You wrote in the {self.name}: {content}"

    def inspect(self) -> str:
        return f"You inspect the {self.name}: {self.description}"

    def play(self) -> str:
        if "is_playing" in self.properties:
            if self.properties["is_playing"]:
                return f"The {self.name} is already playing."
            self.properties["is_playing"] = True
            return f"You start playing the {self.name}."
        return f"The {self.name} cannot be played."

    def stop(self) -> str:
        if "is_playing" in self.properties:
            if not self.properties["is_playing"]:
                return f"The {self.name} is not playing."
            self.properties["is_playing"] = False
            return f"You stop the {self.name}."
        return f"The {self.name} cannot be stopped."

    # New interaction methods for cooking_pot
    def cook(self, ingredient: str) -> str:
        """Cook something in the pot using the specified ingredient."""
        if "contents" not in self.properties:
            return f"The {self.name} cannot be used for cooking."
        
        if not self.properties.get("is_clean", False):
            return f"The {self.name} is dirty and needs to be cleaned before cooking."
        
        self.properties["contents"] = ingredient
        return f"You cook {ingredient} in the {self.name}. It smells delicious!"
    
    def examine(self) -> str:
        """Examine an item closely (similar to inspect but with different wording)."""
        if "contents" in self.properties and self.properties["contents"]:
            return f"You examine the {self.name}: {self.description}. It contains {self.properties['contents']}."
        return f"You examine the {self.name}: {self.description}"
    
    def clean(self) -> str:
        """Clean the item."""
        if "is_clean" not in self.properties:
            return f"The {self.name} doesn't need cleaning."
        
        self.properties["is_clean"] = True
        self.properties["contents"] = ""
        return f"You clean the {self.name} thoroughly. It's now ready for use."
    
    # New interaction methods for watering_can
    def fill(self) -> str:
        """Fill the watering can with water."""
        if "water_level" not in self.properties or "max_capacity" not in self.properties:
            return f"The {self.name} cannot be filled with water."
        
        if self.properties["water_level"] >= self.properties["max_capacity"]:
            return f"The {self.name} is already full."
        
        self.properties["water_level"] = self.properties["max_capacity"]
        return f"You fill the {self.name} with water."
    
    def water(self, plant: str) -> str:
        """Water a plant using the watering can."""
        if "water_level" not in self.properties:
            return f"The {self.name} cannot be used for watering."
        
        if self.properties["water_level"] <= 0:
            return f"The {self.name} is empty. You need to fill it first."
        
        self.properties["water_level"] -= 1
        return f"You water the {plant} with the {self.name}. The plant looks refreshed!"
    
    # New interaction methods for mysterious_device
    def activate(self) -> str:
        """Activate the device."""
        if "is_active" not in self.properties:
            return f"The {self.name} cannot be activated."
        
        if self.properties["is_active"]:
            return f"The {self.name} is already active."
        
        self.properties["is_active"] = True
        return f"You activate the {self.name}. It hums to life with a soft glow and mechanical whirring."
    
    def adjust(self, setting: str) -> str:
        """Adjust the device settings."""
        if "current_setting" not in self.properties:
            return f"The {self.name} cannot be adjusted."
        
        if not self.properties.get("is_active", False):
            return f"The {self.name} needs to be activated before adjusting settings."
        
        self.properties["current_setting"] = setting
        return f"You adjust the {self.name} to the '{setting}' setting. The device's behavior changes subtly."
    
    def disassemble(self) -> str:
        """Disassemble the device to examine its components."""
        if "is_active" not in self.properties:
            return f"The {self.name} cannot be disassembled."
        
        if self.properties.get("is_active", False):
            return f"The {self.name} is currently active. You should deactivate it before disassembling."
        
        return f"You carefully disassemble the {self.name}, revealing intricate gears, circuits, and mysterious components. You reassemble it after your examination."
    
    # New interaction methods for tea_set
    def use(self) -> str:
        """Use the item (generic interaction)."""
        if "is_brewing" in self.properties:
            if self.properties["is_brewing"]:
                return f"The {self.name} is already in use, brewing a fragrant tea."
            
            self.properties["is_brewing"] = True
            return f"You prepare the {self.name} and start brewing a delightful tea. The aroma fills the air."
        
        if "is_filled" in self.properties:
            if not self.properties["is_filled"]:
                return f"The {self.name} is empty and needs to be filled first."
            
            return f"You use the {self.name} to water the nearby plants. They seem to appreciate it."
        
        if "is_focused" in self.properties:
            self.properties["is_focused"] = True
            return f"You use the {self.name}, adjusting it carefully. The view becomes crystal clear."
        
        return f"You use the {self.name}, but nothing particularly interesting happens."
    
    # New interaction methods for stone_bench
    def sit(self) -> str:
        """Sit on the item."""
        return f"You sit on the {self.name} and take a moment to relax. It's quite comfortable and gives you a perfect view of the surroundings."
    
    # New interaction methods for old_chest
    def open(self) -> str:
        """Open the item if possible."""
        if "is_locked" not in self.properties:
            return f"The {self.name} cannot be opened."
        
        if self.properties["is_locked"]:
            return f"The {self.name} is locked. You need to find a key or another way to unlock it."
        
        return f"You open the {self.name}, revealing its contents: old letters, photographs, and small trinkets from a bygone era."
    
    # New interaction methods for telescope
    def adjust(self, **kwargs) -> str:
        """Adjust the item (overloaded method that works for both telescope and mysterious_device)."""
        if "is_focused" in self.properties:
            self.properties["is_focused"] = True
            return f"You carefully adjust the {self.name}, bringing distant objects into sharp focus."
        
        # For mysterious_device, reuse the existing adjust method logic
        if "current_setting" in self.properties:
            setting = kwargs.get("setting", "default")
            if not self.properties.get("is_active", False):
                return f"The {self.name} needs to be activated before adjusting settings."
            
            self.properties["current_setting"] = setting
            return f"You adjust the {self.name} to the '{setting}' setting. The device's behavior changes subtly."
        
        return f"You adjust the {self.name}, but nothing seems to change."


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

    class InteractItemAction(BaseModel):
        # target_item: str
        target_item: Dict[str, Dict[str, Optional[Dict[str, type]]]]

    #example
    class example_interact_with_item(BaseModel):
        action_type: Literal["example_interact_with_item"]
        target_item: str
        interaction: str
        parameter: str


    class GeneralResponse(BaseModel):
        self_talk_reasoning: str
        action: Optional[Union[
            "NPC.EnterSpaceAction", 
            "NPC.InteractItemAction", 
            "NPC.TalkToNPCAction"
        ]] = None


    def update_schema(self):
        """
        Dynamically generate schemas based on NPC's current state.
        Returns a GeneralResponse model with appropriate action schemas.
        """
        # Get valid options from current state
        valid_spaces = [space.name for space in self.current_space.connected_spaces]
        valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
        available_items = self.current_space.items + self.inventory.items

        # --- Dynamic Item Interaction Schemas ---
        item_classes = {}
        for item in available_items:
            # Second layer: Item-specific class (e.g., ArthurBook)
            action_classes = {}
            for action_name, param_spec in item.interactions.items():
                # Third layer: Action-specific class (e.g., Reading, Writing)
                fields = {"action_name": Literal[action_name]}
                
                # Create class attributes dictionary
                class_attrs = {
                    "__annotations__": fields,
                    "action_name": Field(default=..., description=f"Action: {action_name}")
                }
                
                # Only add parameter field if parameters are required
                if param_spec is not None:
                    fields["parameter"] = str  # Add to annotations
                    class_attrs["parameter"] = Field(default=..., description="Parameter for the action")
                
                action_class = type(
                    action_name.capitalize(),  # e.g., "Read", "Write"
                    (BaseModel,),
                    class_attrs
                )
                action_classes[action_name] = action_class

            # Second layer: Define the item class
            item_class_name = item.name.replace("_", "").capitalize()  # e.g., "Arthurbook"
            item_classes[item.name] = type(
                item_class_name,
                (BaseModel,),
                {
                    "__annotations__": {
                        "item_name": Literal[item.name],
                        "action": Union[tuple(action_classes.values())]
                    },
                    "item_name": Field(default=..., description=f"Item: {item.name}")
                }
            )

        # First layer: InteractItemAction
        class InteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            interact_with: Union[tuple(item_classes.values())] if item_classes else Any

        # Static actions
        class EnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: Literal[*valid_spaces] if valid_spaces else str

        class TalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: Literal[*valid_npcs] if valid_npcs else str
            dialogue: str

        # Top-level response
        class GeneralResponse(BaseModel):
            self_talk_reasoning: str
            action: Optional[Union[
                EnterSpaceAction,
                InteractItemAction,
                TalkToNPCAction
            ]] = None
        
        return GeneralResponse


    def add_space_to_history(self):
        """
        Append the current space's information (via __str__) to the NPC's history.
        """
        self.history.append({"role": "system", "content": str(self.current_space)})

    def print_current_schema(self):
        """
        Print the actual schema that AI works with
        """
        try:
            print("\n=== GeneralResponse Schema ===")
            schema = self.GeneralResponse.model_json_schema()
            # Make it more readable with indentation
            import json
            print(json.dumps(schema, indent=2))
            print("=== GeneralResponse Schema END ===\n")

            if self.current_space.connected_spaces:
                print("=== EnterSpaceAction Schema ===")
                schema = self.EnterSpaceAction.model_json_schema()
                print(json.dumps(schema, indent=2))
                print("=== EnterSpaceAction Schema END ===\n")

            if self.current_space.items or self.inventory.items:
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
            # Print additional debug info
            print(f"Current space: {self.current_space.name}")
            print(f"Available items: {[item.name for item in self.current_space.items + self.inventory.items]}")
            print(f"Available NPCs: {[npc.name for npc in self.current_space.npcs if npc != self]}")

    def move_to_space(self, target_space_name: str) -> str:
        """
        Move the NPC to a connected space if valid, and update the NPC's position in the spaces' NPC lists.
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
            if hasattr(response.action, "action_type") and response.action.action_type == "interact_item":
                interact_with = response.action.interact_with
                action_content = f"Action: I'm interacting with {interact_with.item_name} using '{interact_with.action.action_name}'"
                if hasattr(interact_with.action, "parameter"):
                    action_content += f" with parameter: {interact_with.action.parameter}"
            elif hasattr(response.action, "action_type") and response.action.action_type == "enter_space":
                action_content = f"Action: I'm moving to {response.action.target_space}"
            elif hasattr(response.action, "action_type") and response.action.action_type == "talk_to_npc":
                action_content = f"Action: I'm talking to {response.action.target_npc} saying: {response.action.dialogue}"
            else:
                action_content = "Action: Attempting an unknown action type"
                
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
                interact_with = action.interact_with
                action_data = {
                    interact_with.item_name: {
                        interact_with.action.action_name: (
                            {"content": interact_with.action.parameter}
                            if hasattr(interact_with.action, "parameter") else None
                        )
                    }
                }
                result = self.interact_with_item(action_data)
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


    def interact_with_item(self, action_data: Dict[str, Dict[str, Optional[Dict[str, Any]]]]) -> str:
        """
        Handle interactions with items based on the action data from process_tick.
        
        Args:
            action_data: A dictionary with structure {item_name: {interaction_type: parameters_dict}}
                         where parameters_dict is either None or a dictionary of parameter values
        
        Returns:
            A string describing the result of the interaction
        """
        # Extract item name and interaction details
        if not action_data:
            return "No item interaction data provided."
        
        # Get the first (and only) item name and its interaction details
        item_name = next(iter(action_data))
        interaction_details = action_data[item_name]
        
        # Get the first (and only) interaction type and its parameters
        interaction_type = next(iter(interaction_details))
        parameters = interaction_details[interaction_type]
        
        # Find the item in inventory or current space
        target_item = None
        for item in self.inventory.items:
            if item.name == item_name:
                target_item = item
                break
        
        if target_item is None:
            for item in self.current_space.items:
                if item.name == item_name:
                    target_item = item
                    break
        
        if target_item is None:
            return f"Cannot find item '{item_name}' in inventory or current space."
        
        # Call the item's interact method with the appropriate parameters
        if parameters:
            return target_item.interact(interaction_type, **parameters)
        else:
            return target_item.interact(interaction_type)






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
    Build the world objects from the loaded JSON data.
    
    Args:
        world_data: Dictionary containing the world data
        
    Returns:
        Dictionary containing the built world objects
    """
    if not world_data:
        print("Error: No world data provided")
        return {}
    
    # Initialize empty collections
    spaces_dict = {}
    items_dict = {}
    npcs_dict = {}
    
    # First pass: Create all spaces (without connections)
    for space_data in world_data.get("spaces", []):
        spaces_dict[space_data["name"]] = Space(
            name=space_data["name"],
            description=space_data["description"],
            connected_spaces=[],  # Will connect later
            items=[],  # Will add items later
            npcs=[]  # Will add NPCs later
        )
    
    # Second pass: Create all items
    for item_data in world_data.get("items", []):
        # Convert interactions format
        interactions = {}
        for interaction_name, param_spec in item_data["interactions"].items():
            if param_spec is None:
                interactions[interaction_name] = None
            else:
                # Convert parameter types from strings to actual types
                param_dict = {}
                for param_name, param_type_str in param_spec.items():
                    # Simple mapping of type strings to actual types
                    type_map = {"str": str, "int": int, "bool": bool, "float": float}
                    param_dict[param_name] = type_map.get(param_type_str, str)
                interactions[interaction_name] = param_dict
        
        items_dict[item_data["name"]] = Item(
            name=item_data["name"],
            description=item_data["description"],
            interactions=interactions,
            properties=item_data.get("properties", {})
        )
    
    # Third pass: Connect spaces and add items to spaces
    for space_data in world_data.get("spaces", []):
        space = spaces_dict[space_data["name"]]
        
        # Connect spaces
        for connected_space_name in space_data["connected_spaces"]:
            if connected_space_name in spaces_dict:
                connected_space = spaces_dict[connected_space_name]
                # Use biconnect to establish bidirectional connection
                space.biconnect(connected_space)
        
        # Add items to space
        for item_name in space_data["items"]:
            if item_name in items_dict:
                space.items.append(items_dict[item_name])
    
    # Fourth pass: Create NPCs and place them in spaces
    for npc_data in world_data.get("npcs", []):
        # Create inventory for NPC
        inventory = Inventory(items=[])
        
        # Add items to inventory if specified
        for item_name in npc_data.get("inventory", []):
            if item_name in items_dict:
                inventory.add_item(items_dict[item_name])
        
        # Get starting space
        starting_space_name = npc_data.get("starting_space")
        starting_space = spaces_dict.get(starting_space_name)
        
        if starting_space:
            # Create NPC
            npc = NPC(
                name=npc_data["name"],
                description=npc_data["description"],
                current_space=starting_space,
                inventory=inventory,
                history=npc_data.get("history", [])
            )
            
            # Add NPC to its starting space
            starting_space.npcs.append(npc)
            
            # Store NPC in dictionary
            npcs_dict[npc_data["name"]] = npc
    
    return {
        "world_name": world_data.get("world_name", "Unknown World"),
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
    Save the current world state to a JSON file.
    
    Args:
        world: Dictionary containing the world objects
        file_path: Path where to save the JSON file
        
    Returns:
        True if save was successful, False otherwise
    """
    try:
        # Create a dictionary to hold the serialized world data
        world_data = {
            "world_name": world.get("world_name", "Unknown World"),
            "description": world.get("description", ""),
            "spaces": [],
            "items": [],
            "npcs": []
        }
        
        # Serialize spaces
        for space_name, space in world["spaces"].items():
            space_data = {
                "name": space.name,
                "description": space.description,
                "connected_spaces": [connected.name for connected in space.connected_spaces],
                "items": [item.name for item in space.items]
                # NPCs are handled separately
            }
            world_data["spaces"].append(space_data)
        
        # Serialize items
        for item_name, item in world["items"].items():
            # Convert interactions back to string type format
            interactions = {}
            for interaction_name, param_spec in item.interactions.items():
                if param_spec is None:
                    interactions[interaction_name] = None
                else:
                    # Convert parameter types from actual types to strings
                    param_dict = {}
                    for param_name, param_type in param_spec.items():
                        # Map Python types back to strings
                        type_str = "str"
                        if param_type == int:
                            type_str = "int"
                        elif param_type == bool:
                            type_str = "bool"
                        elif param_type == float:
                            type_str = "float"
                        param_dict[param_name] = type_str
                    interactions[interaction_name] = param_dict
            
            item_data = {
                "name": item.name,
                "description": item.description,
                "interactions": interactions,
                "properties": item.properties
            }
            world_data["items"].append(item_data)
        
        # Serialize NPCs
        for npc_name, npc in world["npcs"].items():
            npc_data = {
                "name": npc.name,
                "description": npc.description,
                "starting_space": npc.current_space.name,
                "inventory": [item.name for item in npc.inventory.items],
                "history": npc.history  # Save the NPC's memory/history
            }
            world_data["npcs"].append(npc_data)
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(world_data, f, indent=2, ensure_ascii=False)
        
        print(f"World successfully saved to {file_path}")
        return True
    
    except Exception as e:
        print(f"Error saving world: {str(e)}")
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
    Main sandbox function that handles world selection, loading, and the game loop.
    This function allows users to interact with NPCs in the selected world.
    """
    # Select and load a world
    world_file_path = select_world()
    world_data = load_world_from_json(world_file_path)
    world = build_world_from_data(world_data)
    
    # Get all NPCs from the world
    npcs = list(world["npcs"].values())
    
    if not npcs:
        print("Warning: No NPCs found in this world. The simulation will be limited.")
        print(f"World loaded: {world['world_name']}")
        print(f"Description: {world['description']}")
        print(f"Spaces: {', '.join(world['spaces'].keys())}")
        print(f"Items: {', '.join(world['items'].keys())}")
        
        # Simple loop for worlds without NPCs
        while True:
            print("=====================")
            user_input = input("e -> exit, i -> info: ").strip().lower()
            
            if user_input == "e":
                # Prompt for saving before exit
                save_path = prompt_for_save_location(world_file_path)
                save_world_to_json(world, save_path)
                print("Exiting...")
                break
            elif user_input == "i":
                print(f"World: {world['world_name']}")
                print(f"Description: {world['description']}")
                print(f"Spaces: {', '.join(world['spaces'].keys())}")
                print(f"Items: {', '.join(world['items'].keys())}")
            else:
                print("No NPCs to interact with. Try a different world or add NPCs to this one.")
    else:
        # Print world info
        print(f"World loaded: {world['world_name']}")
        print(f"Description: {world['description']}")
        print(f"NPCs: {', '.join([npc.name for npc in npcs])}")
        
        # Select which NPC to focus on for detailed interactions
        active_npc_index = 0
        if len(npcs) > 1:
            print("\n=== Available NPCs ===")
            for i, npc in enumerate(npcs, 1):
                print(f"{i}. {npc.name} - {npc.description}")
            
            while True:
                npc_choice = input("Select an NPC to focus on (number): ").strip()
                if npc_choice.isdigit() and 1 <= int(npc_choice) <= len(npcs):
                    active_npc_index = int(npc_choice) - 1
                    break
                print(f"Please enter a number between 1 and {len(npcs)}")
        
        active_npc = npcs[active_npc_index]
        print(f"Focusing on NPC: {active_npc.name}")
        
        # Main game loop
        while True:
            print("=====================")
            user_input = input("c -> continue, e -> exit, p -> print history, s -> show schema, n -> switch NPC: ").strip().lower()

            if user_input == "c":
                # Process a tick for all NPCs, but only show result for active NPC
                for npc in npcs:
                    result = npc.process_tick()
                    if npc == active_npc:
                        print(f"[{npc.name}] Tick Result: {result}")
                print()
                print()

            elif user_input == "e":
                # Prompt for saving before exit
                save_path = prompt_for_save_location(world_file_path)
                save_world_to_json(world, save_path)
                print("Exiting...")
                break

            elif user_input == "p":
                try:
                    from rich.console import Console
                    from rich.panel import Panel
                    
                    console = Console()
                    print(f"History for {active_npc.name}:")
                    
                    # Group messages by consecutive role
                    grouped_messages = []
                    current_group = None
                    
                    for message in active_npc.history:
                        role = message['role']
                        content = message['content']
                        
                        if current_group is None or current_group['role'] != role:
                            # Start a new group
                            current_group = {'role': role, 'contents': [content]}
                            grouped_messages.append(current_group)
                        else:
                            # Add to existing group
                            current_group['contents'].append(content)
                    
                    # Display each group
                    for group in grouped_messages:
                        role = group['role']
                        contents = group['contents']
                        
                        # Set style based on role
                        if role == "system":
                            style = "blue"
                            title = "SYSTEM"
                        elif role == "assistant":
                            style = "green"
                            title = active_npc.name.upper()
                        elif role == "user":
                            style = "yellow"
                            title = "USER"
                        else:
                            style = "white"
                            title = role.upper()
                        
                        # Join all contents with line breaks
                        combined_content = "\n".join(contents)
                        
                        # Create a panel with the role name at the top, followed by content on new lines
                        panel_text = f"{title}:\n{combined_content}"
                        panel = Panel(panel_text, border_style=style)
                        
                        # Print the panel
                        console.print(panel)
                        
                except ImportError:
                    # Fallback if rich is not installed
                    print("For better formatting, install the 'rich' library with: pip install rich")
                    print(f"History for {active_npc.name}:")
                    
                    current_role = None
                    role_messages = []
                    
                    for message in active_npc.history:
                        role = message['role']
                        content = message['content']
                        
                        if current_role is None or current_role != role:
                            # Print previous role's messages if any
                            if role_messages:
                                print(f"{current_role.upper()}:")
                                for msg in role_messages:
                                    print(f"  {msg}")
                                print()
                            
                            # Start new role
                            current_role = role
                            role_messages = [content]
                        else:
                            # Add to current role
                            role_messages.append(content)
                    
                    # Print the last group
                    if role_messages:
                        print(f"{current_role.upper()}:")
                        for msg in role_messages:
                            print(f"  {msg}")
                        print()

            elif user_input == "s":
                active_npc.print_current_schema()
                
            elif user_input == "n" and len(npcs) > 1:
                print("\n=== Available NPCs ===")
                for i, npc in enumerate(npcs, 1):
                    print(f"{i}. {npc.name} - {npc.description}")
                
                while True:
                    npc_choice = input("Select an NPC to focus on (number): ").strip()
                    if npc_choice.isdigit() and 1 <= int(npc_choice) <= len(npcs):
                        active_npc_index = int(npc_choice) - 1
                        active_npc = npcs[active_npc_index]
                        print(f"Now focusing on: {active_npc.name}")
                        break
                    print(f"Please enter a number between 1 and {len(npcs)}")

            else:
                # Process user input for the active NPC only
                result = active_npc.process_tick(user_input)
                print(f"[{active_npc.name}] Tick Result: {result}")
                print()
                print()

# Run the sandbox
if __name__ == "__main__":
    SandBox()
```

## history/__init__.py

```py

```

## history/history_manager.py

```py
"""
歷史記錄管理器
處理NPC交互歷史的顯示和管理
"""

from typing import List, Dict, Any


def print_history(npc, max_items: int = None):
    """
    打印NPC的歷史記錄。
    
    Args:
        npc: 要顯示歷史記錄的NPC
        max_items: 要顯示的最大條目數，None顯示全部
    """
    history = npc.history
    
    # 如果指定了最大條目數，則只顯示最後的max_items個條目
    if max_items is not None and max_items > 0:
        history = history[-max_items:]
    
    print(f"\n=== {npc.name} 的歷史記錄 ===")
    
    for item in history:
        role = item["role"]
        content = item["content"]
        
        if role == "system":
            print(f"[系統] {content}")
        elif role == "user":
            print(f"[用戶] {content}")
        elif role == "assistant":
            print(f"[{npc.name}] {content}")
        else:
            print(f"[{role}] {content}")
    
    print("=====================\n")


def save_history_to_file(npc, file_path: str):
    """
    將NPC的歷史記錄保存到文件。
    
    Args:
        npc: 要保存歷史記錄的NPC
        file_path: 保存的文件路徑
    """
    import json
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(npc.history, file, ensure_ascii=False, indent=2)
        print(f"歷史記錄已保存到 {file_path}")
    except Exception as e:
        print(f"保存歷史記錄時出錯: {str(e)}")


def load_history_from_file(npc, file_path: str):
    """
    從文件載入NPC的歷史記錄。
    
    Args:
        npc: 要載入歷史記錄的NPC
        file_path: 歷史記錄文件路徑
    """
    import json
    import os
    
    if not os.path.exists(file_path):
        print(f"錯誤: 找不到檔案 '{file_path}'")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            npc.history = json.load(file)
        print(f"從 {file_path} 載入了歷史記錄")
    except Exception as e:
        print(f"載入歷史記錄時出錯: {str(e)}")
```

## inventory/__init__.py

```py

```

## inventory/inventory.py

```py
"""
庫存類
管理實體可持有的物品
"""

from typing import Dict, List, Optional, Any


class Inventory:
    """
    表示實體（如NPC）的庫存。
    管理庫存中的物品。
    """
    
    def __init__(self, max_capacity: int = 10):
        """
        初始化一個新的庫存。
        
        Args:
            max_capacity: 庫存的最大容量
        """
        self.items = []  # 庫存中的物品列表
        self.max_capacity = max_capacity
    
    def add_item(self, item):
        """
        添加物品到庫存。
        
        Args:
            item: 要添加的物品
            
        Returns:
            成功添加返回True，否則返回False
        """
        if len(self.items) >= self.max_capacity:
            return False
        
        self.items.append(item)
        return True
    
    def remove_item(self, item_name: str):
        """
        從庫存中移除指定名稱的物品。
        
        Args:
            item_name: 要移除的物品名稱
            
        Returns:
            被移除的物品，如果未找到則返回None
        """
        for i, item in enumerate(self.items):
            if item.name == item_name:
                return self.items.pop(i)
        
        return None
    
    def get_item(self, item_name: str):
        """
        獲取庫存中指定名稱的物品，但不從庫存中移除。
        
        Args:
            item_name: 要獲取的物品名稱
            
        Returns:
            找到的物品，如果未找到則返回None
        """
        for item in self.items:
            if item.name == item_name:
                return item
        
        return None
    
    def __str__(self) -> str:
        """返回庫存的字符串表示"""
        if not self.items:
            return "空的庫存"
        
        items_str = ", ".join([item.name for item in self.items])
        return f"庫存: {items_str}"
```

## items/__init__.py

```py

```

## items/item.py

```py
"""
物品類
表示遊戲中可互動的物品
"""

from typing import Dict, List, Optional, Any

from core.base_models import BaseEntity


class Item(BaseEntity):
    """
    表示遊戲中的物品。
    物品可以被放置、拾取、使用等。
    """
    
    def __init__(self, name: str, description: str, interactions: Dict[str, Optional[Dict[str, type]]] = None):
        """
        初始化一個新的物品。
        
        Args:
            name: 物品名稱
            description: 物品描述
            interactions: 物品可進行的互動及其所需參數
                          例如: {"閱讀": None, "寫入": {"content": str}}
        """
        super().__init__(name, description)
        self.interactions = interactions or {"觀察": None}
        
        # 某些物品可能有內容，如書、紙條等
        self.content = ""

    def add_interaction(self, interaction_name: str, params: Optional[Dict[str, type]] = None):
        """
        添加一個新的互動方式。
        
        Args:
            interaction_name: 互動的名稱，如"閱讀"、"使用"等
            params: 互動所需的參數及其類型，如{"内容": str}
        """
        self.interactions[interaction_name] = params

    def __str__(self) -> str:
        """返回物品的字符串表示"""
        return f"{self.name}: {self.description}"
```

## main.py

```py
"""
AI NPC 主程式
整合所有模組並運行遊戲系統
"""

import os
from typing import Optional

# 導入所需模組
from world.world_loader import load_world
from npcs.npc import NPC
from history.history_manager import print_history

def main():
    """主程式入口點"""
    print("歡迎來到 AI NPC 模擬系統！")
    print("正在載入世界...")
    
    # 載入世界 - 使用絕對路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    world_file_path = os.path.join(current_dir, "worlds", "world_test.json")
    print(f"嘗試載入世界檔案：{world_file_path}")
    
    world = load_world(world_file_path)
    
    if not world:
        print("錯誤：無法載入世界。程式終止。")
        return
    
    print(f"成功載入世界：{world['world_name']}")
    print(f"世界描述：{world['description']}")
    
    # 獲取主要NPC (arthur)
    arthur = world["npcs"].get("arthur")
    if not arthur:
        print("錯誤：在世界數據中找不到主要NPC 'arthur'")
        return
    
    print(f"主要NPC：{arthur.name} - {arthur.description}")
    print("\n遊戲開始！\n")
    
    # 確保NPC第一次tick已經執行過，並顯示初始狀態
    if arthur.first_tick:
        result = arthur.process_tick()
        print(f"初始狀態: {result}\n")
        
        # 顯示當前環境和情境
        print(f"{arthur.name} 目前所在空間: {arthur.current_space.name}")
        print(f"空間描述: {arthur.current_space.description}")
        if arthur.current_space.items:
            print("空間中的物品:")
            for item in arthur.current_space.items:
                print(f" - {item.name}: {item.description}")
        if arthur.current_space.npcs:
            print("空間中的其他NPC:")
            for npc in arthur.current_space.npcs:
                if npc.name != arthur.name:
                    print(f" - {npc.name}: {npc.description}")
        print("\n使用 'c' 繼續遊戲，'p' 查看歷史記錄，或輸入指令給NPC\n")
    
    # 遊戲主循環
    while True:
        print("=====================")
        user_input = input("c -> 繼續, e -> 退出, p -> 顯示歷史記錄: ").strip().lower()
        
        if user_input == "c":
            # 與demo_preview_alpha_nighty_RC2.py相同的實現方式
            result = arthur.process_tick()
            print(f"結果: {result}\n")
        
        elif user_input == "p":
            # 顯示歷史記錄
            print_history(arthur)
        
        elif user_input == "e":
            # 退出遊戲
            print("感謝使用 AI NPC 模擬系統！")
            break
        
        else:
            # 將用戶輸入傳遞給NPC
            result = arthur.process_tick(user_input)
            print(f"結果: {result}\n")

if __name__ == "__main__":
    main()
```

## merge.py

```py

#!/usr/bin/env python3
import os
import argparse
import sys
from pathlib import Path


def get_default_ignore_patterns():
    """獲取預設忽略模式列表"""
    return [
        # 常見隱藏目錄和文件
        '.*',                 # 所有隱藏文件和目錄
        # 常見Python相關
        '__pycache__',
        '*.pyc', '*.pyo', '*.pyd',
        # 常見環境相關
        'venv', 'env', '.venv', '.env',
        # 常見二進制和暫存文件
        '*.exe', '*.dll', '*.so', '*.dylib',
        '*.zip', '*.tar.gz', '*.tgz', '*.7z', '*.rar',
        '*.log', '*.tmp', '*.bak',
        # 常見IDE相關
        '.idea', '.vscode',
        # 其他
        'node_modules',
        'dist', 'build',
        'archive',           # 添加 archive 目錄
        # 其他大型二進制文件
        '*.mp4', '*.avi', '*.mov', '*.mp3', '*.wav'
    ]


def is_binary_file(file_path):
    """檢查文件是否為二進制文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # 嘗試讀取一小部分
        return False
    except UnicodeDecodeError:
        return True


def should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
    """判斷是否應該忽略文件"""
    if file_path == output_path:
        return True
    
    file_name = file_path.name
    relative_path = str(file_path.relative_to(directory_path))
    
    # 檢查文件名和相對路徑是否匹配忽略模式
    for pattern in ignore_patterns:
        if pattern.startswith('*'):
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            if file_name.startswith(pattern[:-1]):
                return True
        elif pattern == relative_path or pattern == file_name:
            return True
    
    # 檢查是否為二進制文件
    if any(file_name.endswith(ext) for ext in ['.exe', '.dll', '.so', '.dylib', '.zip', '.tar.gz', '.7z', '.mp4', '.mp3']):
        return True
        
    return False


def merge_files_to_markdown(directory, output_file, ignore_patterns=None, max_file_size_mb=5, 
                           include_binary=False, verbose=False):
    """
    將目錄下的所有文件合併為一個 Markdown 文件
    
    Args:
        directory: 要掃描的目錄路徑
        output_file: 輸出的 Markdown 文件路徑
        ignore_patterns: 要忽略的文件或目錄模式列表
        max_file_size_mb: 最大文件大小限制（MB）
        include_binary: 是否包含二進制文件
        verbose: 是否顯示詳細訊息
    """
    if ignore_patterns is None:
        ignore_patterns = get_default_ignore_patterns()
    
    # 轉換為絕對路徑
    directory_path = Path(directory).resolve()
    output_path = Path(output_file).resolve()
    
    # 確認目錄存在
    if not directory_path.exists() or not directory_path.is_dir():
        raise ValueError(f"目錄 '{directory}' 不存在或不是一個有效的目錄")
    
    if verbose:
        print(f"掃描目錄: {directory_path}")
        print(f"忽略模式: {ignore_patterns}")
    
    # 獲取所有文件路徑
    all_files = []
    skipped_files = []
    total_files = 0
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    
    for root, dirs, files in os.walk(directory_path):
        # 過濾要忽略的目錄
        dirs_to_remove = []
        for d in dirs:
            dir_path = Path(root) / d
            relative_dir = str(dir_path.relative_to(directory_path))
            
            # 檢查是否匹配忽略模式
            if any(
                (d.startswith('.') and '.*' in ignore_patterns) or
                d == p or relative_dir == p
                for p in ignore_patterns
            ):
                dirs_to_remove.append(d)
                if verbose:
                    print(f"忽略目錄: {relative_dir}")
        
        # 從 dirs 列表中移除要忽略的目錄，這樣 os.walk 就不會進入這些目錄
        for d in dirs_to_remove:
            dirs.remove(d)
            
        for file in files:
            total_files += 1
            file_path = Path(root) / file
            
            # 忽略要排除的文件
            if should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
                skipped_files.append(str(file_path.relative_to(directory_path)))
                if verbose:
                    print(f"忽略文件: {file_path.relative_to(directory_path)}")
                continue
            
            # 檢查文件大小
            file_size = file_path.stat().st_size
            if file_size > max_file_size_bytes:
                skipped_files.append(f"{file_path.relative_to(directory_path)} (文件太大: {file_size/(1024*1024):.2f} MB)")
                if verbose:
                    print(f"忽略過大文件: {file_path.relative_to(directory_path)} ({file_size/(1024*1024):.2f} MB)")
                continue
                
            # 檢查是否為二進制文件
            if not include_binary and is_binary_file(file_path):
                skipped_files.append(f"{file_path.relative_to(directory_path)} (二進制文件)")
                if verbose:
                    print(f"忽略二進制文件: {file_path.relative_to(directory_path)}")
                continue
            
            all_files.append(file_path)
    
    # 排序文件路徑，使輸出更加有序
    all_files.sort()
    
    if verbose:
        print(f"找到 {total_files} 個文件，合併 {len(all_files)} 個文件，跳過 {len(skipped_files)} 個文件")
    
    # 寫入合併後的 Markdown 文件
    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write(f"# 項目文件合併\n\n")
        out_file.write(f"目錄: `{directory_path}`\n\n")
        out_file.write(f"包含 {len(all_files)} 個文件\n\n")
        
        # 如果有跳過的文件，添加一個列表
        if skipped_files and verbose:
            out_file.write("## 跳過的文件\n\n")
            for skipped in skipped_files:
                out_file.write(f"- {skipped}\n")
            out_file.write("\n")
        
        for file_path in all_files:
            # 獲取相對路徑作為標題
            relative_path = file_path.relative_to(directory_path)
            out_file.write(f"## {relative_path}\n\n")
            
            # 嘗試讀取文件內容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 判斷文件類型並設置語法高亮
                file_extension = file_path.suffix.lstrip('.')
                if file_extension:
                    out_file.write(f"```{file_extension}\n")
                else:
                    out_file.write("```\n")
                
                out_file.write(content)
                
                # 確保內容後有換行
                if not content.endswith('\n'):
                    out_file.write('\n')
                out_file.write("```\n\n")
                
            except UnicodeDecodeError:
                out_file.write("```\n[二進制文件，內容無法顯示]\n```\n\n")
            except Exception as e:
                out_file.write(f"```\n[讀取文件時出錯: {str(e)}]\n```\n\n")
    
    return len(all_files), len(skipped_files)


def main():
    parser = argparse.ArgumentParser(description='將目錄下的所有文件合併為一個 Markdown 文件')
    parser.add_argument('directory', nargs='?', default='.', 
                     help='要掃描的目錄路徑 (預設為當前目錄)')
    parser.add_argument('-o', '--output', default='merged_files.md', 
                     help='輸出的 Markdown 文件路徑 (預設為 merged_files.md)')
    parser.add_argument('-i', '--ignore', nargs='+', 
                     help='要忽略的文件或目錄模式 (可以多個)')
    parser.add_argument('-s', '--max-size', type=float, default=5, 
                     help='最大文件大小限制（MB，預設為 5MB）')
    parser.add_argument('-b', '--include-binary', action='store_true', 
                     help='包含二進制文件 (預設不包含)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                     help='顯示詳細訊息')
    
    args = parser.parse_args()
    
    # 合併默認忽略模式和用戶指定的忽略模式
    ignore_patterns = get_default_ignore_patterns()
    if args.ignore:
        ignore_patterns.extend(args.ignore)
    
    try:
        included, skipped = merge_files_to_markdown(
            args.directory, 
            args.output, 
            ignore_patterns=ignore_patterns,
            max_file_size_mb=args.max_size,
            include_binary=args.include_binary,
            verbose=args.verbose
        )
        print(f"成功將 {included} 個文件合併到 {args.output}")
        print(f"跳過了 {skipped} 個文件")
    except Exception as e:
        print(f"合併文件時出錯: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## npcs/__init__.py

```py

```

## npcs/npc.py

```py
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
```

## spaces/__init__.py

```py

```

## spaces/space.py

```py
"""
空間類
表示遊戲中的位置和環境
"""

from typing import Dict, List, Optional, Any

from core.base_models import BaseEntity


class Space(BaseEntity):
    """
    表示遊戲中的一個空間或位置。
    包含物品、NPCs和到其他空間的連接。
    """
    
    def __init__(self, name: str, description: str):
        """
        初始化一個新的空間。
        
        Args:
            name: 空間名稱
            description: 空間描述
        """
        super().__init__(name, description)
        self.items = []  # 空間中的物品列表
        self.npcs = []  # 空間中的NPC列表
        self.connected_spaces = []  # 與該空間相連的其他空間
    
    def connect_to(self, other_space):
        """
        將此空間與另一個空間相連。
        
        Args:
            other_space: 要連接的空間
        """
        if other_space not in self.connected_spaces:
            self.connected_spaces.append(other_space)
        
        # 確保雙向連接
        if self not in other_space.connected_spaces:
            other_space.connected_spaces.append(self)
    
    def __str__(self) -> str:
        """返回空間的詳細描述，包括物品和NPC"""
        result = [f"空間: {self.name}"]
        result.append(f"描述: {self.description}")
        
        # 添加物品信息
        if self.items:
            result.append("物品:")
            for item in self.items:
                result.append(f" - {item.name}: {item.description}")
        
        # 添加NPC信息
        if self.npcs:
            result.append("人物:")
            for npc in self.npcs:
                result.append(f" - {npc.name}: {npc.description}")
        
        # 添加連接的空間
        if self.connected_spaces:
            result.append("出口:")
            for space in self.connected_spaces:
                result.append(f" - {space.name}")
        
        return "\n".join(result)
```

## todo.md

```md
# TODO
- 完善 AI System Prompt
我現在有一個計劃，要盡量完善 AI 的 System prompt
  > 像是要給 AI 目的 跟 個性
  > 任務交給 AI 

- AI elaborator
  > 然後可能要加一個 elaborator 另外一個 AI 把 原本AI 的想法加上行為 重新描述
  > because the original AI who leverage structured output might be too boring


- Conversation handle function
  > add another function to handle conversation better with other AI

- 加入另外一個 AI 


# DONE
- A better system to display result more specifically: Add color to different text/message and add line between lines when using print history features
```

## world/__init__.py

```py

```

## world/world_loader.py

```py
"""
世界載入器
從JSON檔案載入遊戲世界
"""

import json
import os
from typing import Dict, List, Optional, Any

from npcs.npc import NPC
from items.item import Item
from spaces.space import Space


def load_world(file_path: str) -> Optional[Dict[str, Any]]:
    """
    從JSON檔案載入遊戲世界。
    
    Args:
        file_path: JSON檔案的路徑
        
    Returns:
        包含遊戲世界數據的字典，載入失敗則返回None
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            print(f"錯誤: 找不到檔案 '{file_path}'")
            return None
        
        # 載入JSON數據
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 創建空間
        spaces = {}
        for space_data in data.get("spaces", []):
            space = Space(space_data["name"], space_data["description"])
            spaces[space_data["id"]] = space
        
        # 連接空間
        for space_data in data.get("spaces", []):
            space = spaces[space_data["id"]]
            for connection in space_data.get("connections", []):
                if connection in spaces:
                    space.connect_to(spaces[connection])
        
        # 創建物品
        items = {}
        for item_data in data.get("items", []):
            # 解析互動
            interactions = {}
            for interaction in item_data.get("interactions", []):
                name = interaction["name"]
                params = interaction.get("params")
                
                # 轉換參數類型
                if params:
                    param_dict = {}
                    for param_name, param_type_str in params.items():
                        if param_type_str == "str":
                            param_dict[param_name] = str
                        elif param_type_str == "int":
                            param_dict[param_name] = int
                        elif param_type_str == "bool":
                            param_dict[param_name] = bool
                        elif param_type_str == "float":
                            param_dict[param_name] = float
                        else:
                            param_dict[param_name] = str
                    interactions[name] = param_dict
                else:
                    interactions[name] = None
            
            # 創建物品
            item = Item(item_data["name"], item_data["description"], interactions)
            
            # 設置物品內容（如果有）
            if "content" in item_data:
                item.content = item_data["content"]
            
            items[item_data["id"]] = item
        
        # 創建NPCs
        npcs = {}
        for npc_data in data.get("npcs", []):
            # 創建NPC
            npc = NPC(
                npc_data["name"], 
                npc_data["description"],
                npc_data.get("personality"),
                npc_data.get("knowledge", {})
            )
            
            # 設置NPC的起始空間
            if "starting_space" in npc_data and npc_data["starting_space"] in spaces:
                npc.current_space = spaces[npc_data["starting_space"]]
                npc.current_space.npcs.append(npc)
            
            # 將物品添加到NPC的庫存
            for item_id in npc_data.get("inventory", []):
                if item_id in items:
                    npc.inventory.add_item(items[item_id])
            
            npcs[npc_data["id"]] = npc
        
        # 將物品放置在空間中
        for space_data in data.get("spaces", []):
            space = spaces[space_data["id"]]
            for item_id in space_data.get("items", []):
                if item_id in items:
                    # 確保物品不在任何NPC的庫存中
                    item_in_inventory = False
                    for npc in npcs.values():
                        if npc.inventory.get_item(items[item_id].name):
                            item_in_inventory = True
                            break
                    
                    if not item_in_inventory:
                        space.items.append(items[item_id])
        
        # 返回完整的世界數據
        return {
            "world_name": data.get("name", "未命名世界"),
            "description": data.get("description", "無描述"),
            "spaces": spaces,
            "items": items,
            "npcs": npcs
        }
    
    except Exception as e:
        print(f"載入世界時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
```

## worlds/world_test.json

```json
{
    "name": "測試世界",
    "description": "這是一個用於測試NPC行為的小型世界",
    "spaces": [
        {
            "id": "living_room",
            "name": "客廳",
            "description": "一個溫馨的客廳，有舒適的沙發和一個咖啡桌。",
            "connections": ["kitchen", "bedroom"],
            "items": ["book", "remote"]
        },
        {
            "id": "kitchen",
            "name": "廚房",
            "description": "一個乾淨的廚房，有各種烹飪器具。",
            "connections": ["living_room"],
            "items": ["apple", "knife"]
        },
        {
            "id": "bedroom",
            "name": "臥室",
            "description": "一個整潔的臥室，有一張大床和一個書桌。",
            "connections": ["living_room"],
            "items": ["diary", "pen"]
        }
    ],
    "items": [
        {
            "id": "book",
            "name": "書",
            "description": "一本有關AI歷史的書籍",
            "content": "人工智能的發展歷程充滿了起伏...",
            "interactions": [
                {
                    "name": "閱讀",
                    "params": null
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        },
        {
            "id": "remote",
            "name": "遙控器",
            "description": "電視的遙控器",
            "interactions": [
                {
                    "name": "使用",
                    "params": {
                        "channel": "str"
                    }
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        },
        {
            "id": "apple",
            "name": "蘋果",
            "description": "一個紅色的新鮮蘋果",
            "interactions": [
                {
                    "name": "吃",
                    "params": null
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        },
        {
            "id": "knife",
            "name": "刀",
            "description": "一把鋒利的廚房刀",
            "interactions": [
                {
                    "name": "使用",
                    "params": {
                        "target": "str"
                    }
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        },
        {
            "id": "diary",
            "name": "日記",
            "description": "一本私人日記",
            "content": "今天是個美好的一天...",
            "interactions": [
                {
                    "name": "閱讀",
                    "params": null
                },
                {
                    "name": "寫入",
                    "params": {
                        "content": "str"
                    }
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        },
        {
            "id": "pen",
            "name": "筆",
            "description": "一支黑色的圓珠筆",
            "interactions": [
                {
                    "name": "使用",
                    "params": {
                        "action": "str"
                    }
                },
                {
                    "name": "拿取",
                    "params": null
                }
            ]
        }
    ],
    "npcs": [
        {
            "id": "arthur",
            "name": "亞瑟",
            "description": "一個友好的AI助手",
            "personality": "好奇且樂於助人",
            "knowledge": {
                "AI": "我對AI領域有豐富的知識",
                "書籍": "我喜歡閱讀各種書籍"
            },
            "starting_space": "living_room",
            "inventory": []
        }
    ]
}
```

