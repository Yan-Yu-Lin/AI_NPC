from queue import Queue
import threading
import time
import random
from thought_manager import ThoughtManager
from decision_manager import DecisionManager
from memory_manager import MemoryManager
from movement_manager import MovementManager


class AIController:
    def __init__(self, ai, objects):
        self.ai = ai
        self.objects = objects

        # 初始化記憶、決策、思考、移動管理器
        self.memory_manager = MemoryManager(ai)
        self.decision_manager = DecisionManager(ai, objects, self.memory_manager)
        self.thought_manager = ThoughtManager(ai, objects, self.memory_manager)
        self.movement_manager = MovementManager(ai)

        # 初始化狀態控制
        self.decision_queue = Queue()
        self.thought_queue = Queue()
        self.is_running = True
        self.is_thinking = False
        self.current_state = "deciding"  # 可能的狀態: "deciding", "moving", "thinking"
        self.decision_made = False  # 新增決策標記
        self.last_decision_time = time.time()
        self.decision_cooldown = 2.0  # 決策冷卻時間

        # 時間控制
        self.last_interaction_time = 0
        self.interaction_cooldown = 3.0
        self.last_target = None

        # 初始化執行緒
        self.init_threads()


    # 初始化執行緒
    def init_threads(self):
        # 決策執行緒
        self.decision_thread = threading.Thread(
            target = self.decision_manager.decision_worker,
            args = (self.decision_queue, self.is_running),
            daemon = True
        )

        # 思考執行緒
        self.thought_thread = threading.Thread(
            target = self.thought_manager.thought_worker,
            args = (self.thought_queue, self.is_running, self.is_thinking),
            daemon = True
        )
        
        self.decision_thread.start()
        self.thought_thread.start()


    def update(self):
        current_time = time.time()
        
        # 如果沒有目標且不在思考中，請求新決策
        if self.ai.target is None and not self.is_thinking:
            if self.decision_manager.decision_result is None: # 如果沒有當前決策
                self.decision_queue.put(True) # 請求新決策
            
            decision_result = self.decision_manager.get_decision_result()
            if decision_result:
                self.process_decision(decision_result)
        
        # 如果有目標，則進行移動
        elif self.ai.target:
            self.handle_movement_and_interaction(current_time)

    def process_decision(self, decision):
        if "移動到" in decision:
            target_name = decision.replace("移動到", "").strip()
            for obj in self.objects:
                if obj.name == target_name:
                    self.ai.target = obj
                    print(f"🎯 AI決定移動到：{obj.name}")
                    break

    def handle_movement_and_interaction(self, current_time):
        # 計算與目標的距離
        dx = self.ai.target.rect.centerx - self.ai.pos[0]
        dy = self.ai.target.rect.centery - self.ai.pos[1]
        distance = (dx**2 + dy**2)**0.5

        if distance < 10:  # 到達目標
            print(f"📍 到達目標位置：{self.ai.target.name}")
            self.current_state = "thinking"
            self.handle_interaction(current_time)
        else:
            # 更新移動
            self.movement_manager.update_movement(
                self.ai.target.rect.center,
                self.ai.pos
            )
            self.ai.rect.center = self.ai.pos

    def handle_interaction(self, current_time):
        if (current_time - self.last_interaction_time) > self.interaction_cooldown and not self.is_thinking:
            print(f"🔍 AI 開始觀察 {self.ai.target.name}")  # 添加調試信息
            
            # 添加新的記憶
            new_memory = {
                "object": self.ai.target.name,
                "action": "觀察",
                "thought": "",
                "time": current_time
            }
            
            # 確保記憶被添加
            try:
                self.memory_manager.add_memory(new_memory)
                print(f"📝 添加新記憶：觀察 {self.ai.target.name}")  # 調試信息
            except Exception as e:
                print(f"❌ 添加記憶失敗：{e}")

            # 將目標信息加入思考佇列
            try:
                self.thought_queue.put((
                    self.ai.target.name,
                    self.ai.target.description,
                    self.ai.target.state
                ))
                print(f"💭 開始思考關於 {self.ai.target.name}")  # 調試信息
            except Exception as e:
                print(f"❌ 添加思考任務失敗：{e}")

            self.is_thinking = True
            self.last_interaction_time = current_time
            
            # 清除當前目標
            self.ai.target = None

    def cleanup(self):
        self.is_running = False
        self.decision_queue.put(None)
        self.thought_queue.put(None)
        self.decision_thread.join(timeout=1)
        self.thought_thread.join(timeout=1)
        print("👋 AI 已停止")