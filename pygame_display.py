#pygame_display.py

import pygame
import threading
import math
import os
from backend import save_world_to_json, world_system
from typing import Optional

# 添加terminal input相關的全域變數
terminal_command = None
terminal_command_lock = threading.Lock()

def print_npc_history_to_terminal(npc_name: str):
    """在terminal中打印指定NPC的完整history"""
    if not npc_name or npc_name not in world_system.npcs_data:
        print(f"\n[錯誤] 找不到名為 '{npc_name}' 的NPC")
        return
    
    npc = world_system.npcs_data[npc_name]
    history = npc.history
    
    print(f"\n{'='*60}")
    print(f"🤖 {npc.name} 的完整History")
    print(f"{'='*60}")
    print(f"總共 {len(history)} 條記錄")
    print("-" * 60)
    
    for i, message in enumerate(history, 1):
        role = message.get('role', 'Unknown')
        content = message.get('content', '')
        
        # 根據role設定顯示樣式
        if role == "system":
            print(f"[{i:3d}] 🔧 系統: {content}")
        elif role == "assistant":
            print(f"[{i:3d}] 🤖 {npc.name}: {content}")
        elif role == "user":
            print(f"[{i:3d}] 👤 用戶: {content}")
        else:
            print(f"[{i:3d}] ❓ {role}: {content}")
        print("-" * 60)
    
    print(f"{'='*60}")
    print(f"History 結束 - 總共 {len(history)} 條記錄")
    print(f"{'='*60}\n")

def terminal_input_listener():
    """在背景執行的terminal input監聽器"""
    global terminal_command
    print("🎮 Terminal輸入監聽器啟動")
    print("💡 可用指令:")
    print("   p <npc_name> - 顯示指定NPC的history")
    print("   p - 顯示當前active NPC的history") 
    print("   quit - 結束程式")
    print("-" * 50)
    
    while True:
        try:
            user_input = input("Terminal> ").strip()
            if user_input:
                with terminal_command_lock:
                    terminal_command = user_input
                    
                if user_input.lower() == 'quit':
                    break
        except (EOFError, KeyboardInterrupt):
            break
    
    print("🎮 Terminal輸入監聽器結束")

