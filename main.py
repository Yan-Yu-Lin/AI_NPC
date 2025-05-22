#main.py

import sys
import os
# 從 backend 導入已經實例化的 world_system，以及其他需要的函數和類
from backend import load_world_from_json, build_world_from_data, world_system 
# 注意：可能不再需要從 backend 導入 AI_System 類本身到 main.py，除非您有特殊用途
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
    # populated_world_data_dict 現在是由 build_world_from_data 返回的，
    # 包含 'world_name_str', 'spaces_data' 等鍵的字典
    returned_data_bundle = build_world_from_data(world_data)   

    # 2.5 將構建好的世界數據的各個部分賦值給 backend.world_system 的相應屬性
    world_system.world_name_str = returned_data_bundle.get("world_name_str", "未知世界")
    world_system.world_description_str = returned_data_bundle.get("world_description_str", "")
    world_system.spaces_data = returned_data_bundle.get("spaces_data", {})
    world_system.items_data = returned_data_bundle.get("items_data", {})
    world_system.npcs_data = returned_data_bundle.get("npcs_data", {})
    
    # 之前直接賦值整個字典給 world_system.world 的程式碼 (現已修改)
    # world_system.world = populated_world_data_dict 

    # 之前用於 AI_System 實例化的程式碼 (現已不需要):
    # if world_system is None:
    #     # This will modify the world_system imported from backend
    #     globals()["world_system"] = AI_System() 
    # # 直接將構建好的世界數據賦值給 AI_System 實例的 world 屬性
    # world_system.world = populated_world_data_dict
    # # 不再需要調用 initialize_world 方法

    # 3. 啟動 pygame 顯示 (不再傳遞 world 參數)
    run_pygame_demo()

if __name__ == "__main__":
    main()
