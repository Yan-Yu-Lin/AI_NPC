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

    # 2. 載入世界資料
    world_data = load_world_from_json(map_path)
    world = build_world_from_data(world_data)   

    # 2.5 初始化 AI 系統全域變數
    if world_system is None:
        globals()["world_system"] = AI_System()
        globals()["world_system"].initialize_world(world)

    # 3. 啟動 pygame 顯示
    run_pygame_demo(world)

if __name__ == "__main__":
    main()