def run_pygame_demo():
    pygame.init()
    # 使用 RESIZABLE 讓視窗可調整大小
    screen = pygame.display.set_mode((1200, 700), pygame.RESIZABLE)  # 增加初始寬度以容納右側資訊欄
    pygame.display.set_caption("AI NPC World Demo")
    font = pygame.font.Font("fonts/msjh.ttf", 22)
    info_font = pygame.font.Font("fonts/msjh.ttf", 18)
    button_font = pygame.font.Font("fonts/msjh.ttf", 20)
    clock = pygame.time.Clock()
    running = True

    # 🎮 啟動terminal input監聽線程
    global terminal_command
    terminal_thread = threading.Thread(target=terminal_input_listener, daemon=True)
    terminal_thread.start()
    print("✅ Terminal監聽線程已啟動，可以在console輸入指令")

    # 功能說明
    info_lines = [
        "【功能說明】",
        "1. 啟動時可用滑鼠選擇地圖（json）",
        "2. 地圖、空間、物品、NPC 會自動根據 json 內容繪製",
        "3. 支援視窗拖拉、最大化，畫面自動縮放",
        "4. 關閉視窗即結束程式",
        "5. 🆕 可在terminal輸入 'p' 查看NPC history",
        "",
        "（如需互動、點擊、移動等功能可再擴充）"
    ]

    # 互動選單對應的按鈕（與 demo.py 主程式一致）
    button_labels = [
        ("c", "繼續"),
        ("e", "退出"),
        ("p", "打印歷史"),
        ("s", "存檔"),
        ("n", "切換NPC"),
        ("w", "改變天氣和時間")
    ]

    # NPC 圓形顏色
    npc_colors = [(255,0,0),(0,128,255),(0,200,0),(200,0,200),(255,128,0)]
    default_npc_radius = 24

    # active_npc 改為存儲 NPC 的名字 (active_npc_name)
    active_npc_name: Optional[str] = None
    # 初始化時嘗試獲取第一個 NPC 的名字
    # world_system.npcs_data 是一個字典 {name: NPCObject}
    if world_system.npcs_data: # Check if npcs_data is not empty and has been populated
        try:
            active_npc_name = next(iter(world_system.npcs_data.keys()))
            print(f"========= 目前關注的NPC: {active_npc_name} ==========")
        except StopIteration: # Should not happen if npcs_data is not empty
             print("========= npcs_data 為空，無法選取初始 active_npc_name ===========")
    else:
        print("========= 初始化時 NPCs 數據為空 ===========")

    last_ai_result = ""
    ai_thinking = False
    ai_thread: Optional[threading.Thread] = None
    ai_running = False

    def ai_process():
        nonlocal last_ai_result, ai_thinking, ai_running
        ai_running = True
        ai_thinking = True
        current_active_npc_object = world_system.npcs_data.get(active_npc_name) if active_npc_name else None
        if current_active_npc_object:
            last_ai_result = current_active_npc_object.process_tick()
        else:
            last_ai_result = "錯誤：AI Process 中 active_npc 未設定或無效。"
        ai_thinking = False
        ai_running = False

    def draw_text_input_box(screen, prompt, font, input_text, rect):
        pygame.draw.rect(screen, (255, 255, 255), rect)
        pygame.draw.rect(screen, (0, 0, 0), rect, 2)
        txt = font.render(prompt + input_text, True, (0, 0, 0))
        screen.blit(txt, (rect.x + 5, rect.y + 5))

    def get_text_input(screen, prompt, font, rect, default_text=""):
        input_text = default_text
        active = True
        while active:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN:
                        active = False
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    elif event.key == pygame.K_ESCAPE:
                        return None
                    else:
                        # 避免輸入不可見字元
                        if len(event.unicode) == 1 and (32 <= ord(event.unicode) <= 126 or ord(event.unicode) > 127):
                            input_text += event.unicode
            screen.fill((200, 200, 200))
            draw_text_input_box(screen, prompt, font, input_text, rect)
            pygame.display.flip()
        return input_text.strip()

    def save_menu(screen, font, world, original_path):
        menu_items = ["直接存檔", "另存新檔", "取消"]
        selected = 0
        menu_rect = pygame.Rect(100, 100, 300, 180)
        button_rects = []
        
        # 初始化按鈕位置
        for i in range(len(menu_items)):
            rect = pygame.Rect(menu_rect.x + 20, menu_rect.y + 30 + i * 40, 260, 36)
            button_rects.append(rect)
        
        running = True
        hovered = -1  # 滑鼠懸停的按鈕索引
        clicked = -1  # 記錄最後點擊的按鈕
        mouse_down = False  # 滑鼠按下狀態
        
        while running:
            # 更新滑鼠狀態
            mouse_pos = pygame.mouse.get_pos()
            
            # 檢查滑鼠懸停
            last_hovered = hovered
            hovered = -1
            for idx, rect in enumerate(button_rects):
                if rect.collidepoint(mouse_pos):
                    hovered = idx
                    break
            
            # 畫選單
            screen.fill((180, 180, 180))
            pygame.draw.rect(screen, (255, 255, 255), menu_rect)
            
            # 畫按鈕
            button_rects.clear()
            for i, item in enumerate(menu_items):
                rect = pygame.Rect(menu_rect.x + 20, menu_rect.y + 30 + i * 40, 260, 36)
                button_rects.append(rect)
                
                # 決定按鈕顏色
                if mouse_down and i == hovered:  # 滑鼠按下時顯示深藍色
                    # 點擊狀態：深藍底色
                    bg_color = (150, 150, 255)
                    text_color = (0, 0, 128)
                elif i == hovered:  # 滑鼠懸停優先於選中狀態
                    # 懸停狀態：淺綠底色
                    bg_color = (220, 255, 220)
                    text_color = (0, 128, 0)
                elif i == selected:
                    # 選中狀態：淺藍底色
                    bg_color = (220, 220, 255)
                    text_color = (0, 0, 255)
                else:
                    # 一般狀態：淺灰底色
                    bg_color = (240, 240, 240)
                    text_color = (0, 0, 0)
                
                pygame.draw.rect(screen, bg_color, rect)
                txt = font.render(item, True, text_color)
                screen.blit(txt, (rect.x + 8, rect.y + 4))
            
            pygame.display.flip()  # 更新畫面
            
            # 處理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        selected = (selected - 1) % len(menu_items)
                    elif event.key == pygame.K_DOWN:
                        selected = (selected + 1) % len(menu_items)
                    elif event.key == pygame.K_RETURN:
                        running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_down = True  # 設置滑鼠按下狀態
                    if hovered != -1:
                        clicked = hovered
                elif event.type == pygame.MOUSEBUTTONUP:
                    if mouse_down and hovered != -1 and hovered == clicked:
                        selected = hovered
                        running = False
                    mouse_down = False  # 重置滑鼠按下狀態
                    clicked = -1  # 重置點擊狀態
        
        # 處理選擇
        if menu_items[selected] == "直接存檔":
            save_world_to_json(world_system, original_path)
        elif menu_items[selected] == "另存新檔":
            input_rect = pygame.Rect(100, 320, 400, 50)
            import os
            default_name = os.path.basename(original_path) if original_path else "new_save.json"
            filename = get_text_input(screen, "輸入新檔名: ", font, input_rect, default_text=default_name)
            if filename:
                if not filename.lower().endswith('.json'):
                    filename += ".json"
                new_path = os.path.join("worlds", filename)
                save_world_to_json(world_system, new_path)
        # 取消則不做事

    def npc_selection_menu(screen, font, npcs, active_npc):
        if not npcs or len(npcs) <= 1:
            return active_npc  # 如果沒有NPC或只有一個NPC，不需要切換
        
        # 設定視窗大小和位置
        screen_w, screen_h = screen.get_size()
        menu_w, menu_h = min(600, screen_w - 200), min(400, screen_h - 200)
        menu_x = (screen_w - menu_w) // 2
        menu_y = (screen_h - menu_h) // 2
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        
        # 設定標題和關閉按鈕
        title = font.render("選擇要關注的 NPC", True, (255, 255, 255))
        close_btn = pygame.Rect(menu_rect.x + menu_rect.width - 90, menu_rect.y + 5, 80, 32)
        
        # 初始化選中的NPC為當前活動的NPC
        selected_npc = active_npc
        selected_index = npcs.index(active_npc) if active_npc in npcs else 0
        
        # 顯示NPC列表的參數
        line_height = 50  # 每個NPC項目的高度
        npc_buttons = []  # 儲存NPC按鈕的矩形
        visible_items = min(len(npcs), (menu_h - 100) // line_height)  # 可見NPC數量
        
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]  # 左鍵
            
            # 繪製背景和標題
            pygame.draw.rect(screen, (220, 220, 220), menu_rect)  # 主背景色改為淺灰白
            pygame.draw.rect(screen, (60, 60, 120), (menu_rect.x, menu_rect.y, menu_rect.width, 40))  # 標題欄深藍
            screen.blit(title, (menu_rect.x + 10, menu_rect.y + 10))
            
            # 設定裁剪區域，確保內容不會超出框框
            clip_rect = pygame.Rect(menu_rect.x, menu_rect.y + 40, menu_rect.width, menu_rect.height - 80)
            screen.set_clip(clip_rect)
            
            # 繪製NPC列表
            npc_buttons.clear()
            for i, npc in enumerate(npcs):
                # 計算按鈕位置
                btn_rect = pygame.Rect(
                    menu_rect.x + 20, 
                    menu_rect.y + 50 + i * line_height, 
                    menu_rect.width - 40, 
                    line_height
                )
                npc_buttons.append(btn_rect)
                
                # 決定按鈕顏色
                if npc == selected_npc:  # 當前選中的NPC
                    bg_color = (220, 220, 255)  # 淺藍背景
                    text_color = (0, 0, 200)     # 深藍文字
                    border_color = (100, 100, 200)  # 藍色邊框
                elif btn_rect.collidepoint(mouse_pos):  # 鼠標懸停
                    bg_color = (240, 240, 250)  # 非常淺藍背景
                    text_color = (100, 100, 200)  # 中藍文字
                    border_color = (180, 180, 220)  # 淺藍邊框
                else:  # 普通狀態
                    bg_color = (240, 240, 240)  # 淺灰背景
                    text_color = (60, 60, 60)   # 深灰文字
                    border_color = (200, 200, 200)  # 灰色邊框
                
                # 繪製按鈕背景
                pygame.draw.rect(screen, bg_color, btn_rect, border_radius=5)
                pygame.draw.rect(screen, border_color, btn_rect, 2, border_radius=5)  # 邊框
                
                # 繪製NPC名稱和描述
                npc_name = font.render(npc.name, True, text_color)
                screen.blit(npc_name, (btn_rect.x + 10, btn_rect.y))
                
                # 繪製描述（較小的字體）
                desc_font = pygame.font.Font("fonts/msjh.ttf", 16)
                desc = desc_font.render(npc.description[:50] + ("..." if len(npc.description) > 50 else ""), True, text_color)
                screen.blit(desc, (btn_rect.x + 15, btn_rect.y + 25))
            
            # 重設裁剪區域
            screen.set_clip(None)
            
            # 繪製底部區域
            pygame.draw.rect(screen, (220, 220, 220), (menu_rect.x, menu_rect.y + menu_rect.height - 40, menu_rect.width, 40))
            
            # 繪製確認和取消按鈕
            confirm_btn = pygame.Rect(menu_rect.x + 20, menu_rect.y + menu_rect.height - 35, 120, 30)
            cancel_btn = pygame.Rect(menu_rect.x + menu_rect.width - 140, menu_rect.y + menu_rect.height - 35, 120, 30)
            
            # 確認按鈕
            confirm_hover = confirm_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (100, 180, 100) if confirm_hover else (80, 160, 80), confirm_btn, border_radius=5)
            confirm_txt = font.render("確認", True, (255, 255, 255))
            screen.blit(confirm_txt, (confirm_btn.x + 40, confirm_btn.y))
            
            # 取消按鈕
            cancel_hover = cancel_btn.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (180, 100, 100) if cancel_hover else (160, 80, 80), cancel_btn, border_radius=5)
            cancel_txt = font.render("取消", True, (255, 255, 255))
            screen.blit(cancel_txt, (cancel_btn.x + 40, cancel_btn.y))
            
            # 更新顯示
            pygame.display.flip()
            
            # 處理事件
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return active_npc  # 保持原來的NPC
                
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        return active_npc  # 取消，返回原NPC
                    elif event.key == pygame.K_RETURN:
                        running = False
                        return selected_npc  # 確認，返回選中的NPC
                    elif event.key == pygame.K_UP and selected_index > 0:   # 上移選項
                        selected_index -= 1
                        selected_npc = npcs[selected_index]
                    elif event.key == pygame.K_DOWN and selected_index < len(npcs) - 1:  # 下移選項
                        selected_index += 1
                        selected_npc = npcs[selected_index]
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if cancel_btn.collidepoint(mouse_pos):
                        running = False
                        return active_npc  # 取消，返回原NPC
                    
                    elif confirm_btn.collidepoint(mouse_pos):
                        running = False
                        return selected_npc  # 確認，返回選中的NPC
                    
                    # 檢查是否點擊了NPC按鈕
                    for i, btn in enumerate(npc_buttons):
                        if btn.collidepoint(mouse_pos):
                            selected_index = i
                            selected_npc = npcs[i]
                            # 雙擊選擇並確認
                            if event.button == 1 and event.type == pygame.MOUSEBUTTONDOWN:
                                return selected_npc
        
        return selected_npc  # 返回選中的NPC

    def wrap_text(text, font, max_width):
        # 處理字元換行，避免超出指定的最大寬度
        # 增強版：確保所有字符都能在視窗內完整顯示
        
        # 安全邊距，預留更多空間
        max_width = max_width - 40  # 增加安全邊距
        
        # 如果字串空白或寬度小於最大寬度，直接返回
        if not text or font.size(text)[0] <= max_width:
            return [text]
            
        lines = []
        # 處理字串
        line = ""
        for char in text:
            test_line = line + char
            # 如果寬度超過最大寬度，需要換行
            if font.size(test_line)[0] > max_width:
                lines.append(line)  # 加入當前行
                line = char         # 重置行內容
            else:
                line = test_line    # 繼續加入字元
        
        # 處理最後一行
        if line:
            lines.append(line)
            
        return lines

    def history_menu(screen, font, active_npc):
        if not active_npc:
            return
        
        history = active_npc.history
        if not history:
            return
        
        # 按角色分組歷史訊息
        grouped_messages = []
        current_group = None
        
        for message in history:
            role = message.get('role', 'Unknown')
            content = message.get('content', '')
            
            if current_group is None or current_group['role'] != role:
                current_group = {'role': role, 'contents': [content]}
                grouped_messages.append(current_group)
            else:
                current_group['contents'].append(content)
        
        # 設定視窗大小和位置
        screen_w, screen_h = screen.get_size()
        menu_w, menu_h = min(800, screen_w - 200), min(500, screen_h - 200)
        menu_x = (screen_w - menu_w) // 2
        menu_y = (screen_h - menu_h) // 2
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)
        
        # 設定標題和關閉按鈕
        title = font.render(f"{active_npc.name} 的歷史記錄", True, (255, 255, 255))
        close_btn = pygame.Rect(menu_rect.x + menu_rect.width - 90, menu_rect.y + 5, 80, 32)
        
        # 滾動相關設定
        scroll_y = 0
        line_height = 30
        
        # 調整最大文字寬度，確保不會超出邊框
        max_text_width = menu_rect.width - 120
        
        # 處理訊息塊結構化
        message_blocks = []
        total_lines = 0
        
        for group in grouped_messages:
            role = group['role']
            contents = group['contents']
            
            # 為角色設定顏色、樣式和圖示
            if role == "system":
                title_text = "系統訊息"
                bg_color = (220, 235, 255)  # 淺藍背景
                text_color = (0, 90, 180)   # 深藍文字
                border_color = (120, 170, 255)  # 藍色邊框
                icon = ""
            elif role == "assistant":
                title_text = f"{active_npc.name} (NPC)"
                bg_color = (220, 250, 220)  # 淺綠背景
                text_color = (0, 110, 0)    # 深綠文字
                border_color = (100, 200, 100)  # 綠色邊框
                icon = ""
            elif role == "user":
                title_text = "玩家"
                bg_color = (255, 245, 220)  # 淺黃背景
                text_color = (180, 100, 0)  # 棕色文字
                border_color = (240, 200, 100)  # 黃色邊框
                icon = ""
            else:
                title_text = role.upper()
                bg_color = (240, 240, 240)  # 淺灰背景
                text_color = (100, 100, 100)  # 灰色文字
                border_color = (200, 200, 200)  # 灰色邊框
                icon = ""
            
            # 處理標題和內容
            header = f"{icon} {title_text}"
            wrapped_contents = []
            
            # 處理內容，特殊處理「思考」和「行動」
            for content in contents:
                lines = []
                
                # 特殊處理 assistant 角色的思考和行動
                if role == "assistant" and content.startswith("Thinking:"):
                    base = "思考: "
                    thinking_text = content[9:].strip()  # 移除 "Thinking: " 前綴
                    # 根據聊天框寬度決定第一行文字
                    first_line = base
                    remaining_text = thinking_text
                    max_allowed_width = max_text_width - 50 - font.size(base)[0]
                    for i in range(len(remaining_text)):
                        test_line = remaining_text[:i+1]    # 嘗試添加一個字元
                        if font.size(test_line)[0] > max_allowed_width: # 如果寬度超過最大寬度
                            first_line += remaining_text[:i]  # 添加到第一行
                            if i < len(remaining_text):
                                first_line += ""           # 添加省略號
                            remaining_text = remaining_text[i:] # 更新剩餘文本
                            break
                    else:
                        first_line += remaining_text
                        remaining_text = ""
                    lines.append(first_line)
                    
                    # 處理剩餘的內容
                    if remaining_text:
                        # 計算剩餘文字的寬度，使用縮排
                        prefix_width = font.size(base)[0]
                        indent = " " * (len(base) + 2)  # 增加縮排
                        
                        # 處理剩餘的內容，使用換行
                        wrapped_lines = wrap_text(remaining_text, font, max_text_width - 50)
                        
                        # 加入縮排的內容
                        for i, line in enumerate(wrapped_lines):
                            lines.append(indent + line)
                    wrapped_contents.extend(lines)
                elif role == "assistant" and content.startswith("Action:"):
                    base = "行動: "
                    action_text = content[8:].strip()  # 移除 "Action: " 前綴
                    # 根據聊天框寬度決定第一行文字
                    first_line = base
                    remaining_text = action_text
                    max_allowed_width = max_text_width - 50 - font.size(base)[0]
                    for i in range(len(remaining_text)):
                        test_line = remaining_text[:i+1]
                        if font.size(test_line)[0] > max_allowed_width:
                            first_line += remaining_text[:i]
                            if i < len(remaining_text):
                                first_line += ""
                            remaining_text = remaining_text[i:]
                            break
                    else:
                        first_line += remaining_text
                        remaining_text = ""
                    lines.append(first_line)
                    
                    # 處理剩餘的內容
                    if remaining_text:
                        # 計算剩餘文字的寬度，使用縮排
                        prefix_width = font.size(base)[0]
                        indent = " " * (len(base) + 2)  # 增加縮排
                        
                        # 處理剩餘的內容，使用換行
                        wrapped_lines = wrap_text(remaining_text, font, max_text_width - 50)
                        
                        # 加入縮排的內容
                        for i, line in enumerate(wrapped_lines):
                            lines.append(indent + line)
                    wrapped_contents.extend(lines)
                else:
                    # 一般內容處理
                    lines = wrap_text(content, font, max_text_width - 40)
                    wrapped_contents.extend(lines)
            
            # 處理左側縮排
            wrapped_contents = ["" + line for line in wrapped_contents]
            
            # 增加左側邊距
            wrapped_contents = [" " + line for line in wrapped_contents]
            
            # 計算塊的高度
            block_lines = 1 + len(wrapped_contents) + (1 if wrapped_contents else 0)
            
            # 添加訊息塊，包含背景色、標題、內容等信息
            message_blocks.append({
                'role': role,
                'header': header,
                'contents': wrapped_contents,
                'bg_color': bg_color,
                'text_color': text_color,
                'border_color': border_color,
                'lines': block_lines  # 標題 + 內容行數 + 間隔
            })
            
            # 累計總行數
            total_lines += block_lines + 1  # 加上額外間隔
        
        # 計算最大滾動範圍
        max_scroll = max(0, total_lines * line_height - (menu_rect.height - 80))
        
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            mouse_pressed = pygame.mouse.get_pressed()[0]
            
            # 繪製背景和標題
            pygame.draw.rect(screen, (220, 220, 220), menu_rect)  # 主背景色改為淺灰白
            pygame.draw.rect(screen, (60, 60, 120), (menu_rect.x, menu_rect.y, menu_rect.width, 40))  # 標題欄深藍
            screen.blit(title, (menu_rect.x + 10, menu_rect.y + 10))
            
            # 設定裁剪區域，確保內容不會超出框框
            clip_rect = pygame.Rect(menu_rect.x, menu_rect.y + 40, menu_rect.width, menu_rect.height - 80)
            screen.set_clip(clip_rect)
            
            # 繪製歷史記錄（使用訊息塊結構）
            y_offset = menu_rect.y + 50 - scroll_y
            
            for block in message_blocks:
                # 跳過完全不在視圖中的塊
                block_height = block['lines'] * line_height
                if y_offset + block_height < menu_rect.y + 40 or y_offset > menu_rect.y + menu_rect.height - 40:
                    y_offset += block_height + line_height // 2  # 加上額外間隔
                    continue
                
                # 添加塊之間的間隔
                y_offset += line_height // 2
                
                # 繪製訊息塊背景
                block_padding = 10  # 塊內部邊距
                block_rect = pygame.Rect(
                    menu_rect.x + 60,  # 更大的左邊距
                    y_offset, 
                    menu_rect.width - 120,  # 更窄的寬度
                    block_height - line_height // 2
                )
                
                # 使用圓角矩形繪製背景
                pygame.draw.rect(screen, block['bg_color'], block_rect, border_radius=10)
                pygame.draw.rect(screen, block['border_color'], block_rect, 2, border_radius=10)  # 有顏色的邊框
                
                # 繪製標題 (加粗效果)
                header_bg = pygame.Rect(
                    block_rect.x, 
                    block_rect.y, 
                    block_rect.width, 
                    line_height
                )
                pygame.draw.rect(screen, (255, 255, 255, 40), header_bg, border_top_left_radius=10, border_top_right_radius=10)  # 半透明標題背景
                
                header_txt = font.render(block['header'], True, block['text_color'])
                screen.blit(header_txt, (block_rect.x + block_padding, y_offset + 5))
                y_offset += line_height
                
                # 繪製內容（稍微縮排）
                for i, line in enumerate(block['contents']):
                    if y_offset >= menu_rect.y + 40 and y_offset < menu_rect.y + menu_rect.height - 40:
                        txt = font.render(line, True, block['text_color'])
                        # 對第一行特殊處理，如果是思考或行動的情況
                        if i == 0 and (line.startswith("思考: ") or line.startswith("行動: ")):
                            screen.blit(txt, (block_rect.x + block_padding, y_offset + 5))
                        else:  # 一般內容行縮排
                            screen.blit(txt, (block_rect.x + block_padding + 15, y_offset + 5))  # 內容縮排
                    y_offset += line_height
                
                # 塊間間隔
                y_offset += line_height // 2
            
            # 重設裁剪區域
            screen.set_clip(None)
            
            # 繪製底部區域（避免內容溢出）
            pygame.draw.rect(screen, (220, 220, 220), (menu_rect.x, menu_rect.y + menu_rect.height - 40, menu_rect.width, 40))
            
            # 繪製關閉按鈕 - 移到這裡確保它不會被其他元素覆蓋
            is_hover = close_btn.collidepoint(mouse_pos)
            is_pressed = is_hover and mouse_pressed
            if is_pressed:
                btn_color = (255, 200, 60)  # 點擊顏色（深黃色）
            elif is_hover:
                btn_color = (230, 230, 230)  # 懸停顏色（淺灰色）
            else:
                btn_color = (200, 200, 200)  # 預設顏色（灰色）
            
            pygame.draw.rect(screen, btn_color, close_btn, border_radius=5)
            pygame.draw.rect(screen, (100, 100, 100), close_btn, 1, border_radius=5)  # 邊框
            close_txt = font.render("關閉", True, (0, 0, 0))
            screen.blit(close_txt, (close_btn.x + 20, close_btn.y))
            
            # 更新顯示
            pygame.display.flip()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    return
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                        running = False
                    elif event.key == pygame.K_UP and scroll_y > 0:
                        scroll_y -= line_height
                    elif event.key == pygame.K_DOWN and scroll_y < max_scroll:
                        scroll_y += line_height
                    elif event.key == pygame.K_PAGEUP:
                        scroll_y = max(0, scroll_y - menu_rect.height // 2)
                    elif event.key == pygame.K_PAGEDOWN:
                        scroll_y = min(max_scroll, scroll_y + menu_rect.height // 2)
                    elif event.key == pygame.K_HOME:
                        scroll_y = 0
                    elif event.key == pygame.K_END:
                        scroll_y = max_scroll
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if close_btn.collidepoint(mouse_pos):
                        running = False
                elif event.type == pygame.MOUSEWHEEL:
                    scroll_y = max(0, min(max_scroll, scroll_y - event.y * line_height))

    ai_thread = None    # 用於執行 AI tick 的線程

    def ai_process_thread_target(current_npc_name_for_thread: Optional[str]):
        nonlocal last_ai_result, ai_thinking, ai_running
        if not current_npc_name_for_thread:
            last_ai_result = "錯誤：未指定要處理的 NPC。"
            ai_thinking = False
            return

        # Get the latest NPC object from world_system using the name
        npc_to_process = world_system.npcs_data.get(current_npc_name_for_thread)
        if not npc_to_process:
            last_ai_result = f"錯誤：在 AI 線程中找不到名為 '{current_npc_name_for_thread}' 的 NPC。"
            ai_thinking = False
            return
            
        ai_thinking = True
        last_ai_result = npc_to_process.process_tick()
        ai_thinking = False

    # 主遊戲循環 (Main Game Loop)
    # ========================
    while running:
        # --- 1. 事件處理 (Event Handling) ---
        mouse_pos = pygame.mouse.get_pos()
        
        # +++ Get mouse button states +++
        mouse_buttons = pygame.mouse.get_pressed()  # Returns a tuple (left, middle, right)
        mouse_pressed = mouse_buttons[0]          # True if left mouse button is pressed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE: 
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            
            elif event.type == pygame.KEYDOWN:
                current_active_npc_object_for_event = world_system.npcs_data.get(active_npc_name) if active_npc_name else None
                if event.key == pygame.K_c: 
                    if current_active_npc_object_for_event and (ai_thread is None or not ai_thread.is_alive()):
                        print(f"[DEBUG] Starting AI thread for {active_npc_name}")
                        ai_thread = threading.Thread(target=ai_process_thread_target, args=(active_npc_name,))
                        ai_thread.start()
                elif event.key == pygame.K_e: 
                    running = False
                elif event.key == pygame.K_p: 
                    if current_active_npc_object_for_event:
                        history_menu(screen, font, current_active_npc_object_for_event)
                elif event.key == pygame.K_s: 
                    save_menu(screen, font, "worlds/default_save.json")
                elif event.key == pygame.K_n: 
                    if len(world_system.npcs_data) > 1:
                        new_active_npc_name = npc_selection_menu(screen, font, list(world_system.npcs_data.values()), current_active_npc_object_for_event) 
                        if new_active_npc_name and new_active_npc_name != active_npc_name:
                           active_npc_name = new_active_npc_name
                           last_ai_result = "" 
                           print(f"========= 目前關注的NPC: {active_npc_name} ==========")
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: 
                    # Placeholder for button click logic
                    # This needs to iterate button_rects and check collision
                    # Then dispatch based on the 'key' of the button label
                    pass 

        # 🎮 檢查並處理terminal命令
        global terminal_command
        current_terminal_command = None
        with terminal_command_lock:
            if terminal_command:
                current_terminal_command = terminal_command
                terminal_command = None  # 清除命令

        if current_terminal_command:
            cmd_parts = current_terminal_command.split()
            if len(cmd_parts) >= 1:
                cmd = cmd_parts[0].lower()
                
                if cmd == 'p':
                    # 處理 'p' 命令
                    if len(cmd_parts) >= 2:
                        # 指定NPC名稱: p <npc_name>
                        npc_name = ' '.join(cmd_parts[1:])  # 支援有空格的NPC名稱
                        print_npc_history_to_terminal(npc_name)
                    elif active_npc_name:
                        # 沒指定NPC，使用當前active NPC: p
                        print_npc_history_to_terminal(active_npc_name)
                    else:
                        print("\n[錯誤] 沒有active NPC，請指定NPC名稱: p <npc_name>")
                        print(f"可用的NPC: {', '.join(world_system.npcs_data.keys())}")
                
                elif cmd == 'quit':
                    print("🛑 收到quit命令，正在關閉程式...")
                    running = False
                
                else:
                    print(f"\n[警告] 未知命令: '{current_terminal_command}'")
                    print("可用命令: p [npc_name], quit")

        # --- 2. 遊戲邏輯更新 (Game Logic / State Updates) ---
        if world_system.npcs_data:
            for npc_obj in world_system.npcs_data.values():
                if hasattr(npc_obj, 'position') and hasattr(npc_obj, 'display_pos'):
                     npc_obj.display_pos = [int(n) for n in npc_obj.position]
                if hasattr(npc_obj, 'move_target') and npc_obj.move_target and hasattr(npc_obj, 'move_speed'):
                    dx = npc_obj.move_target[0] - npc_obj.position[0]
                    dy = npc_obj.move_target[1] - npc_obj.position[1]
                    dist = math.hypot(dx, dy)
                    if dist < npc_obj.move_speed:
                        npc_obj.position = list(npc_obj.move_target)
                        npc_obj.move_target = None
                    else:
                        move_x = npc_obj.move_speed * dx / dist
                        move_y = npc_obj.move_speed * dy / dist
                        npc_obj.position[0] += move_x
                        npc_obj.position[1] += move_y

        # --- 3. 繪圖準備 (Calculations for Drawing) ---
        win_w, win_h = screen.get_size()
        
        # 將 map_w, map_h 及相關縮放計算移入循環內部
        current_spaces_for_map_bounds = list(world_system.spaces_data.values())
        map_w = max([s.display_pos[0]+s.display_size[0] for s in current_spaces_for_map_bounds if hasattr(s, 'display_pos') and hasattr(s, 'display_size') and s.display_pos and s.display_size] or [1200])
        map_h = max([s.display_pos[1]+s.display_size[1] for s in current_spaces_for_map_bounds if hasattr(s, 'display_pos') and hasattr(s, 'display_size') and s.display_pos and s.display_size] or [700])

        safe_map_w = map_w if map_w > 0 else 1200
        safe_map_h = map_h if map_h > 0 else 700
        scale_x = win_w / safe_map_w
        scale_y = win_h / safe_map_h
        scale = min(scale_x, scale_y)
        offset_x = (win_w - safe_map_w * scale) / 2
        offset_y = (win_h - safe_map_h * scale) / 2

        # --- 4. 清理螢幕 (Clear Screen) ---
        screen.fill((240,240,240))
        # 顯示說明
        for i, line in enumerate(info_lines):
            text = info_font.render(line, True, (60, 60, 60))
            screen.blit(text, (16, 12 + i * 22))
        
        # 畫空間 - 直接從 world_system.spaces_data 獲取
        if world_system.spaces_data:
            for space_obj in world_system.spaces_data.values(): # Iterate directly
                if hasattr(space_obj, 'display_pos') and hasattr(space_obj, 'display_size') and space_obj.display_pos and space_obj.display_size:
                    px, py = space_obj.display_pos
                    sx, sy = space_obj.display_size
                    rect = pygame.Rect(
                        int(px*scale+offset_x), int(py*scale+offset_y),
                        int(sx*scale), int(sy*scale)
                    )
                    pygame.draw.rect(screen, (200,200,220), rect, border_radius=18)
                    text = font.render(space_obj.name, True, (40,40,40))
                    screen.blit(text, (rect.x+8, rect.y+8))

        # 畫物品 - 直接從 world_system.items_data 獲取
        if world_system.items_data:
            for item_obj in world_system.items_data.values(): # Iterate directly
                # 優先用 item.position，如果沒有則找所屬空間
                ipos = None
                if hasattr(item_obj, "position") and item_obj.position:
                    ipos = item_obj.position
                else:
                    # Try to find item in a space to determine its position if not explicitly set
                    # This part might need adjustment based on how item ownership by space is structured
                    if world_system.spaces_data:
                        for space_obj_for_item_check in world_system.spaces_data.values():
                            if hasattr(space_obj_for_item_check, 'items') and item_obj in space_obj_for_item_check.items: # Assuming space.items holds references
                                if hasattr(space_obj_for_item_check, 'display_pos') and hasattr(space_obj_for_item_check, 'display_size'):                                    
                                    ipos = [
                                        space_obj_for_item_check.display_pos[0] + space_obj_for_item_check.display_size[0] // 3,
                                        space_obj_for_item_check.display_pos[1] + space_obj_for_item_check.display_size[1] // 2
                                    ]
                                    break # Found item in a space
                
                if ipos: # Only draw if we have a position
                    item_rect_dim = getattr(item_obj, 'size', (30,30)) # Use item.size if available, else default
                    item_rect_w = item_rect_dim[0]
                    item_rect_h = item_rect_dim[1]
                    item_rect = pygame.Rect(
                        int(ipos[0]*scale+offset_x), int(ipos[1]*scale+offset_y),
                        int(item_rect_w*scale), int(item_rect_h*scale)
                    )
                    pygame.draw.rect(screen, (100,100,255), item_rect, border_radius=8)
                    item_text = font.render(item_obj.name, True, (20,20,80))
                    # Adjust text blitting based on scaled item_rect height for better centering
                    text_rect = item_text.get_rect(centerx=item_rect.centerx, y=item_rect.top + (item_rect.height - item_text.get_height()) // 2)
                    if item_rect.width > item_text.get_width(): # Only blit if text fits
                         screen.blit(item_text, text_rect)
                    elif item_rect.width > 5 : # Fallback for very small items, show first char
                         screen.blit(font.render(item_obj.name[0] if item_obj.name else "?", True, (20,20,80)), text_rect)
                # else: item has no position, cannot be drawn

        # 畫 NPC - 直接從 world_system.npcs_data 獲取
        # Also, ensure active_npc is correctly referenced or re-fetched if it can change
        # For simplicity, this example assumes active_npc object reference stays valid if it's not None.
        # A more robust way would be to store active_npc_name and fetch the object each frame:
        # active_npc_object_this_frame = world_system.npcs_data.get(active_npc_name_if_stored) if active_npc_name_if_stored else None
        if world_system.npcs_data:
            for npc_obj in world_system.npcs_data.values(): # Iterate directly
                if hasattr(npc_obj, 'display_pos') and npc_obj.display_pos and hasattr(npc_obj, 'radius'): # Ensure attributes exist
                    px, py = npc_obj.display_pos
                    draw_x = int(px * scale + offset_x)
                    draw_y = int(py * scale + offset_y)
                    color = getattr(npc_obj, 'display_color', (255,0,0)) or (255,0,0)  # Default color, handle None case
                    radius = getattr(npc_obj, 'radius', 24) or 24  # Default radius 24, handle None case

                    pygame.draw.circle(screen, color, (draw_x, draw_y), int(radius * scale))
                    npc_text = font.render(npc_obj.name, True, (0,0,0))
                    # Adjust text position to be above the circle
                    text_surf_rect = npc_text.get_rect(centerx=draw_x, bottom=draw_y - int(radius*scale) - 2)
                    screen.blit(npc_text, text_surf_rect)
                    
                    # 聊天氣泡（只顯示 active_npc 的最新 AI 回覆）
                    # Ensure active_npc itself is the up-to-date object if its state can change
                    # or compare by a unique ID/name if active_npc is a snapshot
                    if active_npc_name and npc_obj.name == active_npc_name and (last_ai_result or ai_thinking): # Assuming name is unique and active_npc refers to a valid NPC object
                        bubble_font = info_font
                        bubble_content = last_ai_result if not ai_thinking else "AI 思考中..."
                        # Wrap text for bubble
                        wrapped_lines = wrap_text(bubble_content, bubble_font, 200 - 20) # max_width - padding

                        bubble_height = sum(bubble_font.get_height() for _ in wrapped_lines) + 20
                        bubble_width = 200 # Fixed width for bubble

                        bubble_rect_x = draw_x - bubble_width // 2
                        bubble_rect_y = draw_y - int(radius*scale) - bubble_height - 10 # Position above NPC
                        
                        bubble_rect = pygame.Rect(
                            bubble_rect_x,
                            bubble_rect_y,
                            bubble_width,
                            bubble_height
                        )
                        # Using pygame.Surface for alpha transparency
                        bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
                        bubble_surface.fill((255, 255, 255, 220)) # White with alpha
                        
                        current_y_offset = 10 # Padding inside bubble
                        for line_text in wrapped_lines:
                            line_surface = bubble_font.render(line_text, True, (0,0,0))
                            bubble_surface.blit(line_surface, (10, current_y_offset))
                            current_y_offset += bubble_font.get_height()

                        screen.blit(bubble_surface, (bubble_rect.x, bubble_rect.y))
                        pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=10) # Border

        # 畫互動按鈕
        button_w, button_h = 120, 44
        gap = 24
        total_w = len(button_labels) * (button_w + gap) - gap
        start_x = (win_w - total_w) // 2
        y = win_h - button_h - 24
        for i, (key, label) in enumerate(button_labels):
            rect = pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)  # 判斷滑鼠是否在此按鈕上
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
