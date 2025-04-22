import pygame
import math
import time
import heapq
import random
import json
import os

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

# === 新增：尋找附近不會撞牆的虛擬目標點 ===
def find_alternate_target(center, wall_segments, npc_radius, max_offset=40, step=8):
    """
    嘗試在目標附近微調座標，找一個不會撞牆的點
    """
    for offset in range(step, max_offset+step, step):
        for dx in [-offset, 0, offset]:
            for dy in [-offset, 0, offset]:
                if dx == 0 and dy == 0:
                    continue
                alt_x = center[0] + dx
                alt_y = center[1] + dy
                npc_rect = pygame.Rect(alt_x-npc_radius, alt_y-npc_radius, npc_radius*2, npc_radius*2)
                if not any(npc_rect.colliderect(wall) for wall in wall_segments):
                    return [alt_x, alt_y]
    return None  # 找不到安全點

# 空間自動尋徑並移動（A*簡化版，避開牆壁，遇阻自動重規劃與目標微調）
def move_npc_to_space(npc, target_space, space_positions, space_size, screen, speed=3, draw_callback=None, wall_segments=None, connected_graph=None, max_replans=3, delay_ms=30):
    """
    讓NPC自動從目前空間移動到目標空間中心，並避開牆壁。
    Args:
        npc: NPC物件，需有position屬性
        target_space: 目標空間名稱
        space_positions: {空間名: [x, y]} dict
        space_size: {空間名: [w, h]} dict
        screen: pygame主視窗
        speed: 每frame移動像素數
        draw_callback: 每次移動時呼叫的畫面重繪函數
        wall_segments: 牆壁資料（list of pygame.Rect）
        connected_graph: {空間名: [可到達空間名,...]} dict，若無則自動根據空間相鄰生成
        max_replans: 途中遇阻時最多重新規劃次數
        delay_ms: 每步移動動畫延遲（毫秒）
    Returns:
        True: 成功到達，False: 無法到達
    """
    import heapq
    def get_center(space):
        pos = space_positions[space]
        size = space_size[space]
        return [pos[0]+size[0]//2, pos[1]+size[1]//2]

    replan_count = 0
    while replan_count <= max_replans:
        # --- 1. 尋找可行路徑 ---
        max_attempts = 10
        path = None
        for attempt in range(max_attempts):
            path = a_star_pathfinding(
                npc.current_space, target_space, connected_graph,
                space_positions, wall_segments, randomize=True
            )
            print(f"[DEBUG] 第{attempt+1}次嘗試規劃路徑: {path}")
            if path and not is_path_blocked(path, npc, wall_segments, space_positions, space_size):
                print(f"[DEBUG] 找到不會撞牆的路徑: {path}")
                break
            else:
                print(f"[DEBUG] 路徑被牆壁阻擋，重新嘗試...")
                path = None
        if not path:
            print(f"[DEBUG] 無法找到從 {npc.current_space} 到 {target_space} 的可行路徑（所有嘗試都會撞牆）")
            return False

        # --- 2. 依序穿越空間 ---
        blocked = False
        for idx, space in enumerate(path):
            center = get_center(space)
            while True:
                dx = center[0] - npc.position[0]
                dy = center[1] - npc.position[1]
                dist = math.hypot(dx, dy)
                if dist < 1:
                    npc.position = [int(center[0]), int(center[1])]
                    print(f"[DEBUG] 已抵達空間 {space}，座標: {npc.position}")
                    if draw_callback:
                        draw_callback()
                        pygame.display.flip()
                    break
                # 計算移動步長
                step = min(speed, dist)
                move_x = step * dx / dist
                move_y = step * dy / dist
                next_pos = [npc.position[0] + move_x, npc.position[1] + move_y]
                # 檢查牆壁碰撞
                if wall_segments:
                    npc_rect = pygame.Rect(
                        int(next_pos[0] - npc.radius),
                        int(next_pos[1] - npc.radius),
                        int(npc.radius*2), int(npc.radius*2)
                    )
                    for wall in wall_segments:
                        if npc_rect.colliderect(wall):
                            print(f"[DEBUG] 意外撞牆 at {next_pos}，嘗試尋找替代目標點...")
                            alt = find_alternate_target(center, wall_segments, npc.radius)
                            if alt:
                                print(f"[DEBUG] 找到替代目標點: {alt}，嘗試移動")
                                center = alt
                                blocked = False
                                break  # 跳出 wall 檢查，繼續朝新目標移動
                            else:
                                print(f"[DEBUG] 找不到安全的替代目標點，將重新規劃（replan_count={replan_count}）")
                                blocked = True
                                break
                    if blocked:
                        break
                # 執行一步移動
                npc.position = [int(next_pos[0]), int(next_pos[1])]
                print(f"[DEBUG] NPC 正在移動，座標: {npc.position}")
                if draw_callback:
                    draw_callback()
                pygame.display.flip()
                pygame.time.delay(delay_ms)
            if blocked:
                break
        if not blocked:
            npc.current_space = target_space
            print(f"[DEBUG] NPC 成功到達目標空間 {target_space}")
            return True
        else:
            replan_count += 1
            print(f"[DEBUG] 重新規劃路徑（第 {replan_count} 次）...")
    print(f"[DEBUG] 多次重新規劃後仍無法避開障礙，放棄移動")
    return False

# --- 輔助：A* 路徑搜尋 ---
def a_star_pathfinding(start_space, target_space, connected_graph, space_positions, wall_segments, randomize=False):
    def heuristic(a, b):
        ca, cb = space_positions[a], space_positions[b]
        return math.hypot(ca[0]-cb[0], ca[1]-cb[1])
    import heapq
    frontier = [(0.0, start_space)]
    came_from = {start_space: None}
    cost_so_far = {start_space: 0.0}
    while frontier:
        _, current = heapq.heappop(frontier)
        if current == target_space:
            break
        neighbors = connected_graph.get(current, [])[:]
        if randomize:
            import random
            random.shuffle(neighbors)
        for neighbor in neighbors:
            new_cost = cost_so_far[current] + heuristic(current, neighbor)
            if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                cost_so_far[neighbor] = new_cost
                priority = new_cost + heuristic(neighbor, target_space)
                heapq.heappush(frontier, (priority, neighbor))
                came_from[neighbor] = current
    if target_space not in came_from:
        return None
    # 還原路徑
    s = target_space
    path = []
    while s:
        path.append(s)
        s = came_from[s]
    return path[::-1]

# --- 輔助：檢查路徑是否會撞牆 ---
def is_path_blocked(space_path, npc, wall_segments, space_positions, space_size):
    if not space_path:
        return True
    # 取得空間中心的輔助函數
    def get_center_local(space):
        pos = space_positions[space]
        size = space_size[space]
        return [pos[0]+size[0]//2, pos[1]+size[1]//2]
    for i in range(len(space_path)-1):
        start = npc.position if i == 0 else get_center_local(space_path[i])
        end = get_center_local(space_path[i+1])
        steps = max(1, int(math.hypot(end[0]-start[0], end[1]-start[1]) // (npc.radius)))
        for step in range(steps+1):
            interp_x = start[0] + (end[0]-start[0]) * step / steps
            interp_y = start[1] + (end[1]-start[1]) * step / steps
            npc_rect = pygame.Rect(int(interp_x-npc.radius), int(interp_y-npc.radius), int(npc.radius*2), int(npc.radius*2))
            if wall_segments and any(npc_rect.colliderect(wall) for wall in wall_segments):
                print(f"[DEBUG] 路徑檢查: ({start}->{end}) 第{step}/{steps}步撞牆")
                return True
    return False

# 用法示例：
# move_npc_to_space(npc, 'kitchen', space_positions, space_size, screen, speed=3, draw_callback=main_draw_func, wall_segments=wall_segments)