class MemoryManager:
    def __init__(self, ai):
        self.ai = ai
        if not hasattr(self.ai, 'memory'):
            self.ai.memory = []  # 確保 AI 有記憶屬性
        
    def add_memory(self, memory): # 添加記憶
        self.ai.memory.append(memory) # 將記憶添加到AI的記憶中
        

    def get_formatted_memory(self): # 格式化記憶
        memory_text = ""
        try:
            for memory in self.ai.memory:
                memory_text += (
                    f"- 與 {memory['object']} 互動："
                    f"{memory['action']}，"
                    f"思考：{memory.get('thought', '無')}\n"
                )
        except KeyError as e:
            return f"記憶格式錯誤: {str(e)}"
        return memory_text or "目前沒有記憶"
    
    def get_last_memory(self):
        """安全地獲取最後一條記憶"""
        try:
            return self.ai.memory[-1] if self.ai.memory else None
        except IndexError:
            return None
    
    def has_interacted_with(self, object_name):
        """檢查是否與特定物體互動過（不分大小寫）"""
        if not object_name:
            return False
        return any(
            memory['object'].lower() == object_name.lower() 
            for memory in self.ai.memory
        )
    
    def get_memories_by_object(self, object_name):
        """獲取特定物體的記憶（不分大小寫）"""
        if not object_name:
            return []
        return [
            memory for memory in self.ai.memory 
            if memory['object'].lower() == object_name.lower()
        ]
    
    def get_memories_by_action(self, action):
        """獲取特定行動的記憶（不分大小寫）"""
        if not action:
            return []
        return [
            memory for memory in self.ai.memory 
            if memory['action'].lower() == action.lower()
        ]
    
    def get_memories_by_thought(self, thought):
        """獲取包含特定思考的記憶（不分大小寫）"""
        if not thought:
            return []
        return [
            memory for memory in self.ai.memory 
            if thought.lower() in memory.get('thought', '').lower()
        ]
    
    def clear_memories(self):
        """清除所有記憶"""
        self.ai.memory = []
        return "記憶已清除"

    def get_memory_count(self):
        """獲取記憶數量"""
        return len(self.ai.memory)