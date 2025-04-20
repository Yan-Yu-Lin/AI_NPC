import json
import datetime

def save_game_data(npc_manager, action_history, interaction_history, filename="save.json"):
    """
    儲存遊戲進度，包括所有 NPC 的名稱、座標、狀態、歷史行動紀錄、互動紀錄。
    npc_manager: 管理所有 NPC 的物件，需有 npcs 屬性（list of NPC）
    action_history: 歷史行動紀錄（list）
    interaction_history: 互動紀錄（list）
    filename: 儲存檔案名稱
    """
    npc_data = []
    for npc in npc_manager.npcs:
        npc_data.append({
            "name": getattr(npc, "name", None),
            "position": getattr(npc, "position", None),
            "state": getattr(npc, "state", None),
            "action_history": getattr(npc, "action_history", []),
            "interaction_history": getattr(npc, "interaction_history", [])
        })

    save_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "npcs": npc_data,
        "global_action_history": action_history,
        "global_interaction_history": interaction_history
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)