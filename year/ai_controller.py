import json
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import threading
from queue import Queue, Empty
import time
import random

class AIController:
    def __init__(self, ai, objects):
        self.client = OpenAI()  #初始化AI客戶端
        self.ai = ai #初始化AI
        self.objects = objects #初始化物件列表
        self.decision_queue = Queue()    #初始化決策佇列
        self.thought_queue = Queue()     #初始化思考佇列
        self.decision_timeout = 2        #決策超時時間
        self.decision_cooldown = 2       #決策冷卻時間
        self.last_decision_time = time.time() #上次決策時間
        self.decision_result = None       #決策結果
        self.last_interaction_time = 0    #上次互動時間
        self.interaction_cooldown = 3.0  #互動冷卻時間
        self.current_thought = None      #當前思考
        self.is_thinking = False        #是否正在思考
        self.is_running = True          #是否正在運行
        self.last_distance = float('inf')  #距離追蹤
        self.distance_update_threshold = 10  #距離更新閾值
        self.last_target = None  #追蹤上一次的目標
        
        # 初始化時立即選擇第一個目標
        if self.objects:
            first_object = self.objects[0]
            self.ai.target = first_object
            self.last_target = first_object
            print(f"🚶 AI 開始移動到 {first_object.name}")
        
        # 啟動決策和思考執行緒
        self.decision_thread = threading.Thread(target=self.decision_worker, daemon=True)
        self.thought_thread = threading.Thread(target=self.thought_worker, daemon=True)
        self.decision_thread.start()
        self.thought_thread.start()

    def update(self):
        """更新 AI 的狀態和行動"""
        if not self.is_running:
            return
            
        current_time = time.time()
        
        # AI 思考行動
        if self.ai.target is None and not self.is_thinking:
            # 立即進行新的決策
            self.decision_queue.put(True)
            self.last_decision_time = current_time
            
            if self.decision_result is not None:
                ai_decision = self.decision_result
                self.decision_result = None

                if "移動到" in ai_decision:
                    target_name = ai_decision.replace("移動到 ", "").strip()
                    self.ai.target = next((obj for obj in self.objects if obj.name == target_name), None)
                    if self.ai.target and self.ai.target != self.last_target:
                        print(f"🚶 AI 開始移動到 {self.ai.target.name}")
                        self.last_target = self.ai.target
                        self.last_distance = float('inf')  # 重置距離追蹤
                elif ai_decision == "重新開始":
                    print("🔄 AI 重新開始探索...")
                    self.ai.target = None
                    self.last_target = None
                    self.ai.thought_cache.clear()
                    self.ai.memory.clear()

        # AI 移動邏輯
        if self.ai.target:
            target_x, target_y = self.ai.target.rect.center
            dx, dy = target_x - self.ai.pos[0], target_y - self.ai.pos[1]
            dist = (dx ** 2 + dy ** 2) ** 0.5

            if dist > 5:
                move_speed = min(self.ai.speed, dist / 10)
                self.ai.pos[0] += move_speed * (dx / dist)
                self.ai.pos[1] += move_speed * (dy / dist)
                self.ai.rect.center = self.ai.pos
                
                # 只在距離變化超過閾值時更新訊息
                if abs(dist - self.last_distance) > self.distance_update_threshold:
                    # 計算移動方向
                    direction = ""
                    if abs(dx) > abs(dy):
                        direction = "水平" if dx > 0 else "水平"
                    else:
                        direction = "垂直" if dy > 0 else "垂直"
                    
                    # 計算精確距離
                    precise_dist = round(dist, 2)
                    print(f"📍 距離目標還有 {precise_dist:.2f} 像素，正在{direction}移動")
                    self.last_distance = dist
            else:
                # 檢查是否已經與這個物件互動過，且過了冷卻時間
                has_interacted = any(memory["object"] == self.ai.target.name for memory in self.ai.memory)
                if not has_interacted and current_time - self.last_interaction_time > self.interaction_cooldown and not self.is_thinking:
                    # 將思考任務加入佇列
                    self.thought_queue.put((
                        self.ai.target.name,
                        self.ai.target.description,
                        self.ai.target.state
                    ))
                    self.is_thinking = True
                
                # 立即開始新的決策
                self.ai.target = None
        else:
            self.ai.rect.center = self.ai.pos

    def thought_worker(self):
        """背景思考執行緒"""
        while self.is_running:
            try:
                task = self.thought_queue.get(timeout=0.1)
                if task is None:
                    break
                    
                object_name, object_description, object_state = task
                
                # 進行思考
                thought = self.get_ai_thoughts(
                    object_name,
                    object_description,
                    object_state
                )
                
                if thought:
                    # 根據思考結果選擇動作
                    action = self.choose_action_based_on_thought(thought)
                    print(f"🤖 AI 思考：{thought}")
                    time.sleep(1.0)  # 等待1秒
                    print(f"🤖 AI 執行 {object_name} 的動作: {action}")
                    
                    # 更新記憶
                    self.ai.memory.append({
                        "object": object_name,
                        "action": action,
                        "thought": thought,
                        "state": object_state,
                        "time": time.time()
                    })
                    self.last_interaction_time = time.time()
                
                # 等待一段時間再繼續
                time.sleep(3.0)  # 增加等待時間到3秒
                self.is_thinking = False
                self.thought_queue.task_done()
                
            except Empty:
                continue

    def choose_action_based_on_thought(self, thought):
        """根據思考結果選擇最合適的動作"""
        # 根據思考內容選擇最合適的動作
        if "放" in thought or "放置" in thought:
            return "移動"
        elif "撿" in thought or "拿" in thought:
            return "撿起"
        elif "開" in thought or "推" in thought:
            return "打開"
        elif "敲" in thought or "打" in thought:
            return "敲門"
        else:
            return "查看"

    def get_ai_thoughts(self, object_name, object_description, object_state):
        try:
            cache_key = f"{object_name}_{object_state}_{json.dumps(self.ai.memory, ensure_ascii=False)}"
            if cache_key in self.ai.thought_cache:
                return self.ai.thought_cache[cache_key]

            memory_text = ""
            for memory in self.ai.memory[-3:]:  # 只使用最近3條記憶
                memory_text += f"- 與 {memory['object']} 互動：{memory['action']}\n"

            prompt = f"""
            你是一個AI，正在2D世界中探索。你現在正在觀察一個物件：
            物件名稱：{object_name}
            物件描述：{object_description}
            物件狀態：{object_state}

            你最近的互動記憶：
            {memory_text}

            請描述你對這個物件的觀察和想法，以及你想要如何與它互動。
            你可以加入一些想像和情感，但請保持適度，不要太多。
            最後也請以比較實際的行動來總結
            
            請用中文回答，並以「🤔 AI 思考：」開頭。
            回答請簡短，一到兩句話即可。
            """

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "你是一個有想像力的AI，可以適度表達想法和情感，但也要保持務實。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # 減少token數量以限制回答長度
                temperature=0.4  # 設定為0.5以平衡創意性和穩定性
            )
            thought = response.choices[0].message.content.strip()
            
            self.ai.thought_cache[cache_key] = thought
            return thought
        except Exception as e:
            print(f"AI 思考時發生錯誤：{e}")
            return None

    def get_ai_decision_async(self):
        try:
            unvisited_objects = []
            current_time = time.time()
            
            # 檢查是否所有物件都互動過了
            all_interacted = all(any(memory["object"] == obj.name for memory in self.ai.memory) for obj in self.objects)
            if all_interacted:
                print("🔄 AI 重新開始探索...")
                self.ai.memory.clear()
                return "重新開始"
            
            # 找出所有未訪問的物件
            for obj in self.objects:
                if not any(memory["object"] == obj.name for memory in self.ai.memory):
                    unvisited_objects.append(obj)
            
            if not unvisited_objects:
                # 如果沒有未訪問的物件，重新開始探索
                print("🔄 AI 重新開始探索...")
                self.ai.memory.clear()
                return "重新開始"
                
            # 選擇最近的未訪問物件
            nearest_object = min(
                unvisited_objects,
                key=lambda obj: ((obj.rect.center[0] - self.ai.pos[0])**2 +
                            (obj.rect.center[1] - self.ai.pos[1])**2)**0.5
            )

            if nearest_object:
                return f"移動到 {nearest_object.name}"
            else:
                return "重新開始"
                
        except Exception as e:
            print(f"AI 決策時發生錯誤：{e}")
            return "重新開始"

    def decision_worker(self):
        while self.is_running:
            try:
                task = self.decision_queue.get(timeout=0.1)
                if task is None:
                    break
                
                self.decision_result = self.get_ai_decision_async()
                self.decision_queue.task_done()
            except Empty:
                continue

    def get_ai_decision(self):
        if time.time() - self.last_decision_time > self.decision_cooldown:
            self.decision_queue.put(True)
            self.last_decision_time = time.time()
            return "等待"
        
        if self.decision_result is not None:
            result = self.decision_result
            self.decision_result = None
            return result
            
        return "等待"

    def cleanup(self):
        """清理資源並關閉執行緒"""
        self.is_running = False
        self.decision_queue.put(None)
        self.thought_queue.put(None)
        self.decision_thread.join(timeout=1.0)
        self.thought_thread.join(timeout=1.0) 