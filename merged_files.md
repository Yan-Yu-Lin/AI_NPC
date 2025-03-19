# 項目文件合併

目錄: `/Users/linyanyu/Desktop/Coding/python/AI_NPCs`

包含 10 個文件

## __init__.py

```py
from .ai_controller import AIController
from .thought_manager import ThoughtManager
from .decision_manager import DecisionManager
from .memory_manager import MemoryManager
from .movement_manager import MovementManager

__all__ = [
    'AIController',
    'ThoughtManager',
    'DecisionManager',
    'MemoryManager',
    'MovementManager'
]
```

## ai_controller.py

```py
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
```

## decision_manager.py

```py
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
```

## game_object.py

```py
import pygame

#定義顏色
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PINK = (255, 192, 203)
GRAY = (128, 128, 128)

class GameObject:
    #初始化物件的各參數
    def __init__(self, x, y, width, height, color, name, description, state = "正常"):
        self.rect = pygame.Rect(x, y, width, height)
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.name = name
        self.description = description
        self.state = state
        self.type = "一般物件"

    #繪製物件
    #screen: 繪製的畫面
    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        
    #更新物件狀態
    def update(self, screen):
        pass

    #處理互動
    def interact(self, action):
        pass

    #取得物件的資訊
    def get_info(self):
        return f"{self.name}：{self.description}"
    
    #取得物件的狀態
    def get_state(self):
        return self.state
    
    #取得物件的類型
    def get_type(self):
        return self.type
    
    #取得物件的座標
    def get_position(self):
        return self.x, self.y
    
    #取得物件的尺寸
    def get_size(self):
        return self.width, self.height
    
class AI:
    #初始化AI的各參數
    def __init__(self, x, y, name, description, state = "正常"):
        self.pos = [x, y]
        self.rect = pygame.Rect(x, y, 10, 10)
        self.rect.center = self.pos  # 確保 rect 中心點對齊
        self.speed = 2
        self.target = None
        self.name = name
        self.description = description #描述
        self.state = state #狀態
        self.memory = [] #記憶
        self.thought_cache = {} #思考緩存
        self.action_history = [] #行動歷史
        self.current_task = None #當前任務
        self.task_history = [] #任務歷史
        self.task_queue = [] #任務隊列
        self.target_history = [] #目標歷史
        self.target_queue = [] #目標隊列
        self.target_cache = {} #目標緩存

    #繪製AI
    def draw(self, screen):
        pygame.draw.rect(screen, RED, self.rect)  # 使用 rect 來繪製
        
    def update(self):
        self.rect.center = self.pos

    def move_to(self, target):
        self.target = target
        self.target_history.append(target)
        self.target_queue.append(target)
        
class InteractiveObject(GameObject):
    #初始化互動物件的各參數
    def __init__(self, x, y, width, height, color, name, description, interaction = None, state = "正常"):
        super().__init__(x, y, width, height, color, name, description, state)
        self.type = "互動物件"
        self.interaction = interaction #互動
        self.interaction_result = {} #互動結果
        
    def add_interaction(self, action, result):
        if action not in self.interaction:
            self.interaction.append(action) #新增互動
        self.interaction_result[action] = result
        
    def interact(self, action):
        if action in self.interaction:
            return self.interaction_result.get(action, f"對{self.name}執行了{action}，{self.interaction_result[action]}")
        else:
            return f"無法對{self.name}執行{action}"
    
class Container(InteractiveObject):
    def __init__(self, x, y, width, height, color, name, capacity, description, interaction = None, state = "正常"):
        super().__init__(x, y, width, height, color, name, description, interaction, state)
        self.type = "容器"
        self.contents = [] #容器內容物
        self.capacity = capacity #容器容量
        self.interaction = ["查看", "拿取", "放置"] #容器互動

    def add_item(self, item):
        if len(self.contents) < self.capacity:
            self.contents.append(item)
            return f"成功將{item.name}放入{self.name}"
        else:
            return f"{self.name}已滿"
        
    def remove_item(self, item_name):
        for item in self.contents:
            if item.name == item_name:
                self.contents.remove(item)
                return f"成功從{self.name}中移除{item_name}"
        return f"{item_name}不在{self.name}中"
    
    def get_contents(self):
        return [item.name for item in self.contents]

class Door(InteractiveObject):
    def __init__(self, x, y, width, height, color, name, description, interaction=None, state="正常"):
        super().__init__(x, y, width, height, color, name, description, interaction, state)
        self.type = "門"
        self.interaction = ["開啟", "關閉", "查看", "敲門"] #門互動
        self.is_open = False #門是否開啟
        self.locked = False #門是否上鎖
        self.lock_code = None #門鎖密碼

    def interact(self, action):
        if action == "開啟":
            if not self.is_open:
                self.is_open = True
                self.state = "開啟"
                return f"{self.name}被打開了"
            return f"{self.name}已經是開啟的了"
        elif action == "關閉":
            if self.is_open:
                self.is_open = False
                self.state = "關閉"
                return f"{self.name}被關閉了"
            return f"{self.name}已經是關閉的了"
        elif action == "查看":
            if self.is_open:
                return f"{self.name}是開啟的"
            else:
                return f"{self.name}是關閉的"
        elif action == "敲門":
            return f"你敲了敲{self.name}"
        return super().interact(action)

def create_box(x, y, color=BLUE, name="盒子", description ="一個普通的盒子"):
    return Container(x, y, 50, 50, color, name, 1, description)

def create_door(x, y, color=RED, name="門", description="一扇普通的門"):
    return Door(x, y, 50, 100, color, name, description)

def create_basic_object(x, y, color=GREEN, name="物件", description="一個普通的物件"):
    return GameObject(x, y, 50, 50, color, name, description)
```

