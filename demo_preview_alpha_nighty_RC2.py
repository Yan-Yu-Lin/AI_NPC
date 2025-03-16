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
