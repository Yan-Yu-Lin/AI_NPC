"""
Backend Adapter - 將現有 backend.py 適配到新的接口系統
這個適配器展示了如何將現有代碼轉換為使用 interfaces.py 中定義的清晰接口

使用方式：
1. 這個適配器包裝現有的 AI_System 和相關類
2. 提供符合新接口的方法
3. 將前端顯示相關邏輯分離出來
4. 作為重構過程中的過渡方案
"""

from typing import List, Dict, Any, Optional, Union
import time
from dataclasses import dataclass

# 導入新的接口定義
from interfaces import (
    BackendAPI, Position, Size, Color, NPCState,
    NPCDisplayData, ItemDisplayData, SpaceDisplayData, WorldDisplayData,
    UserInput, AIResponse, NPCNotFoundError, InvalidInputError, AIProcessingError
)

# 導入現有的後端組件
from backend import AI_System, NPC, Space, Item, world_system


class WorldBackendAdapter(BackendAPI):
    """
    將現有的 AI_System 適配到新接口的適配器類
    
    這個類展示了如何：
    1. 將後端數據轉換為前端顯示所需的DTO
    2. 隱藏後端的內部數據結構
    3. 提供清晰的API邊界
    4. 處理顯示相關的計算（原本不應該在後端）
    """
    
    def __init__(self, ai_system: AI_System):
        """
        初始化適配器
        
        Args:
            ai_system: 現有的 AI_System 實例
        """
        self.ai_system = ai_system
        self.active_npc_id: Optional[str] = None
        self.npc_states: Dict[str, NPCState] = {}
        self.ai_thinking: Dict[str, bool] = {}
        
        # 初始化時設定第一個NPC為活躍NPC
        if self.ai_system.npcs_data:
            self.active_npc_id = next(iter(self.ai_system.npcs_data.keys()))
    
    # ========== DisplayDataProvider 接口實現 ==========
    
    def get_world_display_data(self) -> WorldDisplayData:
        """獲取完整的世界顯示數據"""
        try:
            npcs = self._convert_npcs_to_display_data()
            items = self._convert_items_to_display_data()
            spaces = self._convert_spaces_to_display_data()
            
            return WorldDisplayData(
                world_name=self.ai_system.world_name_str,
                description=self.ai_system.world_description_str,
                current_time=self.ai_system.current_time,
                weather=self.ai_system.weather,
                npcs=npcs,
                items=items,
                spaces=spaces
            )
        except Exception as e:
            raise AIProcessingError(f"Failed to get world display data: {str(e)}")
    
    def get_npc_display_data(self, npc_id: Optional[str] = None) -> Union[List[NPCDisplayData], NPCDisplayData]:
        """獲取NPC顯示數據"""
        try:
            if npc_id:
                if npc_id not in self.ai_system.npcs_data:
                    raise NPCNotFoundError(f"NPC with ID '{npc_id}' not found")
                npc = self.ai_system.npcs_data[npc_id]
                return self._convert_npc_to_display_data(npc)
            else:
                return self._convert_npcs_to_display_data()
        except NPCNotFoundError:
            raise
        except Exception as e:
            raise AIProcessingError(f"Failed to get NPC display data: {str(e)}")
    
    def get_active_npc_id(self) -> Optional[str]:
        """獲取當前活躍的NPC ID"""
        return self.active_npc_id
    
    # ========== UserInputHandler 接口實現 ==========
    
    def handle_terminal_command(self, command: str) -> str:
        """處理終端命令"""
        try:
            command = command.strip().lower()
            
            if command == 'quit':
                return "退出命令已接收"
            elif command.startswith('p'):
                # 處理打印歷史命令
                parts = command.split()
                if len(parts) == 1 and self.active_npc_id:
                    # 只有 'p'，顯示當前活躍NPC的歷史
                    return self._format_npc_history(self.active_npc_id)
                elif len(parts) == 2:
                    # 'p <npc_name>'，顯示指定NPC的歷史
                    npc_name = parts[1]
                    if npc_name in self.ai_system.npcs_data:
                        return self._format_npc_history(npc_name)
                    else:
                        return f"找不到名為 '{npc_name}' 的NPC"
                else:
                    return "用法：p [npc_name]"
            else:
                return f"未知命令：{command}"
                
        except Exception as e:
            raise InvalidInputError(f"Failed to handle terminal command: {str(e)}")
    
    def handle_npc_selection(self, npc_id: str) -> bool:
        """處理NPC選擇"""
        try:
            if npc_id not in self.ai_system.npcs_data:
                raise NPCNotFoundError(f"NPC with ID '{npc_id}' not found")
            
            self.active_npc_id = npc_id
            return True
        except NPCNotFoundError:
            raise
        except Exception as e:
            raise InvalidInputError(f"Failed to select NPC: {str(e)}")
    
    def handle_save_request(self, save_path: Optional[str] = None) -> bool:
        """處理保存請求"""
        try:
            from backend import save_world_to_json
            
            if save_path is None:
                save_path = "worlds/auto_save.json"
                
            return save_world_to_json(self.ai_system, save_path)
        except Exception as e:
            raise AIProcessingError(f"Failed to save world: {str(e)}")
    
    # ========== AIProcessor 接口實現 ==========
    
    def process_npc_tick(self, npc_id: str, user_input: Optional[str] = None) -> AIResponse:
        """處理NPC的一個時間步"""
        try:
            if npc_id not in self.ai_system.npcs_data:
                raise NPCNotFoundError(f"NPC with ID '{npc_id}' not found")
            
            npc = self.ai_system.npcs_data[npc_id]
            
            # 設置AI思考狀態
            self.ai_thinking[npc_id] = True
            self.npc_states[npc_id] = NPCState.THINKING
            
            try:
                # 調用原有的process_tick方法
                result = npc.process_tick(user_input)
                
                # 檢查是否有動作
                action_taken = None
                world_changed = False
                
                if result and len(result.strip()) > 0:
                    # 簡化的動作檢測（可以根據需要增強）
                    if "移動到" in result:
                        action_taken = "move"
                        world_changed = True
                    elif "互動" in result:
                        action_taken = "interact"
                        world_changed = True
                    elif "對話" in result:
                        action_taken = "talk"
                
                return AIResponse(
                    npc_id=npc_id,
                    response_text=result,
                    action_taken=action_taken,
                    world_changed=world_changed
                )
                
            finally:
                # 重置AI思考狀態
                self.ai_thinking[npc_id] = False
                self.npc_states[npc_id] = NPCState.IDLE
                
        except NPCNotFoundError:
            raise
        except Exception as e:
            raise AIProcessingError(f"Failed to process NPC tick: {str(e)}")
    
    def is_ai_thinking(self, npc_id: str) -> bool:
        """檢查AI是否正在思考中"""
        return self.ai_thinking.get(npc_id, False)
    
    # ========== 私有輔助方法 ==========
    
    def _convert_npcs_to_display_data(self) -> List[NPCDisplayData]:
        """將所有NPC轉換為顯示數據"""
        display_data = []
        for npc_id, npc in self.ai_system.npcs_data.items():
            display_data.append(self._convert_npc_to_display_data(npc))
        return display_data
    
    def _convert_npc_to_display_data(self, npc: NPC) -> NPCDisplayData:
        """將單個NPC轉換為顯示數據"""
        # 從現有的顯示屬性中提取數據（這些在重構後會從後端移除）
        position = Position(x=0, y=0)
        if hasattr(npc, 'position') and npc.position:
            position = Position(x=npc.position[0], y=npc.position[1])
        elif hasattr(npc, 'display_pos') and npc.display_pos:
            position = Position(x=npc.display_pos[0], y=npc.display_pos[1])
        
        # 處理顏色
        color = None
        if hasattr(npc, 'display_color') and npc.display_color:
            color = Color(r=npc.display_color[0], g=npc.display_color[1], b=npc.display_color[2])
        
        # 處理半徑
        radius = 24.0
        if hasattr(npc, 'radius') and npc.radius:
            radius = float(npc.radius)
        
        # 獲取狀態
        state = self.npc_states.get(npc.name, NPCState.IDLE)
        
        return NPCDisplayData(
            npc_id=npc.name,
            name=npc.name,
            description=npc.description,
            position=position,
            color=color,
            radius=radius,
            state=state,
            chat_text=None,  # 可以根據需要添加最近的對話
            is_active=(npc.name == self.active_npc_id)
        )
    
    def _convert_items_to_display_data(self) -> List[ItemDisplayData]:
        """將所有物品轉換為顯示數據"""
        display_data = []
        for item_id, item in self.ai_system.items_data.items():
            display_data.append(self._convert_item_to_display_data(item))
        return display_data
    
    def _convert_item_to_display_data(self, item: Item) -> ItemDisplayData:
        """將單個物品轉換為顯示數據"""
        position = Position(x=0, y=0)
        if hasattr(item, 'position') and item.position:
            position = Position(x=item.position[0], y=item.position[1])
        
        size = Size(width=30, height=30)
        if hasattr(item, 'size') and item.size:
            size = Size(width=item.size[0], height=item.size[1])
        
        return ItemDisplayData(
            item_id=item.name,
            name=item.name,
            description=item.description,
            position=position,
            size=size
        )
    
    def _convert_spaces_to_display_data(self) -> List[SpaceDisplayData]:
        """將所有空間轉換為顯示數據"""
        display_data = []
        for space_id, space in self.ai_system.spaces_data.items():
            display_data.append(self._convert_space_to_display_data(space))
        return display_data
    
    def _convert_space_to_display_data(self, space: Space) -> SpaceDisplayData:
        """將單個空間轉換為顯示數據"""
        position = Position(x=0, y=0)
        if hasattr(space, 'display_pos') and space.display_pos:
            position = Position(x=space.display_pos[0], y=space.display_pos[1])
        
        size = Size(width=100, height=100)
        if hasattr(space, 'display_size') and space.display_size:
            size = Size(width=space.display_size[0], height=space.display_size[1])
        
        connected_spaces = [connected.name for connected in space.connected_spaces]
        
        return SpaceDisplayData(
            space_id=space.name,
            name=space.name,
            description=space.description,
            position=position,
            size=size,
            connected_spaces=connected_spaces
        )
    
    def _format_npc_history(self, npc_id: str) -> str:
        """格式化NPC歷史記錄"""
        if npc_id not in self.ai_system.npcs_data:
            return f"找不到NPC: {npc_id}"
        
        npc = self.ai_system.npcs_data[npc_id]
        history = npc.history
        
        if not history:
            return f"{npc.name} 沒有歷史記錄"
        
        formatted_lines = [f"=== {npc.name} 的歷史記錄 ==="]
        
        for i, message in enumerate(history[-10:], 1):  # 只顯示最近10條
            role = message.get('role', 'Unknown')
            content = message.get('content', '')
            formatted_lines.append(f"[{i:2d}] {role}: {content[:100]}...")
        
        return "\n".join(formatted_lines)


