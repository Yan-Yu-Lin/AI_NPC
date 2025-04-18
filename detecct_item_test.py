from detecct_item import detect_items_in_space

if __name__ == "__main__":
    # 你可以根據實際空間名稱修改
    space_name = "living_room"
    result = detect_items_in_space(space_name, {})
    print(f"detect_items_in_space('{space_name}', {{}}) 回傳:")
    print(result)
