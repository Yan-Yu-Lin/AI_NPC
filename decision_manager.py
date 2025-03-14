import time
import random
from queue import Empty
global n
n = 0

class DecisionManager:
    def __init__(self, ai, objects, memory_manager):
        self.ai = ai
        self.objects = objects
        self.memory_manager = memory_manager
        self.current_decision = None
        self.decision_made = False
        self.decision_result = None
        self.decision_cooldown = 2
        self.last_decision_time = time.time()
        self.mentioned_objects = []
        self.obj_is_important_list = []
        self.obj_is_important = False

    def decision_worker(self, decision_queue, is_running): # 決策執行緒（背景執行）
        while is_running: # 如果執行緒正在運行
            try:
                # task在這裡只作為觸發信號，True表示需要做出新的決策
                task = decision_queue.get(block=True, timeout=1) # 從決策佇列中獲取任務
                if task is None: # 如果任務為None
                    break # 退出迴圈
                
                # 只在沒有當前決策時才生成新決策
                if self.decision_result is None:
                    self.decision_result = self.choose_next_object()
                    print(f"🤔 生成新決策: {self.decision_result}")
                
                decision_queue.task_done()
            except Empty: # 如果佇列為空
                continue # 繼續迴圈
            
    def choose_next_object(self):
        
        if not self.ai.memory:
            print("📝 AI沒有記憶，隨機選擇目標")
            if self.objects:
                next_object = random.choice(self.objects)
                if next_object:
                    print(f"🎯 AI選擇了目標：{next_object.name}")
                    self.ai.memory.append({
                        "object": next_object.name,
                        "action": "移動到",
                        "thought": "隨機選擇"
                    })
                    return f"移動到{next_object.name}"
        elif self.ai.memory and n != 0:
            n=n+1
            print(f"💾 AI有 {len(self.ai.memory)} 條記憶")
            next_object = self.choose_base_on_memory(self.objects)
            if next_object:
                print(f"🎯 AI基於記憶選擇了目標：{next_object.name}")
                return f"移動到{next_object.name}"
    
    def choose_base_on_memory(self, objects):
        # 根據記憶選擇下一個物件
        if not self.ai.memory:
            return None
        
        mentioned_objects = []  # 在函數開始時初始化
        obj_is_important_list = []  # 在函數開始時初始化
        
        for interaction in self.ai.memory:
            thought = interaction.get("thought","") # 獲取互動中的想法

            for obj in objects:
                if obj.name.lower() in thought.lower(): # 如果物件名稱在想法中
                    mentioned_objects.append(obj) # 將物件加入到mentioned_objects列表中

            if "關鍵" in thought.lower() or "重要" in thought.lower():
                for obj in objects:
                    if obj.name.lower() in thought.lower():
                        obj_is_important_list.append(obj) # 將物件加入到obj_is_important列表中
                        obj_is_important = True

        if mentioned_objects:
            chosen_object = random.choice(mentioned_objects)
            print("AI選擇了物件：", chosen_object.name)
            return chosen_object

    def get_decision_result(self):
        current_time = time.time()
        # 確保決策有足夠的冷卻時間
        if current_time - self.last_decision_time > self.decision_cooldown:
            result = self.decision_result
            if result:  # 只有在有結果時才重置
                self.decision_result = None
                self.last_decision_time = current_time
            return result
        return None

    def make_decision(self):
        if not self.decision_made: # 如果沒有做出決策
            available_objects = [obj for obj in self.objects if obj != self.ai.target] # 獲取可用的物件
            if available_objects: # 如果可用的物件存在
                chosen_object = random.choice(available_objects) # 隨機選擇一個物件
                self.current_decision = chosen_object # 設置當前決策
                self.decision_made = True # 設置決策已做出
                return chosen_object # 返回選擇的物件
        return None

    def reset_decision(self):
        self.current_decision = None
        self.decision_made = False