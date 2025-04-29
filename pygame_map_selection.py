import pygame
import glob
import os

def pygame_map_selection(maps_dir='worlds/maps'):
    pygame.init()
    # 設定一個較大的預設解析度，並允許調整大小
    info = pygame.display.Info()
    width, height = int(info.current_w * 0.95), int(info.current_h * 0.95)
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    pygame.display.set_caption("選擇地圖")
    font = pygame.font.Font("pygame/msjh.ttf", 48)
    button_font = pygame.font.SysFont("arial", 36)
    clock = pygame.time.Clock()
    map_files = glob.glob(f"{maps_dir}/*.json")
    map_files = [os.path.basename(f) for f in map_files]
    if not map_files:
        raise RuntimeError("找不到任何地圖檔案！請確認 maps 資料夾下有 .json 檔案。")
    selected = None
    running = True
    while running:
        screen.fill((30, 30, 60))
        # 標題
        title = font.render("請選擇要載入的地圖", True, (255, 255, 0))
        title_rect = title.get_rect(center=(screen.get_width() // 2, 100))
        screen.blit(title, title_rect)
        # 計算按鈕位置
        button_w, button_h = 600, 80
        gap = 30
        total_h = len(map_files) * (button_h + gap) - gap
        start_y = (screen.get_height() - total_h) // 2
        mouse_pos = pygame.mouse.get_pos()
        for i, fname in enumerate(map_files):
            x = (screen.get_width() - button_w) // 2
            y = start_y + i * (button_h + gap)
            rect = pygame.Rect(x, y, button_w, button_h)
            color = (100, 200, 255) if rect.collidepoint(mouse_pos) else (80, 80, 180)
            pygame.draw.rect(screen, color, rect, border_radius=20)
            pygame.draw.rect(screen, (255, 255, 255), rect, 4, border_radius=20)
            text = button_font.render(fname, True, (0, 0, 0))
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)
            if rect.collidepoint(mouse_pos):
                if pygame.mouse.get_pressed()[0]:
                    selected = fname
        # 按 ESC 離開
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                pygame.quit()
                exit()
        pygame.display.flip()
        clock.tick(60)
        if selected:
            pygame.time.wait(200)  # 防止多次點擊
            break
    pygame.quit()
    return os.path.join(maps_dir, selected)