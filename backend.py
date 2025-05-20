from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Union, Literal, List, Optional, Dict, Any, Tuple
import json
import os
import glob
import asyncio
from dataclasses import dataclass, field as dataclass_field
import heapq
import sys
import math

client = OpenAI()

# --- Image Generation Helper Functions ---
def get_picture_dir():
    """Returns the absolute path to the 'worlds/picture' directory."""
    return os.path.join("worlds", "picture")

# 設定全局變量使 NPC 類可以訪問
world_system = None

def get_world_system():
    """
    獲取全局 world_system 物件。如果不存在，則創建一個新的 AI_System 物件。
    返回：
        AI_System 物件
    """
    global world_system
    if world_system is None:
        from backend import AI_System
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
    position: Optional[List[int]] = None  # 允許 None，代表未指定，改為列表而不是元組
    size: Optional[List[int]] = None      # 允許 None，代表未指定，改為列表而不是元組
    image_path: Optional[str] = None      # 新增：圖片路徑
    image_scale: float = 1.0              # 新增：圖片縮放比例


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

# --- A* Pathfinding Utilities (移至 backend.py) ---

@dataclass
class SimpleRect:
    """簡單的矩形類，用於路徑規劃的碰撞檢測"""
    x: float
    y: float
    width: float
    height: float
    
    def collidepoint(self, x: float, y: float) -> bool:
        """檢查點 (x, y) 是否在矩形內"""
        return (self.x <= x <= self.x + self.width and
                self.y <= y <= self.y + self.height)
                
    def colliderect(self, other: "SimpleRect") -> bool:
        """檢查兩個矩形是否重疊"""
        return (self.x < other.x + other.width and
                self.x + self.width > other.x and
                self.y < other.y + other.height and
                self.y + self.height > other.y)

# 為了路徑規劃實現 PathPlanner 類
class PathPlanner(BaseModel):
    """
    路徑規劃器類，用於處理 NPC 的路徑規劃和障礙物避免
    """
    grid_cell_size: int = 20
    npc_radius: float = 15.0
    model_config = {"arbitrary_types_allowed": True}
    
    def get_space_obstacles_for_grid(self, space: "Space", obstacle_buffer: float = 5.0) -> List["SimpleRect"]:
        """獲取空間中的障礙物。用於網格路徑規劃。"""
        obstacles = []
        
        if not hasattr(space, 'items') or not space.items:
            return obstacles
        
        for item in space.items:
            if hasattr(item, 'position') and item.position and hasattr(item, 'size') and item.size:
                item_x, item_y = item.position
                item_w, item_h = item.size
                
                # 加上緩衝區，使NPC不會太接近物品
                buffered_x = item_x - obstacle_buffer
                buffered_y = item_y - obstacle_buffer
                buffered_w = item_w + 2 * obstacle_buffer
                buffered_h = item_h + 2 * obstacle_buffer
                
                obstacles.append(SimpleRect(buffered_x, buffered_y, buffered_w, buffered_h))
        
        return obstacles
    
    def find_path_with_obstacles(self, start_space: Space, goal_space: Space,
                             start_pos: Tuple[float,float], goal_pos: Tuple[float,float],
                             all_spaces: Dict[str, Space]) -> List[Tuple[float,float]]:
        """
        尋找考慮障礙物的路徑
        
        Args:
            start_space: 起始空間
            goal_space: 目標空間
            start_pos: 起始位置 (世界座標)
            goal_pos: 目標位置 (世界座標)
            all_spaces: 所有空間的字典
            
        Returns:
            包含路徑點的列表 (世界座標)
        """
        path = [start_pos, goal_pos]
        
        # 如果起點和終點在同一空間
        if start_space == goal_space:
            # 檢查是否有障礙物
            obstacles = self.get_space_obstacles_for_grid(start_space)
            if not obstacles:
                return path
            
            # 在這裡我們可以實現障礙物避讓的邏輯
            # 簡化版：檢查直線路徑是否穿過障礙物，如果是，添加中間點
            for obstacle in obstacles:
                if self._line_intersects_rect(start_pos, goal_pos, obstacle):
                    # 簡單的障礙物避讓：繞過障礙物中心
                    midpoint = (
                        (start_pos[0] + goal_pos[0]) / 2,
                        (start_pos[1] + goal_pos[1]) / 2
                    )
                    # 將中間點向外偏移
                    offset_x = midpoint[0] - obstacle.x - obstacle.width / 2
                    offset_y = midpoint[1] - obstacle.y - obstacle.height / 2
                    
                    # 標準化偏移
                    norm = math.sqrt(offset_x**2 + offset_y**2)
                    if norm > 0:
                        offset_x = offset_x / norm * (obstacle.width + 20)
                        offset_y = offset_y / norm * (obstacle.height + 20)
                    
                    # 創建避讓點
                    avoid_point = (
                        obstacle.x + obstacle.width/2 + offset_x,
                        obstacle.y + obstacle.height/2 + offset_y
                    )
                    
                    # 更新路徑
                    path = [start_pos, avoid_point, goal_pos]
                    break
            
            return path
        
        # 使用高級路徑規劃找到空間級路徑
        space_level_path = find_path_astar(all_spaces, start_space.name, goal_space.name)
        
        if not space_level_path or len(space_level_path) <= 1:
            return path
        
        # 返回起點和終點構成的直線路徑
        # 在實際應用中，這裡可以實現更複雜的路徑規劃邏輯
        return path
    
    def _line_intersects_rect(self, start: Tuple[float, float], end: Tuple[float, float], rect: SimpleRect) -> bool:
        """檢查線段是否與矩形相交"""
        # 檢查起點或終點是否在矩形內
        if rect.collidepoint(start[0], start[1]) or rect.collidepoint(end[0], end[1]):
            return True
        
        # 檢查線段是否與矩形的任一邊相交
        edges = [
            ((rect.x, rect.y), (rect.x + rect.width, rect.y)),
            ((rect.x + rect.width, rect.y), (rect.x + rect.width, rect.y + rect.height)),
            ((rect.x, rect.y + rect.height), (rect.x + rect.width, rect.y + rect.height)),
            ((rect.x, rect.y), (rect.x, rect.y + rect.height))
        ]
        
        for edge_start, edge_end in edges:
            if self._line_segments_intersect(start, end, edge_start, edge_end):
                return True
        
        return False
    
    def _line_segments_intersect(self, p1: Tuple[float, float], p2: Tuple[float, float],
                            p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
        """檢查兩線段是否相交"""
        def cross_product(p1, p2, p3):
            return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])
        
        d1 = cross_product(p3, p4, p1)
        d2 = cross_product(p3, p4, p2)
        d3 = cross_product(p1, p2, p3)
        d4 = cross_product(p1, p2, p4)
        
        return ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
               ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0))

