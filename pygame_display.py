import pygame
import threading
import math
import os
import time
from backend import save_world_to_json
import base64
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

# 圖片快取，避免重複載入
item_image_cache = {}

# Added generate_image function from user's script
def generate_image(prompt_text: str, output_filename: str):
    """Generates an image based on the prompt and saves it."""
    try:
        # NOTE: "gpt-image-1" and "background" are non-standard from user's script.
        # If API errors occur, these might need to be changed to "dall-e-3"
        # and background transparency handled via prompt or post-processing.
        img = client.images.generate(
            model = "gpt-image-1",
            background = "transparent",
            prompt = prompt_text,
            n = 1,
            size="1024x1024",
        )
        # Assuming the response structure has .data[0].b64_json
        # User script had: image_bytes = base64.b64decode(img.data[0].b64_json)
        # Need to ensure img.data[0] and b64_json attribute exist.
        if img.data and len(img.data) > 0 and hasattr(img.data[0], 'b64_json') and img.data[0].b64_json:
            image_bytes = base64.b64decode(img.data[0].b64_json)
            with open(output_filename, "wb") as f:
                f.write(image_bytes)
            print(f"Image saved as {output_filename}")
        else:
            print(f"Error generating image for {output_filename}: No b64_json data in response.")
            # Optionally, log this error or handle it more gracefully
    except Exception as e:
        print(f"An error occurred during image generation for {output_filename}: {e}")

# 在適當的位置添加圖片載入功能
def load_item_image(image_path):
    """載入並返回物品圖片，主要從 worlds/picture 目錄加載。
    如果圖片不存在，則嘗試使用 generate_image 生成它。
    """
    if not image_path: # 如果 image_path 是 None 或空字串
        # print("load_item_image: image_path is None or empty, returning placeholder.") # Debugging line
        placeholder = pygame.Surface((40, 40), pygame.SRCALPHA)
        placeholder.fill((150, 150, 200, 180))
        pygame.draw.rect(placeholder, (80, 80, 120), placeholder.get_rect(), 2)
        # For None/empty path, cache under a special key to avoid issues if image_path is reused
        item_image_cache[image_path or "__placeholder_default__"] = placeholder 
        return placeholder

    # 如果圖片已經在快取中，直接返回
    if image_path in item_image_cache:
        return item_image_cache[image_path]

    # 主要圖片路徑
    # 假設 image_path 只是檔案名，例如 "table.png"
    primary_path = os.path.join("worlds", "picture", image_path)

    # 檢查主要路徑的檔案是否存在
    if not os.path.exists(primary_path):
        print(f"Image not found at {primary_path}. Attempting to generate...")
        # 從 image_path (檔案名) 推斷物品名稱
        item_name_for_prompt = os.path.splitext(image_path)[0] # 例如 "table.png" -> "table"
        
        # 建立 prompt (依照使用者最新腳本的風格)
        base_prompt = f"Create a top-down view pixel art image of a {item_name_for_prompt}. "
        style_prompt = f"pixel like {item_name_for_prompt} looking down"
        full_prompt = base_prompt + style_prompt

        print(f"Generating image for: '{item_name_for_prompt}' (from filename: {image_path})")
        print(f"Using prompt: '{full_prompt}'")
        generate_image(full_prompt, primary_path) # 呼叫 generate_image

    # (無論是否生成) 再次嘗試載入主要路徑
    try:
        if os.path.exists(primary_path):
            image = pygame.image.load(primary_path).convert_alpha()
            item_image_cache[image_path] = image
            return image
    except Exception as e:
        print(f"載入圖片失敗 {primary_path} (even after attempting generation): {e}")

    # 如果主要路徑失敗 (即使在嘗試生成後)，嘗試備用位置
    # 這部分備用路徑的邏輯可能需要重新評估，因為主要目的是生成到 standard path
    # 但為了保持原有的 robustness，暫時保留
    backup_paths = [
        image_path, # 例如，如果 image_path 本身就是完整路徑
        os.path.join("images", image_path),
        os.path.join("worlds", "images", image_path)
    ]

    for path_idx, path in enumerate(backup_paths):
        try:
            if os.path.exists(path):
                # print(f"Loading from backup path {path_idx+1}: {path}") # Debugging line
                image = pygame.image.load(path).convert_alpha()
                item_image_cache[image_path] = image
                # 考慮是否要將備用路徑找到的圖片複製到主要路徑
                # try:
                #     import shutil
                #     os.makedirs(os.path.dirname(primary_path), exist_ok=True)
                #     shutil.copy(path, primary_path)
                #     print(f"圖片已從備用位置複製到標準位置: {primary_path}")
                # except Exception as copy_e:
                #     print(f"複製備用圖片到主要位置失敗: {copy_e}")
                return image
        except Exception as e_backup:
            # print(f"Failed to load from backup {path}: {e_backup}") # Debugging line
            continue

    # print(f"All loading attempts failed for {image_path}, using placeholder.") # Debugging line
    # 找不到圖片時使用占位圖
    placeholder = pygame.Surface((40, 40), pygame.SRCALPHA)
    placeholder.fill((150, 150, 200, 180))
    pygame.draw.rect(placeholder, (80, 80, 120), placeholder.get_rect(), 2)
    item_image_cache[image_path] = placeholder
    return placeholder

