import pygame
import json
import random

# 初始化pygame
pygame.init()

# 設置窗口大小和標題
window_size = (1280, 720)
screen = pygame.display.set_mode(window_size)
pygame.display.set_caption('測試世界')

# 加載世界數據
with open('worlds/world_test.json', 'r', encoding='utf-8') as file:
    world_data = json.load(file)

# 定義顏色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

# 定義字體
font = pygame.font.Font('pygame/msjh.ttf', 16)

# 設定固定的座標
space_positions = {
    '客廳': (0, 0),
    '臥室': (505, 0),
    '廚房': (0, 446),
    '浴室': (828, 0),
    '浴室2': (995, 222),
    '書房': (505, 446)
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
    '書': (65, 206),
    '遙控器': (45,77),
    '蘋果': (100, 100),
    '刀': (150, 150),
    '日記': (200, 200),
    '筆': (250, 250)
}

# 定義空間顏色
space_colors = {
    '客廳': GREEN,
    '臥室': (255, 0, 0),  # 紅色
    '廚房': (0, 255, 255),  # 青色
    '浴室': (0, 0, 255),  # 藍色
    '浴室2': (0, 0, 255),  # 藍色
    '書房': (255, 255, 0)  # 黃色
}

class NPC:
    def __init__(self, name, description):
        self.name = name
        self.description = description
        self.x = 300
        self.y = 300
        self.speed = 5
        self.history = []

        # 生成 NPC 的想法
        thought = f"{self.name} 想到了 {random.choice(['一隻貓', '一本書', '一個朋友'])}"
        self.history.append({'content': thought})

    def process_tick(self):
        # 生成 NPC 的新想法
        thought = f"{self.name} 想到了 {random.choice(['一隻貓', '一本書', '一個朋友'])}"
        self.history.append({'content': thought})

existing_x = 0
existing_y = 0
offset_x = 0
offset_y = 0

# 創建 NPC 實例
npc = NPC(name="亞瑟", description="一個友好的AI助手")

# 主循環
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()  # 捕獲鍵盤按鍵
    if keys[pygame.K_LEFT]:  # 向左移動
        npc.x -= npc.speed
    if keys[pygame.K_RIGHT]:  # 向右移動
        npc.x += npc.speed
    if keys[pygame.K_UP]:  # 向上移動
        npc.y -= npc.speed
    if keys[pygame.K_DOWN]:  # 向下移動
        npc.y += npc.speed

    npc.process_tick()  # 調用 NPC 的行為處理方法
    thought = npc.history[-1]['content']  # 提取 NPC 的想法

    # 清空屏幕
    screen.fill(WHITE)  # 清空畫面

    # 繪製所有空間
    for space_name, (pos_x, pos_y) in space_positions.items():
        size_x, size_y = space_size[space_name]
        space_rect = pygame.Rect(pos_x, pos_y, size_x, size_y)  # 使用指定的大小
        pygame.draw.rect(screen, space_colors[space_name], space_rect)
        # 繪製空間名稱
        text = font.render(space_name, True, BLACK)
        screen.blit(text, (space_rect.x + 5, space_rect.y + 5))

    # 繪製所有物品
    for item_name, (item_x, item_y) in item_positions.items():
        # 繪製物品方塊
        item_rect = pygame.Rect(item_x, item_y, 50, 50)  # 假設每個物品的方塊大小為 50x50
        pygame.draw.rect(screen, (0, 255, 255), item_rect)  # 使用青色繪製方塊
        # 繪製物品名稱
        item_text = font.render(item_name, True, BLACK)
        screen.blit(item_text, (item_x + 5, item_y + 5))

    # 繪製 NPC
    npc_radius = 25  # 假設 NPC 圓形的半徑為 25
    pygame.draw.circle(screen, (255, 0, 0), (npc.x + npc_radius, npc.y + npc_radius), npc_radius)  # 使用紅色繪製 NPC 圓形
    npc_text = font.render(npc.name, True, BLACK)
    screen.blit(npc_text, (npc.x + 5, npc.y + 5))

    # 繪製 NPC 的聊天泡泡
    chat_bubble_width = 200
    chat_bubble_height = 50
    chat_bubble_rect = pygame.Rect(npc.x, npc.y - chat_bubble_height - 10, chat_bubble_width, chat_bubble_height)
    pygame.draw.rect(screen, (255, 255, 255), chat_bubble_rect)  # 繪製聊天泡泡背景
    pygame.draw.rect(screen, (0, 0, 0), chat_bubble_rect, 2)  # 繪製聊天泡泡邊框
    chat_text = font.render(thought, True, BLACK)
    screen.blit(chat_text, (npc.x + 5, npc.y - chat_bubble_height + 5))

    # 更新顯示
    pygame.display.flip()

# 退出pygame
pygame.quit()
