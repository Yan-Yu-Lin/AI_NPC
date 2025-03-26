"""
AI NPC 結合版主程式
整合了主遊戲邏輯和Pygame視覺化系統
"""

import os
from typing import Optional
import pygame
import json
import random
import time
import threading
import math

# 導入所需模組
from world.world_loader import load_world
from npcs.npc import NPC
from spaces.space import Space
from items.item import Item
from history.history_manager import print_history

# 初始化Pygame
pygame.init()

# 設置窗口大小和標題
window_size = (1280, 720)
screen = pygame.display.set_mode(window_size)
pygame.display.set_caption("AI NPC 模擬系統")

# 定義顏色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255) # 青色
MAGENTA = (255, 0, 255) # 紅紫色
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
GRAY = (128, 128, 128)
BROWN = (165, 42, 42)
DARK_GRAY = (50, 50, 50)
SILVER = (192, 192, 192)

# 定義字體
try:
    font = pygame.font.Font('pygame/msjh.ttf', 16)
except:
    font = pygame.font.SysFont(None, 24)

# 設定固定的座標
space_positions = {
    '客廳': (0, 0),
    '臥室': (505, 0),
    '廚房': (0, 446),
    '浴室': (828, 0),
    '浴室2': (995, 222),
    '書房': (505, 446)
}
space_center = {
    '客廳': (497.5, 361),
    '臥室': (666.5, 169.5),
    '廚房': (129.5, 584),
    '浴室': (963.5, 138),
    '浴室2': (1072, 269.5),
    '書房': (666.5, 584)
}
space_size = {
    '客廳': (995, 722),
    '臥室': (323, 339),
    '廚房': (259, 276),
    '浴室': (271, 222),
    '浴室2': (154, 95),
    '書房': (323, 276)
}
item_positions = {
    '書':(46,232),
    '遙控器':(68,92),
    '蘋果':(234,766),
    '刀':(38,476),
    '臥室門':(764,352),
    
}
item_size = {
    '臥室門':(91.5,14.5),

}
# 定義空間顏色
space_colors = {
    '客廳': GREEN,
    '臥室': RED,
    '廚房': CYAN,
    '浴室': BLUE,
    '浴室2': BLUE,
    '書房': YELLOW
}

# 儲存所有門的位置
door_positions = {}

