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
            