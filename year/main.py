import pygame
from game_objects import GameObject, Player, AI
from ai_controller import AIController

pygame.init()

width, height = 1200, 800
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("AI互動系統")

# 設定玩家
player = Player(100, 100, 20, 5)

# 設定AI
ai = AI(150, 150, 20, 2)

# 物品列表
objects = [
    GameObject(
        "桌子",
        pygame.Rect(400, 300, 100, 50),
        ["查看", "移動"],
        "一張木製的桌子，表面有些許灰塵，看起來很穩固",
        "灰塵",
        [
            "這張桌子看起來很適合放東西",
            "桌面有點髒，需要擦拭",
        ]
    ),
    GameObject(
        "筆記本",
        pygame.Rect(600, 400, 50, 30),
        ["查看", "撿起"],
        "一本嶄新的筆記本，封面是藍色的，看起來很乾淨",
        "嶄新",
        [
            "這本筆記本看起來很適合寫字",
            "筆記本很新，應該要好好保管",
            "這本筆記本放在這裡不太合適，應該要放在桌子上"
        ]
    ),
    GameObject(
        "門",
        pygame.Rect(800, 200, 80, 150),
        ["打開", "敲門"],
        "一扇木門，看起來有些老舊，門把是銅製的",
        "老舊",
        [
            "這扇門看起來有點老舊，不知道會不會發出聲音",
            "門把是銅製的，摸起來應該很涼",
            "這扇門通向哪裡呢？"
        ]
    )
]

# 初始化AI控制器
ai_controller = AIController(ai, objects)

last_interaction_object = None
last_interaction = None

running = True
while running:
    screen.fill((0, 128, 255))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player.move(-player.speed, 0)
    if keys[pygame.K_RIGHT]:
        player.move(player.speed, 0)
    if keys[pygame.K_UP]:
        player.move(0, -player.speed)
    if keys[pygame.K_DOWN]:
        player.move(0, player.speed)

    pygame.draw.circle(screen, (255, 0, 0), player.pos, player.radius)
    pygame.draw.circle(screen, (0, 255, 0), ai.pos, ai.radius)

    # 繪製物品
    for obj in objects:
        pygame.draw.rect(screen, (139, 69, 19), obj.rect)

    # 偵測玩家是否靠近物品
    nearby_object = next((obj for obj in objects if obj.rect.colliderect(player.rect.inflate(50, 50))), None)

    if nearby_object and last_interaction_object != nearby_object:
        print(f"你靠近了 {nearby_object.name}")
        print("選項：")
        for i, action in enumerate(nearby_object.interactions):
            print(f"{i+1}. {action}")
        last_interaction_object = nearby_object

    if nearby_object is None:
        last_interaction_object = None
        last_interaction = None

    # 玩家按鍵觸發互動
    if keys[pygame.K_1] and last_interaction is None and nearby_object:
        print(f"執行動作：{nearby_object.interactions[0]}")
        last_interaction = nearby_object.interactions[0]
    if keys[pygame.K_2] and last_interaction is None and nearby_object and len(nearby_object.interactions) > 1:
        print(f"執行動作：{nearby_object.interactions[1]}")
        last_interaction = nearby_object.interactions[1]

    # AI 行動
    ai_controller.update()

    pygame.display.flip()

# 清理工作執行緒
ai_controller.cleanup()

pygame.quit()
