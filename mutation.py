from models import NPC, Space, Item, Inventory
from typing import Optional

# --- NPC 移動 ---
def npc_move_to_space(npc: NPC, target_space: Space) -> str:
    """
    將 NPC 從目前空間移動到目標空間，並維護雙方 reference。
    """
    if npc.current_space is not None:
        try:
            npc.current_space.npcs.remove(npc)
        except ValueError:
            pass  # 已不在舊空間
    npc.current_space = target_space
    if npc not in target_space.npcs:
        target_space.npcs.append(npc)
    return f"{npc.name} 移動到 {target_space.name}"

# --- 物品互動 ---
def npc_interact_with_item(npc: NPC, item: Item, how: str) -> str:
    """
    NPC 與物品互動（根據 how 參數決定互動方式）。
    你可以根據 item.properties 或 how 決定不同效果。
    """
    # 這裡只做簡單描述，真實遊戲可擴充
    return f"{npc.name} 用方式「{how}」與 {item.name} 互動"

# --- NPC 拿起物品 ---
def npc_pick_up_item(npc: NPC, item: Item, space: Space) -> str:
    """
    NPC 從空間拿起物品，物品進入 NPC 的 inventory。
    """
    if item in space.items:
        space.items.remove(item)
        npc.inventory.add_item(item)
        return f"{npc.name} 拿起了 {item.name}"
    return f"{item.name} 不在空間 {space.name}"

# --- NPC 放下物品 ---
def npc_drop_item(npc: NPC, item: Item, space: Space) -> str:
    """
    NPC 將物品從 inventory 放回空間。
    """
    if item in npc.inventory.items:
        npc.inventory.items.remove(item)
        space.items.append(item)
        return f"{npc.name} 放下了 {item.name} 在 {space.name}"
    return f"{npc.name} 沒有 {item.name}"

# --- 空間連結/解除連結 ---
def connect_space(space1: Space, space2: Space) -> None:
    if space2 not in space1.connected_spaces:
        space1.connected_spaces.append(space2)
    if space1 not in space2.connected_spaces:
        space2.connected_spaces.append(space1)

def disconnect_space(space1: Space, space2: Space) -> None:
    if space2 in space1.connected_spaces:
        space1.connected_spaces.remove(space2)
    if space1 in space2.connected_spaces:
        space2.connected_spaces.remove(space1)

# --- 空間物品增減 ---
def space_add_item(space: Space, item: Item) -> None:
    if item not in space.items:
        space.items.append(item)

def space_remove_item(space: Space, item: Item) -> None:
    if item in space.items:
        space.items.remove(item)
