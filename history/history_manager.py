"""
歷史記錄管理器
處理NPC交互歷史的顯示和管理
"""

from typing import List, Dict, Any


def print_history(npc, max_items: int = None):
    """
    打印NPC的歷史記錄。
    
    Args:
        npc: 要顯示歷史記錄的NPC
        max_items: 要顯示的最大條目數，None顯示全部
    """
    history = npc.history
    
    # 如果指定了最大條目數，則只顯示最後的max_items個條目
    if max_items is not None and max_items > 0:
        history = history[-max_items:]
    
    print(f"\n=== {npc.name} 的歷史記錄 ===")
    
    for item in history:
        role = item["role"]
        content = item["content"]
        
        if role == "system":
            print(f"[系統] {content}")
        elif role == "user":
            print(f"[用戶] {content}")
        elif role == "assistant":
            print(f"[{npc.name}] {content}")
        else:
            print(f"[{role}] {content}")
    
    print("=====================\n")


def save_history_to_file(npc, file_path: str):
    """
    將NPC的歷史記錄保存到文件。
    
    Args:
        npc: 要保存歷史記錄的NPC
        file_path: 保存的文件路徑
    """
    import json
    
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(npc.history, file, ensure_ascii=False, indent=2)
        print(f"歷史記錄已保存到 {file_path}")
    except Exception as e:
        print(f"保存歷史記錄時出錯: {str(e)}")


def load_history_from_file(npc, file_path: str):
    """
    從文件載入NPC的歷史記錄。
    
    Args:
        npc: 要載入歷史記錄的NPC
        file_path: 歷史記錄文件路徑
    """
    import json
    import os
    
    if not os.path.exists(file_path):
        print(f"錯誤: 找不到檔案 '{file_path}'")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            npc.history = json.load(file)
        print(f"從 {file_path} 載入了歷史記錄")
    except Exception as e:
        print(f"載入歷史記錄時出錯: {str(e)}")
