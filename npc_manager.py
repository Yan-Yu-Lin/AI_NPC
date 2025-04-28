import json
import pygame
import os

class NPC:
    def __init__(self, name, position, color, radius, thinking_result=""):
        self.name = name
        self.position = position
        self.color = color
        self.radius = radius
        self.selected = False
        self.thinking_result = thinking_result  # 新增
        self.first_tick = True  # <--- 新增這一行
        self.history = []  # 確保每個 NPC 都有 history 屬性
        self.current_space = "Unknown"  # 可根據你的實作調整

    def add_space_to_history(self):
        # 將當前空間資訊加入歷史記錄
        space_info = getattr(self, "current_space", "Unknown")
        self.history.append({
            "role": "system",
            "content": f"進入空間: {space_info}"
        })

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, self.position, self.radius)
        font = pygame.font.SysFont("Microsoft JhengHei", 24, bold=True)
        text = font.render(self.name, True, (0, 0, 0))
        screen.blit(text, (self.position[0] - 20, self.position[1] - 30))

        if self.selected:
            pygame.draw.circle(screen, (255, 0, 0), self.position, self.radius + 5, 2)

        if self.thinking_result:
            bubble_font = pygame.font.SysFont("Microsoft JhengHei", 18)
            bubble_text = bubble_font.render(self.thinking_result, True, (0, 0, 0))
            text_width = bubble_text.get_width()
            text_height = bubble_text.get_height()
            bubble_width = max(200, text_width + 20)
            bubble_height = text_height + 20
            bubble_rect = pygame.Rect(
                self.position[0] - bubble_width // 2,
                self.position[1] - self.radius - bubble_height - 10,
                bubble_width,
                bubble_height
            )
            bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
            bubble_surface.fill((255, 255, 255, 220))
            screen.blit(bubble_surface, (bubble_rect.x, bubble_rect.y))
            pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=10)
            screen.blit(bubble_text, (bubble_rect.x + 10, bubble_rect.y + 10))

    def is_clicked(self, mouse_pos):
        distance = ((self.position[0] - mouse_pos[0]) ** 2 + (self.position[1] - mouse_pos[1]) ** 2) ** 0.5
        return distance <= self.radius

    def update_schema(self):
        # 允許與物品互動、移動、與其他NPC對話
        return {
            "actions": ["interact_item", "move", "talk_npc"],  # 可用動作
            "spaces": getattr(self, "available_spaces", [getattr(self, "current_space", "Unknown")]),   # 可進入的空間
            "items": getattr(self, "available_items", []),   # 可互動的物品
            "npcs": getattr(self, "available_npcs", [])   # 可互動的 NPC
        }

    def get_current_space(self, space_positions=None, space_size=None):
        """
        根據 NPC 的 position，判斷目前所在的空間名稱。
        需要傳入空間位置(space_positions)和空間大小(space_size)的 dict。
        若無法判斷則回傳 'Unknown'。
        """
        if space_positions is None or space_size is None:
            return getattr(self, "current_space", "Unknown")
        x, y = self.position
        for space_name, pos in space_positions.items(): # 遍歷所有空間位置
            size = space_size.get(space_name, [0, 0]) # 取得空間大小
            if pos[0] <= x <= pos[0] + size[0] and pos[1] <= y <= pos[1] + size[1]: # 判斷是否在空間範圍內
                return space_name   # 回傳空間名稱
        return "Unknown"

    def interact_with_item(self, item_dict):
        """
        處理 NPC 與物品的互動。
        Args:
            item_dict: 互動的物品資料（dict），格式如 {"item_name": {...}}
        Returns:
            描述互動結果的字符串
        """
        if not item_dict:
            return "沒有指定要互動的物品。"
        item_name = list(item_dict.keys())[0]
        # 這裡可以根據你的遊戲邏輯擴充
        return f"{self.name} 與 {item_name} 進行了互動。"

    def move_to_space(self, target_space):
        """
        將 NPC 移動到指定空間
        Args:
            target_space: 目標空間名稱（字串）
        Returns:
            描述移動結果的字串
        """
        if not target_space or target_space == "Unknown":
            return f"{self.name} 無法移動，目標空間未知。"
        prev_space = self.get_current_space() # 取得當前空間
        # 防呆：如果目標空間等於目前空間，直接回傳已在該空間
        if target_space == prev_space:
            return f"{self.name} 已經在 {target_space}，無需移動。"
        self.current_space = target_space # 正確更新目標空間
        return f"{self.name} 從 {prev_space} 移動到 {target_space}。"

class NPCManager:
    def __init__(self, json_path):
        self.json_path = json_path
        self.npcs = self.load_npcs()
        self.selected_npc = None  # 目前選取的 NPC

    def load_npcs(self):
        if not os.path.exists(self.json_path):
            raise FileNotFoundError(f"NPC JSON file not found: {self.json_path}")

        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        npcs = []
        for npc_data in data.get("npcs", {}).values():
            npc = NPC(
                name=npc_data.get("name", "NPC"),
                position=tuple(npc_data.get("position", [0, 0])),
                color=tuple(npc_data.get("color", [165, 42, 42])),
                radius=npc_data.get("radius", 15),
                thinking_result=npc_data.get("thinking_result", "")
            )
            npcs.append(npc)
        return npcs
    
    def handle_click(self, mouse_pos):
    # 處理滑鼠點擊事件，選取 NPC
        for npc in self.npcs:
            if npc.is_clicked(mouse_pos):
                if self.selected_npc:
                    self.selected_npc.selected = False  # 取消之前選取的 NPC
                npc.selected = True
                self.selected_npc = npc
                return True
        return False
    
    def move_selected_npc(self, new_pos):
        # 移動選取的 NPC 到新位置
        if self.selected_npc:
            # 確保位置是列表而不是 tuple
            if isinstance(new_pos, tuple):
                new_pos = list(new_pos)
            self.selected_npc.position = new_pos

    def draw_all(self, screen):
        for npc in self.npcs:
            npc.draw(screen)