# ========== 便利函數 ==========

def create_backend_adapter(ai_system: Optional[AI_System] = None) -> WorldBackendAdapter:
    """
    創建後端適配器的便利函數
    
    Args:
        ai_system: 可選的AI_System實例，如果為None則使用全局world_system
        
    Returns:
        WorldBackendAdapter: 配置好的適配器實例
    """
    if ai_system is None:
        ai_system = world_system
    
    return WorldBackendAdapter(ai_system)


# ========== 使用範例 ==========

if __name__ == "__main__":
    """
    展示如何使用新的接口系統
    """
    
    # 創建適配器
    adapter = create_backend_adapter()
    
    try:
        # 獲取世界顯示數據
        world_data = adapter.get_world_display_data()
        print(f"世界名稱: {world_data.world_name}")
        print(f"當前時間: {world_data.current_time}")
        print(f"天氣: {world_data.weather}")
        
        # 獲取NPC數據
        npcs = adapter.get_npc_display_data()
        print(f"共有 {len(npcs)} 個NPC")
        
        for npc in npcs:
            print(f"  - {npc.name} 在位置 ({npc.position.x}, {npc.position.y})")
        
        # 處理終端命令
        result = adapter.handle_terminal_command("p")
        print(f"終端命令結果: {result}")
        
    except Exception as e:
        print(f"錯誤: {e}") 