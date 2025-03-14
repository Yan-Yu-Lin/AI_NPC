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
