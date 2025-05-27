import pygame

pygame.init()  # mixer 포함 모든 초기화

# 디스플레이 설정
screen = pygame.display.set_mode((800, 600))  # 해상도는 적절히 조절

# 사운드 로드 및 재생
vanishing_sfx = pygame.mixer.Sound("sounds/vanishing-sfx.mp3")
vanishing_sfx.play()

# 종료 전까지 대기
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    pygame.display.update()
