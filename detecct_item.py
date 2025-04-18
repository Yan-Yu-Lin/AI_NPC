import json
import os
from typing import List, Dict, Any, Optional

def load_save_data(save_json_path: str) -> dict:
    """讀取 new_save.json 並回傳資料"""
    with open(save_json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def detect_items_in_space(space_name: str, save_data: dict) -> List[Dict[str, Any]]:
    """
    根據 new_save.json 的格式，取得指定空間內所有物品的詳細資料
    """
    save_data = load_save_data("worlds/new_save.json")     # 載入 save_data
    # 找到該空間
    space = next((s for s in save_data["spaces"] if s["name"] == space_name), None)
    if not space or "items" not in space:   # 如果沒有該空間或該空間沒有物品
        return []   # 傳回空清單
    item_names = space["items"] # 取得該空間內所有物品名稱
    # 建立物品名稱到詳細資料對應表
    item_dict = {item["name"]: item for item in save_data.get("items", [])} # 建立物品名稱到詳細資料對應表
    return [item_dict[name] for name in item_names if name in item_dict] # 回傳該空間內所有物品的詳細資料

def get_interactive_items(items: List[Dict[str, Any]], allowed_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    根據物品型別篩選可互動物品，若 allowed_types 為 None 則回傳全部
    """
    if allowed_types is None:   # 若 allowed_types 為 None 則回傳全部
        return items
    return [item for item in items if item.get("type") in allowed_types] # 回傳可互動的物品