## main.py

```py
import pygame
import sys
import random
from ai_controller import AIController
from game_object import(
    GameObject, AI, InteractiveObject, Container, Door,
    create_box, create_door, create_basic_object,
    WHITE, BLACK, RED, BLUE, GREEN, YELLOW, PINK
)

# 遊戲初始化
pygame.init()

WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800
screen = pygame.display.set_mode((WINDOW_WIDTH,WINDOW_HEIGHT))
pygame.display.set_caption("AI 冒險遊戲")

def main():
    clock = pygame.time.Clock()

    objects = [
        create_box(100, 100, BLUE, "藍色盒子", "一個神秘的藍色盒子，似乎可以存放物品"),
        create_door(300, 200, GREEN, "綠色門", "一扇神秘的綠色門，不知道通向哪裡"),
        create_basic_object(500, 400, WHITE, "白色物件", "一個純淨的白色物件，散發著柔和的光芒"),
        Container(200, 400, 25, 25, (255, 165, 0), "橙色 容器", 3, "一個充滿活力的橙色容器"),
        InteractiveObject(600, 150, 45, 45, (128, 0, 128), "紫色開關", "一個神秘的紫色開關", ["按下", "旋轉"])
    ]

    ai = AI(
        x=WINDOW_WIDTH // 2,
        y=WINDOW_HEIGHT // 2,
        name="智能助手",
        description="一個能夠自主探索和互動的AI"
    )

    ai_controller = AIController(ai, objects)

    try:
        while True:
            clock.tick(60)  # 限制更新頻率
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    ai_controller.cleanup()
                    pygame.quit()
                    sys.exit()

            ai_controller.update() # 更新AI控制器

            screen.fill(BLACK)
            for obj in objects: # 繪製所有物件
                obj.draw(screen) # 繪製物件
            ai.draw(screen) # 繪製AI

            pygame.display.flip()  # 更新顯示
    except KeyboardInterrupt:
        print("遊戲結束")
    finally:
        ai_controller.cleanup() # 清理AI控制器
        pygame.quit() # 退出遊戲
        sys.exit() # 退出程式

if __name__ == "__main__":
    main()
            
```

## memory_manager.py

```py
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
```

## merge_to_md.py