def calculate_adaptive_scale(image, target_size=100):
    """根據圖片大小計算合適的縮放比例"""
    # 獲取原始尺寸
    orig_width = image.get_width()
    orig_height = image.get_height()

    # 計算較大的邊
    max_side = max(orig_width, orig_height)

    # 計算縮放比例，使較大的邊等於目標尺寸
    return target_size / max_side if max_side > 0 else 1.0

# 在繪製物品的部分使用此函數
def draw_item(screen, item, pos, scale, offset_x, offset_y, font):
    """繪製單個物品"""
    # 獲取物品位置和大小
    ipos = pos
    item_size = getattr(item, "size", [30, 30])
    if item_size is None:
        item_size = [30, 30]

    # 計算物品的螢幕位置和大小
    item_rect = pygame.Rect(
        int(ipos[0] * scale + offset_x),
        int(ipos[1] * scale + offset_y),
        int(item_size[0] * scale),
        int(item_size[1] * scale)
    )

    # 嘗試載入物品圖片
    image = None
    if hasattr(item, "image_path") and item.image_path:
        image = load_item_image(item.image_path)

    # 如果有圖片則繪製圖片，否則繪製矩形
    if image:
        # 獲取縮放比例
        adaptive_scale = calculate_adaptive_scale(image)
        img_scale = getattr(item, "image_scale", 1.0) * scale * adaptive_scale

        # 計算縮放後的尺寸
        img_width = int(image.get_width() * img_scale)
        img_height = int(image.get_height() * img_scale )

        # 縮放圖片
        scaled_img = pygame.transform.scale(image, (img_width, img_height))

        # 居中繪製圖片
        img_rect = scaled_img.get_rect(center=item_rect.center)
        screen.blit(scaled_img, img_rect)
    else:
        # 如果沒有圖片，繪製預設矩形
        pygame.draw.rect(screen, (100, 100, 255), item_rect, border_radius=8)

    # 繪製物品名稱
    item_text = font.render(item.name, True, (20, 20, 80))
    screen.blit(item_text, (item_rect.x, item_rect.y + int(14 * scale)))

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
        ("s", "存檔"),
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
    # 在初始化時輸出目前關注的NPC
    if active_npc:
        print(f"========= 目前關注的NPC: {active_npc.name} ==========")
    else:
        print("========= 目前沒有可用的NPC ===========")
    last_ai_result = ""
    ai_thinking = False
    ai_threading = None
    ai_running = False
    npc_threads = []  # 新增：用於追蹤所有 NPC 執行緒

    def ai_process():
        nonlocal last_ai_result, ai_thinking, ai_running, npc_threads
        ai_running = True
        ai_thinking = True
        
        # 清空現有執行緒列表
        for t in npc_threads:
            if t.is_alive():
                print(f"等待執行緒結束...")
                t.join(0.5)  # 等待最多0.5秒
        npc_threads.clear()
        
        # 在主控 NPC 處理前先處理其他 NPC
        for i, npc in enumerate(npcs):
                # 標記當前 NPC 處於思考狀態
                npc.is_thinking = True
                npc.thinking_status = f"{npc.name} 處理中..."  # 修改 NPC 狀態
                
                # 定義處理單個 NPC 的函數
                def process_single_npc(npc_id, npc_ref):
                    try:
                        this_npc_name = npc_ref.name  # 保存當前 NPC 名稱
                        print(f"執行緒 {npc_id}: 開始處理 {this_npc_name}...")
                        
                        # 處理當前 NPC
                        result = npc_ref.process_tick()
                        
                        # 更新 NPC 狀態
                        npc_ref.is_thinking = False
                        npc_ref.thinking_status = f"{this_npc_name}: {result[:50]}" + ("..." if len(result) > 50 else "")
                        
                        print(f"執行緒 {npc_id}: 完成處理 {this_npc_name}: {result[:30]}...")
                    except Exception as e:
                        print(f"執行緒 {npc_id}: 處理 {npc_ref.name} 失敗: {str(e)}")
                        npc_ref.is_thinking = False
                        npc_ref.thinking_status = f"{npc_ref.name}: 處理失敗"
                
                # 創建並啟動執行緒，確保每個執行緒有自己的 NPC 參考
                t = threading.Thread(target=process_single_npc, args=(i, npc))
                t.daemon = True  # 設定為守護執行緒
                npc_threads.append(t)
                t.start()
                print(f"已啟動執行緒 {i} 用於處理 {npc.name}")
        # 等待所有執行緒完成
        time.sleep(0.1)  
        
        ai_thinking = False
        ai_running = False
        
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
            save_world_to_json(world, original_path)
        elif menu_items[selected] == "另存新檔":
            input_rect = pygame.Rect(100, 320, 400, 50)
            import os
            default_name = os.path.basename(original_path) if original_path else "new_save.json"
            
            # 初始化輸入框和按鈕
            input_text = default_name
            confirm_button = pygame.Rect(100, 390, 150, 50)  # 確認按鈕
            cancel_button = pygame.Rect(350, 390, 150, 50)   # 取消按鈕
            
            input_active = True
            button_hovered = None
            mouse_down = False
            save_action = False
            
            while input_active:
                mouse_pos = pygame.mouse.get_pos()
                
                # 檢查按鈕懸停
                if confirm_button.collidepoint(mouse_pos):
                    button_hovered = "confirm"
                elif cancel_button.collidepoint(mouse_pos):
                    button_hovered = "cancel"
                else:
                    button_hovered = None
                
                # 處理事件
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:  # 按 Enter 確認
                            if input_text.strip():
                                input_active = False
                                save_action = True
                        elif event.key == pygame.K_BACKSPACE:  # 刪除字元
                            input_text = input_text[:-1]
                        elif event.key == pygame.K_ESCAPE:  # 按 Esc 取消
                            input_active = False
                            save_action = False
                        else:  # 輸入字元
                            # 避免輸入不可見字元
                            if len(event.unicode) == 1 and (32 <= ord(event.unicode) <= 126 or ord(event.unicode) > 127):
                                input_text += event.unicode
                    elif event.type == pygame.MOUSEBUTTONDOWN:
                        mouse_down = True
                    elif event.type == pygame.MOUSEBUTTONUP:
                        if mouse_down:
                            if button_hovered == "confirm" and input_text.strip():  # 點擊確認按鈕
                                input_active = False
                                save_action = True
                            elif button_hovered == "cancel":  # 點擊取消按鈕
                                input_active = False
                                save_action = False
                        mouse_down = False
                
                # 繪製畫面
                screen.fill((180, 180, 180))
                
                # 繪製輸入標題
                title_text = font.render("輸入新檔名:", True, (0, 0, 0))
                screen.blit(title_text, (100, 280))
                
                # 繪製輸入框
                pygame.draw.rect(screen, (255, 255, 255), input_rect)
                text_surface = font.render(input_text, True, (0, 0, 0))
                screen.blit(text_surface, (input_rect.x + 5, input_rect.y + 12))
                
                # 繪製確認按鈕
                if button_hovered == "confirm" and mouse_down:  # 點擊狀態
                    confirm_color = (100, 200, 100)
                elif button_hovered == "confirm":  # 懸停狀態
                    confirm_color = (150, 255, 150)
                else:  # 正常狀態
                    confirm_color = (120, 220, 120)
                pygame.draw.rect(screen, confirm_color, confirm_button)
                confirm_text = font.render("確認", True, (0, 0, 0))
                screen.blit(confirm_text, (confirm_button.x + 50, confirm_button.y + 15))
                
                # 繪製取消按鈕
                if button_hovered == "cancel" and mouse_down:  # 點擊狀態
                    cancel_color = (200, 100, 100)
                elif button_hovered == "cancel":  # 懸停狀態
                    cancel_color = (255, 150, 150)
                else:  # 正常狀態
                    cancel_color = (220, 120, 120)
                pygame.draw.rect(screen, cancel_color, cancel_button)
                cancel_text = font.render("取消", True, (0, 0, 0))
                screen.blit(cancel_text, (cancel_button.x + 50, cancel_button.y + 15))
                
                pygame.display.flip()
            
            # 處理存檔動作
            if save_action:
                filename = input_text.strip()
                if not filename.lower().endswith('.json'):
                    filename += ".json"
                new_path = os.path.join("worlds/maps", filename)
                save_world_to_json(world, new_path)
        # 取消則不做事

    def npc_selection_menu(screen, font, npcs, active_npc):
        if not npcs or len(npcs) <= 1:
            return active_npc  # 如果沒有 NPC 或只有一個 NPC，不需要切換

        # 設定視窗大小和位置
        screen_w, screen_h = screen.get_size()
        menu_w, menu_h = min(600, screen_w - 200), min(400, screen_h - 200)
        menu_x = (screen_w - menu_w) // 2
        menu_y = (screen_h - menu_h) // 2
        menu_rect = pygame.Rect(menu_x, menu_y, menu_w, menu_h)

        # 設定標題和關閉按鈕
        title = font.render("選擇要關注的 NPC", True, (255, 255, 255))
        close_btn = pygame.Rect(menu_rect.x + menu_rect.width - 90, menu_rect.y + 5, 80, 32)

        # 初始化選中的 NPC 為當前活動的 NPC
        selected_npc = active_npc
        selected_index = npcs.index(active_npc) if active_npc in npcs else 0

        # 顯示 NPC 列表的參數
        line_height = 50  # 每個 NPC 項目的高度
        npc_buttons = []  # 儲存 NPC 按鈕的矩形
        visible_items = min(len(npcs), (menu_h - 100) // line_height)  # 可見 NPC 數量

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

            # 繪製 NPC 列表
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
                if npc == selected_npc:  # 當前選中的 NPC
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

                # 繪製 NPC 名稱和描述
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
                    return active_npc  # 保持原來的 NPC

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                        return active_npc  # 取消，返回原 NPC
                    elif event.key == pygame.K_RETURN:
                        running = False
                        return selected_npc  # 確認，返回選中的 NPC
                    elif event.key == pygame.K_UP and selected_index > 0:   # 上移選項
                        selected_index -= 1
                        selected_npc = npcs[selected_index]
                    elif event.key == pygame.K_DOWN and selected_index < len(npcs) - 1:  # 下移選項
                        selected_index += 1
                        selected_npc = npcs[selected_index]

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if cancel_btn.collidepoint(mouse_pos):
                        running = False
                        return active_npc  # 取消，返回原 NPC

                    elif confirm_btn.collidepoint(mouse_pos):
                        running = False
                        return selected_npc  # 確認，返回選中的 NPC

                    # 檢查是否點擊了 NPC 按鈕
                    for i, btn in enumerate(npc_buttons):
                        if btn.collidepoint(mouse_pos):
                            selected_index = i
                            selected_npc = npcs[i]
        return selected_npc  # 返回選中的 NPC

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

            # 繪製底部區域
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
                # 新增：S鍵觸發存檔選單
                elif event.key == pygame.K_s:
                    save_menu(screen, font, world, world.get('_file_path', None) or "worlds/maps/unnamed_save.json")
                # 新增：P鍵觸發歷史記錄選單
                elif event.key == pygame.K_p:
                    history_menu(screen, font, active_npc)
                # 新增：N鍵觸發NPC切換選單
                elif event.key == pygame.K_n and len(npcs) > 1:
                    new_active_npc = npc_selection_menu(screen, font, npcs, active_npc)
                    if new_active_npc and new_active_npc != active_npc:
                        active_npc = new_active_npc
                        last_ai_result = ""  # 清空上一個NPC的AI結果
                        # 輸出目前關注的NPC
                        print(f"========= 目前關注的NPC: {active_npc.name} ==========")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                win_w, win_h = screen.get_size()
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
                    if rect.collidepoint(event.pos) and key == "c" and active_npc and not ai_running:
                        ai_threading = threading.Thread(target=ai_process)
                        ai_threading.start()
                    if rect.collidepoint(event.pos) and key == "e":
                        running = False
                    if rect.collidepoint(event.pos) and key == "p":
                        history_menu(screen, font, active_npc)
                    if rect.collidepoint(event.pos) and key == "s":
                        save_menu(screen, font, world, world.get('_file_path', None) or "worlds/maps/unnamed_save.json")
                    # 新增：處理「切換NPC」按鈕
                    if rect.collidepoint(event.pos) and key == "n" and len(npcs) > 1:
                        new_active_npc = npc_selection_menu(screen, font, npcs, active_npc)
                        if new_active_npc and new_active_npc != active_npc:
                            active_npc = new_active_npc
                            last_ai_result = ""  # 清空上一個NPC的AI結果
                            # 輸出目前關注的NPC
                            print(f"========= 目前關注的NPC: {active_npc.name} ==========")

        # 每次主循環都同步 display_pos 與 position，並推進動畫移動
        for npc in npcs:
            # 如果 npc.position 尚未指定，給預設值 [0, 0]
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

                    # 如果NPC正在等待互動，結束互動並顯示結果
                    if hasattr(npc, 'waiting_interaction') and npc.waiting_interaction and npc.waiting_interaction.get('started', False):
                        interaction_result = npc.complete_interaction()
                        if interaction_result:
                            last_ai_result = interaction_result
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
            draw_item(screen, item, ipos, scale, offset_x, offset_y, font)
        # 畫 NPC
        for npc in npcs:
            px, py = npc.display_pos
            draw_x = int(px * scale + offset_x)
            draw_y = int(py * scale + offset_y)
            pygame.draw.circle(screen, npc.display_color, (draw_x, draw_y), int(npc.radius * scale))
            npc_text = font.render(npc.name, True, (0,0,0))
            screen.blit(npc_text, (draw_x-16, draw_y-int(npc.radius*scale)-10))
            
            # 聊天氣泡（為每個NPC都顯示）
            bubble_font = info_font
            
            # 直接使用NPC的thinking_status（即self_talk_reasoning）
            display_text = ""
            
            # 處理NPC的思考狀態
            if npc.is_thinking:
                display_text = f"{npc.name} 思考中..."
            elif hasattr(npc, 'thinking_status') and npc.thinking_status:
                # 處理NPC的思考狀態
                if not npc.thinking_status.startswith(npc.name):
                    display_text = f"{npc.name}: {npc.thinking_status}"
                else:
                    display_text = npc.thinking_status
            else:
                display_text = f"{npc.name} 閒置中"            
            # 如果沒有內容則顯示預設文字
            if not display_text:
                display_text = f"{npc.name} 閒置中"
                
            # 限制文字長度，避免氣泡過大
            if len(display_text) > 60:
                display_text = display_text[:57] + "..."
                
            bubble_text = bubble_font.render(display_text, True, (0,0,0))
                
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
            
            # 繪製氣泡（不再根據狀態變色）
            bubble_surface = pygame.Surface((bubble_width, bubble_height), pygame.SRCALPHA)
            bubble_surface.fill((255, 255, 255, 220))  # 統一使用白色半透明背景
            screen.blit(bubble_surface, (bubble_rect.x, bubble_rect.y))
            pygame.draw.rect(screen, (0, 0, 0), bubble_rect, width=2, border_radius=10)
            screen.blit(bubble_text, (bubble_rect.x + 10, bubble_rect.y + 10))
            
            # 為當前活動NPC添加指示標記
            if npc == active_npc:
                active_marker_rect = pygame.Rect(
                    draw_x - int(npc.radius*scale) - 10,
                    draw_y - int(npc.radius*scale) - 10,
                    int(npc.radius*scale*2) + 20,
                    int(npc.radius*scale*2) + 20
                )
                pygame.draw.rect(screen, (255, 215, 0), active_marker_rect, width=3, border_radius=15)
            
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
