import pygame
import threading
import math # 加入 math 模組以使用 math.hypot
import os
import time
from backend import save_world_to_json
from backend import PathPlanner # Added import for PathPlanner
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

    # 新增：碰撞表面緩存字典，用於避免重複創建大型表面
    collision_surface_cache = {}
    
    # 定義獲取或創建碰撞表面的函數
    def get_collision_surface(width, height, color, border_color=None):
        # 限制最大尺寸，避免記憶體溢出
        max_surface_size = 2000
        safe_width = min(width, max_surface_size)
        safe_height = min(height, max_surface_size)
        
        # 使用尺寸和顏色作為緩存的鍵
        cache_key = (safe_width, safe_height, color[3])  # 使用寬度、高度和透明度作為鍵
        
        if cache_key in collision_surface_cache:
            # 重用緩存的表面，只需要重新填充顏色
            surface = collision_surface_cache[cache_key]
            surface.fill(color)
        else:
            # 創建新的表面並加入緩存
            surface = pygame.Surface((safe_width, safe_height), pygame.SRCALPHA)
            surface.fill(color)
            collision_surface_cache[cache_key] = surface
            
            # 限制緩存大小，避免佔用過多記憶體
            if len(collision_surface_cache) > 50:
                # 移除最早添加的項目
                oldest_key = next(iter(collision_surface_cache))
                del collision_surface_cache[oldest_key]
        
        # 如果指定了邊框顏色，繪製邊框
        if border_color:
            pygame.draw.rect(surface, border_color, surface.get_rect(), 3)
            
        return surface

    # 新增：路徑規劃除錯顯示開關
    show_pathfinding_debug = False # G 鍵切換

    # 新增攝影機相關變數
    camera_offset_x = 0
    camera_offset_y = 0
    panning_speed = 15  # 視角移動速度
    edge_margin = 50    # 螢幕邊緣觸發區域

    # 新增縮放相關變數
    current_zoom_level = 1.0
    zoom_speed = 0.1
    min_zoom = 0.2
    max_zoom = 5.0

    # 新增：顯示碰撞區域的開關
    show_collision_areas = True  # 設置為 True 以默認顯示碰撞區域
    
    # 碰撞區域顏色設置
    SPACE_COLLISION_COLOR = (255, 100, 100, 128)  # 紅色半透明
    ITEM_COLLISION_COLOR = (100, 255, 100, 128)   # 綠色半透明
    NPC_COLLISION_COLOR = (100, 100, 255, 128)    # 藍色半透明

    # 功能說明
    info_lines = []

    # 互動選單對應的按鈕（與 demo.py 主程式一致）
    button_labels = [
        ("c", "繼續"),
        ("e", "退出"),
        ("p", "打印歷史"),
        ("s", "存檔"),
        ("n", "切換NPC"),
        ("w", "改變天氣和時間"),
        ("k", "碰撞顯示"),  # 新增：切換碰撞區域顯示
        ("g", "路徑網格") # 新增：切換路徑規劃網格顯示
    ]

    # 取得物件參考
    spaces = list(world["spaces"].values())
    npcs = list(world["npcs"].values())
    items = list(world["items"].values())
    all_spaces_dict = world["spaces"] # A* 需要空間字典

    # 增加 NPC 移動速度
    for npc in npcs:
        # 設置更快的默認移動速度
        if hasattr(npc, 'move_speed'):
            original_speed = npc.move_speed
            npc.move_speed = 5.0 if original_speed <= 5.0 else original_speed
            print(f"DEBUG: 將 NPC {npc.name} 的移動速度從 {original_speed} 調整為 {npc.move_speed}")

    # 不再需要 map_data，直接用物件屬性
    # 計算原始地圖最大寬高（用於縮放）
    map_w = max([s.display_pos[0]+s.display_size[0] for s in spaces if s.display_size and s.display_pos] or [1200])
    map_h = max([s.display_pos[1]+s.display_size[1] for s in spaces if s.display_size and s.display_pos] or [700])

    # NPC 圓形顏色
    npc_colors = [(255,0,0),(0,128,255),(0,200,0),(200,0,200),(255,128,0)]
    for idx, npc in enumerate(npcs):
        npc.display_color = npc_colors[idx % len(npc_colors)]
        npc.radius = 24
        # A* 路徑相關屬性初始化
        npc.path_to_follow = [] # 確保 NPC 物件有此屬性 (已在 backend.py 中定義)
        npc.current_path_segment_target_space_name = None # 確保 NPC 物件有此屬性
        
        # npc.current_space 應該由 backend.py 中的 build_world_from_data 設定
        # 我們在這裡檢查它是否存在，並給出警告（如果需要）
        if not hasattr(npc, 'current_space') or npc.current_space is None:
            print(f"警告: NPC {npc.name} 沒有有效的 current_space。A* 路徑規劃可能會有問題。")
        elif not hasattr(npc.current_space, 'name'):
            print(f"警告: NPC {npc.name} 的 current_space 物件沒有 name 屬性。")

        # position 屬性也應該由 backend 設定好
        if not hasattr(npc, 'position') or npc.position is None:
            default_initial_pos = [0.0, 0.0]
            if hasattr(npc, 'current_space') and npc.current_space and \
               hasattr(npc.current_space, 'display_pos') and hasattr(npc.current_space, 'display_size'):
                default_initial_pos = [
                    float(npc.current_space.display_pos[0] + npc.current_space.display_size[0] / 2),
                    float(npc.current_space.display_pos[1] + npc.current_space.display_size[1] / 2)
                ]
            npc.position = default_initial_pos
            print(f"警告: NPC {npc.name} 沒有初始位置，已根據其 current_space (如果存在) 或 (0,0) 設定為 {npc.position}")

    active_npc = npcs[0] if npcs else None  # 預設主控第一個 NPC
    # 在初始化時輸出目前關注的NPC
    if active_npc:
        print(f"========= 目前關注的NPC: {active_npc.name} ==========")
    else:
        print("========= 目前沒有可用的NPC ===========")

    # 新增：牆壁和連接相關常數 (使用世界單位，會進行縮放)
    WALL_COLOR = (70, 70, 70)  # 深灰色牆壁
    WALL_THICKNESS_WORLD_UNITS = 2.0  # 牆壁厚度 (世界座標系)
    CONNECTION_TOLERANCE_WORLD_UNITS = 20.0  # 空間邊緣對齊的容差 (世界座標系)
    # MIN_PATH_WIDTH_WORLD_UNITS = 20.0     # 形成路徑所需的最小重疊寬度 (世界座標系) # 註解掉，門的邏輯使用固定寬度
    
    # 新增：門的相關常數
    DOOR_WIDTH_WORLD_UNITS = 80.0  # 門的寬度/高度 (開口大小)，世界座標系
    DOOR_COLOR = (139, 69, 19, 180)   # 門的顏色 (棕色，半透明)
    DOOR_FRAME_THICKNESS_WORLD_UNITS = 20.0 # 門框厚度
    DOOR_FRAME_COLOR = (90, 45, 10) # 深棕色門框

    last_ai_result = ""
    ai_thinking = False
    ai_threading = None
    ai_running = False
    npc_threads = []  # 新增：用於追蹤所有 NPC 執行緒

    # 初始化路徑規劃器 (已在之前步驟中加入)
    # Default values for grid_cell_size and npc_radius
    DEFAULT_GRID_CELL_SIZE = 20 # 與 PathPlanner 預設值一致
    DEFAULT_NPC_RADIUS = 24     # 與 NPC 預設半徑一致 (或取一個代表性值)
    path_planner = PathPlanner(grid_cell_size=DEFAULT_GRID_CELL_SIZE, npc_radius=DEFAULT_NPC_RADIUS)
    
    # 為所有 NPC 設置路徑規劃器 (已在之前步驟中加入)
    if 'npcs' in world and isinstance(world['npcs'], dict):
        for npc_obj in world['npcs'].values(): # 確保迭代的是 NPC 物件
            if hasattr(npc_obj, 'set_path_planner'):
                npc_obj.set_path_planner(path_planner)
            # else:
                # print(f"Warning: NPC {getattr(npc_obj, 'name', 'Unknown')} does not have set_path_planner method.") # 可以取消註解以進行除錯
    # else:
        # print("Warning: world['npcs'] is not a dictionary or not found. Cannot assign path_planner.") # 可以取消註解以進行除錯

    # ========= 新增：路徑規劃除錯繪製函式 =========
    def draw_pathfinding_debug_info(screen, path_planner_instance, spaces_dict, active_npc, overall_scale, cam_offset_x, cam_offset_y): # MODIFIED: current_zoom -> overall_scale, added active_npc
        """繪製路徑規劃的除錯資訊，包括網格、障礙物和活動NPC的路徑""" # MODIFIED: Updated docstring
        GRID_COLOR = (120, 120, 220)  # 更亮的藍紫色網格線 (原本是 180,180,180)
        OBSTACLE_COLOR = (255, 0, 0, 100)  # 半透明紅色障礙物
        
        # 新的路徑顏色定義 - 更鮮豔醒目
        START_COLOR = (0, 255, 255)  # 起點：青色
        END_COLOR = (255, 0, 255)    # 終點：粉紅色
        PATH_DOT_COLOR = (255, 255, 0)  # 路徑點：亮黃色
        PATH_LINE_WIDTH = 5  # 增加線條寬度為5像素（更粗）
        PATH_DOT_RADIUS = 8  # 增加路徑點的圓點半徑

        # 網格和障礙物繪製保持原樣
        print(f"DEBUG: 開始繪製路徑規劃除錯資訊... Scale: {overall_scale:.2f}, Offset: ({cam_offset_x:.0f}, {cam_offset_y:.0f})")

        if not path_planner_instance:
            print("DEBUG: 路徑規劃器實例為空，返回空結果")
            return []

        if not spaces_dict:
            print("DEBUG: 空間字典為空，返回空結果")
            return []

        # 用於追蹤處理的空間數量
        spaces_processed = 0
        spaces_with_valid_area = 0

        # 保存所有空間的格子集合，以便後續畫路徑時參考
        all_grid_rects = []
        all_grid_cells = {}

        # 先繪製所有空間的網格和障礙物
        for space_name, space_obj in spaces_dict.items():
            if space_obj is None:
                continue

            # 獲取空間的面積資訊
            is_area_valid = False
            area_x, area_y, area_width, area_height = 0, 0, 0, 0

            # 優先嘗試從 space_obj.area 取得區域資訊
            if hasattr(space_obj, 'area') and space_obj.area:
                # 檢查 area 是否為 dict 或其他支持的類型
                if isinstance(space_obj.area, dict) and 'x' in space_obj.area and 'y' in space_obj.area and \
                    'width' in space_obj.area and 'height' in space_obj.area:
                    area_x = float(space_obj.area['x'])
                    area_y = float(space_obj.area['y'])
                    area_width = float(space_obj.area['width'])
                    area_height = float(space_obj.area['height'])
                    is_area_valid = True
                elif isinstance(space_obj.area, (list, tuple)) and len(space_obj.area) >= 4:
                    area_x = float(space_obj.area[0])
                    area_y = float(space_obj.area[1])
                    area_width = float(space_obj.area[2])
                    area_height = float(space_obj.area[3])
                    is_area_valid = True

            # 如果 area 不可用或無效，嘗試使用 display_pos 和 display_size
            if not is_area_valid and hasattr(space_obj, 'display_pos') and hasattr(space_obj, 'display_size'):
                try:
                    if isinstance(space_obj.display_pos, (list, tuple)) and len(space_obj.display_pos) >= 2 and \
                        isinstance(space_obj.display_size, (list, tuple)) and len(space_obj.display_size) >= 2:
                        space_x = float(space_obj.display_pos[0])
                        space_y = float(space_obj.display_pos[1])
                        space_width = float(space_obj.display_size[0])
                        space_height = float(space_obj.display_size[1])
                        area_x, area_y = space_x, space_y
                        area_width, area_height = space_width, space_height
                        is_area_valid = True
                except (TypeError, ValueError) as e:
                    print(f"DEBUG: 空間 {space_name} 的 display_pos 或 display_size 格式無效：{e}")
                    pass

            if not is_area_valid:
                print(f"DEBUG: 空間 {space_name} 的區域無效或找不到合適的區域資訊")
                continue

            spaces_processed += 1
            spaces_with_valid_area += 1

            # 計算網格單元格大小 (假設路徑規劃器的 grid_cell_size 為 10)
            grid_cell_size = path_planner_instance.grid_cell_size if path_planner_instance and hasattr(path_planner_instance, 'grid_cell_size') else 10.0

            # 按照當前的縮放和攝像頭偏移量調整網格
            scaled_area_x = area_x * overall_scale + cam_offset_x
            scaled_area_y = area_y * overall_scale + cam_offset_y
            scaled_area_width = area_width * overall_scale
            scaled_area_height = area_height * overall_scale
            scaled_grid_cell_size = grid_cell_size * overall_scale

            # 嚴格限制網格在空間內部
            grid_cols = int(area_width / grid_cell_size)
            grid_rows = int(area_height / grid_cell_size)

            # 調整計算方式，確保網格不會超出空間
            effective_grid_width = grid_cols * grid_cell_size
            effective_grid_height = grid_rows * grid_cell_size

            # 確保網格不超出空間邊界
            if effective_grid_width > area_width:
                grid_cols -= 1
            if effective_grid_height > area_height:
                grid_rows -= 1

            # 繪製網格線（只在空間內部）
            scaled_effective_grid_width = effective_grid_width * overall_scale
            scaled_effective_grid_height = effective_grid_height * overall_scale
            
            # 存儲網格單元格，供路徑繪製時參考
            space_grid_cells = []
            
            # 繪製垂直網格線
            for col in range(grid_cols + 1):
                x_pos = scaled_area_x + col * scaled_grid_cell_size
                if x_pos <= scaled_area_x + scaled_area_width:  # 確保不超出右邊界
                    pygame.draw.line(
                        screen, 
                        GRID_COLOR, 
                        (x_pos, scaled_area_y), 
                        (x_pos, scaled_area_y + scaled_effective_grid_height), 
                        1
                    )

            # 繪製水平網格線
            for row in range(grid_rows + 1):
                y_pos = scaled_area_y + row * scaled_grid_cell_size
                if y_pos <= scaled_area_y + scaled_area_height:  # 確保不超出下邊界
                    pygame.draw.line(
                        screen, 
                        GRID_COLOR, 
                        (scaled_area_x, y_pos), 
                        (scaled_area_x + scaled_effective_grid_width, y_pos), 
                        1
                    )

            # 儲存網格單元格的位置和大小，供路徑繪製時參考
            for row in range(grid_rows):
                for col in range(grid_cols):
                    cell_rect = pygame.Rect(
                        scaled_area_x + col * scaled_grid_cell_size,
                        scaled_area_y + row * scaled_grid_cell_size,
                        scaled_grid_cell_size,
                        scaled_grid_cell_size
                    )
                    space_grid_cells.append((row, col, cell_rect))
                    
            all_grid_cells[space_name] = (area_x, area_y, area_width, area_height, grid_cell_size, space_grid_cells)
            all_grid_rects.append(pygame.Rect(scaled_area_x, scaled_area_y, scaled_area_width, scaled_area_height))

        # ========= 繪製NPC的路徑 (獨立的第二階段) =========
        path_drawn = False  # 跟踪是否成功绘制了路径
        
        # 檢查 active_npc 並嘗試獲取路徑
        if active_npc:
            print(f"DEBUG: 當前活動NPC: {getattr(active_npc, 'name', 'Unknown')}")
            
            # 檢查並嘗試各種可能的路徑屬性 (用於不同版本的代碼相容)
            path_attributes = ['detailed_path', 'path_to_follow', 'path']
            path_points_world = None
            used_attr = None
            
            for attr in path_attributes:
                if hasattr(active_npc, attr):
                    potential_path = getattr(active_npc, attr)
                    if potential_path and len(potential_path) >= 2:
                        path_points_world = potential_path
                        used_attr = attr
                        break
            
            # 如果上述路徑都找不到，但NPC有移動目標，則創建一個簡單的直線路徑
            if not path_points_world and hasattr(active_npc, 'move_target') and active_npc.move_target and hasattr(active_npc, 'position') and active_npc.position:
                # 創建一條從當前位置到移動目標的直線路徑
                path_points_world = [tuple(active_npc.position), tuple(active_npc.move_target)]
                used_attr = 'move_target (直線路徑)'
                print(f"DEBUG_PATH_DRAW: 為 NPC {active_npc.name} 從位置 {active_npc.position} 創建直線路徑到目標 {active_npc.move_target}")
            
            # 增加對避障目標的支持
            elif not path_points_world and hasattr(active_npc, 'position') and active_npc.position and hasattr(active_npc, 'avoiding_item_name') and active_npc.avoiding_item_name:
                # 如果有避障記錄，可以嘗試顯示避障路徑
                path_points_world = [tuple(active_npc.position)]
                
                # 如果有避障目標 (move_target) 且不為空
                if hasattr(active_npc, 'move_target') and active_npc.move_target:
                    path_points_world.append(tuple(active_npc.move_target))
                    
                # 如果還有原始目標 (original_move_target) 且不為空，增加到路徑中
                if hasattr(active_npc, 'original_move_target') and active_npc.original_move_target:
                    path_points_world.append(tuple(active_npc.original_move_target))
                    
                used_attr = f'避障路徑 (避開 {active_npc.avoiding_item_name})'
                print(f"DEBUG_PATH_DRAW: 為 NPC {active_npc.name} 創建避障路徑，點數: {len(path_points_world)}")
            
            if path_points_world:
                print(f"DEBUG_PATH_DRAW: NPC {active_npc.name} 繪製 '{used_attr}' 路徑，點數: {len(path_points_world)}")
                
                # 將世界座標轉換為螢幕座標
                path_points_screen = []
                for point in path_points_world:
                    # 確保點是可迭代的，並且有至少兩個元素
                    if hasattr(point, "__iter__") and len(tuple(point)) >= 2:
                        screen_x = point[0] * overall_scale + cam_offset_x
                        screen_y = point[1] * overall_scale + cam_offset_y
                        path_points_screen.append((screen_x, screen_y))
                
                if len(path_points_screen) >= 2:
                    # 使用漸變彩色繪製路徑線段
                    total_segments = len(path_points_screen) - 1
                    for i in range(total_segments):
                        # 計算此線段應有的顏色（漸變）
                        progress = i / max(1, total_segments - 1)  # 0.0 到 1.0
                        r = int(START_COLOR[0] + (END_COLOR[0] - START_COLOR[0]) * progress)
                        g = int(START_COLOR[1] + (END_COLOR[1] - START_COLOR[1]) * progress)
                        b = int(START_COLOR[2] + (END_COLOR[2] - START_COLOR[2]) * progress)
                        segment_color = (r, g, b)
                        
                        # 繪製此線段，使用彩虹漸變色
                        pygame.draw.line(
                            screen, 
                            segment_color,
                            path_points_screen[i],
                            path_points_screen[i + 1],
                            PATH_LINE_WIDTH
                        )
                        
                        # 在每段的開始繪製一個小圓點
                        pygame.draw.circle(
                            screen,
                            PATH_DOT_COLOR,  # 亮黃色圓點
                            (int(path_points_screen[i][0]), int(path_points_screen[i][1])),
                            PATH_DOT_RADIUS
                        )
                    
                    # 最後一個點也畫圓點
                    pygame.draw.circle(
                        screen,
                        PATH_DOT_COLOR,
                        (int(path_points_screen[-1][0]), int(path_points_screen[-1][1])),
                        PATH_DOT_RADIUS
                    )
                
                    # 在路徑起點和終點繪製特殊標記（更大、更醒目）
                    # 起點 - 青色圓圈，外圍白色邊框
                    pygame.draw.circle(
                        screen,
                        (255, 255, 255),  # 白色外圈
                        (int(path_points_screen[0][0]), int(path_points_screen[0][1])),
                        PATH_DOT_RADIUS + 6
                    )
                    pygame.draw.circle(
                        screen,
                        START_COLOR,  # 青色
                        (int(path_points_screen[0][0]), int(path_points_screen[0][1])),
                        PATH_DOT_RADIUS + 3
                    )
                    
                    # 終點 - 粉紅色圓圈，外圍白色邊框
                    pygame.draw.circle(
                        screen,
                        (255, 255, 255),  # 白色外圈
                        (int(path_points_screen[-1][0]), int(path_points_screen[-1][1])),
                        PATH_DOT_RADIUS + 6
                    )
                    pygame.draw.circle(
                        screen,
                        END_COLOR,  # 粉紅色
                        (int(path_points_screen[-1][0]), int(path_points_screen[-1][1])),
                        PATH_DOT_RADIUS + 3
                    )
                    
                    # 標記已成功繪製路徑
                    path_drawn = True
                else:
                    print(f"DEBUG: 路徑點轉換後數量不足: {len(path_points_screen)} (至少需要2個點)")
            else:
                print(f"DEBUG: NPC {getattr(active_npc, 'name', 'Unknown')} 沒有有效的路徑")
                
                # 用於調試：輸出 active_npc 具有的所有屬性
                if hasattr(active_npc, '__dict__'):
                    print(f"DEBUG: NPC 屬性: {dir(active_npc)}")
        
        # 顯示最終的路徑繪製狀態
        print(f"DEBUG: 處理了 {spaces_processed} 個空間，其中 {spaces_with_valid_area} 個有有效的區域資訊。路徑繪製狀態: {'成功' if path_drawn else '失敗'}")
        
        return all_grid_rects

    def ai_process():
        nonlocal last_ai_result, ai_thinking, ai_running, npc_threads
        
        # 如果已經在執行，則不啟動新的 (額外的保護)
        if ai_running:
            print("DEBUG: ai_process - AI process already running, skipping new request.") # MODIFIED
            return

        ai_running = True
        ai_thinking = True
        
        # 清理舊的執行緒引用 (主要為了列表乾淨)
        npc_threads.clear()
        
        active_threads_this_batch = [] # 儲存當前批次啟動的執行緒
        print("DEBUG: ai_process - Starting batch AI processing for NPCs...") # MODIFIED
        for i, npc_obj in enumerate(npcs): # 使用 npc_obj 避免與外層 npc 變數混淆
                npc_obj.is_thinking = True
                npc_obj.thinking_status = f"{npc_obj.name} 處理中..."
                
                def process_single_npc(npc_id, single_npc_ref):
                    try:
                        this_npc_name = single_npc_ref.name
                        print(f"DEBUG: process_single_npc (Thread {npc_id}, {this_npc_name}) - Starting process_tick()...") # MODIFIED
                        result = single_npc_ref.process_tick()
                        print(f"DEBUG: process_single_npc (Thread {npc_id}, {this_npc_name}) - process_tick() completed. Result: {str(result)[:50]}...") # MODIFIED
                        single_npc_ref.thinking_status = f"{this_npc_name}: {str(result)[:50]}" + ("..." if len(str(result)) > 50 else "") # MODIFIED (added str())
                        # print(f"執行緒 {npc_id}: 完成處理 {this_npc_name}: {result[:30]}...")

                    except Exception as e_single:
                        print(f"DEBUG: process_single_npc (Thread {npc_id}, {single_npc_ref.name}) - ERROR in process_tick(): {str(e_single)}") # MODIFIED
                        single_npc_ref.thinking_status = f"{single_npc_ref.name}: 處理失敗"
                    finally:
                        single_npc_ref.is_thinking = False # 確保 thinking 狀態被重置
                        print(f"DEBUG: process_single_npc (Thread {npc_id}, {single_npc_ref.name}) - Finished thread execution.") # MODIFIED
                
                t = threading.Thread(target=process_single_npc, args=(i, npc_obj))
                t.daemon = True
                active_threads_this_batch.append(t)
                t.start()
                print(f"DEBUG: ai_process - Launched thread {i} for {npc_obj.name}") # MODIFIED
        
        # 等待當前批次的所有NPC思考執行緒完成
        print("DEBUG: ai_process - All NPC thinking threads launched. Waiting for completion...") # MODIFIED
        for t_idx, t_join in enumerate(active_threads_this_batch): # MODIFIED to add t_idx
            npc_name_for_join = "UnknownNPC"
            if t_idx < len(npcs): # Check index bounds
                npc_name_for_join = npcs[t_idx].name
            print(f"DEBUG: ai_process - Attempting to join thread {t_idx} for {npc_name_for_join}...") # MODIFIED
            t_join.join() # 等待每個執行緒執行完畢
            print(f"DEBUG: ai_process - Successfully joined thread {t_idx} for {npc_name_for_join}.") # MODIFIED
        print("DEBUG: ai_process - All NPC thinking processes (process_tick) completed and threads joined.") # MODIFIED
        
        ai_thinking = False
        ai_running = False # AI 思考和 tick 處理階段結束
        print("DEBUG: ai_process - Batch AI processing finished. ai_running set to False.") # MODIFIED
        
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
        
        # 決定是否禁用「繼續」按鈕和相關觸發
        # 檢查是否有任何 NPC 正在移動
        any_npc_moving = False
        for npc_check in npcs: # 使用不同的變數名稱以避免混淆
            if hasattr(npc_check, 'move_target') and npc_check.move_target is not None:
                any_npc_moving = True
                break # 只要有一個正在移動就足夠了
        
        disable_continue_trigger = ai_running or any_npc_moving # 使用 any_npc_moving 來判斷整體移動狀態
        can_trigger_ai = not disable_continue_trigger

        # 這兩個變數在您的原始程式碼中似乎沒有被後續使用，如果確實不需要，可以考慮移除以簡化
        hovered_button = None 
        pressed_button = None 

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_c and active_npc and can_trigger_ai: # 使用 can_trigger_ai
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
                # 新增：K鍵切換碰撞區域顯示
                elif event.key == pygame.K_k:
                    show_collision_areas = not show_collision_areas
                    print(f"{'顯示' if show_collision_areas else '隱藏'}碰撞區域")
                elif event.key == pygame.K_w:
                    # 新增功能：處理「改變天氣和時間」按鈕
                    print(f"當前時間: {world_system.time}")
                    print(f"當前天氣: {world_system.weather}")

                    new_time = input("輸入新的時間 (直接按 Enter 保持不變): ").strip()
                    if new_time:
                        world_system.time = new_time

                    new_weather = input("輸入新的天氣 (直接按 Enter 保持不變): ").strip()
                    if new_weather:
                        world_system.weather = new_weather

                    print(f"更新後 - 時間: {world_system.time}, 天氣: {world_system.weather}")
                elif event.key == pygame.K_g: # 新增：切換路徑規劃網格顯示
                    show_pathfinding_debug = not show_pathfinding_debug
                    print(f"DEBUG: 路徑網格顯示已切換: {show_pathfinding_debug}")
                    if show_pathfinding_debug:
                        print(f"DEBUG: 路徑規劃器實例: {path_planner}")
                        if path_planner:
                            print(f"DEBUG: 路徑規劃器網格大小: {path_planner.grid_cell_size}")
                            print(f"DEBUG: 路徑規劃器 NPC 半徑: {path_planner.npc_radius}")
            elif event.type == pygame.MOUSEBUTTONDOWN:
                win_w, win_h = screen.get_size()
                button_w, button_h = 120, 44
                gap = 24
                total_w = len(button_labels) * (button_w + gap) - gap
                start_x = (win_w - total_w) // 2
                y = win_h - button_h - 24
                for i, (key_char, label) in enumerate(button_labels):
                    rect = pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)  # 判斷滑鼠是否在此按鈕上
                    is_hover = rect.collidepoint(mouse_pos)
                    
                    # MOUSEBUTTONDOWN 事件中的按鈕外觀設定 (主要用於即時反饋)
                    # 按鈕的持續外觀由主繪圖迴圈的底部邏輯處理
                    current_btn_color_event = (180, 180, 0) # 預設顏色
                    current_border_color_event = (80, 80, 0) # 預設邊框顏色
                    text_color_event = (0,0,0) # 預設文字顏色

                    if key_char == "c" and disable_continue_trigger:
                        current_btn_color_event = (150, 150, 150) # 禁用時的按鈕顏色
                        current_border_color_event = (100, 100, 100) # 禁用時的邊框顏色
                    elif is_hover and mouse_pressed: # 滑鼠在按鈕上且按鍵被按下
                        # 只有非禁用的按鈕才能顯示按下效果
                        if not (key_char == "c" and disable_continue_trigger):
                            current_btn_color_event = (255, 200, 60) # 按下時的顏色
                            current_border_color_event = (180, 120, 0) # 按下時的邊框顏色
                    elif is_hover: # 滑鼠僅在按鈕上懸停
                        # 只有非禁用的按鈕才能顯示懸停效果
                        if not (key_char == "c" and disable_continue_trigger):
                            current_btn_color_event = (255, 240, 120) # 懸停時的顏色
                            current_border_color_event = (200, 160, 0) # 懸停時的邊框顏色
                    
                    pygame.draw.rect(screen, current_btn_color_event, rect, border_radius=12)
                    pygame.draw.rect(screen, current_border_color_event, rect, 3, border_radius=12)
                    btn_text_surface_event = button_font.render(f"[{key_char.upper()}] {label}", True, text_color_event)
                    btn_text_rect_event = btn_text_surface_event.get_rect(center=rect.center)
                    screen.blit(btn_text_surface_event, btn_text_rect_event)

                    # 動作觸發
                    if rect.collidepoint(event.pos): # 使用 event.pos 判斷點擊位置
                        if key_char == "c" and active_npc and can_trigger_ai: # 使用 can_trigger_ai
                            ai_threading = threading.Thread(target=ai_process)
                            ai_threading.start()
                        if key_char == "e":
                            running = False
                        if key_char == "p":
                            history_menu(screen, font, active_npc)
                        if key_char == "s":
                            save_menu(screen, font, world, world.get('_file_path', None) or "worlds/maps/unnamed_save.json")
                        # 新增：處理「切換NPC」按鈕
                        if key_char == "n" and len(npcs) > 1:
                            new_active_npc = npc_selection_menu(screen, font, npcs, active_npc)
                            if new_active_npc and new_active_npc != active_npc:
                                active_npc = new_active_npc
                                last_ai_result = ""  # 清空上一個NPC的AI結果
                                # 輸出目前關注的NPC
                                print(f"========= 目前關注的NPC: {active_npc.name} ==========")
                        # 新增：處理「k」按鈕的功能
                        if key_char == "k":
                            # 切換顯示碰撞區域
                            show_collision_areas = not show_collision_areas
                            print(f"{'顯示' if show_collision_areas else '隱藏'}碰撞區域")
                        # 新增：處理「g」按鈕的功能
                        if key_char == "g":
                            # 切換路徑規劃網格顯示
                            show_pathfinding_debug = not show_pathfinding_debug
            elif event.type == pygame.MOUSEWHEEL: # 處理滑鼠滾輪事件
                if event.y > 0: # 向上滾動，放大
                    current_zoom_level += zoom_speed
                elif event.y < 0: # 向下滾動，縮小
                    current_zoom_level -= zoom_speed
                current_zoom_level = max(min_zoom, min(current_zoom_level, max_zoom)) # 限制縮放範圍

        # 每次主循環都同步 display_pos 與 position，並推進動畫移動
        # 在 NPC 移動更新之前，確保 calculated_doors 是最新的
        # --- 預先計算門的位置 (整合 TypeError 修復) --- (這段邏輯移到 NPC 移動更新之前，以確保 A* 可以使用最新的門信息)
        calculated_doors = [] # 儲存計算出的門的資訊
        space_map_for_doors = {s.name: s for s in spaces} # 空間名稱到物件的映射 (避免與全域 space_map 衝突)
        processed_space_pairs_for_doors = set() # 避免重複處理空間對

        for s1 in spaces:
            if not hasattr(s1, "connected_spaces") or not s1.connected_spaces or not hasattr(s1, "display_pos") or not hasattr(s1, "display_size") :
                continue
            for connected_item in s1.connected_spaces: # connected_item 可能是字串或 Space 物件
                s2_name = None
                if isinstance(connected_item, str): # 假設是字串
                    s2_name = connected_item    # 直接使用字串
                elif hasattr(connected_item, 'name'): # 假設是 Space 物件
                    s2_name = connected_item.name # 使用 Space 物件的 name 屬性
                else:
                    continue
                
                s2 = space_map_for_doors.get(s2_name)
                if not s2 or s1 == s2 or not hasattr(s2, "display_pos") or not hasattr(s2, "display_size"): # s2 不存在或 s2 就是 s1 自己，或s2缺少位置資訊
                    continue

                pair_key = tuple(sorted((s1.name, s2.name))) # 將空間名稱組成一個唯一的鍵
                if pair_key in processed_space_pairs_for_doors:
                    continue
                
                s1_rect_world = pygame.Rect(s1.display_pos[0], s1.display_pos[1], s1.display_size[0], s1.display_size[1])
                s2_rect_world = pygame.Rect(s2.display_pos[0], s2.display_pos[1], s2.display_size[0], s2.display_size[1])
                door_info = None
                
                # 檢查 s1 的右邊緣是否連接 s2 的左邊緣
                if abs(s1_rect_world.right - s2_rect_world.left) < CONNECTION_TOLERANCE_WORLD_UNITS:
                    overlap_y_start = max(s1_rect_world.top, s2_rect_world.top)
                    overlap_y_end = min(s1_rect_world.bottom, s2_rect_world.bottom)
                    if overlap_y_end - overlap_y_start >= DOOR_WIDTH_WORLD_UNITS:   # 門的寬度/高度 (開口大小)，世界座標系
                        door_center_y = (overlap_y_start + overlap_y_end) / 2
                        door_info = {
                            "s1_name": s1.name, "s2_name": s2.name, "type": "vertical",
                            "wall_x_world": s1_rect_world.right, 
                            "opening_start_world": door_center_y - DOOR_WIDTH_WORLD_UNITS / 2, 
                            "opening_end_world": door_center_y + DOOR_WIDTH_WORLD_UNITS / 2,   
                            "s1_edge_name": "right", "s2_edge_name": "left"
                        }
                # 檢查 s1 的左邊緣是否連接 s2 的右邊緣
                elif abs(s1_rect_world.left - s2_rect_world.right) < CONNECTION_TOLERANCE_WORLD_UNITS:
                    overlap_y_start = max(s1_rect_world.top, s2_rect_world.top)
                    overlap_y_end = min(s1_rect_world.bottom, s2_rect_world.bottom)
                    if overlap_y_end - overlap_y_start >= DOOR_WIDTH_WORLD_UNITS:
                        door_center_y = (overlap_y_start + overlap_y_end) / 2
                        door_info = {
                            "s1_name": s1.name, "s2_name": s2.name, "type": "vertical",
                            "wall_x_world": s1_rect_world.left,
                            "opening_start_world": door_center_y - DOOR_WIDTH_WORLD_UNITS / 2,
                            "opening_end_world": door_center_y + DOOR_WIDTH_WORLD_UNITS / 2,
                            "s1_edge_name": "left", "s2_edge_name": "right"
                        }
                # 檢查 s1 的下邊緣是否連接 s2 的上邊緣
                elif abs(s1_rect_world.bottom - s2_rect_world.top) < CONNECTION_TOLERANCE_WORLD_UNITS:
                    overlap_x_start = max(s1_rect_world.left, s2_rect_world.left)
                    overlap_x_end = min(s1_rect_world.right, s2_rect_world.right)
                    if overlap_x_end - overlap_x_start >= DOOR_WIDTH_WORLD_UNITS:
                        door_center_x = (overlap_x_start + overlap_x_end) / 2
                        door_info = {
                            "s1_name": s1.name, "s2_name": s2.name, "type": "horizontal",
                            "wall_y_world": s1_rect_world.bottom, 
                            "opening_start_world": door_center_x - DOOR_WIDTH_WORLD_UNITS / 2, 
                            "opening_end_world": door_center_x + DOOR_WIDTH_WORLD_UNITS / 2,   
                            "s1_edge_name": "bottom", "s2_edge_name": "top"
                        }
                # 檢查 s1 的上邊緣是否連接 s2 的下邊緣
                elif abs(s1_rect_world.top - s2_rect_world.bottom) < CONNECTION_TOLERANCE_WORLD_UNITS:
                    overlap_x_start = max(s1_rect_world.left, s2_rect_world.left)
                    overlap_x_end = min(s1_rect_world.right, s2_rect_world.right)
                    if overlap_x_end - overlap_x_start >= DOOR_WIDTH_WORLD_UNITS:
                        door_center_x = (overlap_x_start + overlap_x_end) / 2
                        door_info = {
                            "s1_name": s1.name, "s2_name": s2.name, "type": "horizontal",
                            "wall_y_world": s1_rect_world.top,
                            "opening_start_world": door_center_x - DOOR_WIDTH_WORLD_UNITS / 2,
                            "opening_end_world": door_center_x + DOOR_WIDTH_WORLD_UNITS / 2,
                            "s1_edge_name": "top", "s2_edge_name": "bottom"
                        }
                
                if door_info:
                    calculated_doors.append(door_info)
                    processed_space_pairs_for_doors.add(pair_key)
        # --- 預計算門結束 --- (calculated_doors 現在在此處更新)

        for npc in npcs:
            if npc.position is None: 
                npc.position = [0.0, 0.0]
            else:
                npc.position = [float(p) for p in npc.position]

            current_npc_space_name = npc.current_space.name if hasattr(npc, 'current_space') and npc.current_space and hasattr(npc.current_space, 'name') else None

            # --- A* Path Following Logic (largely unchanged, sets npc.move_target to doors/space centers) ---
            if hasattr(npc, 'current_path_segment_target_space_name') and npc.current_path_segment_target_space_name:
                # ... (Your existing A* segment target logic, lines 1118-1183 or similar) ...
                # This part should set npc.move_target to a door or space center if on an A* path
                # For brevity, I'm not reproducing all of it, but it should remain functional.
                target_segment_space_name = npc.current_path_segment_target_space_name
                target_space_obj = all_spaces_dict.get(target_segment_space_name)
                current_npc_actual_space = npc.current_space

                if target_space_obj and current_npc_actual_space and hasattr(current_npc_actual_space, 'name'):
                    if current_npc_actual_space.name != target_segment_space_name:
                        entry_door_to_target = None
                        for door_candidate in calculated_doors:
                            if ((door_candidate.get('s1_name') == current_npc_actual_space.name and door_candidate.get('s2_name') == target_segment_space_name) or
                                (door_candidate.get('s2_name') == current_npc_actual_space.name and door_candidate.get('s1_name') == target_segment_space_name)):
                                entry_door_to_target = door_candidate
                                break
                        if entry_door_to_target:
                            door_center_x, door_center_y = 0.0, 0.0
                            if entry_door_to_target['type'] == 'vertical':
                                door_center_x = float(entry_door_to_target['wall_x_world'])
                                door_center_y = float((entry_door_to_target['opening_start_world'] + entry_door_to_target['opening_end_world']) / 2)
                            elif entry_door_to_target['type'] == 'horizontal':
                                door_center_x = float((entry_door_to_target['opening_start_world'] + entry_door_to_target['opening_end_world']) / 2)
                                door_center_y = float(entry_door_to_target['wall_y_world'])
                            nudge_amount = 15.0
                            final_target_x, final_target_y = door_center_x, door_center_y
                            current_space_name_for_nudge = current_npc_actual_space.name
                            if entry_door_to_target.get('s1_name') == current_space_name_for_nudge and entry_door_to_target.get('s2_name') == target_segment_space_name:
                                s1_edge = entry_door_to_target.get('s1_edge_name')
                                if s1_edge == 'right': final_target_x += nudge_amount
                                elif s1_edge == 'left': final_target_x -= nudge_amount
                                elif s1_edge == 'bottom': final_target_y += nudge_amount
                                elif s1_edge == 'top': final_target_y -= nudge_amount
                            elif entry_door_to_target.get('s2_name') == current_space_name_for_nudge and entry_door_to_target.get('s1_name') == target_segment_space_name:
                                s2_edge = entry_door_to_target.get('s2_edge_name')
                                if s2_edge == 'right': final_target_x += nudge_amount
                                elif s2_edge == 'left': final_target_x -= nudge_amount
                                elif s2_edge == 'bottom': final_target_y += nudge_amount
                                elif s2_edge == 'top': final_target_y -= nudge_amount
                            npc.move_target = [final_target_x, final_target_y]
                        else:
                            if hasattr(target_space_obj, 'display_pos') and hasattr(target_space_obj, 'display_size'):
                                center_x = float(target_space_obj.display_pos[0] + target_space_obj.display_size[0] / 2)
                                center_y = float(target_space_obj.display_pos[1] + target_space_obj.display_size[1] / 2)
                                npc.move_target = [center_x, center_y]
                            else:
                                npc.move_target = None
                    else:
                        space_it_just_entered_obj = all_spaces_dict.get(npc.current_path_segment_target_space_name)
                        if space_it_just_entered_obj and hasattr(space_it_just_entered_obj, 'display_pos') and hasattr(space_it_just_entered_obj, 'display_size'):
                            center_x = float(space_it_just_entered_obj.display_pos[0] + space_it_just_entered_obj.display_size[0] / 2)
                            center_y = float(space_it_just_entered_obj.display_pos[1] + space_it_just_entered_obj.display_size[1] / 2)
                            npc.move_target = [center_x, center_y]
                        else:
                            npc.current_path_segment_target_space_name = None
                            if hasattr(npc, 'path_to_follow'): npc.path_to_follow = []
                            npc.move_target = None
                else:
                    npc.current_path_segment_target_space_name = None
                    if hasattr(npc, 'path_to_follow'): npc.path_to_follow = []
                    npc.move_target = None
            # --- A* Path Following Logic END ---

            if hasattr(npc, 'move_target') and npc.move_target:
                target_pos = [float(tp) for tp in npc.move_target] 

                if not isinstance(npc.position, list) or not all(isinstance(p, (float, int)) for p in npc.position):
                    print(f"DEBUG: ERROR - NPC {npc.name} has invalid position: {npc.position}. Skipping move.")
                    continue

                dx = target_pos[0] - npc.position[0]
                dy = target_pos[1] - npc.position[1]
                dist = math.hypot(dx, dy)
                
                current_move_speed = getattr(npc, 'move_speed', 1.0) 
                if current_move_speed <= 0: current_move_speed = 1.0 

                # --- Target Reached Logic --- 
                if dist < current_move_speed: # Use actual move speed as threshold
                    npc.position[0] = target_pos[0]
                    npc.position[1] = target_pos[1]
                    print(f"DEBUG: NPC {npc.name} REACHED {target_pos}. Current pos: {npc.position}")

                    reached_original_target_after_avoidance = False
                    if npc.avoiding_item_name and npc.original_move_target is None: # Was avoiding, and original_move_target was cleared (meaning it was set as current target)
                        # Check if current target_pos (which was reached) matches the _last_original_target
                        if hasattr(npc, '_last_original_target_x') and hasattr(npc, '_last_original_target_y') and \
                            abs(target_pos[0] - npc._last_original_target_x) < 0.1 and \
                            abs(target_pos[1] - npc._last_original_target_y) < 0.1:
                            reached_original_target_after_avoidance = True

                    if npc.avoiding_item_name and not reached_original_target_after_avoidance:
                        print(f"DEBUG: NPC {npc.name} reached AVOIDANCE waypoint for {npc.avoiding_item_name}. Original was {getattr(npc, 'original_move_target', 'None')}")
                        if hasattr(npc, 'original_move_target') and npc.original_move_target:
                            npc.move_target = list(npc.original_move_target) # Target original again
                            # Store the original target to check against when it's reached
                            npc._last_original_target_x = npc.original_move_target[0]
                            npc._last_original_target_y = npc.original_move_target[1]
                            npc.original_move_target = None # Clear it, as it's now the main target
                            print(f"DEBUG: NPC {npc.name} now targeting stored original: {npc.move_target}")
                        else:
                            # Reached an avoidance point, but no original target to go to. Clear avoidance.
                            print(f"DEBUG: NPC {npc.name} cleared avoidance for {npc.avoiding_item_name} (no original_move_target).")
                            npc.avoiding_item_name = None
                        npc.move_target = None
                        if hasattr(npc, '_last_original_target_x'): del npc._last_original_target_x
                        if hasattr(npc, '_last_original_target_y'): del npc._last_original_target_y
                    
                    elif reached_original_target_after_avoidance:
                        print(f"DEBUG: NPC {npc.name} successfully reached ORIGINAL target after avoiding {npc.avoiding_item_name}.")
                        npc.avoiding_item_name = None
                        npc.move_target = None
                        if hasattr(npc, '_last_original_target_x'): del npc._last_original_target_x
                        if hasattr(npc, '_last_original_target_y'): del npc._last_original_target_y
                    
                    else: # Reached a non-avoidance related target, or an original target directly
                        if npc.move_target: # If it was a direct original target reach
                            if hasattr(npc, '_last_original_target_x') and hasattr(npc, '_last_original_target_y') and \
                                abs(target_pos[0] - npc._last_original_target_x) < 0.1 and \
                                abs(target_pos[1] - npc._last_original_target_y) < 0.1:
                                print(f"DEBUG: NPC {npc.name} directly reached its original target.")
                                if hasattr(npc, '_last_original_target_x'): del npc._last_original_target_x
                                if hasattr(npc, '_last_original_target_y'): del npc._last_original_target_y
                        
                        npc.move_target = None 
                        if npc.original_move_target: npc.original_move_target = None
                        if npc.avoiding_item_name: npc.avoiding_item_name = None # Clear if any lingering state

                    # A* path advancement and interaction completion (only if move_target is now None)
                    if npc.move_target is None:
                        is_on_astar_path_and_active = hasattr(npc, 'current_path_segment_target_space_name') and npc.current_path_segment_target_space_name is not None
                        if is_on_astar_path_and_active:
                            current_segment_target_space_obj = all_spaces_dict.get(npc.current_path_segment_target_space_name)
                            if current_segment_target_space_obj and hasattr(current_segment_target_space_obj, 'display_pos') and hasattr(current_segment_target_space_obj, 'display_size'):
                                center_x_of_current_segment = float(current_segment_target_space_obj.display_pos[0] + current_segment_target_space_obj.display_size[0] / 2)
                                center_y_of_current_segment = float(current_segment_target_space_obj.display_pos[1] + current_segment_target_space_obj.display_size[1] / 2)
                                if abs(npc.position[0] - center_x_of_current_segment) < 1.0 and abs(npc.position[1] - center_y_of_current_segment) < 1.0: # 稍微放寬判斷條件
                                    print(f"DEBUG: NPC {npc.name} reached CENTER of A* segment: {npc.current_path_segment_target_space_name}")
                                if hasattr(npc, 'path_to_follow') and npc.path_to_follow:
                                    npc.current_path_segment_target_space_name = npc.path_to_follow.pop(0)
                                    print(f"DEBUG: NPC {npc.name} A* path advanced. New segment target: {npc.current_path_segment_target_space_name}. Remaining A* path: {npc.path_to_follow}")
                            else:
                                        print(f"DEBUG: NPC {npc.name} A* path COMPLETED. Final segment was: {npc.current_path_segment_target_space_name}")
                                        npc.current_path_segment_target_space_name = None # A* 路徑完成

                        elif npc.current_space and npc.current_path_segment_target_space_name and npc.current_space.name == npc.current_path_segment_target_space_name:
                                    # NPC 已經進入了 A* 路徑的當前目標空間 (current_path_segment_target_space_name)。
                                    # 但可能還未到達該空間的中心點。
                                    print(f"DEBUG: NPC {npc.name} is IN A* segment target space: {npc.current_space.name} (which is {npc.current_path_segment_target_space_name}). Advancing A* if possible.")
                                    if hasattr(npc, 'path_to_follow') and npc.path_to_follow:
                                        # 如果 A* 路徑中還有下一個空間，則推進 A* 路徑。
                                        npc.current_path_segment_target_space_name = npc.path_to_follow.pop(0)
                                        print(f"DEBUG: NPC {npc.name} A* path advanced WHILE IN SPACE. New segment target: {npc.current_path_segment_target_space_name}. Remaining A* path: {npc.path_to_follow}")
                                    elif not npc.path_to_follow: # path_to_follow 為空，表示當前空間就是最終目標
                                        print(f"DEBUG: NPC {npc.name} A* path COMPLETED (already in final space {npc.current_space.name}, which was target {npc.current_path_segment_target_space_name}).")
                                        npc.current_path_segment_target_space_name = None # A* 路徑完成
                                    # npc.move_target is already None, the A* path following logic (around L1520) will pick up the new
                                    # current_path_segment_target_space_name (if not None) and set a new precise move_target (door or center).

                        elif npc.current_path_segment_target_space_name: 
                                    # NPC 到達了某個點 (通常是門的微調點)，但其 current_space 記錄尚未更新為 A* 的目標空間。
                                    # 主要依賴後續的 "Update NPC's actual current_space" (L1839) 邏輯來處理基於物理位置的空間變更。
                                    # 這裡僅作日誌記錄，因為 move_target 為 None 會讓 A* path following logic (L1520) 重新評估。
                                    current_space_name_for_debug = npc.current_space.name if npc.current_space else "None"
                                    print(f"DEBUG: NPC {npc.name} at {npc.position} reached move_target. Current space: {current_space_name_for_debug}, A* target space: {npc.current_path_segment_target_space_name}. Awaiting space update or next A* target recalc.")
                                    # The "FORCE UPDATED current_space" logic previously here was removed as it could lead to premature A* advancement
                                    # if the physical space update (around L1839) hadn't occurred yet.
                                    # Relying on npc.move_target = None to re-trigger A* planning (L1520) with current state.

                        if hasattr(npc, 'waiting_interaction') and npc.waiting_interaction and npc.waiting_interaction.get('started', False):
                            interaction_result = npc.complete_interaction() 
                            if interaction_result: last_ai_result = interaction_result
                else:
                    # --- Normal Movement & Collision Detection --- 
                    effective_move_x = current_move_speed * dx / dist
                    effective_move_y = current_move_speed * dy / dist
                    
                    next_pos_x_candidate = npc.position[0] + effective_move_x
                    next_pos_y_candidate = npc.position[1] + effective_move_y
                    
                    npc_world_radius = npc.radius 
                    npc_next_rect_world = pygame.Rect(
                        next_pos_x_candidate - npc_world_radius,
                        next_pos_y_candidate - npc_world_radius,
                        2 * npc_world_radius,
                        2 * npc_world_radius
                    )

                    # --- Item Collision & Avoidance --- 
                    collided_item_this_step = None
                    current_space_obj_for_item_check = npc.current_space 
                    if current_space_obj_for_item_check and hasattr(current_space_obj_for_item_check, 'items'):
                        for item_obj in current_space_obj_for_item_check.items:
                            if not (hasattr(item_obj, 'position') and hasattr(item_obj, 'size') and item_obj.position and item_obj.size):
                                continue
                            
                            # Skip collision check if this item is the interaction target
                            if hasattr(npc, 'waiting_interaction') and npc.waiting_interaction and npc.waiting_interaction.get("item_name") == item_obj.name:
                                continue
                            
                            # Skip if already avoiding this item AND still moving towards an avoidance waypoint (original_move_target is set)
                            if npc.avoiding_item_name == item_obj.name and npc.original_move_target is not None:
                                continue

                            item_rect_check = pygame.Rect(item_obj.position[0], item_obj.position[1], item_obj.size[0], item_obj.size[1])
                            if npc_next_rect_world.colliderect(item_rect_check):
                                collided_item_this_step = item_obj
                                break
                            
                    if collided_item_this_step:
                        print(f"DEBUG: NPC {npc.name} predicted collision with {collided_item_this_step.name}")
                        if npc.avoiding_item_name != collided_item_this_step.name: # New collision or re-collision after trying original target
                            if npc.move_target:
                                npc.original_move_target = list(npc.move_target) # Store current main target
                                npc._last_original_target_x = npc.original_move_target[0]
                                npc._last_original_target_y = npc.original_move_target[1]
                            npc.avoiding_item_name = collided_item_this_step.name

                        item_center_x = collided_item_this_step.position[0] + collided_item_this_step.size[0] / 2
                        item_center_y = collided_item_this_step.position[1] + collided_item_this_step.size[1] / 2
                        vec_npc_to_item_x = item_center_x - npc.position[0]
                        vec_npc_to_item_y = item_center_y - npc.position[1]

                        # Try to find a clear perpendicular direction
                        # This is a simplified avoidance, could be made more robust
                        perp_x_option1 = -vec_npc_to_item_y
                        perp_y_option1 = vec_npc_to_item_x
                        perp_x_option2 = vec_npc_to_item_y
                        perp_y_option2 = -vec_npc_to_item_x

                        avoid_dist_factor = npc_world_radius + max(collided_item_this_step.size[0], collided_item_this_step.size[1]) / 2 + 20.0 # Increased buffer
                        
                        # Normalize and scale perpendicular vectors
                        len_perp1 = math.hypot(perp_x_option1, perp_y_option1)
                        if len_perp1 > 1e-6 : 
                            avoid_target1_x = npc.position[0] + (perp_x_option1 / len_perp1) * avoid_dist_factor
                            avoid_target1_y = npc.position[1] + (perp_y_option1 / len_perp1) * avoid_dist_factor
                        else: # Should not happen if vec_npc_to_item is non-zero
                            avoid_target1_x, avoid_target1_y = npc.position[0], npc.position[1]

                        len_perp2 = math.hypot(perp_x_option2, perp_y_option2)
                        if len_perp2 > 1e-6:
                            avoid_target2_x = npc.position[0] + (perp_x_option2 / len_perp2) * avoid_dist_factor
                            avoid_target2_y = npc.position[1] + (perp_y_option2 / len_perp2) * avoid_dist_factor
                        else:
                            avoid_target2_x, avoid_target2_y = npc.position[0], npc.position[1]
                        
                        # Simplistic choice: alternate or pick one. A better way would be to check if these points are clear.
                        # For now, let's try the one further from the item center, or alternate.
                        if not hasattr(npc, '_last_avoid_choice') or npc._last_avoid_choice == 1:
                            npc.move_target = [avoid_target1_x, avoid_target1_y]
                            npc._last_avoid_choice = 2
                        else: 
                            npc.move_target = [avoid_target2_x, avoid_target2_y]
                            npc._last_avoid_choice = 1

                        print(f"DEBUG: NPC {npc.name} NEW AVOIDANCE TARGET: {npc.move_target} for {npc.avoiding_item_name}")
                        
                        # Recalculate movement based on new avoidance target for this frame
                        dx = npc.move_target[0] - npc.position[0]
                        dy = npc.move_target[1] - npc.position[1]
                        dist = math.hypot(dx, dy)
                        if dist > 1e-6:
                            effective_move_x = current_move_speed * dx / dist
                            effective_move_y = current_move_speed * dy / dist
                        else:
                            effective_move_x = 0
                            effective_move_y = 0
                            next_pos_x_candidate = npc.position[0] + effective_move_x
                            next_pos_y_candidate = npc.position[1] + effective_move_y
                    # --- Item Collision END ---

                    # --- Wall Collision (uses the potentially updated next_pos_x/y_candidate) --- 
                    can_move_x = True
                    can_move_y = True
                    npc_try_x_rect_world = pygame.Rect(next_pos_x_candidate - npc_world_radius, npc.position[1] - npc_world_radius, 2 * npc_world_radius, 2 * npc_world_radius)
                    npc_try_y_rect_world = pygame.Rect(npc.position[0] - npc_world_radius, next_pos_y_candidate - npc_world_radius, 2 * npc_world_radius, 2 * npc_world_radius)
                    current_space_obj_for_wall_check = npc.current_space # Use the most up-to-date current_space

                    if current_space_obj_for_wall_check and hasattr(current_space_obj_for_wall_check, 'display_pos') and hasattr(current_space_obj_for_wall_check, 'display_size'):
                        space_rect_for_walls = pygame.Rect(
                            current_space_obj_for_wall_check.display_pos[0], current_space_obj_for_wall_check.display_pos[1],
                            current_space_obj_for_wall_check.display_size[0], current_space_obj_for_wall_check.display_size[1]
                        )
                        
                        allow_exit_via_astar_path = False
                        if hasattr(npc, 'current_path_segment_target_space_name') and \
                            npc.current_path_segment_target_space_name and \
                            npc.current_space and \
                            hasattr(npc.current_space, 'name') and \
                            npc.current_path_segment_target_space_name != npc.current_space.name:
                            
                            target_is_connected_via_door = False
                            for door_info_check in calculated_doors:
                                if (door_info_check.get('s1_name') == npc.current_space.name and door_info_check.get('s2_name') == npc.current_path_segment_target_space_name) or \
                                    (door_info_check.get('s2_name') == npc.current_space.name and door_info_check.get('s1_name') == npc.current_path_segment_target_space_name):
                                    target_is_connected_via_door = True
                                    break
                            if target_is_connected_via_door:
                                allow_exit_via_astar_path = True
                        
                        # Check X movement
                        if not space_rect_for_walls.contains(npc_try_x_rect_world): # If NPC's next X step is outside current space boundaries
                            if allow_exit_via_astar_path and npc.move_target:
                                # If moving towards the A* target's X coordinate, allow exit.
                                if (effective_move_x < 0 and npc.move_target[0] < space_rect_for_walls.left - 1e-6) or \
                                    (effective_move_x > 0 and npc.move_target[0] > space_rect_for_walls.right + 1e-6):
                                    pass # can_move_x remains True, allowing exit
                                else:
                                    # Exiting, but not towards the A* target's X direction relative to space edge
                                    can_move_x = False 
                            else:
                                # Not on A* path to exit, or no move_target; apply standard wall collision
                                # This part of the original logic was already checking specific edge collision:
                                if ((next_pos_x_candidate - npc_world_radius < space_rect_for_walls.left and effective_move_x < 0) or \
                                    (next_pos_x_candidate + npc_world_radius > space_rect_for_walls.right and effective_move_x > 0)):
                                        can_move_x = False
                        
                        # Check Y movement
                        if not space_rect_for_walls.contains(npc_try_y_rect_world): # If NPC's next Y step is outside current space boundaries
                            if allow_exit_via_astar_path and npc.move_target:
                                # If moving towards the A* target's Y coordinate, allow exit.
                                if (effective_move_y < 0 and npc.move_target[1] < space_rect_for_walls.top - 1e-6) or \
                                    (effective_move_y > 0 and npc.move_target[1] > space_rect_for_walls.bottom + 1e-6):
                                    pass # can_move_y remains True, allowing exit
                                else:
                                    # Exiting, but not towards the A* target's Y direction relative to space edge
                                    can_move_y = False
                            else:
                                # Not on A* path to exit, or no move_target; apply standard wall collision
                                # This part of the original logic was already checking specific edge collision:
                                if ((next_pos_y_candidate - npc_world_radius < space_rect_for_walls.top and effective_move_y < 0) or \
                                    (next_pos_y_candidate + npc_world_radius > space_rect_for_walls.bottom and effective_move_y > 0)):
                                        can_move_y = False
                    # --- Wall Collision END ---
                    
                    # --- Final Movement Update --- 
                    if can_move_x:
                        npc.position[0] = next_pos_x_candidate
                    else:
                        print(f"DEBUG: NPC {npc.name} X-move blocked by wall. Target was {npc.move_target}")

                    if can_move_y:
                        npc.position[1] = next_pos_y_candidate
                    else:
                        print(f"DEBUG: NPC {npc.name} Y-move blocked by wall. Target was {npc.move_target}")
                    
                    if not can_move_x and not can_move_y and collided_item_this_step:
                        print(f"DEBUG: NPC {npc.name} FULLY STUCK by {collided_item_this_step.name} and/or walls. Pos: {npc.position}")
                        # Consider clearing avoidance if fully stuck to allow AI to replan
                        # npc.avoiding_item_name = None
                        # npc.original_move_target = None
                        # npc.move_target = None
            
            # Update display_pos and NPC's current actual space (largely unchanged)
            if npc.position is not None:
                npc.display_pos = [int(p) for p in npc.position]

            # --- Update NPC's actual current_space based on position (Your lines 1520-1590) ---
            if npc.position is not None:
                npc_rect_world_for_space_update = pygame.Rect(
                    npc.position[0] - getattr(npc, 'radius', 10),
                    npc.position[1] - getattr(npc, 'radius', 10),
                    getattr(npc, 'radius', 10) * 2,
                    getattr(npc, 'radius', 10) * 2
                )
                npc_center_point_for_space_update = (npc.position[0], npc.position[1])
                current_space_name_before_update = getattr(npc.current_space, 'name', None) if hasattr(npc, 'current_space') else None
                
                found_new_space_for_npc = False
                # Check current space first for optimization
                if hasattr(npc, 'current_space') and npc.current_space and \
                    hasattr(npc.current_space, 'display_pos') and hasattr(npc.current_space, 'display_size'):
                    current_space_rect_check = pygame.Rect(
                        npc.current_space.display_pos[0], npc.current_space.display_pos[1],
                        npc.current_space.display_size[0], npc.current_space.display_size[1]
                    )
                    if current_space_rect_check.collidepoint(npc_center_point_for_space_update):
                        found_new_space_for_npc = True # Still in the same space
                    
                if not found_new_space_for_npc:
                    for space_name_iter, space_obj_iter in all_spaces_dict.items():
                        if not hasattr(space_obj_iter, 'display_pos') or not hasattr(space_obj_iter, 'display_size'):
                            continue
                        space_rect_iter = pygame.Rect(
                            space_obj_iter.display_pos[0], space_obj_iter.display_pos[1],
                            space_obj_iter.display_size[0], space_obj_iter.display_size[1]
                        )
                        if space_rect_iter.collidepoint(npc_center_point_for_space_update):
                            if current_space_name_before_update != space_name_iter:
                                if hasattr(npc, 'current_space') and npc.current_space and hasattr(npc.current_space, 'npcs') and npc in npc.current_space.npcs:
                                    npc.current_space.npcs.remove(npc)
                                npc.current_space = space_obj_iter
                                if npc not in space_obj_iter.npcs: space_obj_iter.npcs.append(npc)
                                print(f"DEBUG: NPC {npc.name} SPACE UPDATE (pos) - from {current_space_name_before_update} to {space_name_iter}")
                            found_new_space_for_npc = True
                        break
                
                if not found_new_space_for_npc and npc.current_path_segment_target_space_name:
                    # 特殊處理：在門的位置且正在走 A* 路徑
                    for door in calculated_doors:
                        door_rect_for_space_update = None
                        # 計算門區域
                        if door["type"] == "vertical":
                            # 垂直門 (在左右邊牆上)
                            padding = 10.0  # 增加一些寬度讓門區域更容易被偵測到
                            door_rect_for_space_update = pygame.Rect(
                                door["wall_x_world"] - padding, 
                                door["opening_start_world"],
                                padding * 2,  # 2倍 padding 作為寬度
                                door["opening_end_world"] - door["opening_start_world"]
                            )
                        elif door["type"] == "horizontal":
                            # 水平門 (在上下邊牆上)
                            padding = 10.0
                            door_rect_for_space_update = pygame.Rect(
                                door["opening_start_world"],
                                door["wall_y_world"] - padding,
                                door["opening_end_world"] - door["opening_start_world"],
                                padding * 2
                            )
                        
                        # 檢查 NPC 是否在門區域，並且門連接到 NPC 正在前往的目標空間
                        if door_rect_for_space_update and door_rect_for_space_update.colliderect(npc_rect_world_for_space_update) and \
                            npc.current_path_segment_target_space_name in [door.get('s1_name'), door.get('s2_name')]:
                            target_space_obj_on_door = all_spaces_dict.get(npc.current_path_segment_target_space_name)
                            if target_space_obj_on_door and npc.current_space != target_space_obj_on_door:
                                # 更新 NPC 的當前空間
                                if hasattr(npc, 'current_space') and npc.current_space and hasattr(npc.current_space, 'npcs'):
                                    if npc in npc.current_space.npcs:
                                        npc.current_space.npcs.remove(npc)
                                npc.current_space = target_space_obj_on_door
                                if hasattr(target_space_obj_on_door, 'npcs') and npc not in target_space_obj_on_door.npcs:
                                    target_space_obj_on_door.npcs.append(npc)
                                print(f"DEBUG: NPC {npc.name} SPACE UPDATE (door) - from {current_space_name_before_update} to {target_space_obj_on_door.name}")
                                found_new_space_for_npc = True
                                break
            # --- End NPC Current Space Update ---

        # 滑鼠控制視角移動邏輯
        pan_mouse_x, pan_mouse_y = pygame.mouse.get_pos()
        win_w_for_pan, win_h_for_pan = screen.get_size()

        if pan_mouse_x < edge_margin:
            camera_offset_x += panning_speed
        elif pan_mouse_x > win_w_for_pan - edge_margin:
            camera_offset_x -= panning_speed

        if pan_mouse_y < edge_margin:
            camera_offset_y += panning_speed
        elif pan_mouse_y > win_h_for_pan - edge_margin:
            camera_offset_y -= panning_speed

        # 根據視窗大小計算縮放比例
        win_w, win_h = screen.get_size()
        # 防止 map_w 或 map_h 為 0
        safe_map_w = map_w if map_w != 0 else 1
        safe_map_h = map_h if map_h != 0 else 1

        # 根據縮放級別調整有效地圖尺寸
        effective_map_w = safe_map_w / current_zoom_level
        effective_map_h = safe_map_h / current_zoom_level

        scale_x = win_w / effective_map_w
        scale_y = win_h / effective_map_h
        scale = min(scale_x, scale_y)
        
        # 計算基礎位移 (用於置中等，使用包含縮放的 scale)
        base_offset_x = (win_w - safe_map_w * scale) // 2
        base_offset_y = (win_h - safe_map_h * scale) // 2

        # 攝影機邊界限制 (Clamping)
        scaled_map_width = safe_map_w * scale # 實際渲染的地圖寬度
        scaled_map_height = safe_map_h * scale # 實際渲染的地圖高度

        if scaled_map_width > win_w:
            min_cam_x = win_w - scaled_map_width - base_offset_x
            max_cam_x = -base_offset_x
            camera_offset_x = max(min_cam_x, min(camera_offset_x, max_cam_x))
        else:
            camera_offset_x = 0 # 地圖比視窗窄或一樣寬，則不進行水平平移，保持居中

        if scaled_map_height > win_h:
            min_cam_y = win_h - scaled_map_height - base_offset_y
            max_cam_y = -base_offset_y
            camera_offset_y = max(min_cam_y, min(camera_offset_y, max_cam_y))
        else:
            camera_offset_y = 0 # 地圖比視窗矮或一樣高，則不進行垂直平移，保持居中

        # 計算最終繪圖位移 (加入攝影機位移)
        final_draw_offset_x = base_offset_x + camera_offset_x
        final_draw_offset_y = base_offset_y + camera_offset_y

        # 繪製背景
        screen.fill((230, 230, 250))  # 淡藍紫色背景

        # --- 繪製空間的牆壁和連接 ---
        # (這部分程式碼參考之前的版本，確保牆壁繪製正確)
        # 首先計算牆壁和門的螢幕座標
        for space in spaces:
            px, py = space.display_pos
            sx, sy = space.display_size
            rect = pygame.Rect(
                int(px*scale + final_draw_offset_x), int(py*scale + final_draw_offset_y),
                int(sx*scale), int(sy*scale)
            )
            pygame.draw.rect(screen, (200,200,220), rect, border_radius=18)
            
            # 顯示空間碰撞邊緣
            if show_collision_areas:
                collision_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                collision_surface.fill(SPACE_COLLISION_COLOR)
                pygame.draw.rect(collision_surface, (255, 0, 0, 180), collision_surface.get_rect(), 3)  # 紅色邊框
                screen.blit(collision_surface, rect.topleft)

        # --- 修改後的牆壁繪製邏輯 --- 
        wall_thickness_scaled = int(max(1, WALL_THICKNESS_WORLD_UNITS * scale))
        door_frame_thickness_scaled = int(max(1, DOOR_FRAME_THICKNESS_WORLD_UNITS * scale))

        for current_space in spaces: # 使用 current_space 避免命名衝突
            # 定義 current_space 的四條邊的資訊 (世界座標)
            space_edges_world = {
                "top":    {"fixed_coord": current_space.display_pos[1], "start_main_axis": current_space.display_pos[0], "end_main_axis": current_space.display_pos[0] + current_space.display_size[0], "orient": "h"},
                "bottom": {"fixed_coord": current_space.display_pos[1] + current_space.display_size[1], "start_main_axis": current_space.display_pos[0], "end_main_axis": current_space.display_pos[0] + current_space.display_size[0], "orient": "h"},
                "left":   {"fixed_coord": current_space.display_pos[0], "start_main_axis": current_space.display_pos[1], "end_main_axis": current_space.display_pos[1] + current_space.display_size[1], "orient": "v"},
                "right":  {"fixed_coord": current_space.display_pos[0] + current_space.display_size[0], "start_main_axis": current_space.display_pos[1], "end_main_axis": current_space.display_pos[1] + current_space.display_size[1], "orient": "v"}
            }

            for edge_name, edge_details in space_edges_world.items():
                # 獲取在這條特定邊上的所有門，並按開口位置排序
                doors_on_this_edge = []
                for door in calculated_doors:
                    if (door["s1_name"] == current_space.name and door["s1_edge_name"] == edge_name) or \
                        (door["s2_name"] == current_space.name and door["s2_edge_name"] == edge_name):
                        # 確保門的類型與邊的方向匹配
                        if (door["type"] == "horizontal" and edge_details["orient"] == "h") or \
                            (door["type"] == "vertical" and edge_details["orient"] == "v"):
                            doors_on_this_edge.append(door)
                doors_on_this_edge.sort(key=lambda d: d["opening_start_world"]) 

                # 開始繪製牆壁段
                current_pos_on_edge = edge_details["start_main_axis"] # 游標，沿著邊的主軸移動

                for door in doors_on_this_edge:
                    door_start = door["opening_start_world"]
                    door_end = door["opening_end_world"]

                    # 繪製門前的那段牆 (如果有的話)
                    if door_start > current_pos_on_edge:
                        if edge_details["orient"] == "h": # 水平牆
                            p1_world = (current_pos_on_edge, edge_details["fixed_coord"])
                            p2_world = (door_start, edge_details["fixed_coord"])
                        else: # 垂直牆
                            p1_world = (edge_details["fixed_coord"], current_pos_on_edge)
                            p2_world = (edge_details["fixed_coord"], door_start)
                        
                        p1_screen = (int(p1_world[0] * scale + final_draw_offset_x), int(p1_world[1] * scale + final_draw_offset_y))
                        p2_screen = (int(p2_world[0] * scale + final_draw_offset_x), int(p2_world[1] * scale + final_draw_offset_y))
                        if p1_screen != p2_screen: pygame.draw.line(screen, WALL_COLOR, p1_screen, p2_screen, wall_thickness_scaled)
                    
                    current_pos_on_edge = max(current_pos_on_edge, door_end) # 移動游標到門的結束位置之後
                
                # 繪製最後一個門之後 (或者如果沒有門，則是整條邊) 的那段牆
                if current_pos_on_edge < edge_details["end_main_axis"]:
                    if edge_details["orient"] == "h":
                        p1_world = (current_pos_on_edge, edge_details["fixed_coord"])
                        p2_world = (edge_details["end_main_axis"], edge_details["fixed_coord"])
                    else:
                        p1_world = (edge_details["fixed_coord"], current_pos_on_edge)
                        p2_world = (edge_details["fixed_coord"], edge_details["end_main_axis"])

                    p1_screen = (int(p1_world[0] * scale + final_draw_offset_x), int(p1_world[1] * scale + final_draw_offset_y))
                    p2_screen = (int(p2_world[0] * scale + final_draw_offset_x), int(p2_world[1] * scale + final_draw_offset_y))
                    if p1_screen != p2_screen: pygame.draw.line(screen, WALL_COLOR, p1_screen, p2_screen, wall_thickness_scaled)

        # --- 單獨繪製門 (確保門在牆和空間背景之上) ---
        if calculated_doors: # 只有在實際計算出門的情況下才嘗試繪製
            for door in calculated_doors:
                if door["type"] == "vertical":
                    # 門的中心X是牆的X，開口是Y方向
                    center_x_world = door["wall_x_world"]
                    opening_start_y_world = door["opening_start_world"]
                    opening_end_y_world = door["opening_end_world"]
                    
                    # 門的視覺矩形 (填充部分)
                    door_fill_rect_world = pygame.Rect(
                        center_x_world - WALL_THICKNESS_WORLD_UNITS / 2, # 門的填充與牆同厚，並居中於牆線
                        opening_start_y_world,
                        WALL_THICKNESS_WORLD_UNITS,
                        opening_end_y_world - opening_start_y_world
                    )
                    door_fill_rect_screen = pygame.Rect(
                        int(door_fill_rect_world.left * scale + final_draw_offset_x),
                        int(door_fill_rect_world.top * scale + final_draw_offset_y),
                        int(door_fill_rect_world.width * scale),
                        int(door_fill_rect_world.height * scale)
                    )
                    if door_fill_rect_screen.width > 0 and door_fill_rect_screen.height > 0:
                        s = pygame.Surface((door_fill_rect_screen.width, door_fill_rect_screen.height), pygame.SRCALPHA)
                        s.fill(DOOR_COLOR)
                        screen.blit(s, door_fill_rect_screen.topleft)

                    # 門框 (繪製在門填充矩形的兩側)
                    frame_offset_screen = door_frame_thickness_scaled // 2
                    # 左門框 (緊貼填充矩形的左邊)
                    p1_frame_left_screen = (door_fill_rect_screen.left - frame_offset_screen, door_fill_rect_screen.top)
                    p2_frame_left_screen = (door_fill_rect_screen.left - frame_offset_screen, door_fill_rect_screen.bottom)
                    if door_frame_thickness_scaled > 0: pygame.draw.line(screen, DOOR_FRAME_COLOR, p1_frame_left_screen, p2_frame_left_screen, door_frame_thickness_scaled)
                    # 右門框 (緊貼填充矩形的右邊)
                    p1_frame_right_screen = (door_fill_rect_screen.right + frame_offset_screen -1, door_fill_rect_screen.top) # -1 避免因取整導致偏移
                    p2_frame_right_screen = (door_fill_rect_screen.right + frame_offset_screen -1, door_fill_rect_screen.bottom)
                    if door_frame_thickness_scaled > 0: pygame.draw.line(screen, DOOR_FRAME_COLOR, p1_frame_right_screen, p2_frame_right_screen, door_frame_thickness_scaled)

                elif door["type"] == "horizontal":
                    center_y_world = door["wall_y_world"]
                    opening_start_x_world = door["opening_start_world"]
                    opening_end_x_world = door["opening_end_world"]

                    door_fill_rect_world = pygame.Rect(
                        opening_start_x_world,
                        center_y_world - WALL_THICKNESS_WORLD_UNITS / 2,
                        opening_end_x_world - opening_start_x_world,
                        WALL_THICKNESS_WORLD_UNITS
                    )
                    door_fill_rect_screen = pygame.Rect(
                        int(door_fill_rect_world.left * scale + final_draw_offset_x),
                        int(door_fill_rect_world.top * scale + final_draw_offset_y),
                        int(door_fill_rect_world.width * scale),
                        int(door_fill_rect_world.height * scale)
                    )
                    if door_fill_rect_screen.width > 0 and door_fill_rect_screen.height > 0:
                        s = pygame.Surface((door_fill_rect_screen.width, door_fill_rect_screen.height), pygame.SRCALPHA)
                        s.fill(DOOR_COLOR)
                        screen.blit(s, door_fill_rect_screen.topleft)

                    frame_offset_screen = door_frame_thickness_scaled // 2
                    # 上門框
                    p1_frame_top_screen = (door_fill_rect_screen.left, door_fill_rect_screen.top - frame_offset_screen)
                    p2_frame_top_screen = (door_fill_rect_screen.right, door_fill_rect_screen.top - frame_offset_screen)
                    if door_frame_thickness_scaled > 0: pygame.draw.line(screen, DOOR_FRAME_COLOR, p1_frame_top_screen, p2_frame_top_screen, door_frame_thickness_scaled)
                    # 下門框
                    p1_frame_bottom_screen = (door_fill_rect_screen.left, door_fill_rect_screen.bottom + frame_offset_screen -1)
                    p2_frame_bottom_screen = (door_fill_rect_screen.right, door_fill_rect_screen.bottom + frame_offset_screen -1)
                    if door_frame_thickness_scaled > 0: pygame.draw.line(screen, DOOR_FRAME_COLOR, p1_frame_bottom_screen, p2_frame_bottom_screen, door_frame_thickness_scaled)

        # 新增：繪製空間名稱 (確保在牆壁和門之上)
        for space in spaces:
            px, py = space.display_pos
            sx, sy = space.display_size
            space_screen_rect = pygame.Rect( # 計算空間在螢幕上的矩形
                int(px*scale + final_draw_offset_x), int(py*scale + final_draw_offset_y),
                int(sx*scale), int(sy*scale)
            )
            text = font.render(space.name, True, (40,40,40))
            screen.blit(text, (space_screen_rect.x+8, space_screen_rect.y+8)) # 在矩形左上角繪製名稱

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
            
            draw_item(screen, item, ipos, scale, final_draw_offset_x, final_draw_offset_y, font)
            
            # 顯示物品碰撞邊緣
            if show_collision_areas and hasattr(item, "size") and item.size:
                item_rect = pygame.Rect(
                    int(ipos[0] * scale + final_draw_offset_x),
                    int(ipos[1] * scale + final_draw_offset_y),
                    int(item.size[0] * scale),
                    int(item.size[1] * scale)
                )
                # Check line near 2183 - add size check before creating collision surface
                # 檢查並限制碰撞表面大小，避免記憶體溢出
                max_surface_size = 2000  # 設定最大表面尺寸限制
                safe_width = min(item_rect.width, max_surface_size)
                safe_height = min(item_rect.height, max_surface_size)
                
                # 使用緩存函數獲取碰撞表面
                collision_surface = get_collision_surface(
                    item_rect.width, 
                    item_rect.height, 
                    ITEM_COLLISION_COLOR, 
                    border_color=(0, 255, 0, 180)
                )
                screen.blit(collision_surface, item_rect.topleft)

        # 畫 NPC
        for npc in npcs:
            px, py = npc.display_pos
            draw_x = int(px * scale + final_draw_offset_x)
            draw_y = int(py * scale + final_draw_offset_y)
            pygame.draw.circle(screen, npc.display_color, (draw_x, draw_y), int(npc.radius * scale))
            npc_text = font.render(npc.name, True, (0,0,0))
            screen.blit(npc_text, (draw_x-16, draw_y-int(npc.radius*scale)-10))
            
            # 顯示 NPC 碰撞邊緣
            if show_collision_areas:
                npc_collision_rect = pygame.Rect(
                    draw_x - int(npc.radius * scale),
                    draw_y - int(npc.radius * scale),
                    int(npc.radius * scale * 2),
                    int(npc.radius * scale * 2)
                )
                collision_surface = pygame.Surface((npc_collision_rect.width, npc_collision_rect.height), pygame.SRCALPHA)
                collision_surface.fill(NPC_COLLISION_COLOR)
                pygame.draw.rect(collision_surface, (0, 0, 255, 180), collision_surface.get_rect(), 3)  # 藍色邊框
                screen.blit(collision_surface, npc_collision_rect.topleft)
                
            # 聊天氣泡 - 移到循環內部，確保每個 NPC 都有氣泡
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
        for i, (key_char, label) in enumerate(button_labels):
            rect = pygame.Rect(start_x + i * (button_w + gap), y, button_w, button_h)
            is_hover = rect.collidepoint(mouse_pos)
            
            is_this_button_pressed = False
            # 判斷按鈕是否真的被按下 (考慮滑鼠狀態和按鈕是否可被觸發)
            if mouse_pressed and is_hover:
                if key_char == "c": # 對於'繼續'按鈕
                    if can_trigger_ai: # 只有在可以觸發AI時才算按下
                        is_this_button_pressed = True
                else: # 其他按鈕總是可被按下
                    is_this_button_pressed = True
            
            current_btn_color = (180, 180, 0)  # 預設按鈕顏色
            current_border_color = (80, 80, 0) # 預設邊框顏色
            current_text_color = (0,0,0)      # 預設文字顏色

            if key_char == "c" and disable_continue_trigger: # "繼續"按鈕在 AI 執行或 NPC 移動時的禁用狀態
                current_btn_color = (150, 150, 150)    # 灰色表示禁用
                current_border_color = (100, 100, 100) # 禁用時的邊框顏色
                current_text_color = (80,80,80)     # 文字也變灰
            elif is_this_button_pressed: # 按鈕被按下時的狀態
                current_btn_color = (255, 200, 60)  # 按下時的顏色
                current_border_color = (180, 120, 0) # 按下時的邊框顏色
            elif is_hover: # 滑鼠懸停在按鈕上時的狀態
                # "繼續"按鈕的懸停效果只在 AI 未執行且沒有 NPC 移動時顯示
                if key_char == "c" and can_trigger_ai:
                    current_btn_color = (255, 240, 120)  # 懸停時的顏色
                    current_border_color = (200, 160, 0) # 懸停時的邊框顏色
                elif key_char != "c": # 其他按鈕總是顯示懸停效果
                    current_btn_color = (255, 240, 120)
                    current_border_color = (200, 160, 0)
                # 如果是 'c' 且 disable_continue_trigger 且 is_hover，則由上面的禁用狀態處理，這裡不用 else
            
            pygame.draw.rect(screen, current_btn_color, rect, border_radius=12)
            pygame.draw.rect(screen, current_border_color, rect, 3, border_radius=12)
            btn_text_surface = button_font.render(f"[{key_char.upper()}] {label}", True, current_text_color)
            btn_text_rect = btn_text_surface.get_rect(center=rect.center)
            screen.blit(btn_text_surface, btn_text_rect)

        # ========= NEW POSITION FOR PATHFINDING DEBUG DRAWING =========
        if show_pathfinding_debug:
            print(f"DEBUG: 在最上層畫出路徑規劃網格與路徑...")
            # 繪製路徑規劃網格，確保顯示在所有元素之上
            draw_pathfinding_debug_info(
                screen, 
                path_planner, 
                world['spaces'], 
                active_npc, 
                scale,  # MODIFIED: 使用 'scale' 替換 'current_zoom_level'
                final_draw_offset_x, 
                final_draw_offset_y
            )
            
        # 顯示思考狀態
        if hasattr(npc, 'is_thinking') and npc.is_thinking:
            display_text = f"{npc.name} 思考中..."
            bubble_font = info_font
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
        
        pygame.display.flip()
        clock.tick(30)
    pygame.quit()

    # 新增：碰撞表面緩存字典，用於避免重複創建大型表面
    collision_surface_cache = {}
    
    # 定義獲取或創建碰撞表面的函數
    def get_collision_surface(width, height, color, border_color=None):
        # 限制最大尺寸，避免記憶體溢出
        max_surface_size = 2000
        safe_width = min(width, max_surface_size)
        safe_height = min(height, max_surface_size)
        
        # 使用尺寸和顏色作為緩存的鍵
        cache_key = (safe_width, safe_height, color[3])  # 使用寬度、高度和透明度作為鍵
        
        if cache_key in collision_surface_cache:
            # 重用緩存的表面，只需要重新填充顏色
            surface = collision_surface_cache[cache_key]
            surface.fill(color)
        else:
            # 創建新的表面並加入緩存
            surface = pygame.Surface((safe_width, safe_height), pygame.SRCALPHA)
            surface.fill(color)
            collision_surface_cache[cache_key] = surface
            
            # 限制緩存大小，避免佔用過多記憶體
            if len(collision_surface_cache) > 50:
                # 移除最早添加的項目
                oldest_key = next(iter(collision_surface_cache))
                del collision_surface_cache[oldest_key]
        
        # 如果指定了邊框顏色，繪製邊框
        if border_color:
            pygame.draw.rect(surface, border_color, surface.get_rect(), 3)
            
        return surface

