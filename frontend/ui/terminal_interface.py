"""
TerminalInterface - Terminal input/output handling

This class manages terminal commands and output in a separate thread.
"""

import threading
from typing import Optional
from queue import Queue, Empty

from interfaces import BackendAPI


class TerminalInterface:
    """
    Manages terminal input and output.
    
    This runs in a separate thread to handle:
    1. Terminal command input
    2. NPC history output
    3. Debug information
    """
    
    def __init__(self, backend_api: BackendAPI):
        """
        Initialize the terminal interface.
        
        Args:
            backend_api: Backend API for accessing game data
        """
        self.backend_api = backend_api
        self.running = False
        self.thread = None
        self.command_queue = Queue()
        
    def start(self):
        """Start the terminal interface thread."""
        self.running = True
        self.thread = threading.Thread(target=self._listener_thread, daemon=True)
        self.thread.start()
        
        print("🎮 Terminal輸入監聽器啟動")
        print("💡 可用指令:")
        print("   p <npc_name> - 顯示指定NPC的history")
        print("   p - 顯示當前active NPC的history")
        print("   save <filename> - 儲存世界")
        print("   help - 顯示幫助")
        print("   quit - 結束程式")
        print("-" * 50)
    
    def stop(self):
        """Stop the terminal interface thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def get_pending_command(self) -> Optional[str]:
        """
        Get the next pending command from the queue.
        
        Returns:
            Command string if available, None otherwise
        """
        try:
            return self.command_queue.get_nowait()
        except Empty:
            return None
    
    def print_npc_history(self, npc_id: str):
        """
        Print NPC history to terminal.
        
        Args:
            npc_id: NPC identifier
        """
        try:
            history = self.backend_api.get_npc_history(npc_id)
            
            print(f"\n{'='*60}")
            print(f"🤖 {npc_id} 的完整History")
            print(f"{'='*60}")
            print(f"總共 {len(history.entries)} 條記錄")
            print("-" * 60)
            
            for i, entry in enumerate(history.entries, 1):
                role = entry.role
                content = entry.content
                
                # Format based on role
                if role == "system":
                    print(f"[{i:3d}] 🔧 系統: {content}")
                elif role == "assistant":
                    print(f"[{i:3d}] 🤖 {npc_id}: {content}")
                elif role == "user":
                    print(f"[{i:3d}] 👤 用戶: {content}")
                else:
                    print(f"[{i:3d}] ❓ {role}: {content}")
                print("-" * 60)
            
            print(f"{'='*60}")
            print(f"History 結束 - 總共 {len(history.entries)} 條記錄")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"\n[錯誤] 無法獲取 '{npc_id}' 的歷史記錄: {e}")
    
    def print_help(self):
        """Print help information."""
        print("\n" + "="*50)
        print("可用指令:")
        print("  p [npc_name]    - 顯示NPC歷史記錄")
        print("  save [filename] - 儲存當前世界狀態")
        print("  help           - 顯示此幫助信息")
        print("  quit           - 退出程式")
        print("="*50 + "\n")
    
    def _listener_thread(self):
        """Background thread for listening to terminal input."""
        while self.running:
            try:
                user_input = input("Terminal> ").strip()
                if user_input:
                    self.command_queue.put(user_input)
                    
                    if user_input.lower() == 'quit':
                        break
            except (EOFError, KeyboardInterrupt):
                break
        
        print("🎮 Terminal輸入監聽器結束")