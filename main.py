import ctypes  # 用於檢測輸入法
import pygame
import sys
import json
import os  # 新增 os 模組
import datetime  # 用於記錄互動時間
from npc_manager import NPCManager
from AI_thinking import AIThinking
import threading
from save_data import save_game_data  # 匯入存檔功能
from NPC_move import move_npc_to_item, move_npc_to_space  # 新增：引入 NPC 移動功能
import math

pygame.init()
pygame.font.init()

thinking_lock = threading.Lock()
npc_manager = NPCManager("npc.json")

# 顏色
white = (255, 255, 255)
black = (0, 0, 0)
yellow = (255, 255, 0)
brown = (165, 42, 42)
blue = (0, 0, 255)  # 新增藍色，用於門的顏色

# 在 pygame.init() 之後、主循環之前新增以下函數
def show_map_selection():
    map_selection_running = True
    map_screen = pygame.display.set_mode((600, 400))
    pygame.display.set_caption("Map Selection")

    # 確定地圖資料夾路徑
    maps_dir = os.path.join(os.path.dirname(__file__), "worlds", "maps")
    default_map_path = os.path.join(maps_dir, "map.json")

    # 創建資料夾如果不存在
    if not os.path.exists(maps_dir):
        os.makedirs(maps_dir)
        # 如果是新創建的資料夾，把預設地圖複製進去作為第一個選項
        if os.path.exists(default_map_path):
            import shutil
            shutil.copy(default_map_path, os.path.join(maps_dir, "default_map.json"))

    # 獲取所有可用地圖
    available_maps = [f for f in os.listdir(maps_dir) if f.endswith('.json')]
    available_map_paths = [os.path.join(maps_dir, f) for f in available_maps]
    # 加入預設地圖選項（如果不是已經在列表裡）
    if os.path.exists(default_map_path) and "map.json" not in available_maps:
        available_maps.insert(0, "map.json")
        available_map_paths.insert(0, default_map_path)

    # 如果沒有找到地圖文件
    if not available_maps:
        font = pygame.font.SysFont("arial", 20, bold=True)
        map_screen.fill(white)
        text = font.render("No maps found. Using default map.", True, (255, 0, 0))
        map_screen.blit(text, (150, 180))
        pygame.display.flip()
        pygame.time.wait(2000)
        return default_map_path

    # 計算按鈕位置與大小
    button_width = 400
    button_height = 50
    button_margin = 10
    button_start_y = 50

    # 定義返回按鈕
    back_button_rect = pygame.Rect(250, 350, 100, 40)

    # 建立地圖按鈕列表
    map_buttons = []
    for i, map_name in enumerate(available_maps):
        map_buttons.append({
            'name': map_name,
            'rect': pygame.Rect(100, button_start_y + i * (button_height + button_margin), button_width, button_height),
            'hover': False,
            'path': available_map_paths[i]
        })

    selected_map_path = available_map_paths[0]  # 預設值

    while map_selection_running:
        map_screen.fill(white)
        # 標題
        title_font = pygame.font.SysFont("arial", 32, bold=True)
        title = title_font.render("Select a Map", True, black)
        title_rect = title.get_rect(center=(300, 25))
        map_screen.blit(title, title_rect)
        # 滑鼠位置
        mouse_pos = pygame.mouse.get_pos()
        # 繪製地圖按鈕
        for btn in map_buttons:
            btn['hover'] = btn['rect'].collidepoint(mouse_pos)
            color = (180, 180, 255) if btn['hover'] else (220, 220, 220)
            pygame.draw.rect(map_screen, color, btn['rect'], border_radius=10)
            pygame.draw.rect(map_screen, (0,0,0), btn['rect'], width=2, border_radius=10)
            font = pygame.font.SysFont("arial", 20, bold=True)
            text = font.render(btn['name'], True, (0,0,0))
            text_rect = text.get_rect(center=btn['rect'].center)
            map_screen.blit(text, text_rect)
        # 處理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                for btn in map_buttons:
                    if btn['rect'].collidepoint(event.pos):
                        selected_map_path = btn['path']
                        map_selection_running = False
                        break
        pygame.display.flip()
    return selected_map_path

selected_map_path = show_map_selection()
with open(selected_map_path, "r", encoding="utf-8") as f:
    map_data = json.load(f)

if "space_positions" in map_data and "space_size" in map_data:
    # 標準格式（如 map.json）
    space_positions = {name: list(pos) for name, pos in map_data["space_positions"].items()}
    space_size = {name: list(size) for name, size in map_data["space_size"].items()}
