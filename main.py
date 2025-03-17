"""
AI NPC 主程式
整合所有模組並運行遊戲系統
"""

import os
from typing import Optional

# 導入所需模組
from world.world_loader import load_world
from npcs.npc import NPC
from history.history_manager import print_history

def main():
    """主程式入口點"""
    print("歡迎來到 AI NPC 模擬系統！")
    print("正在載入世界...")
    
    # 載入世界 - 使用絕對路徑
    current_dir = os.path.dirname(os.path.abspath(__file__))
    world_file_path = os.path.join(current_dir, "worlds", "world_test.json")
    print(f"嘗試載入世界檔案：{world_file_path}")
    
    world = load_world(world_file_path)
    
    if not world:
        print("錯誤：無法載入世界。程式終止。")
        return
    
    print(f"成功載入世界：{world['world_name']}")
    print(f"世界描述：{world['description']}")
    
    # 獲取主要NPC (arthur)
    arthur = world["npcs"].get("arthur")
    if not arthur:
        print("錯誤：在世界數據中找不到主要NPC 'arthur'")
        return
    
    print(f"主要NPC：{arthur.name} - {arthur.description}")
    print("\n遊戲開始！\n")
    
    # 確保NPC第一次tick已經執行過，並顯示初始狀態
    if arthur.first_tick:
        result = arthur.process_tick()
        print(f"初始狀態: {result}\n")
        
        # 顯示當前環境和情境
        print(f"{arthur.name} 目前所在空間: {arthur.current_space.name}")
        print(f"空間描述: {arthur.current_space.description}")
        if arthur.current_space.items:
            print("空間中的物品:")
            for item in arthur.current_space.items:
                print(f" - {item.name}: {item.description}")
        if arthur.current_space.npcs:
            print("空間中的其他NPC:")
            for npc in arthur.current_space.npcs:
                if npc.name != arthur.name:
                    print(f" - {npc.name}: {npc.description}")
        print("\n使用 'c' 繼續遊戲，'p' 查看歷史記錄，或輸入指令給NPC\n")
    
    # 遊戲主循環
    while True:
        print("=====================")
        user_input = input("c -> 繼續, e -> 退出, p -> 顯示歷史記錄: ").strip().lower()
        
        if user_input == "c":
            # 與demo_preview_alpha_nighty_RC2.py相同的實現方式
            result = arthur.process_tick()
            print(f"結果: {result}\n")
        
        elif user_input == "p":
            # 顯示歷史記錄
            print_history(arthur)
        
        elif user_input == "e":
            # 退出遊戲
            print("感謝使用 AI NPC 模擬系統！")
            break
        
        else:
            # 將用戶輸入傳遞給NPC
            result = arthur.process_tick(user_input)
            print(f"結果: {result}\n")

if __name__ == "__main__":
    main()