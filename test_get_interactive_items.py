from detecct_item import detect_items_in_space, get_interactive_items

if __name__ == "__main__":
    # 取得 living_room 的所有物品
    items = detect_items_in_space("living_room", {})
    print("所有物品:", [item.get("name") for item in items])
    # 指定要篩選的型別
    interactive_items = get_interactive_items(items)
    print("可互動的物品 (instrument, electronics):", [item.get("name") for item in interactive_items])
    # 測試 allowed_types=None
    print("全部物品 (allowed_types=None):", [item.get("name") for item in get_interactive_items(items)])