elif "spaces" in map_data:
    # RPG/新格式（如 new_save.json/world_test.json）
    space_positions = {}
    space_size = {}
    for idx, space in enumerate(map_data["spaces"]):
        name = space["name"]
        # 優先使用 json 內的 position 欄位，否則 fallback 用 idx
        if "position" in space:
            space_positions[name] = list(space["position"])
        else:
            space_positions[name] = [100 + idx * 100, 100 + idx * 50]
        if "size" in space:
            space_size[name] = list(space["size"])
        else:
            space_size[name] = [200, 150]
else:
    raise KeyError("地圖文件缺少 'space_positions'/'space_size' 或 'spaces' 欄位，無法初始化地圖。")

ai_thinking = AIThinking(
    npc_manager.selected_npc,
    buttons=None,
    thinking_lock=thinking_lock,
    space_positions=space_positions,
    space_size=space_size,
    map_path=selected_map_path  # 新增 map_path 參數
)

# 先讀取地圖檔案並解析空間資訊
# （這段必須在 AIThinking 初始化前）
# default_map_path = os.path.join(os.path.dirname(__file__), "worlds", "maps", "map.json")
# with open(default_map_path, "r", encoding="utf-8") as f:
#     map_data = json.load(f)
# space_positions = {name: list(pos) for name, pos in map_data["space_positions"].items()}
# space_size = {name: list(size) for name, size in map_data["space_size"].items()}

# 再初始化 AIThinking
# ai_thinking = AIThinking(
#     npc_manager.selected_npc, 
#     buttons=None, 
#     thinking_lock=thinking_lock, 
#     space_positions=space_positions, 
#     space_size=space_size)

original_caption = "AI NPC Simulation System"  # 更改為英文標題

# 使用可調整大小的視窗
window_size = [1500, 800]  # 初始視窗大小
screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
pygame.display.set_caption(original_caption)