```py
#!/usr/bin/env python3
import os
import argparse
import sys
from pathlib import Path


def get_default_ignore_patterns():
    """獲取預設忽略模式列表"""
    return [
        # 常見隱藏目錄和文件
        '.*',                 # 所有隱藏文件和目錄
        # 常見Python相關
        '__pycache__',
        '*.pyc', '*.pyo', '*.pyd',
        # 常見環境相關
        'venv', 'env', '.venv', '.env',
        # 常見二進制和暫存文件
        '*.exe', '*.dll', '*.so', '*.dylib',
        '*.zip', '*.tar.gz', '*.tgz', '*.7z', '*.rar',
        '*.log', '*.tmp', '*.bak',
        # 常見IDE相關
        '.idea', '.vscode',
        # 其他
        'node_modules',
        'dist', 'build',
        'archive',           # 添加 archive 目錄
        # 其他大型二進制文件
        '*.mp4', '*.avi', '*.mov', '*.mp3', '*.wav'
    ]


def is_binary_file(file_path):
    """檢查文件是否為二進制文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # 嘗試讀取一小部分
        return False
    except UnicodeDecodeError:
        return True


def should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
    """判斷是否應該忽略文件"""
    if file_path == output_path:
        return True
    
    file_name = file_path.name
    relative_path = str(file_path.relative_to(directory_path))
    
    # 檢查文件名和相對路徑是否匹配忽略模式
    for pattern in ignore_patterns:
        if pattern.startswith('*'):
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            if file_name.startswith(pattern[:-1]):
                return True
        elif pattern == relative_path or pattern == file_name:
            return True
    
    # 檢查是否為二進制文件
    if any(file_name.endswith(ext) for ext in ['.exe', '.dll', '.so', '.dylib', '.zip', '.tar.gz', '.7z', '.mp4', '.mp3']):
        return True
        
    return False


def merge_files_to_markdown(directory, output_file, ignore_patterns=None, max_file_size_mb=5, 
                           include_binary=False, verbose=False):
    """
    將目錄下的所有文件合併為一個 Markdown 文件
    
    Args:
        directory: 要掃描的目錄路徑
        output_file: 輸出的 Markdown 文件路徑
        ignore_patterns: 要忽略的文件或目錄模式列表
        max_file_size_mb: 最大文件大小限制（MB）
        include_binary: 是否包含二進制文件
        verbose: 是否顯示詳細訊息
    """
    if ignore_patterns is None:
        ignore_patterns = get_default_ignore_patterns()
    
    # 轉換為絕對路徑
    directory_path = Path(directory).resolve()
    output_path = Path(output_file).resolve()
    
    # 確認目錄存在
    if not directory_path.exists() or not directory_path.is_dir():
        raise ValueError(f"目錄 '{directory}' 不存在或不是一個有效的目錄")
    
    if verbose:
        print(f"掃描目錄: {directory_path}")
        print(f"忽略模式: {ignore_patterns}")
    
    # 獲取所有文件路徑
    all_files = []
    skipped_files = []
    total_files = 0
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    
    for root, dirs, files in os.walk(directory_path):
        # 過濾要忽略的目錄
        dirs_to_remove = []
        for d in dirs:
            dir_path = Path(root) / d
            relative_dir = str(dir_path.relative_to(directory_path))
            
            # 檢查是否匹配忽略模式
            if any(
                (d.startswith('.') and '.*' in ignore_patterns) or
                d == p or relative_dir == p
                for p in ignore_patterns
            ):
                dirs_to_remove.append(d)
                if verbose:
                    print(f"忽略目錄: {relative_dir}")
        
        # 從 dirs 列表中移除要忽略的目錄，這樣 os.walk 就不會進入這些目錄
        for d in dirs_to_remove:
            dirs.remove(d)
            
        for file in files:
            total_files += 1
            file_path = Path(root) / file
            
            # 忽略要排除的文件
            if should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
                skipped_files.append(str(file_path.relative_to(directory_path)))
                if verbose:
                    print(f"忽略文件: {file_path.relative_to(directory_path)}")
                continue
            
            # 檢查文件大小
            file_size = file_path.stat().st_size
            if file_size > max_file_size_bytes:
                skipped_files.append(f"{file_path.relative_to(directory_path)} (文件太大: {file_size/(1024*1024):.2f} MB)")
                if verbose:
                    print(f"忽略過大文件: {file_path.relative_to(directory_path)} ({file_size/(1024*1024):.2f} MB)")
                continue
                
            # 檢查是否為二進制文件
            if not include_binary and is_binary_file(file_path):
                skipped_files.append(f"{file_path.relative_to(directory_path)} (二進制文件)")
                if verbose:
                    print(f"忽略二進制文件: {file_path.relative_to(directory_path)}")
                continue
            
            all_files.append(file_path)
    
    # 排序文件路徑，使輸出更加有序
    all_files.sort()
    
    if verbose:
        print(f"找到 {total_files} 個文件，合併 {len(all_files)} 個文件，跳過 {len(skipped_files)} 個文件")
    
    # 寫入合併後的 Markdown 文件
    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write(f"# 項目文件合併\n\n")
        out_file.write(f"目錄: `{directory_path}`\n\n")
        out_file.write(f"包含 {len(all_files)} 個文件\n\n")
        
        # 如果有跳過的文件，添加一個列表
        if skipped_files and verbose:
            out_file.write("## 跳過的文件\n\n")
            for skipped in skipped_files:
                out_file.write(f"- {skipped}\n")
            out_file.write("\n")
        
        for file_path in all_files:
            # 獲取相對路徑作為標題
            relative_path = file_path.relative_to(directory_path)
            out_file.write(f"## {relative_path}\n\n")
            
            # 嘗試讀取文件內容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 判斷文件類型並設置語法高亮
                file_extension = file_path.suffix.lstrip('.')
                if file_extension:
                    out_file.write(f"```{file_extension}\n")
                else:
                    out_file.write("```\n")
                
                out_file.write(content)
                
                # 確保內容後有換行
                if not content.endswith('\n'):
                    out_file.write('\n')
                out_file.write("```\n\n")
                
            except UnicodeDecodeError:
                out_file.write("```\n[二進制文件，內容無法顯示]\n```\n\n")
            except Exception as e:
                out_file.write(f"```\n[讀取文件時出錯: {str(e)}]\n```\n\n")
    
    return len(all_files), len(skipped_files)