class Game:
    def __init__(self):
        """初始化遊戲"""
        self.running = True
        self.current_dir = os.path.dirname(os.path.abspath(__file__)) # 現在的路徑
        self.world_file_path = os.path.join(self.current_dir, "worlds", "world_test.json") # 世界檔案路徑
        self.world = None
        self.arthur = None
        self.offset_x = 0
        self.offset_y = 0
        self.existing_x = 0
        self.existing_y = 0
        self.last_action_time = 0  # 上次NPC動作的時間
        self.action_interval = 0.5  # NPC動作之間的間隔（秒）
        self.processing_action = False  # 是否正在處理動作
        self.target_space = None  # 目標空間
        self.moving = False  # 是否正在移動
        self.move_speed = 3  # 減慢移動速度到3
        self.target_pos = None  # 目標位置
        self.last_update_time = 0  # 上次更新時間
        self.update_interval = 0.05  # 更新間隔（秒）
        self.keys_pressed = set()  # 當前按下的鍵
        self.thinking = False  # NPC是否在思考
        self.font_large = pygame.font.Font('pygame/msjh.ttf', 36)  # 字體
        self.font_small = pygame.font.Font('pygame/msjh.ttf', 24)  # 按鈕字體
        self.screen_width = 1200  # 屏幕寬度
        self.screen_height = 800  # 屏幕高度
        self.thinking_thread = None  # 思考線程
        self.thinking_result = None  # 思考結果
        self.thinking_lock = threading.Lock()  # 線程鎖
        self.mouse_disabled = False  # 是否禁用滑鼠點擊
        self.door_interactions = []  # 儲存門的互動狀態
        self.target_item = None  # 新增目標物品變量
        
        # 定義顏色常量
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.BROWN = (139, 69, 19)
        self.GRAY = (128, 128, 128)
        self.DARK_GRAY = (64, 64, 64)
        self.RED = (255, 0, 0)
        self.SILVER = (192, 192, 192)
        
        # 按鈕配置
        self.button_padding = 20  # 按鈕間距
        self.button_width = 100
        self.button_height = 50
        self.button_color = (100, 100, 255)  # 按鈕顏色
        self.button_hover_color = (150, 150, 255)  # 滑鼠懸停時的按鈕顏色
        self.button_text_color = (255, 255, 255)  # 按鈕文字顏色
        self.button_disabled_color = (150, 150, 150)  # 禁用按鈕顏色
        self.c_press_interval = 5  # 繼續按鈕重新啟用的時間間隔（秒）
        
        # 創建按鈕
        self.buttons = [
            {
                'text': '繼續',
                'action': self.process_continue,
                'rect': pygame.Rect(
                    self.screen_width - self.button_width - self.button_padding,
                    self.screen_height - self.button_height - self.button_padding,
                    self.button_width,
                    self.button_height
                ),
                'disabled': False  # 按鈕是否禁用
            },
            {
                'text': '歷史',
                'action': self.print_history,
                'rect': pygame.Rect(
                    self.screen_width - self.button_width * 2 - self.button_padding * 2,
                    self.screen_height - self.button_height - self.button_padding,
                    self.button_width,
                    self.button_height
                ),
                'disabled': False
            },
            {
                'text': '退出',
                'action': self.quit_game,
                'rect': pygame.Rect(
                    self.screen_width - self.button_width * 3 - self.button_padding * 3,
                    self.screen_height - self.button_height - self.button_padding,
                    self.button_width,
                    self.button_height
                ),
                'disabled': False
            }
        ]

        # 設置遊戲窗口
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("AI NPC 遊戲")

    def load_world(self):
        """載入世界數據"""
        print(f"嘗試載入世界檔案：{self.world_file_path}")
        self.world = load_world(self.world_file_path)
        
        if not self.world:
            print("錯誤：無法載入世界。程式終止。")
            return False
            
        print(f"成功載入世界：{self.world['world_name']}")
        print(f"世界描述：{self.world['description']}")
        return True

    def setup_npc(self):
        """設置主要NPC"""
        self.arthur = self.world["npcs"].get("arthur")
        if not self.arthur:
            print("錯誤：在世界數據中找不到主要NPC 'arthur'")
            return False
            
        print(f"主要NPC：{self.arthur.name} - {self.arthur.description}")
        
        # 設置NPC的初始位置
        if self.arthur.current_space:
            print(f"NPC當前空間：{self.arthur.current_space.name}")
            space_pos = list(space_positions.get(self.arthur.current_space.name, (100, 100)))  # Default position
            space_pos[0] = 100
            space_pos[1] = 100
            print(f"設置NPC初始位置到：{self.arthur.current_space.name} ({space_pos[0]}, {space_pos[1]})")
            self.arthur.x = space_pos[0]
            self.arthur.y = space_pos[1]
            self.existing_x = space_pos[0]
            self.existing_y = space_pos[1]
        else:
            print("NPC當前空間為None")
            self.arthur.x = 10
            self.arthur.y = 10
            self.existing_x = 10
            self.existing_y = 10
            print(f"NPC初始位置設置為預設位置：(10, 10)")
        
        return True

    def update_door_positions(self):
        """更新所有門的位置"""
        door_positions.clear()
        if self.world and "spaces" in self.world:
            for space_id, space in self.world["spaces"].items():
                if space.name in space_positions and space.connected_spaces:
                    for connected_space in space.connected_spaces:
                        if connected_space.name in space_positions:
                            # 計算兩個空間的相對位置
                            space1_x = space_positions[space.name][0]
                            space1_y = space_positions[space.name][1]
                            space2_x = space_positions[connected_space.name][0]
                            space2_y = space_positions[connected_space.name][1]
                            
                            # 橫向門（左右連接）
                            if abs(space1_x - space2_x) > abs(space1_y - space2_y):
                                door_x = (space1_x + space2_x) // 2
                                door_y = min(space1_y, space2_y) + 50
                            # 縱向門（上下連接）
                            else:
                                door_x = min(space1_x, space2_x) + 50
                                door_y = (space1_y + space2_y) // 2
                            
                            # 儲存門的位置和連接的空間
                            door_key = tuple(sorted([space.name, connected_space.name]))
                            door_positions[door_key] = {
                                'position': (door_x, door_y),
                                'connected_spaces': [space.name, connected_space.name]
                            }

    def check_door_interaction(self, npc):
        """檢查NPC是否與門互動"""
        # 移除門互動邏輯
        return False

    def move_npc_to_space(self, npc, target_space):
        """移動NPC到指定空間，必須先經過門"""
        if not target_space:
            return

        # 首先檢查NPC是否在當前空間
        if npc.current_space and npc.current_space.name == target_space.name:
            return

        # 找到當前空間和目標空間之間的門
        current_space_name = npc.current_space.name if npc.current_space else None
        door_key = tuple(sorted([current_space_name, target_space.name]))
        
        if door_key in door_positions:
            door_info = door_positions[door_key]
            door_x, door_y = door_info['position']
            
            # 先移動到門的位置
            if npc.x != door_x or npc.y != door_y:
                # 計算移動方向
                dx = door_x - npc.x
                dy = door_y - npc.y
                distance = math.sqrt(dx**2 + dy**2)
                
                if distance > 1:
                    # 計算單位向量
                    unit_dx = dx / distance
                    unit_dy = dy / distance
                    
                    # 移動NPC
                    npc.x += unit_dx * npc.speed
                    npc.y += unit_dy * npc.speed
                    
                    # 確保NPC不會移動過頭
                    npc.x = min(max(npc.x, door_x - npc.speed), door_x + npc.speed)
                    npc.y = min(max(npc.y, door_y - npc.speed), door_y + npc.speed)
                    
                    return False
            
            # 在門的位置，檢查是否已經互動過
            if door_key in self.door_interactions:
                # 門已經互動過，可以通過
                print(f"NPC通過了連接{door_info['connected_spaces']}的門")
                npc.current_space = target_space
                npc.x = target_space.x + target_space.width // 2
                npc.y = target_space.y + target_space.height // 2
                return True
            else:
                # 門還沒有互動過，等待互動
                print("等待NPC與門互動...")
                return False
        
        return False

    def draw_spaces(self, screen):
        """繪製所有空間"""
        # 使用集合來追蹤已經繪製的門
        drawn_doors = set()
        
        # 先繪製所有空間和文字
        for space_name, pos in space_positions.items():
            color = space_colors.get(space_name, WHITE)
            pygame.draw.rect(screen, color, 
                           (pos[0] - self.offset_x, pos[1] - self.offset_y, 
                            space_size[space_name][0], space_size[space_name][1]))
            
            # 繪製空間名稱
            text = font.render(space_name, True, BLACK)
            screen.blit(text, (pos[0] - self.offset_x + 10, pos[1] - self.offset_y + 10))
            
            # 如果是NPC當前空間，顯示特殊標記
            if self.arthur and self.arthur.current_space and self.arthur.current_space.name == space_name:
                pygame.draw.circle(screen, ORANGE, 
                                 (pos[0] - self.offset_x + 10, pos[1] - self.offset_y + 10), 8)

        # 然後繪製所有門（根據空間連接關係）
        if self.world and "spaces" in self.world:
            for space_id, space in self.world["spaces"].items():
                if space.name in space_positions and space.connected_spaces:
                    for connected_space in space.connected_spaces:
                        # 確保只繪製一次門
                        door_key = tuple(sorted([space.name, connected_space.name]))
                        if door_key in drawn_doors:
                            continue
                        drawn_doors.add(door_key)
                        
                        if connected_space.name in space_positions:
                            # 計算兩個空間的相對位置
                            space1_x = space_positions[space.name][0]
                            space1_y = space_positions[space.name][1]
                            space2_x = space_positions[connected_space.name][0]
                            space2_y = space_positions[connected_space.name][1]
                            
                            # 橫向門（左右連接）
                            if abs(space1_x - space2_x) > abs(space1_y - space2_y):
                                # 門的位置
                                door_x = space2_x
                                door_y = space_size[connected_space.name][1] // 2
                                # 繪製橫向門框
                                pygame.draw.rect(screen, PURPLE, 
                                                (door_x - 10, door_y - 60, 20, 120), 3)
                                # 在門的中間繪製門把手
                                pygame.draw.circle(screen, YELLOW, 
                                                (door_x, door_y), 5)
                            # 縍向門（上下連接）
                            else:
                                # 門的位置
                                door_x = min(space1_x, space2_x) + 50
                                door_y = space2_y
                                # 繪製縱向門框
                                pygame.draw.rect(screen, PURPLE, 
                                                (door_x - 60, door_y - 10, 120, 20), 3)
                                # 在門的中間繪製門把手
                                pygame.draw.circle(screen, YELLOW, 
                                                (door_x, door_y), 5)

    def draw_npc(self, screen):
        """繪製NPC"""
        if self.arthur:
            # 繪製NPC
            pygame.draw.circle(screen, MAGENTA, 
                             (int(self.arthur.x - self.offset_x), 
                              int(self.arthur.y - self.offset_y)), 20)
            
            # 繪製思考結果氣泡
            if self.arthur.thinking_result:
                # 測量文字寬度
                text = font.render(self.arthur.thinking_result, True, BLACK)
                text_width = text.get_width()
                text_height = text.get_height()
                
                # 根據文字寬度調整氣泡大小
                bubble_width = max(200, text_width + 20)  # 最小寬度為200像素
                bubble_height = text_height + 20  # 文字高度加上上下邊距
                
                # 創建氣泡背景
                bubble_rect = pygame.Rect(
                    self.arthur.x - self.offset_x - bubble_width // 2,
                    self.arthur.y - self.offset_y - bubble_height - 20,
                    bubble_width,
                    bubble_height
                )
                pygame.draw.rect(screen, (255, 255, 255, 128), bubble_rect, border_radius=10)
                pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=10)
                
                # 繪製思考結果文字
                text = font.render(self.arthur.thinking_result, True, BLACK)                
                screen.blit(text, (bubble_rect.x + 10, bubble_rect.y + 10))

    def draw_buttons(self, screen):
        """繪製按鈕"""
        mouse_pos = pygame.mouse.get_pos()
        
        for button in self.buttons:
            # 檢查滑鼠是否懸停在按鈕上
            if button['rect'].collidepoint(mouse_pos) and not button['disabled']:
                color = self.button_hover_color
            else:
                color = self.button_color if not button['disabled'] else self.button_disabled_color
            
            # 繪製按鈕背景
            pygame.draw.rect(screen, color, button['rect'])
            
            # 繪製按鈕文字
            text_surface = self.font_small.render(button['text'], True, self.button_text_color)
            text_rect = text_surface.get_rect(center=button['rect'].center)
            screen.blit(text_surface, text_rect)

    def handle_events(self):
        """處理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not self.mouse_disabled:
                    # 獲取滑鼠位置
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    # 檢查是否點擊了空間
                    for space_name, pos in space_positions.items():
                        x, y = pos
                        width, height = space_size[space_name]
                        if (x <= mouse_x <= x + width and 
                            y <= mouse_y <= y + height):
                            # 找到目標空間
                            target_space = None
                            for space in self.world["spaces"].values():
                                if space.name == space_name:
                                    target_space = space
                                    break
                            
                            if target_space:
                                # 指示NPC移動到目標空間
                                self.target_space = target_space
                                break
                    
                    # 檢查是否點擊了按鈕
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_x, mouse_y) and not button['disabled']:
                            # 禁用滑鼠點擊並立即處理輸入
                            self.mouse_disabled = True
                            try:
                                # 執行按鈕對應的動作
                                button['action']()
                            except Exception as e:
                                print(f"執行按鈕動作時出錯: {str(e)}")
                            break
            elif event.type == pygame.KEYUP:
                # 當鍵盤鬆開時重置狀態
                self.keys_pressed.discard(event.key)

    def process_continue(self):
        """處理繼續按鈕點擊"""
        if self.arthur:
            self.thinking = True
            self.thinking_result = None
            
            # 如果有目標空間，開始移動NPC
            if self.target_space:
                # 獲取目標空間的位置
                target_pos = space_positions.get(self.target_space.name)
                if target_pos:
                    self.target_pos = target_pos
                    self.moving = True
                    
            # 創建思考線程
            self.thinking_thread = threading.Thread(target=self._think_action)
            self.thinking_thread.daemon = True
            self.thinking_thread.start()

    def _think_action(self):
        """NPC思考線程"""
        
        # 在思考開始時禁用繼續按鈕和滑鼠點擊
        for button in self.buttons:
            button['disabled'] = True
        
        try:
            result = self.arthur.process_tick()
            
            # 使用鎖來安全地設置思考結果
            with self.thinking_lock:
                self.thinking_result = result
                self.arthur.thinking_result = result  # 更新NPC的思考結果
                self.thinking = False
                self.mouse_disabled = False
                self.processing_action = False
                
                # 在思考結束時啟用繼續按鈕
                for button in self.buttons:
                    button['disabled'] = False
                
            # 處理NPC思考結果
            if self.arthur.thinking_result:
                
                # 獲取NPC的目標物品名稱
                item_name = self.arthur.item_name
                print(f"NPC的目標物品名稱: {item_name}")
                
                # 獲取NPC的目標空間名稱
                space_name = self.arthur.target_space
                print(f"NPC的目標空間名稱: {space_name}")
                
                # 初始化空間歷史記錄
                if not hasattr(self, 'space_history'):
                    self.space_history = ['出生地']
                
                # 更新空間歷史記錄
                if space_name:
                    self.space_history.append(space_name)
                    # 只保留最近的兩個空間
                    if len(self.space_history) > 2:
                        self.space_history.pop(0)
                
                # 如果有空間歷史記錄
                if self.space_history:
                    # 獲取最後兩個空間
                    current_space = self.space_history[-1] if self.space_history else None
                    previous_space = self.space_history[-2] if len(self.space_history) >= 2 else None
                    
                    # 如果當前空間與前一個空間不同，先處理空間移動
                    if previous_space and current_space and current_space != previous_space:
                        print(f"空間變更：從 {previous_space} 到 {current_space}")
                        
                        # 設置移動目標到新空間中心
                        if current_space in space_center:
                            space_x, space_y = space_center[current_space]
                            self.target_pos = (space_x, space_y)
                            self.moving = True
                            self.target_space = current_space
                            print(f"NPC決定移動到空間 {current_space}")
                        
                        # 不要立即處理物品，讓NPC先完成空間移動
                        return
                    
                # 如果沒有空間變更，或者已經在目標空間，處理物品移動
                if item_name and item_name in item_positions:
                    # 獲取物品位置
                    item_x, item_y = item_positions[item_name]
                    
                    # 設置NPC移動目標
                    self.target_pos = (item_x, item_y)
                    self.moving = True
                    self.target_item = item_name  # 記錄目標物品
                    print(f"NPC決定移動到物品 {item_name} 附近")
                
                # 如果沒有有效目標
                else:
                    print(f"未找到有效目標: 物品={item_name}, 空間={space_name}")
                print(self.space_history)
                # 不要立即重置狀態，讓NPC有時間移動
                # 移動狀態會在update方法中處理
                
                # 重置思考狀態
                self.thinking = False
                self.processing_action = False
                
                # 重置繼續按鈕狀態
                for button in self.buttons:
                    button['disabled'] = False
            
            # 更新最後動作時間
            self.last_action_time = time.time()
            
        except Exception as e:
            print(f"思考線程出錯: {str(e)}")
            with self.thinking_lock:
                self.mouse_disabled = False
                self.thinking = False
                self.processing_action = False
                
                # 在異常處理中啟用繼續按鈕
                for button in self.buttons:
                    button['disabled'] = False

    def print_history(self):
        """顯示歷史記錄"""
        if self.arthur:
            print_history(self.arthur)
        # 重置滑鼠點擊禁用狀態
        self.mouse_disabled = False
    def quit_game(self):
        """退出遊戲"""
        self.running = False

    def update(self):
        """更新遊戲狀態"""
        if self.arthur:
            current_time = time.time()
            
            # 檢查是否需要更新位置
            if current_time - self.last_update_time >= self.update_interval:
                self.last_update_time = current_time
                
                # 更新NPC位置
                if self.arthur.current_space or self.arthur.current_item:
                    space_pos = space_center.get(self.arthur.current_space.name, (100, 100))
                    self.existing_x = space_pos[0]
                    self.existing_y = space_pos[1]

                # 處理NPC移動
                if self.moving and self.target_pos:
                    current_pos = (self.arthur.x, self.arthur.y)
                    
                    # 計算移動方向
                    dx = self.target_pos[0] - current_pos[0]
                    dy = self.target_pos[1] - current_pos[1]
                    
                    # 計算移動距離
                    distance = (dx**2 + dy**2)**0.5
                    print(f"剩餘距離: {distance}")
                    
                    # 如果距離很小，直接到達目標
                    if distance < 5:
                        self.arthur.x = self.target_pos[0]
                        self.arthur.y = self.target_pos[1]
                        print(f"到達目標位置: ({self.target_pos[0]}, {self.target_pos[1]})")
                        
                        # 如果有目標空間，更新NPC當前空間
                        if self.target_space:
                            # 找到目標空間
                            target_space_obj = None
                            for space_id, space in self.world["spaces"].items():
                                if space.name == self.target_space:
                                    target_space_obj = space
                                    break
                            
                            if target_space_obj:
                                # 更新NPC當前空間
                                self.arthur.current_space = target_space_obj
                                print(f"{self.arthur.name} 到達了 {self.target_space}")
                                
                                # 更新歷史記錄
                                self.arthur.history.append({
                                    "role": "system",
                                    "content": f"到達了 {self.target_space}"
                                })
                                
                                # 確保NPC在空間中心
                                if self.target_space in space_center:
                                    center_x, center_y = space_center[self.target_space]
                                    self.arthur.x = center_x
                                    self.arthur.y = center_y
                        
                        # 如果有目標物品，更新NPC當前物品
                        if self.target_item:
                            # 找到目標物品
                            target_item_obj = None
                            for item_id, item in self.world["items"].items():
                                # 獲取物品名稱
                                if isinstance(item, dict):
                                    name = item.get("name", "unknown")
                                else:
                                    name = getattr(item, "name", "unknown")
                                if name == self.target_item:
                                    target_item_obj = item
                                    break
                            
                            if target_item_obj:
                                self.arthur.current_item = target_item_obj
                                print(f"NPC到達了物品 {self.target_item}")
                                
                                # 更新歷史記錄
                                self.arthur.history.append({
                                    "role": "system",
                                    "content": f"到達了物品 {self.target_item}"
                                })
                        
                        # 重置所有狀態
                        self.moving = False
                        self.target_pos = None
                        self.target_space = None
                        self.target_item = None
                        
                        # 重置思考狀態
                        self.thinking = False
                        self.processing_action = False
                        
                        # 重置繼續按鈕狀態
                        for button in self.buttons:
                            button['disabled'] = False
                    else:
                        # 根據方向移動
                        self.arthur.x += dx * (self.move_speed / distance)
                        self.arthur.y += dy * (self.move_speed / distance)
                        print(f"移動到新位置: ({self.arthur.x}, {self.arthur.y})")
                        
                        # 在移動中禁用按鈕
                        for button in self.buttons:
                            button['disabled'] = True

    def handle_events(self):
        """處理遊戲事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if not self.mouse_disabled:
                    # 獲取滑鼠位置
                    mouse_x, mouse_y = pygame.mouse.get_pos()
                    
                    # 檢查是否點擊了按鈕
                    for button in self.buttons:
                        if button['rect'].collidepoint(mouse_x, mouse_y) and not button['disabled']:
                            # 禁用滑鼠點擊並立即處理輸入
                            self.mouse_disabled = True
                            try:
                                # 執行按鈕對應的動作
                                button['action']()
                            except Exception as e:
                                print(f"執行按鈕動作時出錯: {str(e)}")
                            break

    def draw(self):
        """繪製遊戲"""
        # 繪製背景
        self.screen.fill(WHITE)
        
        # 繪製所有空間
        self.draw_spaces(self.screen)
        
        # 繪製NPC
        if self.arthur:
            # 繪製NPC
            pygame.draw.circle(self.screen, BLUE, (int(self.arthur.x), int(self.arthur.y)), 10)
            
            # 繪製NPC名稱
            text = font.render(self.arthur.name, True, BLACK)
            self.screen.blit(text, (self.arthur.x - text.get_width()//2, self.arthur.y - 20))
            
            # 如果NPC在思考，顯示思考提示
            if self.arthur.thinking:
                # 獲取思考文本
                thinking_text = "NPC正在思考中..."
                
                # 計算文本寬度和高度
                text_surface = self.font_large.render(thinking_text, True, BLACK)
                text_width = text_surface.get_width()
                text_height = text_surface.get_height()
                
                # 創建聊天氣泡背景
                bubble_padding = 10
                bubble_width = text_width + bubble_padding * 2
                bubble_height = text_height + bubble_padding * 2
                bubble_x = self.arthur.x - bubble_width // 2
                bubble_y = self.arthur.y - 40 - bubble_height
                
                # 繪製聊天氣泡背景
                pygame.draw.rect(self.screen, (255, 255, 200), 
                              (bubble_x, bubble_y, bubble_width, bubble_height),
                              border_radius=10)
                
                # 繪製邊框
                pygame.draw.rect(self.screen, BLACK, 
                              (bubble_x, bubble_y, bubble_width, bubble_height),
                              width=2,
                              border_radius=10)
                
                # 繪製思考文本
                self.screen.blit(text_surface, 
                              (bubble_x + bubble_padding, bubble_y + bubble_padding))
            
            # 如果有思考結果，顯示思考結果
            if self.arthur.thinking_result:
                    # 獲取思考結果文本
                    result_text = self.arthur.thinking_result
                    
                    # 計算文本寬度和高度
                    text_surface = font.render(result_text, True, BLACK)
                    text_width = text_surface.get_width()
                    text_height = text_surface.get_height()
                    
                    # 創建聊天氣泡背景
                    bubble_padding = 10
                    bubble_width = text_width + bubble_padding * 2
                    bubble_height = text_height + bubble_padding * 2
                    bubble_x = self.arthur.x - bubble_width // 2
                    bubble_y = self.arthur.y - 20 - bubble_height
                    
                    # 繪製聊天氣泡背景
                    pygame.draw.rect(self.screen, (255, 255, 200), 
                                  (bubble_x, bubble_y, bubble_width, bubble_height),
                                  border_radius=10)
                    
                    # 繪製邊框
                    pygame.draw.rect(self.screen, BLACK, 
                                  (bubble_x, bubble_y, bubble_width, bubble_height),
                                  width=2,
                                  border_radius=10)
                    
                    # 繪製思考結果文本
                    self.screen.blit(text_surface, 
                                  (bubble_x + bubble_padding, bubble_y + bubble_padding))
        
        # 繪製物品
        if self.world and "items" in self.world:
            for item_id, item in self.world["items"].items():
                # 獲取物品名稱
                if isinstance(item, dict):
                    name = item.get("name", "unknown")
                else:
                    name = getattr(item, "name", "unknown")
                
                # 使用item_positions字典來獲取位置
                position = item_positions.get(name)
                
                if position is None:
                    continue
                
                x, y = position
                
                # 調整物品位置，考慮到屏幕偏移量
                screen_x = x - self.offset_x
                screen_y = y - self.offset_y
                
                # 確保位置在屏幕範圍內
                if 0 <= screen_x <= self.screen_width and 0 <= screen_y <= self.screen_height:
                    # 根據物品類型繪製不同的圖形
                    item_type = getattr(item, "type", "unknown")
                    
                    if item_id == "book":
                        pygame.draw.rect(self.screen, BROWN, 
                                      (screen_x - 20, screen_y - 30, 40, 60),
                                      border_radius=5)
                        pygame.draw.rect(self.screen, WHITE, 
                                      (screen_x - 18, screen_y - 28, 36, 56),
                                      border_radius=5)
                    elif item_id == "remote":
                        pygame.draw.rect(self.screen, GRAY, 
                                      (screen_x - 20, screen_y - 30, 40, 60),
                                      border_radius=10)
                        pygame.draw.circle(self.screen, DARK_GRAY, 
                                      (screen_x, screen_y - 15), 5)
                        pygame.draw.circle(self.screen, DARK_GRAY, 
                                      (screen_x + 10, screen_y - 15), 5)
                    elif item_id == "apple":
                        pygame.draw.circle(self.screen, RED, (screen_x, screen_y), 15)
                        pygame.draw.line(self.screen, BROWN, 
                                      (screen_x + 3, screen_y - 15),
                                      (screen_x + 3, screen_y - 30), 3)
                    elif item_id == "knife":
                        pygame.draw.polygon(self.screen, SILVER, 
                                      [(screen_x - 10, screen_y),
                                       (screen_x + 10, screen_y),
                                       (screen_x + 10, screen_y - 20),
                                       (screen_x - 10, screen_y - 20)])
                        pygame.draw.rect(self.screen, BROWN, 
                                      (screen_x - 5, screen_y - 20, 10, 30))
                    
                    # 繪製物品名稱
                    text = self.font_small.render(name, True, BLACK)
                    self.screen.blit(text, (screen_x - text.get_width()//2, screen_y + 30))
                else:
                    print(f"物品不在屏幕範圍內: {name} - ({screen_x}, {screen_y})")  # 調試信息
        
        # 最後繪製按鈕，確保顯示在最上層
        self.draw_buttons(self.screen)

    def run(self):
        """運行遊戲主循環"""
        pygame.init()
        self.screen = pygame.display.set_mode((1200, 800))
        pygame.display.set_caption("AI NPC 遊戲")
        clock = pygame.time.Clock()
        
        self.update_door_positions()
        
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            
            # 檢查NPC是否與門互動
            if self.arthur:
                self.check_door_interaction(self.arthur)
            
            pygame.display.flip()
            clock.tick(60)

if __name__ == "__main__":
    game = Game()
    if game.load_world() and game.setup_npc():
        game.run()
    pygame.quit()
