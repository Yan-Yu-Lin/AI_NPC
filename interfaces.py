"""
API 接口和數據契約定義
用於前端（pygame顯示）和後端（AI邏輯）之間的清晰分離

設計原則：
1. 後端不包含任何顯示相關代碼
2. 前端不直接訪問後端的內部數據結構
3. 所有通信通過定義的接口進行
4. 使用類型提示確保類型安全
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol, Tuple, Union
from abc import ABC, abstractmethod
from enum import Enum

# ========== 數據傳輸對象 (DTOs) ==========

@dataclass
class Position:
    """表示2D座標位置"""
    x: float
    y: float
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)

@dataclass
class Size:
    """表示2D尺寸"""
    width: float
    height: float
    
    def to_tuple(self) -> Tuple[float, float]:
        return (self.width, self.height)

@dataclass
class Color:
    """表示RGB顏色"""
    r: int
    g: int
    b: int
    
    def to_tuple(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)

class NPCState(Enum):
    """NPC狀態枚舉"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    TALKING = "talking"

@dataclass
class NPCDisplayData:
    """NPC顯示數據 - 前端渲染需要的所有信息"""
    npc_id: str
    name: str
    description: str
    position: Position
    color: Optional[Color] = None
    radius: float = 24.0
    state: NPCState = NPCState.IDLE
    chat_text: Optional[str] = None
    is_active: bool = False  # 是否為當前選中的NPC

@dataclass
class ItemDisplayData:
    """物品顯示數據"""
    item_id: str
    name: str
    description: str
    position: Position
    size: Size

@dataclass
class SpaceDisplayData:
    """空間顯示數據"""
    space_id: str
    name: str
    description: str
    position: Position
    size: Size
    connected_spaces: List[str]

@dataclass
class WorldDisplayData:
    """完整的世界顯示數據"""
    world_name: str
    description: str
    current_time: str
    weather: str
    npcs: List[NPCDisplayData]
    items: List[ItemDisplayData]
    spaces: List[SpaceDisplayData]

@dataclass
class UserInput:
    """用戶輸入數據"""
    input_type: str  # "terminal_command", "npc_click", "key_press", etc.
    data: Dict[str, Any]
    timestamp: float

@dataclass
class AIResponse:
    """AI響應數據"""
    npc_id: str
    response_text: str
    action_taken: Optional[str] = None
    world_changed: bool = False

# ========== 核心接口定義 ==========

class DisplayDataProvider(Protocol):
    """後端提供顯示數據的接口"""
    
    def get_world_display_data(self) -> WorldDisplayData:
        """獲取完整的世界顯示數據
        
        Returns:
            WorldDisplayData: 包含所有渲染所需的數據
        """
        ...
    
    def get_npc_display_data(self, npc_id: Optional[str] = None) -> Union[List[NPCDisplayData], NPCDisplayData]:
        """獲取NPC顯示數據
        
        Args:
            npc_id: 如果提供，返回特定NPC的數據；否則返回所有NPC
            
        Returns:
            NPCDisplayData或List[NPCDisplayData]
        """
        ...
    
    def get_active_npc_id(self) -> Optional[str]:
        """獲取當前活躍的NPC ID"""
        ...

class UserInputHandler(Protocol):
    """處理用戶輸入的接口"""
    
    def handle_terminal_command(self, command: str) -> str:
        """處理終端命令
        
        Args:
            command: 終端輸入的命令
            
        Returns:
            str: 命令執行結果
        """
        ...
    
    def handle_npc_selection(self, npc_id: str) -> bool:
        """處理NPC選擇
        
        Args:
            npc_id: 選擇的NPC ID
            
        Returns:
            bool: 是否成功選擇
        """
        ...
    
    def handle_save_request(self, save_path: Optional[str] = None) -> bool:
        """處理保存請求
        
        Args:
            save_path: 保存路徑，如果為None則使用默認路徑
            
        Returns:
            bool: 是否保存成功
        """
        ...