def main():
    parser = argparse.ArgumentParser(description='將目錄下的所有文件合併為一個 Markdown 文件')
    parser.add_argument('directory', nargs='?', default='.', 
                     help='要掃描的目錄路徑 (預設為當前目錄)')
    parser.add_argument('-o', '--output', default='merged_files.md', 
                     help='輸出的 Markdown 文件路徑 (預設為 merged_files.md)')
    parser.add_argument('-i', '--ignore', nargs='+', 
                     help='要忽略的文件或目錄模式 (可以多個)')
    parser.add_argument('-s', '--max-size', type=float, default=5, 
                     help='最大文件大小限制（MB，預設為 5MB）')
    parser.add_argument('-b', '--include-binary', action='store_true', 
                     help='包含二進制文件 (預設不包含)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                     help='顯示詳細訊息')
    
    args = parser.parse_args()
    
    # 合併默認忽略模式和用戶指定的忽略模式
    ignore_patterns = get_default_ignore_patterns()
    if args.ignore:
        ignore_patterns.extend(args.ignore)
    
    try:
        included, skipped = merge_files_to_markdown(
            args.directory, 
            args.output, 
            ignore_patterns=ignore_patterns,
            max_file_size_mb=args.max_size,
            include_binary=args.include_binary,
            verbose=args.verbose
        )
        print(f"成功將 {included} 個文件合併到 {args.output}")
        print(f"跳過了 {skipped} 個文件")
    except Exception as e:
        print(f"合併文件時出錯: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

## movement_manager.py

```py
from dataclasses import dataclass
import math

@dataclass
class MovementResult:
    is_moving: bool
    distance: float
    direction: str
    position: tuple

class MovementManager:
    def __init__(self, ai):
        self.ai = ai
        self.speed = 2  # 確保速度不為0
        self.last_distance = float('inf')
        self.distance_update_threshold = 20
        
    def update_movement(self, target_pos, current_pos):
        """更新 AI 的移動"""
        dx = target_pos[0] - current_pos[0]
        dy = target_pos[1] - current_pos[1]
        distance = (dx**2 + dy**2)**0.5
        
        if distance > 5:
            # 標準化方向向量
            dx = dx / distance * self.speed
            dy = dy / distance * self.speed
            
            # 更新位置
            self.ai.pos[0] += dx
            self.ai.pos[1] += dy
            
            # 重要：同時更新 rect 位置
            self.ai.rect.center = self.ai.pos
            return True
        return False
            
    def get_movement_direction(self, dx, dy):
        """獲取移動方向"""
        if abs(dx) > abs(dy):
            return "水平" if dx > 0 else "水平"
        else:
            return "垂直" if dy > 0 else "垂直"
            
    def handle_movement_feedback(self, movement_result):
        """處理移動反饋"""
        if abs(movement_result.distance - self.last_distance) > self.distance_update_threshold:
            print(f"📍 距離目標還有 {movement_result.distance:.2f} 像素，正在{movement_result.direction}移動")
            self.last_distance = movement_result.distance
            
    def reset_distance_tracking(self):
        """重置距離追蹤"""
        self.last_distance = float('inf') 
```

## thought_manager.py

```py
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
```

## worlds/world_test.json

```json
{
  "world_name": "神秘豪宅",
  "description": "一座充滿謎團的古老豪宅，隱藏著許多秘密...",
  "spaces": [
    {
      "name": "living_room",
      "description": "一個優雅的客廳，陽光透過高大的窗戶灑落，使華麗的音樂盒閃閃發光。一面美麗的鏡子立在角落，為房間增添深度。",
      "connected_spaces": ["kitchen", "garden", "basement", "study_room"],
      "items": ["music_box", "mirror"],
      "npcs": ["arthur"]
      
    },
    {
      "name": "study_room",
      "description": "一間舒適的書房，木製書架排列整齊。溫暖的燈光創造了完美的閱讀和寫作氛圍。桌上放著一本個人日記，書架上的一本古老書籍引起了你的注意。",
      "connected_spaces": ["attic", "living_room"],
      "items": ["personal_diary", "ancient_book"],
      "npcs": []
    },
    {
      "name": "kitchen",
      "description": "一個溫馨宜人的廚房，銅鍋從天花板上懸掛下來，陽光透過水槽上方的窗戶灑落。櫃檯上放著一本食譜，旁邊是一套精美的茶具，隨時可以使用。",
      "connected_spaces": ["living_room"],
      "items": ["cookbook", "tea_set", "cooking_pot"],
      "npcs": []
    },
    {
      "name": "garden",
      "description": "一個茂盛的花園，色彩繽紛的花朵和芳香的草本植物隨處可見。石頭小徑穿過綠意盎然的植物，通往一個寧靜的石凳。一個銅製澆水壺放在一旁，隨時可以照料植物。",
      "connected_spaces": ["living_room"],
      "items": ["watering_can", "stone_bench"],
      "npcs": []
    },
    {
      "name": "attic",
      "description": "一個寬敞的閣樓，灰塵在小圓窗透進的光束中飛舞。一個舊木箱放在角落，而一個黃銅望遠鏡立在窗邊，指向天空。",
      "connected_spaces": ["study_room"],
      "items": ["old_chest", "telescope"],
      "npcs": []
    },
    {
      "name": "basement",
      "description": "一個光線昏暗的地下室，石牆和略微潮濕的氛圍。牆上的架子上擺滿了舊瓶子和奇特的工藝品。中央放著一個神秘裝置，閃爍著燈光，齒輪複雜精緻。",
      "connected_spaces": ["living_room"],
      "items": ["mysterious_device"],
      "npcs": []
    }
  ],
  "items": [
    {
      "name": "personal_diary",
      "description": "一本皮革裝訂的日記，頁面鑲有金邊，準備記錄思想和回憶。",
      "interactions": {
        "read": null,
        "write": {"content": "str"},
        "inspect": null
      },
      "properties": {
        "content": "親愛的日記，今天我開始了在這個神秘地方的旅程..."
      }
    },
    {
      "name": "ancient_book",
      "description": "一本破舊的古書，封面上有神秘符號，頁面充滿了迷人的故事。",
      "interactions": {
        "read": null,
        "inspect": null
      },
      "properties": {
        "content": "在奇蹟的時代，當魔法仍然自由地流動於世界之中..."
      }
    },
    {
      "name": "music_box",
      "description": "一個裝飾著舞蹈人物的華麗音樂盒，能夠播放迷人的旋律。",
      "interactions": {
        "play": null,
        "stop": null,
        "inspect": null
      },
      "properties": {
        "is_playing": false
      }
    },
    {
      "name": "mirror",
      "description": "一面鍍金框架的優雅全身鏡，完美清晰地反射著房間。",
      "interactions": {
        "inspect": null
      },
      "properties": {}
    },
    {
      "name": "cookbook",
      "description": "一本使用過的食譜書，邊緣有手寫筆記，喜愛的食譜頁角已經折疊標記。",
      "interactions": {
        "read": null,
        "inspect": null
      },
      "properties": {}
    },
    {
      "name": "tea_set",
      "description": "一套精緻的花卉圖案瓷器茶具，非常適合沖泡和供應茶。",
      "interactions": {
        "use": null,
        "inspect": null
      },
      "properties": {
        "is_brewing": false
      }
    },
    {
      "name": "cooking_pot",
      "description": "一個帶有堅固把手的大型銅鍋，非常適合烹飪豐盛的餐點。",
      "interactions": {
        "cook": {"ingredient": "str"},
        "examine": null,
        "clean": null
      },
      "properties": {
        "contents": "",
        "is_clean": true
      }
    },
    {
      "name": "watering_can",
      "description": "一個帶有長嘴的彩繪金屬澆水壺，非常適合照料花園植物。",
      "interactions": {
        "fill": null,
        "water": {"plant": "str"},
        "inspect": null
      },
      "properties": {
        "water_level": 0,
        "max_capacity": 10
      }
    },
    {
      "name": "stone_bench",
      "description": "一個風化的石凳，坐落在開花植物之間，提供一個寧靜的沉思之地。",
      "interactions": {
        "sit": null,
        "inspect": null
      },
      "properties": {}
    },
    {
      "name": "old_chest",
      "description": "一個帶有鐵配件的塵土飛揚的木箱，上鎖且似乎多年未被觸碰。",
      "interactions": {
        "open": null,
        "inspect": null
      },
      "properties": {
        "is_locked": true
      }
    },
    {
      "name": "telescope",
      "description": "一個安裝在窗邊的古董黃銅望遠鏡，指向夜空。",
      "interactions": {
        "use": null,
        "adjust": null,
        "inspect": null
      },
      "properties": {
        "is_focused": false
      }
    },
    {
      "name": "mysterious_device",
      "description": "一個奇怪的機械裝置，帶有齒輪、按鈕和閃爍的燈光，用途不明。",
      "interactions": {
        "activate": null,
        "adjust": {"setting": "str"},
        "disassemble": null,
        "inspect": null
      },
      "properties": {
        "is_active": false,
        "current_setting": "standby",
        "energy_level": 75
      }
    }
  ],
  "npcs": [
    {
      "name": "arthur",
      "description": "一位好奇且思考深入的探險家，對發掘故事和謎團有濃厚興趣。",
      "starting_space": "living_room",
      "inventory": [],
      "history": [
        {
          "role": "system",
          "content": "你是亞瑟，一位好奇的探險家，發現自己身處一座引人入勝的房子。\n你可以：\n- 探索不同的房間\n- 與你找到的物品互動\n- 如果找到日記，記錄你的想法\n- 享受音樂盒的音樂\n\n你特別感興趣的是：\n- 記下你的觀察和感受\n- 理解你找到的物品背後的故事\n- 用音樂創造平靜的氛圍\n\n慢慢探索並與周圍環境互動。"
        },
        {
          "role": "assistant",
          "content": "我發現自己在這座有趣的房子裡。我應該探索並與我發現的東西互動。我想探索其他空間"
        }
      ]
    }
  ]
} 
```

