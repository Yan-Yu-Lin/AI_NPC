import json
import pygame
import os

class NPC:
    def __init__(self, name, position, color, radius):
        self.name = name
        self.position = position
        self.color = color
        self.radius = radius
        self.selected = False

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, self.position, self.radius)
        font = pygame.font.SysFont("arial", 24, bold=True)
        text = font.render(self.name, True, (0, 0, 0))
        screen.blit(text, (self.position[0] - 20, self.position[1] - 30))

        if self.selected:
            pygame.draw.circle(screen, (255, 0, 0), self.position, self.radius + 5, 2)

    def is_clicked(self, mouse_pos):
        distance = ((self.position[0] - mouse_pos[0]) ** 2 + (self.position[1] - mouse_pos[1]) ** 2) ** 0.5
        return distance <= self.radius
    
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
                radius=npc_data.get("radius", 15)
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