class StateNotifier(Protocol):
    """狀態變化通知接口"""
    
    def on_npc_state_changed(self, npc_id: str, new_state: NPCState) -> None:
        """NPC狀態變化通知"""
        ...
    
    def on_world_state_changed(self) -> None:
        """世界狀態變化通知"""
        ...
    
    def on_ai_response(self, response: AIResponse) -> None:
        """AI響應通知"""
        ...

class AIProcessor(Protocol):
    """AI處理接口"""
    
    def process_npc_tick(self, npc_id: str, user_input: Optional[str] = None) -> AIResponse:
        """處理NPC的一個時間步
        
        Args:
            npc_id: NPC ID
            user_input: 可選的用戶輸入
            
        Returns:
            AIResponse: AI處理結果
        """
        ...
    
    def is_ai_thinking(self, npc_id: str) -> bool:
        """檢查AI是否正在思考中"""
        ...

# ========== 具體實現的抽象基類 ==========

class BackendAPI(ABC):
    """後端API的抽象基類，實現所有後端接口"""
    
    @abstractmethod
    def get_world_display_data(self) -> WorldDisplayData:
        """實現 DisplayDataProvider.get_world_display_data"""
        pass
    
    @abstractmethod
    def get_npc_display_data(self, npc_id: Optional[str] = None) -> Union[List[NPCDisplayData], NPCDisplayData]:
        """實現 DisplayDataProvider.get_npc_display_data"""
        pass
    
    @abstractmethod
    def get_active_npc_id(self) -> Optional[str]:
        """實現 DisplayDataProvider.get_active_npc_id"""
        pass
    
    @abstractmethod
    def handle_terminal_command(self, command: str) -> str:
        """實現 UserInputHandler.handle_terminal_command"""
        pass
    
    @abstractmethod
    def handle_npc_selection(self, npc_id: str) -> bool:
        """實現 UserInputHandler.handle_npc_selection"""
        pass
    
    @abstractmethod
    def handle_save_request(self, save_path: Optional[str] = None) -> bool:
        """實現 UserInputHandler.handle_save_request"""
        pass
    
    @abstractmethod
    def process_npc_tick(self, npc_id: str, user_input: Optional[str] = None) -> AIResponse:
        """實現 AIProcessor.process_npc_tick"""
        pass
    
    @abstractmethod
    def is_ai_thinking(self, npc_id: str) -> bool:
        """實現 AIProcessor.is_ai_thinking"""
        pass

class FrontendEventHandler(ABC):
    """前端事件處理器的抽象基類"""
    
    @abstractmethod
    def on_npc_state_changed(self, npc_id: str, new_state: NPCState) -> None:
        """實現 StateNotifier.on_npc_state_changed"""
        pass
    
    @abstractmethod
    def on_world_state_changed(self) -> None:
        """實現 StateNotifier.on_world_state_changed"""
        pass
    
    @abstractmethod
    def on_ai_response(self, response: AIResponse) -> None:
        """實現 StateNotifier.on_ai_response"""
        pass

# ========== 輔助函數 ==========

def create_position(x: float, y: float) -> Position:
    """創建Position對象的輔助函數"""
    return Position(x=x, y=y)

def create_size(width: float, height: float) -> Size:
    """創建Size對象的輔助函數"""
    return Size(width=width, height=height)

def create_color(r: int, g: int, b: int) -> Color:
    """創建Color對象的輔助函數"""
    return Color(r=r, g=g, b=b)

# ========== 錯誤定義 ==========

class InterfaceError(Exception):
    """接口相關錯誤的基礎異常類"""
    pass

class NPCNotFoundError(InterfaceError):
    """找不到指定NPC時拋出"""
    pass

class InvalidInputError(InterfaceError):
    """無效輸入時拋出"""
    pass

class AIProcessingError(InterfaceError):
    """AI處理錯誤時拋出"""
    pass 