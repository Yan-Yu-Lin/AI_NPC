import pygame
import threading
import math
import os

def run_pygame_demo(world):
    pygame.init()
    # 使用 RESIZABLE 讓視窗可調整大小
    screen = pygame.display.set_mode((1200, 700), pygame.RESIZABLE)  # 增加初始寬度以容納右側資訊欄
    pygame.display.set_caption("AI NPC World Demo")
    font = pygame.font.Font("fonts/msjh.ttf", 22)
    info_font = pygame.font.Font("fonts/msjh.ttf", 18)
    button_font = pygame.font.Font("fonts/msjh.ttf", 20)
    clock = pygame.time.Clock()
    running = True

    # 功能說明
    info_lines = [
        "【功能說明】",
        "1. 啟動時可用滑鼠選擇地圖（json）",
        "2. 地圖、空間、物品、NPC 會自動根據 json 內容繪製",
        "3. 支援視窗拖拉、最大化，畫面自動縮放",
        "4. 關閉視窗即結束程式",
        "",
        "（如需互動、點擊、移動等功能可再擴充）"
    ]

    # 互動選單對應的按鈕（與 demo.py 主程式一致）
    button_labels = [
        ("c", "繼續"),
        ("e", "退出"),
        ("p", "打印歷史"),
        ("s", "顯示模式"),
        ("n", "切換NPC"),
        ("w", "改變天氣和時間")
    ]

    # 取得物件參考
    spaces = list(world["spaces"].values())
    npcs = list(world["npcs"].values())
    items = list(world["items"].values())

    # 不再需要 map_data，直接用物件屬性
    # 計算原始地圖最大寬高（用於縮放）
    map_w = max([s.display_pos[0]+s.display_size[0] for s in spaces if s.display_size and s.display_pos] or [1200])
    map_h = max([s.display_pos[1]+s.display_size[1] for s in spaces if s.display_size and s.display_pos] or [700])

    # NPC 圓形顏色
    npc_colors = [(255,0,0),(0,128,255),(0,200,0),(200,0,200),(255,128,0)]
    for idx, npc in enumerate(npcs):
        npc.display_color = npc_colors[idx % len(npc_colors)]
        npc.radius = 24

    active_npc = npcs[0] if npcs else None  # 預設主控第一個 NPC
    last_ai_result = ""
    ai_thinking = False
    ai_threading = None
    ai_running = False

    def ai_process():
        nonlocal last_ai_result, ai_thinking, ai_running
        ai_running = True
        ai_thinking = True
        last_ai_result = active_npc.process_tick() if active_npc else ""
        ai_thinking = False
        ai_running = False

    while running:
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]  # 只考慮左鍵
        hovered_button = None
        pressed_button = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and active_npc and not ai_running:
                    ai_threading = threading.Thread(target=ai_process)
                    ai_threading.start()
                elif event.key == pygame.K_e:
                    running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                win_w, win_h = screen.get_size()
                button_w, button_h = 120, 44
                gap = 24
                total_w = len(button_labels) * (button_w + gap) - gap
                start_x = (win_w - total_w) // 2
                y = win_h - button_h - 24
                for i, (key, label) in enumerate(button_labels):
                    rect = pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)
                    if rect.collidepoint(event.pos) and key == "c" and active_npc and not ai_running:
                        ai_threading = threading.Thread(target=ai_process)
                        ai_threading.start()
                    if rect.collidepoint(event.pos) and key == "e":
                        running = False

        # 每次主循環都同步 display_pos 與 position，並推進動畫移動
        for npc in npcs:
            # 如果 npc.position 尚未指定，給預設值 (0, 0)
            if npc.position is None:
                npc.position = [0, 0]
            if npc.display_pos is None:
                npc.display_pos = [int(n) for n in npc.position]
            else:
                npc.display_pos = [int(n) for n in npc.position]
            if hasattr(npc, 'move_target') and npc.move_target:
                dx = npc.move_target[0] - npc.position[0]
                dy = npc.move_target[1] - npc.position[1]
                dist = math.hypot(dx, dy)
                if dist < npc.move_speed:
                    npc.position = list(npc.move_target)
                    npc.move_target = None
                else:
                    move_x = npc.move_speed * dx / dist
                    move_y = npc.move_speed * dy / dist
                    npc.position[0] += move_x
                    npc.position[1] += move_y

        # 根據視窗大小計算縮放比例
        win_w, win_h = screen.get_size()
        # 防止 map_w 或 map_h 為 0
        safe_map_w = map_w if map_w != 0 else 1
        safe_map_h = map_h if map_h != 0 else 1
        scale_x = win_w / safe_map_w
        scale_y = win_h / safe_map_h
        scale = min(scale_x, scale_y)
        offset_x = (win_w - safe_map_w * scale) // 2
        offset_y = (win_h - safe_map_h * scale) // 2

        screen.fill((240,240,240))
        # 顯示說明
        for i, line in enumerate(info_lines):
            text = info_font.render(line, True, (60, 60, 60))
            screen.blit(text, (16, 12 + i * 22))
        # 畫空間
        for space in spaces:
            px, py = space.display_pos
            sx, sy = space.display_size
            rect = pygame.Rect(
                int(px*scale+offset_x), int(py*scale+offset_y),
                int(sx*scale), int(sy*scale)
            )
            pygame.draw.rect(screen, (200,200,220), rect, border_radius=18)
            text = font.render(space.name, True, (40,40,40))
            screen.blit(text, (rect.x+8, rect.y+8))
        # 畫物品
        for item in items:
            # 優先用 item.position，如果沒有則找所屬空間
            if hasattr(item, "position") and item.position:
                ipos = item.position
            else:
                found = False   # 用於標記是否找到物品
                for space in spaces:    # 遍歷所有空間
                    if item in space.items: # 如果物品在空間中
                        ipos = [
                            space.display_pos[0] + space.display_size[0] // 3,
                            space.display_pos[1] + space.display_size[1] // 2
                        ]
                        found = True    # 找到物品
                        break
                if not found:   # 如果沒有找到物品
                    continue    # 跳過
            # 固定大小為 30x30
            item_rect = pygame.Rect(
                int(ipos[0]*scale+offset_x), int(ipos[1]*scale+offset_y),
                int(30*scale), int(30*scale)
            )
            pygame.draw.rect(screen, (100,100,255), item_rect, border_radius=8)
            item_text = font.render(item.name, True, (20,20,80))
            screen.blit(item_text, (item_rect.x, item_rect.y+int(14*scale)))
        # 畫 NPC
        for npc in npcs:
            px, py = npc.display_pos
            draw_x = int(px * scale + offset_x)
            draw_y = int(py * scale + offset_y)
            pygame.draw.circle(screen, npc.display_color, (draw_x, draw_y), int(npc.radius * scale))
            npc_text = font.render(npc.name, True, (0,0,0))
            screen.blit(npc_text, (draw_x-16, draw_y-int(npc.radius*scale)-10))
            # 聊天氣泡（只顯示 active_npc 的最新 AI 回覆）
            if npc == active_npc and (last_ai_result or ai_thinking):
                bubble_font = info_font
                bubble_text = bubble_font.render(last_ai_result if not ai_thinking else "AI 思考中...", True, (0,0,0))
                text_width = bubble_text.get_width()
                text_height = bubble_text.get_height()
                bubble_width = max(200, text_width + 20)
                bubble_height = text_height + 20
                bubble_rect = pygame.Rect(
                    draw_x - bubble_width // 2,
                    draw_y - int(npc.radius*scale) - bubble_height - 10,
                    bubble_width,
                    bubble_height
                )
                bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
                bubble_surface.fill((255, 255, 255, 220))
                screen.blit(bubble_surface, (bubble_rect.x, bubble_rect.y))
                pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=10)
                screen.blit(bubble_text, (bubble_rect.x + 10, bubble_rect.y + 10))
        # 畫互動按鈕
        button_w, button_h = 120, 44
        gap = 24
        total_w = len(button_labels) * (button_w + gap) - gap
        start_x = (win_w - total_w) // 2
        y = win_h - button_h - 24
        for i, (key, label) in enumerate(button_labels):
            rect = pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)
            # 判斷滑鼠是否在此按鈕上
            is_hover = rect.collidepoint(mouse_pos)
            is_pressed = is_hover and mouse_pressed
            if is_pressed:
                btn_color = (255, 200, 60)  # 點擊顏色
                border_color = (180, 120, 0)
            elif is_hover:
                btn_color = (255, 240, 120)  # hover 顏色
                border_color = (200, 160, 0)
            else:
                btn_color = (180, 180, 0)  # 預設顏色
                border_color = (80, 80, 0)
            pygame.draw.rect(screen, btn_color, rect, border_radius=12)
            pygame.draw.rect(screen, border_color, rect, 3, border_radius=12)
            btn_text = button_font.render(f"[{key.upper()}] {label}", True, (0,0,0))
            btn_text_rect = btn_text.get_rect(center=rect.center)
            screen.blit(btn_text, btn_text_rect)
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()
