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
        # 僅允許進入空間、與NPC交談、與物品互動
        return {
            "actions": ["interact_item"], # 設定可用的動作
            "spaces": [getattr(self, "current_space", "Unknown")],
            "items": getattr(self, "available_items", [])
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
