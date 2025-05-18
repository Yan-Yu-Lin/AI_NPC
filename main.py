#main.py

import sys
import os
from backend import load_world_from_json, build_world_from_data, AI_System, world_system
from pygame_display import run_pygame_demo
from pygame_map_selection import pygame_map_selection

def main():
    # 1. 讓使用者選擇地圖（JSON）
    map_path = pygame_map_selection(maps_dir='worlds/maps')
    if not os.path.exists(map_path):
        print(f"找不到地圖檔案: {map_path}")
        sys.exit(1)

    # 2. 載入並構建世界資料
    world_data = load_world_from_json(map_path)
    # populated_world_data_dict 將持有完整的世界數據結構
    populated_world_data_dict = build_world_from_data(world_data)   

    # 2.5 初始化 AI 系統 (如果尚未初始化) 並直接賦值 world 屬性
    if world_system is None:
        # This will modify the world_system imported from backend
        globals()["world_system"] = AI_System() 
    
    # 直接將構建好的世界數據賦值給 AI_System 實例的 world 屬性
    world_system.world = populated_world_data_dict
    # 不再需要調用 initialize_world 方法

    # 3. 啟動 pygame 顯示 (不再傳遞 world 參數)
    run_pygame_demo()

if __name__ == "__main__":
    main()