def heuristic(space_a_pos: Tuple[float, float], space_b_pos: Tuple[float, float]) -> float:
    """計算兩點之間的歐幾里得距離。"""
    return math.sqrt((space_a_pos[0] - space_b_pos[0])**2 + (space_a_pos[1] - space_b_pos[1])**2)

def find_path_astar(world_spaces: Dict[str, "Space"], start_space_name: str, goal_space_name: str) -> Optional[List[str]]:
    """
    使用 A* 演算法尋找 start_space_name 和 goal_space_name 之間的最短路徑。
    此版本直接使用 Space 物件的 connected_spaces。

    Args:
        world_spaces (dict): 空間物件的字典，以名稱為鍵。
        start_space_name (str): 起始空間的名稱。
        goal_space_name (str): 目標空間的名稱。

    Returns:
        list: 代表從起點到終點路徑的空間名稱列表，如果找不到路徑則返回 None。
    """
    if not start_space_name or not goal_space_name:
        print(f"A* 錯誤: 起始或目標空間名稱無效。") # Debugging
        return None
    if start_space_name not in world_spaces or goal_space_name not in world_spaces:
        print(f"A* 錯誤: 起始或目標空間不存在於 world_spaces 中。起始: {start_space_name}, 目標: {goal_space_name}") # Debugging
        return None
    if start_space_name == goal_space_name:
        return [start_space_name]

    start_space = world_spaces[start_space_name]
    goal_space = world_spaces[goal_space_name]

    def get_space_center(space_obj: "Space") -> Tuple[float, float]:
        if not hasattr(space_obj, 'display_pos') or not hasattr(space_obj, 'display_size') or \
            space_obj.display_pos is None or space_obj.display_size is None:
            # print(f"警告: 空間 {getattr(space_obj, 'name', '未知')} 缺少 display_pos 或 display_size 或其值為None。") # Debugging
            return (0.0, 0.0)
        return (
            float(space_obj.display_pos[0] + space_obj.display_size[0] / 2),
            float(space_obj.display_pos[1] + space_obj.display_size[1] / 2)
        )

    open_set = []
    heapq.heappush(open_set, (0, start_space_name))

    came_from = {}
    g_score = {name: float('inf') for name in world_spaces}
    if start_space_name in g_score: # 防禦性檢查
        g_score[start_space_name] = 0
    else:
        # print(f"A* 內部錯誤: start_space_name '{start_space_name}' 不在 g_score 字典中。") # Debugging
        return None # 或者其他錯誤處理
        
    f_score = {name: float('inf') for name in world_spaces}
    if start_space_name in f_score: # 防禦性檢查
        f_score[start_space_name] = heuristic(get_space_center(start_space), get_space_center(goal_space))
    else:
        # print(f"A* 內部錯誤: start_space_name '{start_space_name}' 不在 f_score 字典中。") # Debugging
        return None # 或者其他錯誤處理

    processed_nodes_count = 0
    while open_set:
        processed_nodes_count += 1
        if processed_nodes_count > len(world_spaces) * 10: 
            # print(f"A* 警告: 處理節點過多 ({processed_nodes_count})，可能存在迴圈或無法到達的目標 ({start_space_name} -> {goal_space_name})。") # Debugging
            return None

        _, current_name = heapq.heappop(open_set)

        if current_name == goal_space_name:
            path = []
            temp_name = current_name
            while temp_name in came_from:
                path.append(temp_name)
                temp_name = came_from[temp_name]
            path.append(start_space_name)
            return path[::-1]

        current_space_obj = world_spaces.get(current_name)
        if not current_space_obj:
            continue
        current_center = get_space_center(current_space_obj)

        if not hasattr(current_space_obj, 'connected_spaces') or current_space_obj.connected_spaces is None:
            continue

        for neighbor_space_obj in current_space_obj.connected_spaces:
            if not hasattr(neighbor_space_obj, 'name') or neighbor_space_obj.name not in world_spaces or \
                neighbor_space_obj.name is None: # 確保 neighbor_space_obj.name 不是 None
                continue 

            neighbor_name = neighbor_space_obj.name
            neighbor_center = get_space_center(neighbor_space_obj)
            
            # 確保 g_score[current_name] 不是 inf，如果是，則跳過 (表示 current_name 從未被正確處理)
            if g_score.get(current_name, float('inf')) == float('inf'):
                # print(f"A* Debug: Skipping neighbor {neighbor_name} of {current_name} because g_score of current is inf.") # Debugging
                continue
            
            cost_to_neighbor = heuristic(current_center, neighbor_center)
            if cost_to_neighbor <= 0: cost_to_neighbor = 1.0

            tentative_g_score = g_score.get(current_name, float('inf')) + cost_to_neighbor

            if tentative_g_score < g_score.get(neighbor_name, float('inf')):
                came_from[neighbor_name] = current_name
                g_score[neighbor_name] = tentative_g_score
                f_score[neighbor_name] = tentative_g_score + heuristic(neighbor_center, get_space_center(goal_space))
                heapq.heappush(open_set, (f_score[neighbor_name], neighbor_name))
    
    # print(f"A* 警告: 從 {start_space_name} 到 {goal_space_name} 找不到路徑。") # Debugging
    return None

