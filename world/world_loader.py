"""
世界載入器
從JSON檔案載入遊戲世界
"""

import json
import os
from typing import Dict, List, Optional, Any

from npcs.npc import NPC
from items.item import Item
from spaces.space import Space


def load_world(file_path: str) -> Optional[Dict[str, Any]]:
    """
    從JSON檔案載入遊戲世界。
    
    Args:
        file_path: JSON檔案的路徑
        
    Returns:
        包含遊戲世界數據的字典，載入失敗則返回None
    """
    try:
        # 檢查檔案是否存在
        if not os.path.exists(file_path):
            print(f"錯誤: 找不到檔案 '{file_path}'")
            return None
        
        # 載入JSON數據
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        # 創建空間
        spaces = {}
        for space_data in data.get("spaces", []):
            space = Space(space_data["name"], space_data["description"])
            spaces[space_data["id"]] = space
        
        # 連接空間
        for space_data in data.get("spaces", []):
            space = spaces[space_data["id"]]
            for connection in space_data.get("connections", []):
                if connection in spaces:
                    space.connect_to(spaces[connection])
        
        # 創建物品
        items = {}
        for item_data in data.get("items", []):
            # 解析互動
            interactions = {}
            for interaction in item_data.get("interactions", []):
                name = interaction["name"]
                params = interaction.get("params")
                
                # 轉換參數類型
                if params:
                    param_dict = {}
                    for param_name, param_type_str in params.items():
                        if param_type_str == "str":
                            param_dict[param_name] = str
                        elif param_type_str == "int":
                            param_dict[param_name] = int
                        elif param_type_str == "bool":
                            param_dict[param_name] = bool
                        elif param_type_str == "float":
                            param_dict[param_name] = float
                        else:
                            param_dict[param_name] = str
                    interactions[name] = param_dict
                else:
                    interactions[name] = None
            
            # 創建物品
            item = Item(item_data["name"], item_data["description"], interactions)
            
            # 設置物品內容（如果有）
            if "content" in item_data:
                item.content = item_data["content"]
            
            items[item_data["id"]] = item
        
        # 創建NPCs
        npcs = {}
        for npc_data in data.get("npcs", []):
            # 創建NPC
            npc = NPC(
                npc_data["name"], 
                npc_data["description"],
                npc_data.get("personality"),
                npc_data.get("knowledge", {})
            )
            
            # 設置NPC的起始空間
            if "starting_space" in npc_data and npc_data["starting_space"] in spaces:
                npc.current_space = spaces[npc_data["starting_space"]]
                npc.current_space.npcs.append(npc)
            
            # 將物品添加到NPC的庫存
            for item_id in npc_data.get("inventory", []):
                if item_id in items:
                    npc.inventory.add_item(items[item_id])
            
            npcs[npc_data["id"]] = npc
        
        # 將物品放置在空間中
        for space_data in data.get("spaces", []):
            space = spaces[space_data["id"]]
            for item_id in space_data.get("items", []):
                if item_id in items:
                    # 確保物品不在任何NPC的庫存中
                    item_in_inventory = False
                    for npc in npcs.values():
                        if npc.inventory.get_item(items[item_id].name):
                            item_in_inventory = True
                            break
                    
                    if not item_in_inventory:
                        space.items.append(items[item_id])
        
        # 返回完整的世界數據
        return {
            "world_name": data.get("name", "未命名世界"),
            "description": data.get("description", "無描述"),
            "spaces": spaces,
            "items": items,
            "npcs": npcs
        }
    
    except Exception as e:
        print(f"載入世界時發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