# 檢測當前輸入法是否為英文，並在畫面中央提示用戶切換
def check_input_method():
    try:
        u32 = ctypes.WinDLL('user32', use_last_error=True)
        hkl = u32.GetKeyboardLayout(0)  # 獲取當前鍵盤佈局
        lang_id = hkl & 0xFFFF  # 提取語言 ID
        if lang_id != 0x0409:  # 0x0409 是英文（美國）的語言 ID
            font = pygame.font.SysFont("arial", 36, bold=True)
            if not font:  # 如果字體加載失敗，使用默認字體
                font = pygame.font.SysFont(None, 36)
            text = font.render("Please switch to English input method", True, (255, 0, 0))  # 紅色提示文字
            text_rect = text.get_rect(center=(window_size[0] // 2, window_size[1] // 2))  # 顯示在畫面中央
            screen.blit(text, text_rect)
        else:
            pygame.display.set_caption(original_caption)
    except Exception as e:
        print(f"Error checking input method: {e}")

# 從 map.json 載入空間資料
# default_map_path = os.path.join(os.path.dirname(__file__), "worlds", "maps", "map.json")
# with open(default_map_path, "r", encoding="utf-8") as f:
#     map_data = json.load(f)
# space_positions = {name: list(pos) for name, pos in map_data["space_positions"].items()}
# space_size = {name: list(size) for name, size in map_data["space_size"].items()}

# 顏色
# white = (255, 255, 255)
# black = (0, 0, 0)
# yellow = (255, 255, 0)
# brown = (165, 42, 42)
# blue = (0, 0, 255)  # 新增藍色，用於門的顏色

# 從 item.json 載入物品資料
item_path = os.path.join(os.path.dirname(__file__), "worlds", "item.json")  # 指定 item.json 路徑
with open(item_path, "r", encoding="utf-8") as f:
    item_data = json.load(f)

item_positions = {name: list(info["position"]) for name, info in item_data["items"].items()}

# 處理 $shared_properties 的引用
def resolve_shared_properties(value, shared_properties):
    if isinstance(value, str) and value.startswith("$shared_properties."):
        keys = value.split(".")[1:]  # 移除 "$shared_properties."
        resolved = shared_properties
        for key in keys:
            if not isinstance(resolved, dict):
                print(f"警告: 無法解析共享屬性 {value}")
                return value  # 返回原始值
            resolved = resolved.get(key, {})
        return resolved
    return value

# 繪製空間
def draw_spaces(screen):
    displayed_labels = {}  # 用於追蹤已顯示的標示及其位置
    shared_properties = map_data.get("shared_properties", {})  # 取得共享屬性

    for space_name, pos in space_positions.items():
        if space_name not in space_size:  # 檢查是否有對應的空間大小
            continue

        # 解決顏色的共享屬性引用
        raw_color = map_data["space_colors"].get(space_name, white)
        color = resolve_shared_properties(raw_color, shared_properties)

        # 解決空間大小的共享屬性引用
        raw_size = space_size.get(space_name, [0, 0])
        size = resolve_shared_properties(raw_size, shared_properties)

        pygame.draw.rect(screen, color, (*pos, *size))

        # 計算標示位置，避免重疊
        label_x, label_y = pos[0] + 10, pos[1] + 10
        while (label_x, label_y) in displayed_labels.values():
            label_y += 30  # 如果重疍，將標示移到下一行

        # 添加到已顯示的標示中
        displayed_labels[space_name] = (label_x, label_y)

        # 顯示空間名稱（使用粗體字體）
        font = pygame.font.SysFont("arial", 24, bold=True)
        text = font.render(space_name, True, black)
        screen.blit(text, (label_x, label_y))

unknown_types = set()  # 用於記錄未知的物品類型

# 繪製物品
def draw_items(screen):
    item_colors = {
        "reading_material": (255, 255, 0),  # 黃色
        "electronics": (0, 255, 255),      # 青色
        "furniture": (139, 69, 19),       # 棕色
        "instrument": (128, 0, 128),      # 紫色
        "appliance": (0, 128, 128),       # 深青色
        "kitchen_tool": (255, 165, 0),    # 橙色
        "stationery": (0, 0, 255),        # 藍色
        "bathroom_fixture": (128, 128, 128),  # 灰色
        "hygiene": (255, 192, 203)        # 粉紅色
    }

    for item_name, pos in item_positions.items():
        item_type = item_data["items"][item_name].get("type")
        color = item_colors.get(item_type, (255, 0, 0))  # 默認為紅色（未知類型）

        # 根據物品類型繪製形狀
        if item_type in ["furniture", "appliance", "bathroom_fixture"]:
            pygame.draw.rect(screen, color, (*pos, 20, 20))  # 繪製矩形
        else:
            pygame.draw.circle(screen, color, pos, 10)  # 繪製圓形

        # 顯示物品名稱
        font = pygame.font.SysFont("arial", 16, bold=True)
        text = font.render(item_name, True, black)
        screen.blit(text, (pos[0] + 15, pos[1] - 10))

# 繪製門
def draw_doors(screen):
    shared_properties = map_data.get("shared_properties", {})  # 取得共享屬性
    doors_data = map_data.get("doors", {})  # 使用 .get() 確保鍵存在
    for door_name, door_data in map_data["doors"].items():
        # 解析門的位置e, door_data in doors_data.items():
        door_pos = list(door_data.get("position", [0, 0]))
        # 解析門的大小 = tuple(door_data.get("position", (0, 0)))
        raw_size = resolve_shared_properties(door_data.get("direction", []), shared_properties)
        door_size = list(raw_size) if isinstance(raw_size, list) and len(raw_size) == 2 else [0, 0]
        # 解析門的顏色e = tuple(raw_size) if isinstance(raw_size, list) and len(raw_size) == 2 else (0, 0)
        raw_color = resolve_shared_properties(door_data.get("color", blue), shared_properties)
        door_color = list(raw_color) if isinstance(raw_color, list) and len(raw_color) == 3 else blue
        door_color = list(raw_color) if isinstance(raw_color, list) and len(raw_color) == 3 else blue
        # 繪製門
        if len(door_pos) == 2 and len(door_size) == 2:  # 確保位置和大小有效
            pygame.draw.rect(screen, door_color, (*door_pos, *door_size))
            pygame.draw.rect(screen, door_color, (*door_pos, *door_size))

# 檢查牆壁碰撞
def check_wall_collision(npc_rect, wall_segments):
    for wall_segment in wall_segments:
        if npc_rect.colliderect(wall_segment):
            return True
    return False

# 修正牆壁繪製邏輯
def draw_walls(screen):
    wall_color = (128, 128, 128)  # 灰色，用於牆壁顏色
    wall_thickness = 8  # 牆壁的厚度
    shared_properties = map_data.get("shared_properties", {})  # 取得共享屬性

    # 獲取所有門的位置和大小
    door_rects = [
        pygame.Rect(*door_data["position"], *resolve_shared_properties(door_data["direction"], shared_properties))
        for door_data in map_data["doors"].values()
    ]

    # 獲取所有區域的位置和大小
    space_rects = [
        pygame.Rect(*pos, *space_size[space_name])
        for space_name, pos in space_positions.items()
        if space_name in space_size
    ]

    wall_segments = []  # 用於存儲所有牆壁段

    # 繪製每個區域的牆壁
    for space_name, pos in space_positions.items():
        size = space_size.get(space_name, [0, 0])
        if not size or len(size) != 2:  # 檢查 size 是否有效
            continue

        # 計算牆壁的外框矩形
        outer_rect = pygame.Rect(
            pos[0] - wall_thickness, pos[1] - wall_thickness,
            size[0] + 2 * wall_thickness, size[1] + 2 * wall_thickness
        )
        # 修正 inner_rect 的創建方式
        inner_rect = pygame.Rect(pos[0], pos[1], size[0], size[1])

        # 繪製牆壁的四個邊，跳過門的位置
        wall_segments_for_space = [
            pygame.Rect(outer_rect.left, outer_rect.top, outer_rect.width, wall_thickness),  # 上邊
            pygame.Rect(outer_rect.left, outer_rect.bottom - wall_thickness, outer_rect.width, wall_thickness),  # 下邊
            pygame.Rect(outer_rect.left, outer_rect.top, wall_thickness, outer_rect.height),  # 左邊
            pygame.Rect(outer_rect.right - wall_thickness, outer_rect.top, wall_thickness, outer_rect.height)  # 右邊
        ]

        for wall_segment in wall_segments_for_space:
            remaining_segments = [wall_segment]
            for door_rect in door_rects:
                new_segments = []
                for segment in remaining_segments:
                    if segment.colliderect(door_rect):
                        # 如果牆壁與門重疊，分割牆壁
                        if segment.width > segment.height:  # 水平牆壁
                            if segment.left < door_rect.left:
                                new_segments.append(pygame.Rect(segment.left, segment.top, door_rect.left - segment.left, segment.height))
                            if segment.right > door_rect.right:
                                new_segments.append(pygame.Rect(door_rect.right, segment.top, segment.right - door_rect.right, segment.height))
                        else:  # 垂直牆壁
                            if segment.top < door_rect.top:
                                new_segments.append(pygame.Rect(segment.left, segment.top, segment.width, door_rect.top - segment.top))
                            if segment.bottom > door_rect.bottom:
                                new_segments.append(pygame.Rect(segment.left, door_rect.bottom, segment.width, segment.bottom - door_rect.bottom))
                    else:
                        new_segments.append(segment)
                remaining_segments = new_segments

            # 檢查牆壁是否與其他區域重疊
            for segment in remaining_segments:
                if not any(segment.colliderect(space_rect) for space_rect in space_rects):
                    pygame.draw.rect(screen, wall_color, segment)
                    wall_segments.append(segment)

    return wall_segments

# 繪製 NPC
def draw_npc(screen, npc_pos):
    pygame.draw.circle(screen, brown, npc_pos, 15)
    font = pygame.font.SysFont("arial", 24)  # Use a font that supports English
    npc_manager.draw_all(screen)
    if not font:  # If font loading fails, use the default font
        font = pygame.font.SysFont(None, 24)
    text = font.render("NPC", True, black)  # NPC label
    screen.blit(text, (npc_pos[0] - 20, npc_pos[1] - 30))

    # 判斷 NPC 所在的空間
    current_space = "Unknown"
    for space_name, pos in space_positions.items():
        size = space_size.get(space_name, [0, 0])
        if pos[0] <= npc_pos[0] <= pos[0] + size[0] and pos[1] <= npc_pos[1] <= pos[1] + size[1]:
            current_space = space_name
            break

    # 判斷 NPC 接觸的物品
    current_item = "None"
    for item_name, pos in item_positions.items():
        if abs(npc_pos[0] - pos[0]) <= 15 and abs(npc_pos[1] - pos[1]) <= 15:
            current_item = item_name
            break

    # 動態計算資訊界面的位置（右上角）
    info_x = window_size[0] - 200  # 距離右邊界 200 像素
    info_y = 10  # 起始 Y 位置
    line_height = 25  # 每行之間的間距

    # 縮小字體大小以避免資訊擠壓
    info_font = pygame.font.SysFont("arial", 20)  # 統一字體大小

    # 顯示座標信息
    coord_text = info_font.render(f"({npc_pos[0]}, {npc_pos[1]})", True, black)
    screen.blit(coord_text, (info_x, info_y))

    # 顯示空間信息
    space_text = info_font.render(f"Space: {current_space}", True, black)
    screen.blit(space_text, (info_x, info_y + line_height))

    # 顯示物品信息
    item_text = info_font.render(f"Item: {current_item}", True, black)
    screen.blit(item_text, (info_x, info_y + line_height * 2))

    # 顯示 FPS
    fps_text = info_font.render(f"FPS: {int(clock.get_fps())}", True, black)
    screen.blit(fps_text, (info_x, info_y + line_height * 3))

    # 顯示最新歷史紀錄標題
    history_title = info_font.render("Latest Event:", True, black)
    screen.blit(history_title, (info_x, info_y + line_height * 4))

    # 顯示最新記錄內容或提示
    if interaction_history:
        # 獲取最新的一條記錄並截短以適應顯示
        latest_record = interaction_history[-1]
        # 減少顯示字數，確保不會超出屏幕
        short_record = latest_record if len(latest_record) < 25 else latest_record[:22] + "..."
        history_text = info_font.render(short_record, True, black)
        screen.blit(history_text, (info_x, info_y + line_height * 5))
    else:
        # 沒有記錄時顯示提示
        no_history = info_font.render("No events yet", True, (150, 150, 150))
        screen.blit(no_history, (info_x, info_y + line_height * 5))

# 定義退出按鈕的屬性
button_color = (200, 0, 0)  # 紅色
button_hover_color = (255, 0, 0)  # 更亮的紅色
button_text_color = white
button_rect = pygame.Rect(window_size[0] - 110, window_size[1] - 50, 100, 40)  # 按鈕位置與大小（右下角）

# 定義紀錄按鈕的屬性
record_button_color = (0, 200, 0)  # 綠色
record_button_hover_color = (0, 255, 0)  # 更亮的綠色
record_button_text_color = white
record_button_rect = pygame.Rect(window_size[0] - 220, window_size[1] - 50, 100, 40)  # 紀錄按鈕位置與大小（退出按鈕左側）

# 定義繼續按鈕的屬性
continue_button_color = (0, 120, 255)  # 藍色
continue_button_hover_color = (0, 180, 255)  # 更亮的藍色
continue_button_text_color = white
continue_button_rect = pygame.Rect(window_size[0] - 330, window_size[1] - 50, 100, 40)  # 繼續按鈕位置與大小（紀錄按鈕左側）

# 定義存檔按鈕屬性
save_button_color = (120, 60, 200)
save_button_hover_color = (150, 90, 255)
save_button_text_color = white
save_button_rect = pygame.Rect(window_size[0] - 440, window_size[1] - 50, 100, 40)  # 存檔按鈕位置（繼續按鈕左側）

# 存檔檔名輸入框狀態
inputting_save_filename = False
save_filename_input = ""
save_filename_canceled = False

# 繪製繼續按鈕
def draw_continue_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    color = continue_button_hover_color if continue_button_rect.collidepoint(mouse_pos) else continue_button_color
    pygame.draw.rect(screen, color, continue_button_rect, border_radius=10)
    pygame.draw.rect(screen, black, continue_button_rect, width=2, border_radius=10)
    font = pygame.font.SysFont("arial", 20, bold=True)
    text = font.render("Continue", True, continue_button_text_color)
    text_rect = text.get_rect(center=continue_button_rect.center)
    screen.blit(text, text_rect)

# 繪製存檔按鈕
def draw_save_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    color = save_button_hover_color if save_button_rect.collidepoint(mouse_pos) else save_button_color
    pygame.draw.rect(screen, color, save_button_rect, border_radius=10)
    pygame.draw.rect(screen, black, save_button_rect, width=2, border_radius=10)
    font = pygame.font.SysFont("arial", 20, bold=True)
    text = font.render("Save", True, save_button_text_color)
    text_rect = text.get_rect(center=save_button_rect.center)
    screen.blit(text, text_rect)

# 繪製退出按鈕
def draw_exit_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    color = button_hover_color if button_rect.collidepoint(mouse_pos) else button_color
    pygame.draw.rect(screen, color, button_rect, border_radius=10)  # 圓角矩形
    # 添加黑色邊框，寬度為2像素
    pygame.draw.rect(screen, black, button_rect, width=2, border_radius=10)
    font = pygame.font.SysFont("arial", 20, bold=True)
    text = font.render("Exit", True, button_text_color)
    text_rect = text.get_rect(center=button_rect.center)
    screen.blit(text, text_rect)

# 繪製紀錄按鈕
def draw_record_button(screen):
    mouse_pos = pygame.mouse.get_pos()
    color = record_button_hover_color if record_button_rect.collidepoint(mouse_pos) else record_button_color
    pygame.draw.rect(screen, color, record_button_rect, border_radius=10)  # 圓角矩形
    # 添加黑色邊框，寬度為2像素
    pygame.draw.rect(screen, black, record_button_rect, width=2, border_radius=10)
    font = pygame.font.SysFont("arial", 20, bold=True)
    text = font.render("History", True, record_button_text_color)
    text_rect = text.get_rect(center=record_button_rect.center)
    screen.blit(text, text_rect)

# 顯示互動歷史的視窗
def show_interaction_history():
    history_running = True
    # 保存當前主視窗大小，以便之後恢復
    original_size = window_size.copy()
    history_screen = pygame.display.set_mode((600, 400))  # 新視窗大小
    pygame.display.set_caption("Interaction History")  # 更改為英文標題
    font = pygame.font.SysFont("arial", 20)

    # 定義返回按鈕的屬性
    back_button_color = (200, 200, 0)  # 黃色
    back_button_hover_color = (255, 255, 0)  # 更亮的黃色
    back_button_text_color = black
    back_button_rect = pygame.Rect(250, 350, 100, 40)  # 按鈕位置與大小（視窗底部中央）

    # 新增滾動功能相關變數
    scroll_y = 0
    scroll_speed = 20  # 每次滾動的像素數
    line_height = 25  # 行高

    # 定義不同互動類型的背景顏色
    space_interaction_bg = (230, 240, 255)  # 空間互動使用淡藍色背景
    item_interaction_bg = (255, 240, 230)   # 物品互動使用淡橘色背景
    separator_color = (50, 50, 50)          # 分隔線顏色

    # 計算最大可滾動範圍
    max_lines = len(interaction_history)
    visible_area_height = 330  # 可見區域高度 (扣除按鈕區域)

    # 創建邊框矩形，用於限制文字顯示區域
    text_area_rect = pygame.Rect(5, 5, 590, 340)

    while history_running:
        history_screen.fill(white)  # 填充背景色
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                history_running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button_rect.collidepoint(event.pos):  # 檢查是否點擊了返回按鈕
                    history_running = False
                # 處理滑鼠滾輪事件
                elif event.button == 4:  # 滾輪向上滾動
                    scroll_y = min(0, scroll_y + scroll_speed)
                elif event.button == 5:  # 滾輪向下滾動
                    # 計算最大滾動距離，確保不會滾動超出內容範圍
                    max_scroll = -(max(0, max_lines * line_height - visible_area_height))
                    scroll_y = max(max_scroll, scroll_y - scroll_speed)

        # 繪製文字區域邊框
        pygame.draw.rect(history_screen, (200, 200, 200), text_area_rect, width=2)

        # 顯示歷史紀錄，現在包含滾動偏移
        y_offset = 10 + scroll_y
        # 使用剪裁來限制文字只在指定區域內顯示
        history_screen.set_clip(text_area_rect)

        # 先繪製所有的分隔線 (確保在背景色和文字下面)
        if len(interaction_history) > 1:
            temp_y = 10 + scroll_y + line_height
            for i in range(len(interaction_history) - 1):
                if 5 <= temp_y <= 340:
                    # 分隔線更粗更明顯
                    pygame.draw.line(history_screen,
                                    separator_color,
                                    (10, temp_y),
                                    (580, temp_y),
                                    2)  # 線寬增加為2像素
                temp_y += line_height

        # 繪製每條記錄的背景和文字
        for i, record in enumerate(interaction_history):
            # 只渲染在可見區域內的記錄
            if 5 <= y_offset <= 340:
                # 判斷互動類型並設置相應的背景顏色
                record_bg = None
                if "Space Change" in record:
                    record_bg = space_interaction_bg
                elif "Item Contact" in record:
                    record_bg = item_interaction_bg

                # 繪製背景色 - 縮短背景高度避開分隔線
                if record_bg:
                    bg_rect = pygame.Rect(10, y_offset, 570, line_height - 3)
                    pygame.draw.rect(history_screen, record_bg, bg_rect)

                # 渲染文字
                text = font.render(record, True, black)
                history_screen.blit(text, (10, y_offset))

            y_offset += line_height

        # 重設剪裁區域
        history_screen.set_clip(None)

        # 繪製返回按鈕 (在剪裁區域外)
        mouse_pos = pygame.mouse.get_pos()
        color = back_button_hover_color if back_button_rect.collidepoint(mouse_pos) else back_button_color
        pygame.draw.rect(history_screen, color, back_button_rect, border_radius=10)  # 圓角矩形
        # 添加黑色邊框，寬度為2像素
        pygame.draw.rect(history_screen, black, back_button_rect, width=2, border_radius=10)
        button_font = pygame.font.SysFont("arial", 20, bold=True)
        button_text = button_font.render("Back", True, back_button_text_color)  # 更改為英文
        button_text_rect = button_text.get_rect(center=back_button_rect.center)
        history_screen.blit(button_text, button_text_rect)

        pygame.display.flip()

    # 返回主視窗時，恢復原始視窗大小
    screen = pygame.display.set_mode(original_size, pygame.RESIZABLE)
    pygame.display.set_caption(original_caption)

    # 更新按鈕位置，適應恢復後的窗口大小
    global button_rect, record_button_rect, continue_button_rect
    button_rect = pygame.Rect(original_size[0] - 110, original_size[1] - 50, 100, 40)
    record_button_rect = pygame.Rect(original_size[0] - 220, original_size[1] - 50, 100, 40)
    continue_button_rect = pygame.Rect(original_size[0] - 330, original_size[1] - 50, 100, 40)

# 更新互動歷史
def update_interaction_history(event_type, detail):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 將事件類型轉換為英文
    if event_type == "空間變更":
        event_type = "Space Change"
    elif event_type == "物品接觸":
        event_type = "Item Contact"

    # 將詳細信息前綴轉換為英文
    if "進入" in detail:
        detail = detail.replace("進入", "Entered")
    elif "接觸" in detail:
        detail = detail.replace("接觸", "Contacted")

    interaction_history.append(f"[{timestamp}] {event_type}: {detail}")
    if len(interaction_history) > 100:  # 限制歷史記錄長度
        interaction_history.pop(0)

# 改進 FPS 顯示
def draw_fps(screen, clock):
    font = pygame.font.SysFont("arial", 16, bold=True)
    fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, white)
    fps_bg = pygame.Surface((80, 30))
    fps_bg.fill(black)
    fps_bg.set_alpha(150)  # 半透明背景
    screen.blit(fps_bg, (10, 10))
    screen.blit(fps_text, (20, 15))

# 主迴圈
auto_move_enabled = True  # 預設啟用自動移動
last_target_item = None   # 記錄上一次自動移動的目標
last_target_space = None  # 記錄上一次自動移動的空間
running = True
npc_pos = [150, 150]  # NPC 初始位置
npc_speed = 3  # NPC 移動速度
clock = pygame.time.Clock()  # 用於控制刷新率
FPS = int(os.getenv("FPS", 30))  # 默認為 30，可通過環境變數設置
current_space = "Unknown"  # 初始化當前空間
current_item = "None"  # 初始化當前物品

interaction_history = []

# --- 新增：NPC 空間移動動畫狀態 ---
npc_move_target_pos = None  # 目標座標
npc_move_target_space = None  # 目標空間名稱

while running:
    try:
        ai_thinking.npc = npc_manager.selected_npc
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if button_rect.collidepoint(event.pos):  # 檢查是否點擊了退出按鈕
                    running = False

                elif record_button_rect.collidepoint(event.pos):  # 檢查是否點擊了紀錄按鈕
                    show_interaction_history()
                elif continue_button_rect.collidepoint(event.pos):  # 檢查是否點擊了繼續按鈕
                    if npc_manager.selected_npc:
                        if not ai_thinking.thinking:
                            ai_thinking.npc = npc_manager.selected_npc
                            ai_thinking.thinking = True
                            threading.Thread(target=ai_thinking._think_action, daemon=True).start()
                
                elif save_button_rect.collidepoint(event.pos):  # 檢查是否點擊了存檔按鈕
                    inputting_save_filename = True  # 開始輸入檔名
                    save_filename_input = ""    # 初始化輸入的檔名
                    save_filename_canceled = False

                elif npc_manager.handle_click(event.pos):   # 檢查是否點擊了 NPC
                    ai_thinking.npc = npc_manager.selected_npc
                    
            elif event.type == pygame.KEYDOWN and inputting_save_filename:  # 檢查是否正在輸入存檔名稱
                if event.key == pygame.K_RETURN:
                    if save_filename_input.strip():
                        save_game_data(npc_manager, [h for npc in npc_manager.npcs for h in getattr(npc, 'action_history', [])], interaction_history, filename=save_filename_input.strip())
                    inputting_save_filename = False
                    save_filename_input = ""
                    save_filename_canceled = False
                elif event.key == pygame.K_ESCAPE:  # 新增：ESC 鍵取消
                    inputting_save_filename = False
                    save_filename_input = ""
                    save_filename_canceled = True
                elif event.key == pygame.K_BACKSPACE:  # 新增：Backspace 鍵刪除
                    save_filename_input = save_filename_input[:-1]  # 刪除最後一個字元
                else:
                    if len(save_filename_input) < 32:  # 新增：限制字元數
                        save_filename_input += event.unicode
            elif event.type == pygame.VIDEORESIZE:  # 處理視窗大小調整事件
                window_size = [event.w, event.h]
                screen = pygame.display.set_mode(window_size, pygame.RESIZABLE)
                button_rect = pygame.Rect(window_size[0] - 110, window_size[1] - 50, 100, 40)  # 更新退出按鈕位置
                record_button_rect = pygame.Rect(window_size[0] - 220, window_size[1] - 50, 100, 40)  # 更新紀錄按鈕位置
                continue_button_rect = pygame.Rect(window_size[0] - 330, window_size[1] - 50, 100, 40)  # 更新繼續按鈕位置
                save_button_rect = pygame.Rect(window_size[0] - 440, window_size[1] - 50, 100, 40)  # 更新存檔按鈕位置

        # 處理鍵盤輸入
        keys = pygame.key.get_pressed()
        moved = False
        if npc_manager.selected_npc:
            new_pos = list(npc_manager.selected_npc.position)
            if keys[pygame.K_w]:  # 按下 W 鍵向上移動
                new_pos[1] -= npc_speed
                moved = True    # 設置 moved 為 True
            if keys[pygame.K_s]:
                new_pos[1] += npc_speed
                moved = True
            if keys[pygame.K_a]:
                new_pos[0] -= npc_speed
                moved = True
            if keys[pygame.K_d]:
                new_pos[0] += npc_speed
                moved = True
            if moved:
                npc_rect = pygame.Rect(new_pos[0] - 15, new_pos[1] - 15, 30, 30)
                wall_segments = draw_walls(screen)
                if not check_wall_collision(npc_rect, wall_segments):
                    npc_manager.move_selected_npc(new_pos)
                auto_move_enabled = False  # 只要有手動移動就停用自動移動

        # === 修正：用 A* 路徑規劃並避開牆壁 ===
        target_item = getattr(ai_thinking, "target_item", None)
        target_space = getattr(ai_thinking, "target_space", None)
        if npc_manager.selected_npc is not None and auto_move_enabled:
            if target_space:
                result = move_npc_to_space(
                    npc_manager.selected_npc, target_space,
                    space_positions, space_size, screen,
                    speed=npc_speed, draw_callback=None, wall_segments=draw_walls(screen)
                )
                if result:
                    print(f"[DEBUG] NPC 成功到達 {target_space}")
                else:
                    print(f"[DEBUG] NPC 無法到達 {target_space}（所有路徑都會撞牆）")
                ai_thinking.target_space = None
                auto_move_enabled = False
            elif target_item:
                move_npc_to_item(npc_manager.selected_npc, target_item, item_data, screen, speed=npc_speed)

        # 檢查 AI 目標是否有變化
        if (target_item and target_item != last_target_item) or (target_space and target_space != last_target_space):
            auto_move_enabled = True
            last_target_item = target_item
            last_target_space = target_space

        # 更新互動歷史（檢測空間變更）
        previous_space = current_space
        current_space = "Unknown"
        npc_pos = npc_manager.selected_npc.position if npc_manager.selected_npc else [0, 0]  # 用 NPC 物件位置
        for space_name, pos in space_positions.items():
            size = space_size.get(space_name, [0, 0])
            if pos[0] <= npc_pos[0] <= pos[0] + size[0] and pos[1] <= npc_pos[1] <= pos[1] + size[1]:
                current_space = space_name
                break
        if current_space != previous_space:
            update_interaction_history("Space Change", f"Entered {current_space}")  # 直接使用英文

        # 更新互動歷史（檢測物品接觸）
        previous_item = current_item
        current_item = "None"
        for item_name, pos in item_positions.items():
            if abs(npc_pos[0] - pos[0]) <= 15 and abs(npc_pos[1] - pos[1]) <= 15:
                current_item = item_name
                break
        if current_item != previous_item:
            update_interaction_history("Item Contact", f"Contacted {current_item}")

        # === 只刷新一次畫面，確保 NPC 不會被覆蓋 ===
        screen.fill(white)
        draw_spaces(screen)
        draw_doors(screen)
        wall_segments = draw_walls(screen)
        draw_items(screen)
        npc_manager.draw_all(screen)

        # 繪製退出按鈕和紀錄按鈕
        draw_exit_button(screen)
        draw_record_button(screen)
        draw_continue_button(screen)
        draw_save_button(screen)

        # 顯示輸入法提示
        check_input_method()

        # 顯示輸入存檔檔名的輸入框
        if inputting_save_filename:
            font = pygame.font.SysFont("arial", 24, bold=True)
            input_box_rect = pygame.Rect(window_size[0]//2 - 150, window_size[1]//2 - 30, 300, 50)
            pygame.draw.rect(screen, (255,255,255), input_box_rect)
            pygame.draw.rect(screen, (0,0,0), input_box_rect, 2)
            prompt = font.render("Enter save filename:", True, (0,0,0))
            screen.blit(prompt, (input_box_rect.x+10, input_box_rect.y+5))
            filename_text = font.render(save_filename_input + "|", True, (0,0,200))
            screen.blit(filename_text, (input_box_rect.x+10, input_box_rect.y+28))

        # 更新顯示
        pygame.display.flip()

        # 控制刷新率clock.tick(FPS)
        draw_fps(screen, clock)
    except Exception as e:
        print(f"發生錯誤: {e}")
        running = False

# 結束 pygame
pygame.quit()
sys.exit()