class NPC(BaseModel):
    name: str
    description: str
    current_space: "Space"
    inventory: "Inventory"
    history: List[Dict[str, str]] = []
    first_tick: bool = True
    display_color: Optional[Tuple[int, int, int]] = None
    radius: Optional[int] = None
    position: Optional[List[float]] = None
    display_pos: Optional[List[int]] = None
    move_target: Optional[List[float]] = None
    move_speed: Optional[float] = 1.0
    waiting_interaction: Optional[Dict[str, Any]] = None
    is_thinking: bool = False
    thinking_status: str = ""
    action_status: str = ""

    path_to_follow: List[str] = Field(default_factory=list)
    current_path_segment_target_space_name: Optional[str] = None
    home_space_name: Optional[str] = None

    # 新增用於避讓物品的欄位
    original_move_target: Optional[List[float]] = None
    avoiding_item_name: Optional[str] = None # 假設用物品名稱作為ID
    
    # 新增：用於路徑規劃的欄位
    path_planner: Optional["PathPlanner"] = None
    current_path_points: List[Tuple[float, float]] = Field(default_factory=list)

    # ForwardRef必須在模型定義之後更新
    # Space.model_rebuild() # 這行通常在所有模型定義後執行
    # Inventory.model_rebuild()
    
    def set_path_planner(self, planner: "PathPlanner"):
        """設置NPC使用的路徑規劃器實例"""
        self.path_planner = planner
        
    def plan_path_to_target(self):
        """使用路徑規劃器規劃從當前位置到目標位置的路徑"""
        if not self.path_planner or not self.move_target or not self.position:
            return
            
        if hasattr(self, "current_space") and self.current_space:
            # 從當前位置到目標位置的路徑規劃
            start_pos = tuple(self.position[:2])  # 確保是二維座標
            target_pos = tuple(self.move_target[:2])  # 確保是二維座標
            
            # 使用全局空間數據
            global world_system
            if world_system and world_system.world and 'spaces' in world_system.world:
                all_spaces = world_system.world['spaces']
                # 使用路徑規劃器規劃路徑
                self.current_path_points = self.path_planner.find_path_with_obstacles(
                    self.current_space, 
                    self.current_space,  # 當前僅支持在同一空間內規劃
                    start_pos, 
                    target_pos, 
                    all_spaces
                )

    @classmethod

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

        # 定義物品互動操作
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
        使用 A* 演算法規劃路徑並開始移動到目標空間。
        更新 NPC 的 path_to_follow 和 current_path_segment_target_space_name。
        """
        target_space_name_lower = target_space_name.lower()

        if not hasattr(self, 'current_space') or not self.current_space or \
           not hasattr(self.current_space, 'name') or not self.current_space.name:
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'): # 確保屬性存在
                self.current_path_segment_target_space_name = None
            return f"錯誤: NPC {self.name} 沒有有效的 current_space 或 current_space.name，無法規劃路徑。"

        current_space_name_lower = self.current_space.name.lower()

        if current_space_name_lower == target_space_name_lower:
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'):
                self.current_path_segment_target_space_name = None
            return f"{self.name} 已經在 {target_space_name}。"

        global world_system
        if world_system is None or not hasattr(world_system, 'world') or 'spaces' not in world_system.world:
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'):
                self.current_path_segment_target_space_name = None
            return "錯誤: world_system 或其 world_spaces 未初始化，無法規劃路徑。"
        
        all_world_spaces = world_system.world.get('spaces')
        if not all_world_spaces:
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'):
                self.current_path_segment_target_space_name = None
            return "錯誤: world_system.world 中缺少 'spaces' 字典，無法規劃路徑。"

        # 先用精確的目標空間名稱搜索
        exact_target_space_name = None
        for space_name in all_world_spaces.keys():
            if space_name.lower() == target_space_name_lower:
                exact_target_space_name = space_name
                break
                
        # 如果找不到精確匹配，使用原始參數
        final_target_name = exact_target_space_name if exact_target_space_name else target_space_name

        print(f"DEBUG: move_to_space - 從 {self.current_space.name} 尋找路徑前往 {final_target_name}")
        path = find_path_astar(
            all_world_spaces,
            self.current_space.name, 
            final_target_name
        )

        if path and len(path) > 1:
            self.path_to_follow = path[1:]  # 排除當前空間
            
            # 確保第一個目標段落被設置
            if self.path_to_follow:
                self.current_path_segment_target_space_name = self.path_to_follow.pop(0)
                print(f"DEBUG: move_to_space - 找到路徑: {path}. 設置目標段落: {self.current_path_segment_target_space_name}")
                self.thinking_status = f"正在透過 A* 路徑前往 {final_target_name}。下一站: {self.current_path_segment_target_space_name}"
                
                # 新增：如果當前空間和下一個空間有連接點，使用路徑規劃器規劃到門口的路徑
                if self.current_path_segment_target_space_name in all_world_spaces:
                    next_space = all_world_spaces[self.current_path_segment_target_space_name]
                    # 當NPC有位置時，嘗試規劃到連接點的路徑
                    if hasattr(self, 'position') and self.position and len(self.position) >= 2 and hasattr(self, 'path_planner') and self.path_planner:
                        # 找到當前空間到下一空間的連接點（通常是門口）
                        connection_point = self._find_connection_point(self.current_space, next_space)
                        if connection_point:
                            # 設置移動目標為連接點
                            self.move_target = list(connection_point)
                            # 使用路徑規劃器規劃到連接點的路徑
                            self.plan_path_to_target()
                
                return f"開始 A* 路徑前往 {final_target_name}。下一站: {self.current_path_segment_target_space_name}"
            else: 
                # 路徑只有 [current, target]，所以 path[1:] 就是 [target]，pop 後 path_to_follow 為空
                self.current_path_segment_target_space_name = final_target_name  # 直接設置為目標
                print(f"DEBUG: move_to_space - 找到直接路徑: {path}. 設置目標段落: {self.current_path_segment_target_space_name}")
                self.thinking_status = f"正在直接前往鄰近的 {final_target_name}"
                return f"開始 (單步) 路徑前往 {final_target_name}."
        elif path and len(path) == 1: 
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'):
                self.current_path_segment_target_space_name = None
            return f"{self.name} 已經在 {final_target_name} (A* 確認)。"
        else:
            print(f"DEBUG: move_to_space - 找不到從 {self.current_space.name} 到 {final_target_name} 的路徑")
            self.path_to_follow = []
            if hasattr(self, 'current_path_segment_target_space_name'):
                self.current_path_segment_target_space_name = None
            return f"找不到從 {self.current_space.name} 到 {final_target_name} 的 A* 路徑。"
            
    def _find_connection_point(self, current_space: "Space", next_space: "Space") -> Optional[Tuple[float, float]]:
        """找到兩個空間之間的連接點（門口位置）"""
        # 這裡假設空間是矩形，並檢查它們是否有重疊
        if not hasattr(current_space, 'display_pos') or not hasattr(current_space, 'display_size') or \
           not hasattr(next_space, 'display_pos') or not hasattr(next_space, 'display_size'):
            return None
            
        # 獲取空間矩形
        cs_x, cs_y = current_space.display_pos
        cs_w, cs_h = current_space.display_size
        ns_x, ns_y = next_space.display_pos
        ns_w, ns_h = next_space.display_size
        
        # 檢查空間是否有重疊區域
        overlap_x1 = max(cs_x, ns_x)
        overlap_y1 = max(cs_y, ns_y)
        overlap_x2 = min(cs_x + cs_w, ns_x + ns_w)
        overlap_y2 = min(cs_y + cs_h, ns_y + ns_h)
        
        # 如果有重疊
        if overlap_x2 > overlap_x1 and overlap_y2 > overlap_y1:
            # 返回重疊區域中心
            connection_x = (overlap_x1 + overlap_x2) / 2
            connection_y = (overlap_y1 + overlap_y2) / 2
            return (connection_x, connection_y)
            
        # 如果沒有重疊，檢查它們是否為相鄰空間（假設相差在30像素內可視為相鄰）
        tolerance = 30.0
        
        # 檢查左/右相鄰
        if abs(cs_x + cs_w - ns_x) < tolerance or abs(ns_x + ns_w - cs_x) < tolerance:
            # 計算垂直方向上的重疊
            vertical_overlap_y1 = max(cs_y, ns_y)
            vertical_overlap_y2 = min(cs_y + cs_h, ns_y + ns_h)
            
            if vertical_overlap_y2 > vertical_overlap_y1:
                # 在垂直中點和水平相接處創建連接點
                middle_y = (vertical_overlap_y1 + vertical_overlap_y2) / 2
                
                if abs(cs_x + cs_w - ns_x) < tolerance:
                    # 當前空間在左側，下一個空間在右側
                    connection_x = (cs_x + cs_w + ns_x) / 2
                else:
                    # 當前空間在右側，下一個空間在左側
                    connection_x = (ns_x + ns_w + cs_x) / 2
                    
                return (connection_x, middle_y)
        
        # 檢查上/下相鄰
        if abs(cs_y + cs_h - ns_y) < tolerance or abs(ns_y + ns_h - cs_y) < tolerance:
            # 計算水平方向上的重疊
            horizontal_overlap_x1 = max(cs_x, ns_x)
            horizontal_overlap_x2 = min(cs_x + cs_w, ns_x + ns_w)
            
            if horizontal_overlap_x2 > horizontal_overlap_x1:
                # 在水平中點和垂直相接處創建連接點
                middle_x = (horizontal_overlap_x1 + horizontal_overlap_x2) / 2
                
                if abs(cs_y + cs_h - ns_y) < tolerance:
                    # 當前空間在上方，下一個空間在下方
                    connection_y = (cs_y + cs_h + ns_y) / 2
                else:
                    # 當前空間在下方，下一個空間在上方
                    connection_y = (ns_y + ns_h + cs_y) / 2
                    
                return (middle_x, connection_y)
        
        # 如果以上都不符合，返回兩個空間中心點的中點作為連接點
        center_cs_x = cs_x + cs_w / 2
        center_cs_y = cs_y + cs_h / 2
        center_ns_x = ns_x + ns_w / 2
        center_ns_y = ns_y + ns_h / 2
        
        return ((center_cs_x + center_ns_x) / 2, (center_cs_y + center_ns_y) / 2)

    def move_to_item(self, item_name: str) -> str:
        """
        將 NPC 移動到指定物品的位置。
        修改：嚴格限制在當前空間查找物品，並計算停在物品邊緣。
        """
        # 在當前空間中查找物品
        for item in self.current_space.items:
            if item.name.lower() == item_name.lower():
                # --- 開始：計算停在物品邊緣的邏輯 ---
                if hasattr(item, "position") and item.position and \
                    hasattr(item, "size") and item.size and \
                    hasattr(self, "radius") and self.radius is not None and \
                    hasattr(self, "position") and self.position is not None and \
                    all(isinstance(p, (float, int)) for p in self.position) and \
                    all(isinstance(p, (float, int)) for p in item.position) and \
                    all(isinstance(s, (float, int)) for s in item.size):

                    # 確保 item.position 和 item.size 是有效的數值列表
                    item_pos_x, item_pos_y = float(item.position[0]), float(item.position[1])
                    item_size_w, item_size_h = float(item.size[0]), float(item.size[1])
                    npc_pos_x, npc_pos_y = float(self.position[0]), float(self.position[1])
                    npc_rad = float(self.radius)
                    
                    # 假設 item.position 是左上角
                    item_center_x = item_pos_x + item_size_w / 2
                    item_center_y = item_pos_y + item_size_h / 2

                    vec_x = item_center_x - npc_pos_x
                    vec_y = item_center_y - npc_pos_y
                    dist_to_item_center = math.hypot(vec_x, vec_y)

                    item_effective_radius = max(item_size_w, item_size_h) / 2
                    
                    stopping_distance_from_center = npc_rad + item_effective_radius + 5.0 # 5.0 是小間隙

                    # 最小互動距離，防止 NPC 距離太遠就停下 (例如，比目標停止點遠2步)
                    move_speed_val = self.move_speed if self.move_speed is not None and self.move_speed > 0 else 1.0
                    min_interaction_engage_distance = stopping_distance_from_center + (move_speed_val * 2.0)

                    if dist_to_item_center <= stopping_distance_from_center: 
                        self.move_target = list(self.position) 
                        self.original_move_target = None 
                        self.avoiding_item_name = None   
                        return f"已經在 {item.name} 旁邊，準備互動。"
                    elif dist_to_item_center <= min_interaction_engage_distance : 
                        norm_vec_x = vec_x / dist_to_item_center if dist_to_item_center > 1e-6 else 0 # 避免除以零
                        norm_vec_y = vec_y / dist_to_item_center if dist_to_item_center > 1e-6 else 0
                        
                        target_x = item_center_x - norm_vec_x * stopping_distance_from_center
                        target_y = item_center_y - norm_vec_y * stopping_distance_from_center
                        
                        self.move_target = [target_x, target_y]
                        if not self.original_move_target : self.original_move_target = list(self.move_target) 
                        
                        # 新增：使用路徑規劃器規劃路徑
                        self.plan_path_to_target()
                        
                        return f"靠近 {item.name} 的邊緣準備互動。"
                    else: 
                        norm_vec_x = vec_x / dist_to_item_center if dist_to_item_center > 1e-6 else 0
                        norm_vec_y = vec_y / dist_to_item_center if dist_to_item_center > 1e-6 else 0
                        
                        target_x = item_center_x - norm_vec_x * stopping_distance_from_center
                        target_y = item_center_y - norm_vec_y * stopping_distance_from_center
                        
                        self.move_target = [target_x, target_y]
                        if not self.original_move_target : self.original_move_target = list(self.move_target)
                        
                        # 新增：使用路徑規劃器規劃路徑
                        self.plan_path_to_target()
                        
                        return f"移動到 {item.name} 的邊緣進行互動。"
                # --- 結束：計算停在物品邊緣的邏輯 ---
                else:
                    # This block executes if the detailed edge calculation cannot be performed
                    if hasattr(item, "position") and item.position:
                        self.move_target = [float(p) for p in item.position]
                        
                        # 新增：使用路徑規劃器規劃路徑
                        self.plan_path_to_target()
                        
                        return f"移動到{item.name}的位置 (詳細邊緣計算所需資訊不足)"
                    else: # Item does not have a direct position, or the earlier check failed.
                        # Fallback: try to use current_space center
                        if hasattr(self.current_space, 'display_pos') and self.current_space.display_pos and \
                           hasattr(self.current_space, 'display_size') and self.current_space.display_size and \
                           len(self.current_space.display_pos) == 2 and len(self.current_space.display_size) == 2:
                            space_center_x = self.current_space.display_pos[0] + self.current_space.display_size[0] // 3
                            space_center_y = self.current_space.display_pos[1] + self.current_space.display_size[1] // 2
                            self.move_target = [float(space_center_x), float(space_center_y)]
                            
                            # 新增：使用路徑規劃器規劃路徑
                            self.plan_path_to_target()
                        else: # Fallback if space position/size is invalid
                            self.move_target = [0.0,0.0] # Default to origin or handle error
                        return f"移動到{item.name}所在空間的大致位置 (物品位置資訊不足或空間資訊無效)"

        return f"在 {self.current_space.name} 中找不到物品：{item_name} (請確認 AI 選擇的物品確實存在於當前空間)"

    def interact_with_item(self, item_name: str, how_to_interact: str) -> str:
        """
        將 NPC 移動到指定物品的位置並與之互動。
        """
        # 先移動到物品位置
        move_result = self.move_to_item(item_name)
        if not move_result.startswith("找不到物品"):
            # 設置等待互動的狀態資訊
            self.waiting_interaction = {
                "item_name": item_name,
                "how_to_interact": how_to_interact,
                "started": True
            }
            return f"正在移動到{item_name}準備互動..."
        return move_result

    def complete_interaction(self) -> str:
        """
        當NPC完成移動後，執行互動。
        """
        if hasattr(self, "waiting_interaction") and self.waiting_interaction and self.waiting_interaction.get("started", False):
            item_name = self.waiting_interaction["item_name"]
            how_to_interact = self.waiting_interaction["how_to_interact"]

            # 使用 world_system 處理互動，而不是簡單地添加消息
            global world_system
            if world_system is None:
                from backend import AI_System
                world_system = AI_System()

            # 調用 AI_System 的 process_interaction 方法處理互動
            interaction_result = world_system.process_interaction(self, item_name, how_to_interact)

            # 如果互動結果為空，提供一個默認消息
            if not interaction_result:
                interaction_result = f"與{item_name}互動: {how_to_interact}"

            return interaction_result
        return "沒有待處理的互動。"

    def process_tick(self, user_input: Optional[str] = None):
        """
        處理這一 tick 的 NPC 行為
        """
        global world_system # 移到方法頂部

        # 檢查 NPC 是否完成了互動等待
        if self.waiting_interaction and self.waiting_interaction.get("started", False):
            # 檢查是否到達目的地
            if self.move_target is None: # 已到達
                interaction_result = self.complete_interaction()
                self.waiting_interaction = None # 清除等待狀態
                self.history.append({"role": "system", "content": f"互動完成: {interaction_result}"})
                return f"與 {self.waiting_interaction.get('item_name', '物品')} 的互動完成: {interaction_result}"
            else: # 尚未到達，繼續移動
                # (移動邏輯會在下面處理)
                self.action_status = f"正在前往 {self.waiting_interaction.get('item_name', '物品')} 以便互動"
                # return f"NPC {self.name} 正在前往 {self.waiting_interaction.get('item_name', '物品')} 以便互動..."
        
        # 記錄此 NPC 進入當前空間
        if self.first_tick:
            self.add_space_to_history()
            self.first_tick = False
            
        # --- 移動處理開始 ---
        original_thinking_status_before_move = self.thinking_status # 保存移動前的思考狀態
        movement_occurred_this_tick = False

        if hasattr(self, 'move_target') and self.move_target and hasattr(self, 'position') and self.position:
            movement_occurred_this_tick = True # 標記發生了移動計算
            target_x, target_y = self.move_target[0], self.move_target[1]
            curr_x, curr_y = self.position[0], self.position[1]
            
            next_point = None
            if hasattr(self, 'current_path_points') and self.current_path_points and len(self.current_path_points) > 0:
                next_point = self.current_path_points[0]
                target_x, target_y = next_point[0], next_point[1]
            
            dx = target_x - curr_x
            dy = target_y - curr_y
            distance = math.sqrt(dx * dx + dy * dy)
            move_speed_val = self.move_speed if hasattr(self, 'move_speed') and self.move_speed is not None else 1.0
            move_distance = min(distance, move_speed_val)
            
            if distance < move_speed_val: # 已到達（或非常接近）目標點
                self.position[0] = target_x
                self.position[1] = target_y
                # print(f"DEBUG: NPC {self.name} REACHED point {target_x, target_y}. Current pos: {self.position}")
                
                if next_point and hasattr(self, 'current_path_points') and self.current_path_points:
                    self.current_path_points.pop(0)
                    if not self.current_path_points: # 如果路徑點已空
                        # print(f"DEBUG: NPC {self.name} finished path. Original target: {self.original_move_target}, Current pos: {self.position}")
                        # 檢查是否到達最終的 original_move_target
                        if self.original_move_target and \
                            math.isclose(self.position[0], self.original_move_target[0]) and \
                            math.isclose(self.position[1], self.original_move_target[1]):
                            print(f"DEBUG: NPC {self.name} has reached the final original_move_target: {self.original_move_target}")
                            self.move_target = None
                            self.original_move_target = None
                            self.avoiding_item_name = None
                            self.action_status = f"已到達 {self.original_move_target}"
                            self.thinking_status = f"已到達目的地 {self.original_move_target}"
                        elif not self.current_path_segment_target_space_name: # 如果不是跨空間移動
                            # print(f"DEBUG: NPC {self.name} path empty, not cross-space, clearing move_target.")
                            self.move_target = None # 清除移動目標，因為路徑已完成
                            self.original_move_target = None
                            self.avoiding_item_name = None


                elif self.move_target and math.isclose(self.position[0], self.move_target[0]) and math.isclose(self.position[1], self.move_target[1]):
                    # 如果沒有路徑點，但已到達 move_target，則清除
                    # print(f"DEBUG: NPC {self.name} reached direct move_target, clearing it.")
                    self.move_target = None
                    self.original_move_target = None
                    self.avoiding_item_name = None
            else: # 尚未到達目標點，繼續移動
                norm_dx = dx / distance if distance > 1e-9 else 0
                norm_dy = dy / distance if distance > 1e-9 else 0
                new_x = curr_x + norm_dx * move_distance
                new_y = curr_y + norm_dy * move_distance
                
                can_move_x = True
                can_move_y = True
                if hasattr(self.current_space, 'display_pos') and hasattr(self.current_space, 'display_size'):
                    space_x, space_y = self.current_space.display_pos
                    space_width, space_height = self.current_space.display_size
                    npc_radius = self.radius if hasattr(self, 'radius') and self.radius is not None else 15
                    
                    if new_x - npc_radius < space_x or new_x + npc_radius > space_x + space_width:
                        can_move_x = False
                    if new_y - npc_radius < space_y or new_y + npc_radius > space_y + space_height:
                        can_move_y = False
                
                if can_move_x: self.position[0] = new_x
                if can_move_y: self.position[1] = new_y
                self.action_status = f"移動到 {[round(target_x,1), round(target_y,1)]}"

            # 檢查是否需要移動到下一個空間
            if not self.move_target and self.current_path_segment_target_space_name:
                global world_system
                target_space_obj = world_system.world['spaces'].get(self.current_path_segment_target_space_name)
                if target_space_obj:
                    # NPC 進入新空間的邏輯
                    if self.current_space and hasattr(self.current_space, 'npcs') and self in self.current_space.npcs:
                        self.current_space.npcs.remove(self)
                    self.current_space = target_space_obj
                    if hasattr(target_space_obj, 'npcs') and self not in target_space_obj.npcs:
                        target_space_obj.npcs.append(self)
                    self.add_space_to_history() # 記錄進入新空間
                    
                    # 更新NPC的位置到新空間的中心 (或入口點，如果有的話)
                    if hasattr(self, '_find_connection_point'):
                        entry_point = self._find_connection_point(target_space_obj, self.current_space) # 反過來找入口
                        if entry_point:
                            self.position = list(entry_point)
                        else:
                            self.position = [target_space_obj.display_pos[0] + target_space_obj.display_size[0] / 2,
                                        target_space_obj.display_pos[1] + target_space_obj.display_size[1] / 2]
                    else: # Fallback
                        self.position = [target_space_obj.display_pos[0] + target_space_obj.display_size[0] / 2,
                                        target_space_obj.display_pos[1] + target_space_obj.display_size[1] / 2]


                    self.thinking_status = f"已到達 {self.current_space.name}."
                    self.action_status = f"進入 {self.current_space.name}"
                    
                    if self.path_to_follow: # 如果還有後續路徑
                        self.current_path_segment_target_space_name = self.path_to_follow.pop(0)
                        self.thinking_status = f"繼續前往 {self.current_path_segment_target_space_name}"
                        # 這裡可以再次調用 move_to_space 的部分邏輯來規劃到下一個連接點
                        next_target_space_obj = world_system.world['spaces'].get(self.current_path_segment_target_space_name)
                        if next_target_space_obj and hasattr(self, '_find_connection_point') and self.path_planner:
                            connection_point = self._find_connection_point(self.current_space, next_target_space_obj)
                            if connection_point:
                                self.move_target = list(connection_point)
                                self.original_move_target = list(connection_point) # 更新原始目標
                                self.plan_path_to_target()
                    else: # 到達最終空間
                        self.current_path_segment_target_space_name = None
                        self.thinking_status = f"已完成跨空間移動，抵達最終空間 {self.current_space.name}"
                else:
                    self.current_path_segment_target_space_name = None # 目標空間無效
        # --- 移動處理結束 ---

        # 如果這一 tick 主要是移動，或者正在等待互動，則可能不需要立即進行新的 AI 思考
        if movement_occurred_this_tick and self.move_target: # 如果還在移動中
            # self.thinking_status = original_thinking_status_before_move # 恢復移動前的思考狀態，如果被移動覆蓋
            return self.action_status # 返回當前移動狀態

        if self.waiting_interaction and self.waiting_interaction.get("started", False) and self.move_target:
             return f"NPC {self.name} 正在前往 {self.waiting_interaction.get('item_name', '物品')} 以便互動..."


        # --- AI 思考和行動決策 ---
        self.is_thinking = True
        self.thinking_status = "正在思考..."
        
        # global world_system # 確保 world_system 是最新的 # <--- 原本在這裡，已上移
        if world_system is None:
            from backend import AI_System # 應該在頂層或初始化時完成
            world_system = AI_System() 
            # world_system.initialize_world(...) # 需要 world data, 這不應該在這裡發生

        GeneralResponseSchema = self.update_schema() # 獲取動態 schema

        if user_input:
            self.history.append({"role": "user", "content": f"User: {user_input}"})

        # 準備 API 調用
        messages_for_api = list(self.history) # 複製歷史記錄
        
        # 構建系統提示 (可以根據需要調整)
        system_prompt = (
            f"你是 NPC {self.name} ({self.description}). "
            f"目前時間是 {world_system.time}, 天氣是 {world_system.weather}. "
            f"你位於 {self.current_space.name} ({self.current_space.description}). "
            f"你的家是 {self.home_space_name if self.home_space_name else '未設定'}. "
            "根據你的歷史、當前環境和用戶輸入來決定下一步行動。"
            "思考你的目標和可能的行動，然後選擇一個具體的行動或決定什麼都不做。"
        )
        messages_for_api.insert(0, {"role": "system", "content": system_prompt})
        
        self.action_status = "" # 清除上一tick的行動狀態
        
        try:
            completion = client.beta.chat.completions.parse(
                model="gpt-4o", # 使用標準模型
                messages=messages_for_api, # 使用添加了系統提示的歷史記錄
                response_format=GeneralResponseSchema # 使用動態生成的 Pydantic 模型
            )
            response = completion.choices[0].message.parsed
        except Exception as e:
            print(f"ERROR: NPC {self.name} 思考時 API 調用失敗: {e}")
            self.history.append({"role": "system", "content": f"思考錯誤: {e}"})
            self.is_thinking = False
            self.thinking_status = f"思考出錯: {e}"
            return f"NPC {self.name} 思考出錯。"

        self.is_thinking = False
        self.thinking_status = response.self_talk_reasoning if response and hasattr(response, 'self_talk_reasoning') else "思考完成"
        
        # 將 AI 的思考加入歷史
        if response and hasattr(response, 'self_talk_reasoning'):
            self.history.append({"role": "assistant", "content": f"Thinking: {response.self_talk_reasoning}"})
        else: # response 可能為 None 或沒有 self_talk_reasoning
             self.history.append({"role": "assistant", "content": "Thinking: (No reasoning provided or error in response structure)"})


        action_result_str = "決定不採取行動。"
        if response and response.action:
            action = response.action
            action_type_str = getattr(action, 'action_type', 'unknown_action')
            self.action_status = f"準備執行: {action_type_str}"

            if hasattr(action, "action_type"):
                action_description_for_history = ""
                if action.action_type == "interact_item":
                    item_name = getattr(action, 'interact_with', '未知物品')
                    how_to = getattr(action, 'how_to_interact', '未知方式')
                    action_result_str = self.interact_with_item(item_name, how_to)
                    action_description_for_history = f"Action: 計劃與 {item_name} 互動: {how_to}"
                elif action.action_type == "enter_space":
                    target_space = getattr(action, 'target_space', '未知空間')
                    action_result_str = self.move_to_space(target_space)
                    action_description_for_history = f"Action: 計劃移動到 {target_space}"
                elif action.action_type == "talk_to_npc":
                    target_npc = getattr(action, 'target_npc', '未知NPC')
                    dialogue = getattr(action, 'dialogue', '')
                    action_result_str = self.talk_to_npc(target_npc, dialogue) # 同步版本
                    # 如果需要異步，可以使用 await self.async_talk_to_npc(target_npc, dialogue)
                    # 但 process_tick 本身不是 async, 所以這裡用同步的
                    action_description_for_history = f"Action: 計劃對 {target_npc} 說: {dialogue}"
                else:
                    action_result_str = f"未知行動類型: {action.action_type}"
                    action_description_for_history = f"Action: 嘗試未知行動 {action.action_type}"
                self.history.append({"role": "assistant", "content": action_description_for_history})
            else:
                action_result_str = "行動指令無效 (缺少 action_type)。"
                self.history.append({"role": "system", "content": "系統: AI返回的行動指令無效。"})
        else: # No action
            self.history.append({"role": "system", "content": "系統: AI決定不採取行動。"})
            self.action_status = "無行動"

        self.history.append({"role": "system", "content": f"結果: {action_result_str}"})
        # print(f"NPC {self.name} process_tick result: {self.thinking_status} | Action: {action_result_str}")
        
        # 返回 AI 的思考過程 + 執行結果的簡述
        final_output = f"思考: {self.thinking_status}\n行動結果: {action_result_str}"
        self.action_status = action_result_str # 更新NPC的行動狀態，以便顯示
        return final_output

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
        # 使用 Item 類創建物品
        items_dict[item_data["name"]] = Item(
            name = item_data["name"],
            description = item_data["description"],
            properties = item_data.get("properties", {}),
            position = item_data.get("position"),
            size = item_data.get("size"),
            image_path = item_data.get("image_path"),  # 讀取圖片路徑
            image_scale = item_data.get("image_scale", 1.0)  # 讀取圖片縮放比例
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
                npc_pos = list(npc_data["position"])  # 轉換為列表
            else:
                # 預設在空間中央
                npc_pos = [
                    starting_space.display_pos[0] + starting_space.display_size[0] // 2,
                    starting_space.display_pos[1] + starting_space.display_size[1] // 2
                ]
            # 創建 NPC
            npc = NPC(
                name = npc_data["name"],
                description = npc_data["description"],
                current_space = starting_space,
                inventory = inventory,
                history = npc_data.get("history", []),
                display_pos = npc_data.get("display_pos", list(npc_pos)), # display_pos 通常是整數像素座標
                position = [float(p) for p in npc_data.get("position", npc_pos)], # 確保 position 是 float 列表
                move_target = [float(p) for p in npc_data.get("move_target")] if npc_data.get("move_target") else None, # 確保 move_target 是 float 列表
                move_speed = float(npc_data.get("move_speed", 1.0)), # 確保 move_speed 是 float
                display_color = npc_data.get("display_color", None),
                radius = npc_data.get("radius", 15),
                is_thinking = npc_data.get("is_thinking", False),
                first_tick = npc_data.get("first_tick", True),
                home_space_name = npc_data.get("home_space_name"), # 新增讀取 home_space_name
                original_move_target = [float(p) for p in npc_data.get("move_target")] if npc_data.get("move_target") else None, # 確保 original_move_target 是 float 列表
                avoiding_item_name = npc_data.get("avoiding_item_name") # 新增讀取 avoiding_item_name
            )

            # 將 NPC 添加到其起始空間
            starting_space.npcs.append(npc)

            # 將 NPC 存儲在字典中
            npcs_dict[npc_data["name"]] = npc

    # 取得物件參考
    spaces = list(spaces_dict.values())
    npcs = list(npcs_dict.values())
    items = list(items_dict.values())
    
    # --- Modified Image Handling Logic ---
    picture_dir_path = get_picture_dir()
    os.makedirs(picture_dir_path, exist_ok=True) # Ensure picture directory exists

    for item in items:
        item_name_lower = getattr(item, "name", "").lower()
        determined_image_filename = None

        # 1. If item.image_path is already set (e.g., from JSON item_data), respect it.
        if getattr(item, "image_path", None):
            determined_image_filename = item.image_path
        # 2. If not set from JSON, try to derive it.
        elif item_name_lower: # Only if item has a name
            core_name_filename = None
            if "_" in item_name_lower:
                core_name = item_name_lower.split("_")[0]
                core_name_filename = f"{core_name}.png"
            
            full_name_filename = f"{item_name_lower}.png"

            # Check existence to assign preferred existing file
            # This logic helps in providing a potentially existing file path to pygame_display
            if core_name_filename and os.path.exists(os.path.join(picture_dir_path, core_name_filename)):
                determined_image_filename = core_name_filename
            elif os.path.exists(os.path.join(picture_dir_path, full_name_filename)):
                determined_image_filename = full_name_filename
            else:
                # Neither known derived name exists. Assign one for pygame_display to potentially generate.
                # Prefer simpler core_name if applicable, otherwise full name.
                if core_name_filename:
                    determined_image_filename = core_name_filename
                else:
                    determined_image_filename = full_name_filename
            item.image_path = determined_image_filename # Assign determined filename to item
        else:
            item.image_path = None # No name, no image path

        # 3. Image generation call REMOVED. 
        #    pygame_display.py will now handle generation if item.image_path is set but file doesn't exist.
        #    If item.image_path is None, pygame_display will use a placeholder.

    # --- End Modified Image Handling Logic ---

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
                "items": [item.name for item in space.items],
                "space_positions": space.display_pos,
                "space_size": space.display_size
                # NPC 單獨處理
            }
            world_data["spaces"].append(space_data)

        # 序列化物品 - 簡化版本，不包含 interactions
        for item_name, item in world["items"].items():
            item_data = {
                "name": item.name,
                "description": item.description,
                "properties": item.properties,
                "position": item.position,  # 轉換為列表
                "size": item.size  # 轉換為列表
            }
            world_data["items"].append(item_data)

        # 序列化 NPC
        for npc_name, npc in world["npcs"].items():
            npc_data = {
                "name": npc.name,
                "description": npc.description,
                "starting_space": npc.current_space.name,
                "inventory": [item.name for item in npc.inventory.items],
                "history": npc.history,  # 保存 NPC 的記憶/歷史記錄
                "position": npc.position,  # 保存 NPC 的位置
                "display_pos": npc.display_pos,  # 保存 NPC 的顯示位置
                "move_target": npc.move_target,  # 保存 NPC 的移動目標
                "move_speed": npc.move_speed,  # 保存 NPC 的移動速度
                "display_color": npc.display_color,  # 保存 NPC 的顯示顏色
                "radius": npc.radius,  # 保存 NPC 的半徑
                "is_thinking": npc.is_thinking,  # 保存 NPC 是否正在思考
                "first_tick": npc.first_tick,  # 保存 NPC 是否是第一次 tick
                "home_space_name": npc.home_space_name,  # 新增保存 home_space_name
                "original_move_target": npc.original_move_target,  # 新增保存 original_move_target
                "avoiding_item_name": npc.avoiding_item_name  # 新增保存 avoiding_item_name
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
        print(f"[DEBUG] initialize_world: world keys before assignment:", list(world.keys()))
        # 深度複製世界數據以確保它是獨立的對象
        self.world = dict(world)  # 使用直接的字典賦值而不是引用賦值
        # 確保設置全局變量
        global world_system
        world_system = self
        print(f"[DEBUG] initialize_world: self.world keys after assignment:", list(self.world.keys()))

        # 顯示世界的基本信息
        print(f"[DEBUG] 世界名稱: {self.world['world_name']}")
        print(f"[DEBUG] 世界描述: {self.world['description']}")

        print(f"[DEBUG] 空間數量: {len(self.world['spaces'])}")
        space_names = list(self.world['spaces'].keys())
        print(f"[DEBUG] 空間名稱: {space_names}")

        print(f"[DEBUG] 物品數量: {len(self.world['items'])}")
        item_names = list(self.world['items'].keys())
        print(f"[DEBUG] 物品名稱: {item_names}")

        print(f"[DEBUG] NPC 數量: {len(self.world['npcs'])}")
        npc_names = list(self.world['npcs'].keys())
        print(f"[DEBUG] NPC 名稱: {npc_names}")

        print(f"[DEBUG] world_system.world keys:", list(world_system.world.keys()) if world_system else "None")

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
        global world_system
        # 確保 world 已經正確初始化
        if not self.world or len(self.world.keys()) == 0:
            print(f"[WARNING] 世界數據未正確初始化，嘗試重新獲取")
            # 使用 world_system
            if "world_system" in globals() and globals()["world_system"] is not None and hasattr(globals()["world_system"], "world"):
                print(f"[DEBUG] 使用 world_system.world")
                self.world = globals()["world_system"].world.copy() if globals()["world_system"].world else {}
                print(f"[DEBUG] world_system.world keys = {list(self.world.keys())}")
            # 使用 main 模組的 world_system
            elif "main" in sys.modules and hasattr(sys.modules["main"], "world_system") and sys.modules["main"].world_system is not None:
                print(f"[DEBUG] 使用 main 模組的 world_system.world")
                self.world = sys.modules["main"].world_system.world.copy() if sys.modules["main"].world_system.world else {}
                print(f"[DEBUG] main 模組的 world_system.world keys = {list(self.world.keys())}")
            else:
                print(f"[ERROR] 無法獲取世界數據，互動可能無法正常工作")

        # 先讓NPC移動到物品位置
        move_result = npc.move_to_item(item_name)
        if not move_result.startswith("找不到物品"):
            # 不再需要調用 OpenAI API，直接使用互動描述
            # 準備互動結果訊息
            interaction_result = f"{npc.name} 與 {item_name} 互動: {how_to_interact}"

            # 將互動訊息加入 NPC 的歷史記錄
            npc.history.append({"role": "system", "content": interaction_result})

            # 結束互動（確保 waiting_interaction 已初始化）
            if hasattr(npc, 'waiting_interaction') and npc.waiting_interaction is not None:
                npc.waiting_interaction["started"] = False
            else:
                print(f"[WARNING] {npc.name} 的 waiting_interaction 為 None 或不存在")

            return interaction_result
        return move_result

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
        print(f"[DEBUG] _create_item: self.world keys = {list(self.world.keys())}")
        if "spaces" not in self.world:
            return f"錯誤：world 結構異常，缺少 'spaces'。目前 world: {self.world}"
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
        return f"已在空間 '{space_name}' 創建新物品 '{item_name}'。"

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
        # 保證 self.world['items'] 存在，即使為空
        items = self.world.get("items", {})
        if item_name in items:
            item = items[item_name]
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
