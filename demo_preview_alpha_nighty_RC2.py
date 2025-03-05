from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Union, Literal, List, Optional, Dict, Any, Annotated


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


#TODO: Define Spaces

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



#TODO: Define inventory
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

#TODO: Define NPC
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


    def update_schema(self): # This is currently abandoned, ignore this part
        """
        Dynamically update schemas based on NPC's current state
        """
        # Get valid options from current state
        valid_spaces = [space.name for space in self.current_space.connected_spaces]
        valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
        available_items = self.current_space.items + self.inventory.items

        # 為每個物品動態創建互動 schema
        # item_interaction_schemas = {}
        # for item in available_items:
        #     # 獲取該物品的所有互動方式
        #     valid_interactions = list(item.interactions.keys())
        #     
        #     # 動態創建該物品的互動 schema
        #     class_name = f"{item.name.capitalize()}Interactions"
        #     item_interaction_schemas[item.name] = type(
        #         class_name,
        #         (BaseModel,),
        #         {
        #             "action": (Literal[*valid_interactions], ...),
        #             "parameters": (Optional[Dict[str, Any]], None)
        #         }
        #     )

        # 動態創建主要的 action schemas
        class EnterSpaceAction(BaseModel):
            action_type: Literal["enter_space"]
            target_space: Literal[*valid_spaces] if valid_spaces else str

        class TalkToNPCAction(BaseModel):
            action_type: Literal["talk_to_npc"]
            target_npc: Literal[*valid_npcs] if valid_npcs else str
            dialogue: str

        # class InteractItemAction(BaseModel):
        #     action_type: Literal["interact_item"]
        #     target_item: Literal[*[item.name for item in available_items]] if available_items else str
        #     interaction: Union[*item_interaction_schemas.values()] if item_interaction_schemas else Dict

        class InteractItemAction(BaseModel):
            action_type: Literal["interact_item"]
            # target_item: str
            target_item: Dict[str, Dict[str, Optional[Dict[str, type]]]]
        # Create new GeneralResponse
        class GeneralResponse(BaseModel):
            self_talk_reasoning: str
            action: Optional[Union[
                EnterSpaceAction,
                InteractItemAction,
                TalkToNPCAction
            ]] = None

        return GeneralResponse


    # def update_schema(self):
    #     """
    #     Dynamically update the schemas based on the NPC's current state.
    #     """
    #
    #     print("---")
    #     # Check and update EnterSpaceAction
    #     valid_spaces = [space.name for space in self.current_space.connected_spaces]
    #     if valid_spaces:  # Only include if there are connected spaces
    #         self.EnterSpaceAction.__annotations__["target_space"] = Literal[tuple(valid_spaces)]
    #         self.EnterSpaceAction.model_rebuild()
    #
    #     # Check and update InteractItemAction
    #     available_items = self.current_space.items + self.inventory.items
    #     if available_items:  # Only include if there are items to interact with
    #         valid_items = {
    #             item.name: item.interactions
    #             for item in available_items
    #         }
    #         print(f"valid items: {valid_items}")
    #         self.InteractItemAction.__annotations__["target_item"] = type(valid_items)
    #         self.InteractItemAction.model_rebuild()
    #
    #     # Check and update TalkToNPCAction
    #     valid_npcs = [npc.name for npc in self.current_space.npcs if npc.name != self.name]
    #     if valid_npcs:  # Only include if there are other NPCs present
    #         self.TalkToNPCAction.__annotations__["target_npc"] = Literal[tuple(valid_npcs)]
    #         self.TalkToNPCAction.model_rebuild()
    #     print(f"valid spaces: {valid_spaces}")
    #     print(f"valid npcs: {valid_npcs}")
    #     print(f"available items: {available_items}")
    #     print("---")


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
            interact_with: Union[tuple(item_classes.values())]

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
            print("No action taken")
            return "nothing happen"

        action = response.action
        result = ""
        if isinstance(action, InteractItemAction):
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
        elif isinstance(action, EnterSpaceAction):
            result = self.move_to_space(action.target_space)
        elif isinstance(action, TalkToNPCAction):
            result = self.talk_to_npc(action.target_npc, action.dialogue)

        self.history.append({"role": "system", "content": result})
        print("\n=== Action Result ===")
        print(result)
        print("===================\n")
        return result

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

