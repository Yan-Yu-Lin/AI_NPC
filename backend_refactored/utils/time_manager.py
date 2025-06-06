"""
Time Manager - 時間管理器

管理遊戲世界的時間系統。
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TimeManager:
    """
    時間管理器
    
    負責管理遊戲世界的時間流逝、天氣變化等。
    """
    
    def __init__(self):
        """初始化時間管理器"""
        self.current_time = "上午8:00"
        self.world_day = 1
        self.tick_count = 0
        self.weather = "晴朗"
        self.time_speed = 10  # 每個 tick 推進的分鐘數
        
        # 天氣選項
        self.weather_options = ["晴朗", "多雲", "陰天", "小雨", "大雨", "霧天", "雪天"]
        self.weather_change_chance = 0.1  # 10% 機率改變天氣
        
    def initialize(self):
        """初始化時間管理器"""
        logger.info("TimeManager initialized")
    
    def advance_time(self) -> str:
        """
        推進世界時間
        
        Returns:
            時間更新訊息
        """
        self.tick_count += 1
        
        # 解析當前時間
        try:
            hour, minute = self._parse_time()
            
            # 推進時間
            minute += self.time_speed
            
            # 處理進位
            if minute >= 60:
                hour += minute // 60
                minute = minute % 60
            
            # 處理天數進位
            if hour >= 24:
                self.world_day += hour // 24
                hour = hour % 24
                self._maybe_change_weather()
            
            # 格式化新時間
            self.current_time = self._format_time(hour, minute)
            
            # 返回更新訊息
            return self._get_time_update_message()
            
        except Exception as e:
            logger.error(f"Error advancing time: {e}")
            return "時間系統錯誤"
    
    def _parse_time(self) -> tuple:
        """
        解析當前時間字串
        
        Returns:
            (小時, 分鐘) 元組
        """
        time_str = self.current_time
        
        # 移除中文前綴並解析
        for prefix in ["深夜", "上午", "中午", "下午", "晚上"]:
            if prefix in time_str:
                time_part = time_str.replace(prefix, "")
                hour, minute = map(int, time_part.split(":"))
                
                # 調整小時數
                if prefix == "下午" and hour != 12:
                    hour += 12
                elif prefix == "晚上" and hour != 12:
                    hour += 12
                
                return hour, minute
        
        # 預設值
        return 8, 0
    
    def _format_time(self, hour: int, minute: int) -> str:
        """
        格式化時間為中文格式
        
        Args:
            hour: 小時 (0-23)
            minute: 分鐘 (0-59)
            
        Returns:
            格式化的時間字串
        """
        if 0 <= hour < 6:
            return f"深夜{hour:02d}:{minute:02d}"
        elif 6 <= hour < 12:
            return f"上午{hour:02d}:{minute:02d}"
        elif hour == 12:
            return f"中午{hour:02d}:{minute:02d}"
        elif 13 <= hour < 18:
            return f"下午{hour-12:02d}:{minute:02d}"
        else:
            return f"晚上{hour-12:02d}:{minute:02d}"
    
    def _maybe_change_weather(self):
        """可能改變天氣"""
        import random
        
        if random.random() < self.weather_change_chance:
            old_weather = self.weather
            self.weather = random.choice(self.weather_options)
            if self.weather != old_weather:
                logger.info(f"Weather changed from {old_weather} to {self.weather}")
    
    def _get_time_update_message(self) -> str:
        """獲取時間更新訊息"""
        day_info = f"第{self.world_day}天" if self.world_day > 1 else "今天"
        return f"時間流逝了{self.time_speed}分鐘，現在是{day_info}{self.current_time}，天氣：{self.weather}。"
    
    def get_formatted_time(self) -> str:
        """獲取格式化的當前時間"""
        day_info = f"第{self.world_day}天" if self.world_day > 1 else "今天"
        return f"{day_info} {self.current_time}"
    
    def get_time_of_day(self) -> str:
        """
        獲取當前時段
        
        Returns:
            時段名稱（深夜、早晨、上午、中午、下午、傍晚、晚上）
        """
        hour, _ = self._parse_time()
        
        if 0 <= hour < 6:
            return "深夜"
        elif 6 <= hour < 9:
            return "早晨"
        elif 9 <= hour < 12:
            return "上午"
        elif hour == 12:
            return "中午"
        elif 13 <= hour < 17:
            return "下午"
        elif 17 <= hour < 19:
            return "傍晚"
        else:
            return "晚上"
    
    def is_daytime(self) -> bool:
        """檢查是否為白天"""
        hour, _ = self._parse_time()
        return 6 <= hour < 18
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "current_time": self.current_time,
            "world_day": self.world_day,
            "tick_count": self.tick_count,
            "weather": self.weather,
            "time_speed": self.time_speed
        }
    
    def from_dict(self, data: Dict[str, Any]):
        """從字典載入"""
        self.current_time = data.get("current_time", "上午8:00")
        self.world_day = data.get("world_day", 1)
        self.tick_count = data.get("tick_count", 0)
        self.weather = data.get("weather", "晴朗")
        self.time_speed = data.get("time_speed", 10)