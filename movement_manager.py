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