#TODO: A general system instruction for AI


#NOTE:
# initializing Items
# Study Room Items
personal_diary = Item(
    name="personal_diary",
    description="A leather-bound diary with gold-trimmed pages, ready to record thoughts and memories.",
    interactions={
        "read": None,
        "write": {"content": str},
        "inspect": None
    },
    properties={
        "content": "Dear Diary, today I began my journey in this mysterious place..."
    }
)

ancient_book = Item(
    name="ancient_book",
    description="A weathered tome bound in mysterious symbols, its pages filled with fascinating stories.",
    interactions={
        "read": None,
        "inspect": None
    },
    properties={
        "content": "In the age of wonders, when magic still flowed freely through the world..."
    }
)

# Living Room Items
music_box = Item(
    name="music_box",
    description="An ornate music box decorated with dancing figures, capable of playing enchanting melodies.",
    interactions={
        "play": None,
        "stop": None,
        "inspect": None
    },
    properties={
        "is_playing": False
    }
)

mirror = Item(
    name="mirror",
    description="An elegant full-length mirror in a gilded frame, reflecting the room with perfect clarity.",
    interactions={
        "inspect": None
    },
    properties={}
)


#NOTE:
# Initialize Spaces with their items
study_room = Space(
    name="study_room",
    description=(
        "A cozy study lined with wooden bookshelves. Warm lamplight creates a perfect "
        "atmosphere for reading and writing. A personal diary rests on the desk, and "
        "an ancient book catches your eye from one of the shelves."
    ),
    items=[personal_diary, ancient_book]
)

living_room = Space(
    name="living_room",
    description=(
        "An elegant living room with plush furnishings. Sunlight streams through tall windows, "
        "making the ornate music box gleam. A beautiful mirror stands in the corner, "
        "adding depth to the room."
    ),
    items=[music_box, mirror]
)

# Connect the spaces
study_room.biconnect(living_room)

#TODO: Instance of an NPC
# 創建 NPC
# Initializing Arthur

arthur = NPC(
    name="arthur",
    description="A curious and thoughtful explorer with a keen interest in uncovering stories and mysteries.",
    current_space=living_room,
    inventory=Inventory(items=[]),
    history=[
        {
            "role": "system", 
            "content": """You are Arthur, a curious explorer who has found yourself in an intriguing house.
            You can:
            - Explore different rooms
            - Interact with items you find
            - Record your thoughts in the diary if you find one
            - Enjoy music from the music box
            
            You have a particular interest in:
            - Writing down your observations and feelings
            - Understanding the stories behind items you find
            - Creating a peaceful atmosphere with music
            
            Take your time to explore and interact with your surroundings."""
        },
        {
            "role": "assistant", 
            "content": "I find myself in this interesting house. I should explore and interact with what I find. I wanna explore other spaces"
        }
    ]
)

# Add Arthur to his starting space's NPCs list
living_room.npcs.append(arthur)


# 主迴圈
while True:
    print("=====================")
    user_input = input("c -> continue, e -> exit, p -> print history, s -> show schema: ").strip().lower()

    if user_input == "c":
        result = arthur.process_tick()
        print(f"Tick Result: {result}")
        print()
        print()

    elif user_input == "e":
        print("Exiting...")
        break

    elif user_input == "p":
        print("History:")
        for message in arthur.history:
            print(f"{message['role']}: {message['content']}")

    elif user_input == "s":
        arthur.print_current_schema()

    else:
        result = arthur.process_tick(user_input)
        print(f"Tick Result: {result}")
        print()
        print()
