import time
from queue import Empty
from openai import OpenAI
import json

class ThoughtManager:
    def __init__(self, ai, objects, memory_manager):
        self.ai = ai
        self.objects = objects
        self.memory_manager = memory_manager
        self.thought_result = None
        self.client = OpenAI()
        self.thought_cache = {}

    def thought_worker(self, thought_queue, is_running, is_thinking):
        """生成思考的背景工作"""
        while is_running:
            try:
                task = thought_queue.get(block=True, timeout=1)
                if task is None:
                    break

                object_name, description, state = task
                thought = self.generate_thought(object_name, description, state)
                
                # 添加調試信息
                print(f"💡 AI的想法: {thought}")
                
                # 更新記憶
                new_memory = {
                    "object": object_name,
                    "action": "思考",
                    "thought": thought,
                    "time": time.time()
                }
                self.memory_manager.add_memory(new_memory)
                
                time.sleep(3.0)
                is_thinking = False
                thought_queue.task_done()

            except Empty: # 如果沒有任務，則繼續等待
                continue # 繼續等待
    
    def get_ai_thoughts(self, object_name, object_description, object_state):
        """獲取AI的思考"""
        try:
            # 從快取中獲取思考
            cache_key = f"{object_name}_{object_state}_{json.dumps(self.ai.memory, ensure_ascii=False)}" # 建立快取金鑰
            if cache_key in self.thought_cache: # 如果快取中有思考，則返回思考
                return self.thought_cache[cache_key] # 返回思考

            memory_text = self.memory_manager.get_formatted_memory()


            prompt = f"""
            你是一個AI，正在2D世界中探索。你現在正在與一個物件互動：
            物件名稱：{object_name}
            物件描述：{object_description}
            物件狀態：{object_state}

            你之前的互動記憶：
            {memory_text}

            請描述你對這個物件的觀察和想法，以及你想要如何與它互動。
            你可以加入一些想像和情感，但請保持適度，不要太多。
            最後也請以實際的行動來總結你要幹嘛
            
            請用中文回答，並以「🤔 AI 思考：」開頭。
            回答請簡短，一到兩句話即可。
            回答請以你是在跟另一個人講話的情況，不要講到別人聽不懂。
            """        

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一個有想像力的AI，請明確表達想法和情感，但也要保持務實。請像個真人一樣思考。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            thought = response.choices[0].message.content.strip()

            self.thought_cache[cache_key] = thought # 將思考添加到快取中
            return thought # 返回思考
        
        except Exception as e:
            print(f"🚨 獲取AI思考錯誤: {e}")
            return None
            

    def choose_action_based_on_thought(self, thought):
        """根據思考選擇行動"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "你是一個有想像力的AI，請透過先前的想法，選擇想要做的下一步行動，可以透過object_name、object_description、object_state來思考，最後請輸出一個行動的動詞就好"},
                    {"role": "user", "content": thought}
                ],
                max_tokens=10,
                temperature=0.3
            )
            print(f"🤖 AI 選擇行動: {response.choices[0].message.content.strip()}")
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"🚨 選擇行動錯誤: {e}")
            return None

    def generate_thought(self, object_name, description, state):
        """生成關於物件的想法"""
        thought = f"我看到了{object_name}"
        
        if description:
            thought += f"，{description}"
        
        if state and state != "正常":
            thought += f"，它的狀態是{state}"
        
        return thought
