import pygame
import math
import time

# 動畫移動 NPC 到目標座標（逐步移動，支援動畫）
def move_npc_to_item(npc, item_name, item_data, screen, speed=3, draw_callback=None, wall_segments=None):
    """
    讓 NPC 逐步移動到指定物品的位置，並顯示動畫。
    Args:
        npc: NPC 物件，需有 position 屬性（[x, y]）
        item_name: 目標物品名稱（string）
        item_data: item.json 解析後的 dict（需有 items[item_name]["position"]）
        screen: pygame 的主視窗
        speed: 每 frame 移動的像素數
        draw_callback: 每次移動時呼叫的畫面重繪函數（建議傳入 main.py 的主畫面刷新函數）
        wall_segments: 牆壁碰撞資料（可選，若有則避開牆壁）
    Returns:
        目標座標
    """
    if item_name not in item_data["items"]:
        print(f"找不到物品 {item_name}")
        return
    target_pos = item_data["items"][item_name]["position"]
    
    # 取得目前 NPC 位置
    current_pos = list(npc.position)
    
    dx = target_pos[0] - current_pos[0]
    dy = target_pos[1] - current_pos[1]
    dist = math.hypot(dx, dy)
    if dist < speed:
        npc.position = list(target_pos)
        return target_pos
    # 計算單位向量
    move_x = speed * dx / dist
    move_y = speed * dy / dist
    next_pos = [current_pos[0] + move_x, current_pos[1] + move_y]
    # 檢查牆壁碰撞（如果有傳入）
    if wall_segments:
        npc_rect = pygame.Rect(next_pos[0] - npc.radius, next_pos[1] - npc.radius, npc.radius*2, npc.radius*2)
        for wall in wall_segments:
            if npc_rect.colliderect(wall):
                print("遇到牆壁，無法前進！")
                return
    npc.position = next_pos
    return target_pos

# 範例用法（需在 main.py 呼叫）：
# move_npc_to_item(npc, 'piano', item_data, screen, speed=3, draw_callback=main_draw_func, wall_segments=wall_segments)