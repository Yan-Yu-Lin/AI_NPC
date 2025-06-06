"""
Backend Refactored Demo - 展示如何使用重構後的後端

這個檔案展示了重構後的純 AI 邏輯後端的使用方式。
"""

import json
from backend_refactored.ai_system import AI_System


def main():
    """執行重構後端的示例"""
    
    # 建立 AI 系統實例
    ai_system = AI_System()
    
    # 初始化系統
    print("初始化 AI 系統...")
    ai_system.initialize()
    
    # 載入範例世界資料
    try:
        with open("worlds/world_test.json", "r", encoding="utf-8") as f:
            world_data = json.load(f)
        
        print(f"載入世界: {world_data.get('world_name', '未知世界')}")
        ai_system.load_world(world_data)
        
    except FileNotFoundError:
        print("找不到世界檔案，建立範例世界...")
        create_sample_world(ai_system)
    
    # 獲取世界顯示資料
    world_display = ai_system.get_world_display_data()
    print(f"\n世界資訊:")
    print(f"- 名稱: {world_display.world_name}")
    print(f"- 時間: {world_display.current_time}")
    print(f"- 天氣: {world_display.weather}")
    print(f"- 空間數: {len(world_display.spaces)}")
    print(f"- NPC數: {len(world_display.npcs)}")
    print(f"- 物品數: {len(world_display.items)}")
    
    # 列出所有 NPC
    print("\nNPC 列表:")
    for npc_data in world_display.npcs:
        print(f"- {npc_data.name} (狀態: {npc_data.state.value}, 位置: {npc_data.current_space_id})")
    
    # 測試 NPC 互動
    if world_display.npcs:
        test_npc_id = world_display.npcs[0].id
        print(f"\n測試 NPC '{test_npc_id}' 的 AI 互動...")
        
        # 觸發 NPC 自主行動
        response = ai_system.trigger_npc_action(test_npc_id)
        print(f"AI 回應: {response.content}")
        
        # 測試使用者輸入
        from interfaces import UserInput
        user_input = UserInput(
            npc_id=test_npc_id,
            input_type="text",
            content="你好！今天天氣如何？"
        )
        
        response = ai_system.process_user_input(user_input)
        print(f"\n對話回應: {response.content}")
    
    # 處理幾個 tick
    print("\n處理遊戲 tick...")
    for i in range(3):
        if ai_system.process_tick():
            print(f"Tick {i+1} 完成")
            
            # 顯示時間變化
            world_display = ai_system.get_world_display_data()
            print(f"  當前時間: {world_display.current_time}")
    
    # 儲存世界
    print("\n儲存世界狀態...")
    if ai_system.save_world("worlds/test_save_refactored.json"):
        print("世界已儲存")
    else:
        print("儲存失敗")


def create_sample_world(ai_system: AI_System):
    """建立範例世界"""
    from backend_refactored.models import Space, Item, NPC, Inventory
    
    # 建立空間
    living_room = Space(
        name="客廳",
        description="一個溫馨的客廳，有舒適的沙發和大電視。",
        space_type="room"
    )
    
    kitchen = Space(
        name="廚房",
        description="現代化的廚房，配備齊全的廚具。",
        space_type="room"
    )
    
    # 連接空間
    living_room.biconnect(kitchen)
    
    # 建立物品
    sofa = Item(
        name="沙發",
        description="一張三人座的舒適沙發",
        position=(50, 50),
        size=(100, 50)
    )
    
    tv = Item(
        name="電視",
        description="65吋的智慧電視",
        position=(100, 20),
        size=(80, 60)
    )
    
    # 添加物品到空間
    living_room.add_item(sofa)
    living_room.add_item(tv)
    
    # 建立 NPC
    alice = NPC(
        name="Alice",
        description="一個友善的居民",
        current_space=living_room,
        inventory=Inventory(capacity=10),
        position=(30, 30)
    )
    
    # 添加到 AI 系統
    ai_system.world_manager.add_space(living_room)
    ai_system.world_manager.add_space(kitchen)
    ai_system.world_manager.add_item(sofa)
    ai_system.world_manager.add_item(tv)
    ai_system.npc_manager.add_npc(alice)
    
    # 設定世界資訊
    ai_system.world_name = "範例世界"
    ai_system.world_description = "一個用於測試的簡單世界"


if __name__ == "__main__":
    main()