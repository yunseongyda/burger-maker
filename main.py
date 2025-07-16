# pip install -r requirements.txt

import pygame
import cv2
import numpy as np
import sys
import random
import mediapipe as mp
import time
import json
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

pygame.init()
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

if not cap.isOpened():
    print("카메라 연동 실패")
else:
    print("카메라 연동 성공")

# SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("Burger Maker")

font = pygame.font.SysFont(None, 36)
big_font = pygame.font.SysFont(None, 72)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (200, 50, 50)
GRAY = (200, 200, 200)
DARK_GRAY = (100, 100, 100)
BLUE = (0, 100, 255)
DARK_BLUE = (0, 50, 150)
BROWN = (222, 184, 135)
GREEN = (0, 200, 0)
DARK_RED = (150, 0, 0)
PINK = (255, 105, 180)

vanishing_sfx = pygame.mixer.Sound(resource_path("sounds/vanishing-sfx.mp3"))
grabbing_sfx = pygame.mixer.Sound(resource_path("sounds/grabbing-sfx.mp3"))
click_sfx = pygame.mixer.Sound(resource_path("sounds/button_click.mp3"))
click_sfx.set_volume(0.25)
submit_sfx = pygame.mixer.Sound(resource_path("sounds/submit-bell.mp3"))

# BGM 설정
bgm_files = [resource_path("sounds/bgm/bgm1.mp3"), resource_path("sounds/bgm/bgm2.mp3"), resource_path("sounds/bgm/bgm3.mp3"), resource_path("sounds/bgm/bgm4.mp3")]
current_bgm_index = 0
bgm_on = True  # BGM 상태 변수
pygame.mixer.music.load(bgm_files[current_bgm_index])
pygame.mixer.music.set_volume(0.25)  # 기본 볼륨 설정


# 손 상태 이미지 로드
open_hand_img = pygame.image.load(resource_path("images/opened-hand.png")).convert_alpha()
closed_hand_img = pygame.image.load(resource_path("images/closed-hand.png")).convert_alpha()

# 사이즈 조절 (적당히)
open_hand_img = pygame.transform.scale(open_hand_img, (50, 50))
closed_hand_img = pygame.transform.scale(closed_hand_img, (50, 50))


# 설명서 페이지
showing_rule_page = False
game_rule_img = pygame.image.load(resource_path("images/GameRulePage.png")).convert()
game_rule_img = pygame.transform.scale(game_rule_img, (SCREEN_WIDTH, SCREEN_HEIGHT))  # 전체 화면에 맞게

# 이름 저장 완료 타이머
saved_message_timer = 0
saved_message_alpha = 0

# 메뉴에서 보여줄 저장 메시지
menu_saved_message_timer = 0
menu_saved_message_alpha = 0
menu_saved_rank = None  # 몇 등인지 저장

ranking_file = os.path.join(os.path.dirname(sys.executable), "ranking.json")
input_active = False
user_input = ""

# 접시,벨,쓰레기통 이미지
dish_img = pygame.image.load(resource_path("images/dish.png")).convert_alpha()
bell_img = pygame.image.load(resource_path("images/bell.png")).convert_alpha()
trashbin_img = pygame.image.load(resource_path("images/trashbin.png")).convert_alpha()

# 게임 화면 이미지
game_bg = pygame.image.load(resource_path("images/GameScreen.png")).convert()
game_bg = pygame.transform.scale(game_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

# 말풍선
talk_balloon_img = pygame.image.load(resource_path("images/howtoplay.png")).convert_alpha()

def save_score(name, score, overwrite=False):
    data = []
    if os.path.exists(ranking_file):
        with open(ranking_file, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    if overwrite:
        data = [entry for entry in data if entry["name"] != name]
    data.append({"name": name, "score": score})
    data.sort(key=lambda x: x["score"], reverse=True)
    with open(ranking_file, "w") as f:
        json.dump(data, f, indent=2)
        f.flush() # 파일 시스템에 즉시 반영
        os.fsync(f.fileno()) # 디스크에 강제 기록록

def get_player_rank(name):
    if not os.path.exists(ranking_file):
        print("파일 없음")
        return None
    with open(ranking_file, "r") as f:
        try:
            data = json.load(f)
            print(f"불러온 데이터: {data}")
            for idx, entry in enumerate(data):
                print(f"비교중: {entry['name']} == {name}")
                if entry["name"] == name:
                    print(f"매칭된 등수: {idx+1}")
                    return idx + 1  # 등수는 1부터 시작
        except json.JSONDecodeError:
            print("JSON 파싱 실패")
            pass
    return None

def reset_game_state():
    global score, round_count, total_accuracy_score, cheat_index
    global all_recipes, current_recipe, items_on_screen, held_item, burger_start_time
    global burger_goal

    score = 0
    round_count = 0
    total_accuracy_score = 0
    cheat_index = 0
    items_on_screen.clear()
    held_item = None
    round_scores.clear()

    all_recipes = []
    for _ in range(burger_goal):
        recipe = ["bottom_bun"] + random.sample(ingredient_names[2:], random.randint(2, 4)) + ["top_bun"]
        all_recipes.append(recipe)

    current_recipe = all_recipes.pop(random.randrange(len(all_recipes)))
    burger_start_time = time.time()


def draw_input_modal():
    BASE_WIDTH, BASE_HEIGHT = 1920, 1080
    width_ratio = SCREEN_WIDTH / BASE_WIDTH
    height_ratio = SCREEN_HEIGHT / BASE_HEIGHT

    # Responsive font
    font_size = int(36 * height_ratio)
    responsive_font = pygame.font.SysFont(None, font_size)

    # Responsive modal box
    box_width = int(400 * width_ratio)
    box_height = int(80 * height_ratio)
    box_x = SCREEN_WIDTH/2 - box_width/2
    box_y = SCREEN_HEIGHT/2 + int(120 * height_ratio)
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height), border_radius=12)
    pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2, border_radius=12)
    
    # Responsive text
    input_text = responsive_font.render(f"Enter your name: {user_input}", True, BLACK)
    screen.blit(input_text, input_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + int(160 * height_ratio))))

def draw_overwrite_prompt():
    BASE_WIDTH, BASE_HEIGHT = 1920, 1080
    width_ratio = SCREEN_WIDTH / BASE_WIDTH
    height_ratio = SCREEN_HEIGHT / BASE_HEIGHT

    # Responsive font
    font_size = int(36 * height_ratio)
    responsive_font = pygame.font.SysFont(None, font_size)

    # Responsive modal box
    box_width = int(700 * width_ratio)
    box_height = int(170 * height_ratio)
    box_x = SCREEN_WIDTH/2 - box_width/2
    box_y = SCREEN_HEIGHT/2 - box_height/2 + 25
    pygame.draw.rect(screen, WHITE, (box_x, box_y, box_width, box_height), border_radius=12)
    pygame.draw.rect(screen, BLACK, (box_x, box_y, box_width, box_height), 2, border_radius=12)
    
    # Responsive text
    warning_text = responsive_font.render("Your name is duplicated. Do you want to overwrite?", True, BLACK)
    screen.blit(warning_text, warning_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))

    # Responsive buttons
    button_width = int(80 * width_ratio)
    button_height = int(40 * height_ratio)
    yes_button_x = SCREEN_WIDTH//2 - button_width - int(20 * width_ratio)
    no_button_x = SCREEN_WIDTH//2 + int(20 * width_ratio)
    button_y = SCREEN_HEIGHT//2 + int(40 * height_ratio)

    overwrite_buttons["yes"] = pygame.Rect(yes_button_x, button_y, button_width, button_height)
    overwrite_buttons["no"] = pygame.Rect(no_button_x, button_y, button_width, button_height)

    pygame.draw.rect(screen, GREEN, overwrite_buttons["yes"], border_radius=6)
    yes_text = responsive_font.render("Yes", True, WHITE)
    screen.blit(yes_text, yes_text.get_rect(center=overwrite_buttons["yes"].center))

    pygame.draw.rect(screen, RED, overwrite_buttons["no"], border_radius=6)
    no_text = responsive_font.render("No", True, WHITE)
    screen.blit(no_text, no_text.get_rect(center=overwrite_buttons["no"].center))


clock = pygame.time.Clock()

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.5)
mp_draw = mp.solutions.drawing_utils
menu_active = True
running = True

burger_goal = 10
round_scores = []

# 중복 이름 덮어쓰기 관련
overwrite_prompt_active = False        # 중복 이름 여부 묻는 상태
overwrite_pending_name = ""            # 중복된 이름
overwrite_buttons = {
    "yes": pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 40, 80, 40),
    "no": pygame.Rect(SCREEN_WIDTH//2 + 20, SCREEN_HEIGHT//2 + 40, 80, 40)
}


start_button_img = pygame.image.load(resource_path("images/button.png")).convert_alpha()
start_button_img = pygame.transform.scale(start_button_img, (450, 150))
start_button_img.set_colorkey((255, 255, 255))
start_button_rect = start_button_img.get_rect(center=(SCREEN_WIDTH // 2 + 2, SCREEN_HEIGHT // 2 + 400))

leaderboard_button_img = pygame.image.load(resource_path("images/button.png")).convert_alpha()
leaderboard_button_img = pygame.transform.scale(leaderboard_button_img, (450, 150))
leaderboard_button_img.set_colorkey((255, 255, 255))
leaderboard_button_rect = leaderboard_button_img.get_rect(center=(SCREEN_WIDTH // 2 + 523, SCREEN_HEIGHT // 2 + 400))

option_button_img = pygame.image.load(resource_path("images/button.png")).convert_alpha()
option_button_img = pygame.transform.scale(option_button_img, (450, 150))
option_button_img.set_colorkey((255, 255, 255))
option_button_rect = option_button_img.get_rect(center=(SCREEN_WIDTH // 2 - 530, SCREEN_HEIGHT // 2 + 400))


hand_status = "Detecting hand..."
prev_hand_status = "None"
message_alpha = 0
message_timer = 0
MESSAGE_DURATION = 60
hand_screen_pos = None

held_item = None
items_on_screen = []

ITEM_RADIUS = 50
PLATE_RADIUS = 100
plate_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 60)

ingredient_names = ["top_bun", "bottom_bun", "patty", "bacon", "lettuce", "pickle", "tomato", "onion", "cheese"]
ingredient_spawns = {}
spacing = ITEM_RADIUS * 2 + 20
start_x = (SCREEN_WIDTH - (spacing * (len(ingredient_names) - 1))) // 2
start_y = SCREEN_HEIGHT - ITEM_RADIUS - 40
for i, name in enumerate(ingredient_names):
    ingredient_spawns[name] = (start_x + i * spacing, start_y)

ingredient_images = {}
for name in ingredient_names:
    # load the “item” icon
    img_item = pygame.image.load(resource_path(f"images/{name}_item.png")).convert_alpha()
    img_item.set_colorkey(WHITE)
    # load the “in stain” icon
    img_stain = pygame.image.load(resource_path(f"images/{name}_in_stain.png")).convert_alpha()
    img_stain.set_colorkey(WHITE)
    # store as a dict for clarity
    ingredient_images[name] = {
        "item": img_item,
        "in_stain": img_stain
    }

reset_button_rect = pygame.Rect(SCREEN_WIDTH - 350, SCREEN_HEIGHT //2 +50, 160, 60)
submit_button_rect = pygame.Rect(SCREEN_WIDTH - 450, SCREEN_HEIGHT //2 -150, 200, 200)


BURGER_TIME_LIMIT = 30
burger_start_time = time.time()
reset_game_state()


# 메뉴 버튼 위치 비율 전역 변수
MENU_BUTTON_Y_RATIO = 0.88
MENU_BUTTON_WIDTH_RATIO = 0.18
MENU_BUTTON_HEIGHT_RATIO = 0.12

# 개별 버튼 X 위치 비율
OPTION_X_RATIO = 0.25
PLAY_X_RATIO = 0.5
QUIT_X_RATIO = 0.75


# 메뉴 버튼 위치 비율 전역 변수
MENU_BUTTON_Y_RATIO = 0.88
MENU_BUTTON_WIDTH_RATIO = 0.18  # 화면 너비의 18%
MENU_BUTTON_HEIGHT_RATIO = 0.12  # 화면 높이의 12%

# 개별 버튼 X 위치 비율
OPTION_X_RATIO = 0.23
PLAY_X_RATIO = 0.5
QUIT_X_RATIO = 0.77

# 인게임 반응형 요소 비율
STATUS_FONT_RATIO = 0.035
ITEM_RADIUS_RATIO = 0.03
PLATE_RADIUS_RATIO = 0.08
CAMERA_WIDTH_RATIO = 0.3
CAMERA_HEIGHT_RATIO = 0.3

status_font = pygame.font.SysFont(None, 36)

# 인게임 반응형 값 설정 (main loop 진입 직후 호출)
def apply_responsive_scaling():
    global ITEM_RADIUS, PLATE_RADIUS, status_font, camera_surface, plate_pos
    global ingredient_spawns, reset_button_rect, submit_button_rect
    global game_bg

    game_bg = pygame.transform.scale(game_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    # 반응형 크기 설정
    ITEM_RADIUS = int(SCREEN_WIDTH * ITEM_RADIUS_RATIO)
    PLATE_RADIUS = int(SCREEN_WIDTH * PLATE_RADIUS_RATIO)
    status_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * STATUS_FONT_RATIO))
    camera_surface = pygame.Surface((
        int(SCREEN_WIDTH * CAMERA_WIDTH_RATIO),
        int(SCREEN_HEIGHT * CAMERA_HEIGHT_RATIO)
    ))


    # 접시 위치
    plate_pos = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - ITEM_RADIUS * 2)

    # 재료 위치 (하단 중앙 정렬)
    spacing = ITEM_RADIUS * 2 + 20
    start_x = (SCREEN_WIDTH - (spacing * (len(ingredient_names) - 1))) // 2
    start_y = SCREEN_HEIGHT - ITEM_RADIUS - 40
    for i, name in enumerate(ingredient_names):
        ingredient_spawns[name] = (start_x + i * spacing, start_y)

    # 버튼 위치 (우측 중간, 화면 비율 기반)
    reset_button_rect = pygame.Rect(SCREEN_WIDTH - int(SCREEN_WIDTH * 0.18),
                                     SCREEN_HEIGHT // 2 + int(SCREEN_HEIGHT * 0.05),
                                     int(SCREEN_WIDTH * 0.1), int(SCREEN_HEIGHT * 0.08))
    submit_button_rect = pygame.Rect(SCREEN_WIDTH - int(SCREEN_WIDTH * 0.28),
                                      SCREEN_HEIGHT // 2 - int(SCREEN_HEIGHT * 0.18),
                                      int(SCREEN_WIDTH * 0.12), int(SCREEN_WIDTH * 0.12))


def draw_menu():
    global talk_balloon_area, exit_button_rect

    # 버튼 중심 좌표
    option_x = int(SCREEN_WIDTH * OPTION_X_RATIO)
    play_x = int(SCREEN_WIDTH * PLAY_X_RATIO)
    quit_x = int(SCREEN_WIDTH * QUIT_X_RATIO)
    button_y = int(SCREEN_HEIGHT * MENU_BUTTON_Y_RATIO)

    # 버튼 이미지 크기 계산
    button_width = int(SCREEN_WIDTH * MENU_BUTTON_WIDTH_RATIO)
    button_height = int(SCREEN_HEIGHT * MENU_BUTTON_HEIGHT_RATIO)

    scaled_start_button = pygame.transform.scale(start_button_img, (button_width, button_height))
    scaled_option_button = pygame.transform.scale(option_button_img, (button_width, button_height))
    scaled_leaderboard_button = pygame.transform.scale(leaderboard_button_img, (button_width, button_height))

    # 버튼 위치 재계산
    start_button_rect.size = (button_width, button_height)
    option_button_rect.size = (button_width, button_height)
    leaderboard_button_rect.size = (button_width, button_height)
    start_button_rect.center = (play_x, button_y)
    option_button_rect.center = (option_x, button_y)
    leaderboard_button_rect.center = (quit_x, button_y)
    
    main_menu_bg = pygame.image.load(resource_path('images/main_menu_bg.png')).convert()
    main_menu_bg = pygame.transform.scale(main_menu_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(main_menu_bg, (0, 0))

    # 버튼 이미지 출력 (반응형)
    screen.blit(scaled_start_button, start_button_rect)
    screen.blit(scaled_option_button, option_button_rect)
    screen.blit(scaled_leaderboard_button, leaderboard_button_rect)

    # 텍스트 크기 비율에 따라 동적으로 설정
    font_size = max(24, int(SCREEN_HEIGHT * 0.065))  # 해상도에 따라 크게 조절, 최소 24
    responsive_font = pygame.font.SysFont(None, font_size)

    # Play 텍스트
    play_text = responsive_font.render("Play", True, WHITE)
    play_rect = play_text.get_rect(center=start_button_rect.center)
    screen.blit(play_text, play_rect)

    # Option 텍스트
    option_text = responsive_font.render("Options", True, WHITE)
    option_rect = option_text.get_rect(center=option_button_rect.center)
    screen.blit(option_text, option_rect)
    
    # LeaderBoard 텍스트
    leaderboard_text = responsive_font.render("LeaderBoard", True, WHITE)
    leaderboard_rect = leaderboard_text.get_rect(center=leaderboard_button_rect.center)
    screen.blit(leaderboard_text, leaderboard_rect)

    # 반응형 X 버튼 생성
    exit_button_size = int(SCREEN_WIDTH * 0.04)
    exit_button_rect = pygame.Rect(SCREEN_WIDTH - exit_button_size - int(SCREEN_WIDTH * 0.01), int(SCREEN_HEIGHT * 0.02), exit_button_size, exit_button_size)
    pygame.draw.rect(screen, RED, exit_button_rect)
    x_font_size = int(exit_button_size * 0.8)
    x_font = pygame.font.SysFont(None, x_font_size)
    x_text = x_font.render("X", True, WHITE)
    x_rect = x_text.get_rect(center=exit_button_rect.center)
    screen.blit(x_text, x_rect)


    # Saved! 메시지 (1회용)
    global menu_saved_message_timer, menu_saved_message_alpha, menu_saved_rank
    if menu_saved_message_timer > 0:
        saved_font = pygame.font.SysFont(None, 72)
        message = "Saved!"
        if menu_saved_rank is not None:
            message += f" You are ranked #{menu_saved_rank}"
        saved_surface = saved_font.render(message, True, (0, 150, 0))
        saved_surface.set_alpha(menu_saved_message_alpha)
        
        # 메시지 위치 계산
        text_rect = saved_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 0))
        
        # 반투명 배경 Surface 만들기
        background_surface = pygame.Surface((text_rect.width + 40, text_rect.height + 20), pygame.SRCALPHA)
        background_surface.fill((255, 255, 255, 180))  # 흰색, 약간 투명

        # 배경 박스를 텍스트보다 먼저 blit
        screen.blit(background_surface, background_surface.get_rect(center=text_rect.center))

        # 텍스트 그리기
        screen.blit(saved_surface, text_rect)

        
        menu_saved_message_timer -= 1
        if menu_saved_message_timer < 30:
            menu_saved_message_alpha = max(0, int(255 * (menu_saved_message_timer / 30)))


    # 말풍선 이미지 크기 조절 (적당히 줄이기)
    scaled_balloon = pygame.transform.scale(talk_balloon_img, (int(SCREEN_WIDTH) * 0.06, int(SCREEN_HEIGHT) * 0.1))

    # 위치 조정: 아저씨 얼굴 오른쪽 위
    balloon_rect = scaled_balloon.get_rect()
    balloon_rect.topleft = (int(SCREEN_WIDTH * 0.93), int(SCREEN_HEIGHT * 0.4))

    talk_balloon_area = balloon_rect

    # 화면에 말풍선 표시
    screen.blit(scaled_balloon, balloon_rect)

    if showing_rule_page:
        screen.blit(game_rule_img, (0, 0))

        # 좌측 하단 닫기 버튼 만들기
        close_btn_width = int(SCREEN_WIDTH * 0.12)
        close_btn_height = int(SCREEN_HEIGHT * 0.06)
        close_btn_x = int(SCREEN_WIDTH * 0.05)
        close_btn_y = int(SCREEN_HEIGHT * 0.85)

        close_btn = pygame.Rect(close_btn_x, close_btn_y, close_btn_width, close_btn_height)
        
        pygame.draw.rect(screen, BLUE, close_btn, border_radius=10)  # 파란색 배경 + 테두리 곡률
        close_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.035))
        close_text = close_font.render("Close", True, WHITE)
        screen.blit(close_text, close_text.get_rect(center=close_btn.center))

        # 전역 버튼 위치 저장
        global rule_close_button
        rule_close_button = close_btn


    pygame.display.flip()


def option_screen():
    global SCREEN_WIDTH, SCREEN_HEIGHT, screen, burger_goal, fullscreen, current_bgm_index, bgm_on

    fullscreen = screen.get_flags() & pygame.FULLSCREEN != 0

    # 기준 해상도 (전체 화면)
    BASE_WIDTH, BASE_HEIGHT = 1920, 1080

    # 현재 해상도에 따른 비율 계산
    width_ratio = SCREEN_WIDTH / BASE_WIDTH
    height_ratio = SCREEN_HEIGHT / BASE_HEIGHT

    center_x = SCREEN_WIDTH // 2
    center_y = SCREEN_HEIGHT // 2

    # UI 요소 크기 및 위치를 비율에 따라 동적 계산
    button_width = int(160 * width_ratio)
    button_height = int(72 * height_ratio)
    font_size = int(36 * height_ratio)
    symbol_font_size = int(54 * height_ratio)

    # 폰트 동적 생성
    dynamic_font = pygame.font.SysFont(None, font_size)
    symbol_font = pygame.font.SysFont(None, symbol_font_size)

    # 버튼 Rect 동적 생성
    minus_button = pygame.Rect(center_x - button_width - 20 * width_ratio, center_y - button_height, button_width, button_height)
    plus_button = pygame.Rect(center_x + 20 * width_ratio, center_y - button_height, button_width, button_height)

    window_button = pygame.Rect(center_x - button_width - 20 * width_ratio, center_y + int(50 * height_ratio), button_width + int(20 * width_ratio), button_height)
    full_button = pygame.Rect(center_x + int(20 * width_ratio), center_y + int(50 * height_ratio), button_width + int(20 * width_ratio), button_height)

    back_button = pygame.Rect(int(40 * width_ratio), SCREEN_HEIGHT - button_height - int(30 * height_ratio), button_width, button_height)

    bgm_minus_button = pygame.Rect(center_x - button_width - 20 * width_ratio, center_y + int(210 * height_ratio), button_width, button_height)
    bgm_plus_button = pygame.Rect(center_x + 20 * width_ratio, center_y + int(210 * height_ratio), button_width, button_height)
    bgm_toggle_button = pygame.Rect(center_x - button_width // 2, center_y + int(280 * height_ratio), button_width, button_height)

    option_bg = pygame.image.load(resource_path('images/OptionScreen.png')).convert()
    option_bg = pygame.transform.scale(option_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

    left_symbol = symbol_font.render("<", True, WHITE)
    right_symbol = symbol_font.render(">", True, WHITE)

    while True:
        screen.blit(option_bg, (0, 0))

        # Burgers to Make
        screen.blit(dynamic_font.render("Burgers to Make", True, BLACK), (center_x - int(90 * width_ratio), center_y - int(150 * height_ratio)))
        left_symbol_rect = left_symbol.get_rect(center=minus_button.center)
        left_symbol_rect.y -= int(30 * height_ratio)
        screen.blit(left_symbol, left_symbol_rect)
        right_symbol_rect = right_symbol.get_rect(center=plus_button.center)
        right_symbol_rect.y -= int(30 * height_ratio)
        screen.blit(right_symbol, right_symbol_rect)

        count_box_width = int(154 * width_ratio)
        count_box_height = int(76 * height_ratio)
        count_box_rect = pygame.Rect(center_x - count_box_width // 2, center_y - int(65 * height_ratio) - count_box_height // 2, count_box_width, count_box_height)
        pygame.draw.rect(screen, GRAY, count_box_rect, border_radius=8)
        count_text = dynamic_font.render(str(burger_goal), True, BLACK)
        screen.blit(count_text, count_text.get_rect(center=(center_x, center_y - int(65 * height_ratio))))
        separator_y = center_y - int(15 * height_ratio)
        pygame.draw.line(screen, DARK_GRAY, (center_x - SCREEN_WIDTH * 0.15, separator_y), (center_x + SCREEN_WIDTH * 0.15, separator_y), 2)
        
        # Screen Mode
        screen.blit(dynamic_font.render("Screen Mode", True, BLACK), (center_x - int(90 * width_ratio), center_y + int(20 * height_ratio)))
        pygame.draw.rect(screen, BLUE if not fullscreen else DARK_GRAY, window_button, border_radius=8)
        pygame.draw.rect(screen, BLUE if fullscreen else DARK_GRAY, full_button, border_radius=8)
        screen.blit(dynamic_font.render("Windowed", True, WHITE), dynamic_font.render("Windowed", True, WHITE).get_rect(center=window_button.center))
        screen.blit(dynamic_font.render("Fullscreen", True, WHITE), dynamic_font.render("Fullscreen", True, WHITE).get_rect(center=full_button.center))
        pygame.draw.line(screen, DARK_GRAY, (center_x - SCREEN_WIDTH * 0.15, separator_y + int(165 * height_ratio)), (center_x + SCREEN_WIDTH * 0.15, separator_y + int(165 * height_ratio)), 2)

        # BGM Settings
        screen.blit(dynamic_font.render("BGM Select", True, BLACK), (center_x - int(70 * width_ratio), center_y + int(180 * height_ratio)))
        left_symbol_rect = left_symbol.get_rect(center=bgm_minus_button.center)
        screen.blit(left_symbol, left_symbol_rect)
        right_symbol_rect = right_symbol.get_rect(center=bgm_plus_button.center)
        screen.blit(right_symbol, right_symbol_rect)
        bgm_name = os.path.basename(bgm_files[current_bgm_index]).split('.')[0]
        bgm_text = dynamic_font.render(bgm_name, True, BLACK)
        screen.blit(bgm_text, bgm_text.get_rect(center=(center_x, center_y + int(245 * height_ratio))))

        pygame.draw.rect(screen, GREEN if bgm_on else RED, bgm_toggle_button, border_radius=8)
        bgm_status_text = "BGM ON" if bgm_on else "BGM OFF"
        bgm_status_surface = dynamic_font.render(bgm_status_text, True, WHITE)
        screen.blit(bgm_status_surface, bgm_status_surface.get_rect(center=bgm_toggle_button.center))

        # Back Button
        pygame.draw.rect(screen, DARK_BLUE, back_button, border_radius=8)
        screen.blit(dynamic_font.render("Back", True, WHITE), dynamic_font.render("Back", True, WHITE).get_rect(center=back_button.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if minus_button.collidepoint(event.pos):
                    burger_goal = max(1, burger_goal - 1)
                    click_sfx.play()
                elif plus_button.collidepoint(event.pos):
                    burger_goal = min(20, burger_goal + 1)
                    click_sfx.play()
                elif window_button.collidepoint(event.pos):
                    fullscreen = False
                    click_sfx.play()
                elif full_button.collidepoint(event.pos):
                    fullscreen = True
                    click_sfx.play()
                elif bgm_minus_button.collidepoint(event.pos):
                    current_bgm_index = (current_bgm_index - 1) % len(bgm_files)
                    pygame.mixer.music.load(bgm_files[current_bgm_index])
                    if bgm_on:
                        pygame.mixer.music.play(-1)
                    click_sfx.play()
                elif bgm_plus_button.collidepoint(event.pos):
                    current_bgm_index = (current_bgm_index + 1) % len(bgm_files)
                    pygame.mixer.music.load(bgm_files[current_bgm_index])
                    if bgm_on:
                        pygame.mixer.music.play(-1)
                    click_sfx.play()
                elif bgm_toggle_button.collidepoint(event.pos):
                    bgm_on = not bgm_on
                    if bgm_on:
                        pygame.mixer.music.play(-1)
                    else:
                        pygame.mixer.music.stop()
                    click_sfx.play()
                elif back_button.collidepoint(event.pos):
                    if fullscreen:
                        click_sfx.play()
                        SCREEN_WIDTH, SCREEN_HEIGHT = 1920, 1080
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
                    else:
                        click_sfx.play()
                        SCREEN_WIDTH, SCREEN_HEIGHT = 1280, 720
                        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                    apply_responsive_scaling()
                    reset_game_state()
                    pygame.mixer.music.stop()
                    return


def leaderboard_screen():
    back_button = pygame.Rect(60, SCREEN_HEIGHT - 80, 160, 50)

    # 랭킹 데이터 불러오기
    rankings = []
    if os.path.exists(ranking_file):
        with open(ranking_file, "r") as f:
            try:
                rankings = json.load(f)
            except json.JSONDecodeError:
                rankings = []

    # 랭킹 스크린 이미지 불러오기
    leaderboard_bg = pygame.image.load(resource_path('images/RankingScreen.png')).convert()
    leaderboard_bg = pygame.transform.scale(leaderboard_bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(leaderboard_bg, (0, 0))

    while True:
        screen.blit(leaderboard_bg, (0, 0))
        # 탑10 순위 출력
        for i, entry in enumerate(rankings[:10]):
            if i == 0:
                rank_text = font.render(f"{i+1}st  {entry['name']} - ${entry['score']}", True, BLACK)
            elif i == 1 :
                rank_text = font.render(f"{i+1}nd  {entry['name']} - ${entry['score']}", True, BLACK)
            elif i == 2:
                rank_text = font.render(f"{i+1}rd  {entry['name']} - ${entry['score']}", True, BLACK)
            else:
                rank_text = font.render(f"{i+1}th  {entry['name']} - ${entry['score']}", True, BLACK)

            x_pos = SCREEN_WIDTH * 0.5 - SCREEN_WIDTH * 0.15  # 가로 기준 중앙에서 왼쪽으로 15% 이동
            y_start = SCREEN_HEIGHT * 0.25  # 시작 y 위치 (대략 180px에 해당)
            y_gap = SCREEN_HEIGHT * 0.05    # 줄 간격 (대략 50px에 해당)
            screen.blit(rank_text, (x_pos, y_start + i  * y_gap))


        # 뒤로가기 버튼
        pygame.draw.rect(screen, DARK_BLUE, back_button, border_radius=8)
        screen.blit(font.render("Back", True, WHITE), font.render("Back", True, WHITE).get_rect(center=back_button.center))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if back_button.collidepoint(event.pos):
                    click_sfx.play()
                    return

def draw_status():
    elapsed = int(time.time() - start_time) - 1
    time_text = status_font.render(f"Time: {elapsed}s", True, BLACK)
    score_text = status_font.render(f"Score: {score}", True, BLACK)
    round_text = status_font.render(f"Burger {round_count + 1} / {burger_goal}", True, BLACK)  # 햄버거 개수 출력
    screen.blit(time_text, time_text.get_rect(center=(SCREEN_WIDTH // 2, 30)))
    screen.blit(score_text, score_text.get_rect(center=(SCREEN_WIDTH // 2, 70)))
    screen.blit(round_text, round_text.get_rect(center=(SCREEN_WIDTH // 2, 110)))

def draw_buttons():
    # Reset (Trashbin)
    trashbin_w = int(reset_button_rect.width * 0.9)
    trashbin_h = int(reset_button_rect.height * 0.9)
    scaled_trashbin = pygame.transform.scale(trashbin_img, (trashbin_w, int(trashbin_h * 1.8)))
    
    # move 적용: 왼쪽으로 10px, 아래로 5px (취소함)
    trashbin_rect = scaled_trashbin.get_rect(center=reset_button_rect.center)
    screen.blit(scaled_trashbin, trashbin_rect)

    # Bell
    bell_w = int(submit_button_rect.width * 0.9)
    bell_h = int(submit_button_rect.height * 0.9)
    scaled_bell = pygame.transform.scale(bell_img, (bell_w, bell_h))
    
    # move 적용: 오른쪽으로 5px, 위로 5px (취소함)
    bell_rect = scaled_bell.get_rect(center=submit_button_rect.center)
    screen.blit(scaled_bell, bell_rect)



def draw_recipe(recipe):
    # starting X/Y
    x = int(SCREEN_WIDTH * 0.08)
    y = int(SCREEN_HEIGHT * 0.60)

    # base for scaling icons (you can tweak the 60 → whatever pixel size you like)
    BASE_SCREEN_HEIGHT = 1080
    ICON_SIZE = int(60 * (SCREEN_HEIGHT / BASE_SCREEN_HEIGHT))

    for ingredient in reversed(recipe):
        # pick which image to show (usually “item” for recipe preview)
        img = ingredient_images[ingredient]["item"]
        # scale it to a uniform square
        img_scaled = pygame.transform.scale(img, (ICON_SIZE, ICON_SIZE))
        # center it on (x, y)
        screen.blit(img_scaled, (x - ICON_SIZE // 2, y - ICON_SIZE // 2))
        # move down for the next one (+10px padding)
        y += ICON_SIZE + 10

def get_camera_surface():
    global hand_status, message_alpha, message_timer, hand_screen_pos
    
    ret, frame = cap.read()
    if not ret:
        return None
    frame = cv2.flip(frame, 0)  # 상하 반전 추가
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)
    hand_screen_pos = None
    hand_status = "None"
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            folded = {
                "Thumb": hand_landmarks.landmark[4].x < hand_landmarks.landmark[2].x,
                "Index": hand_landmarks.landmark[8].y > hand_landmarks.landmark[6].y,
                "Middle": hand_landmarks.landmark[12].y > hand_landmarks.landmark[10].y,
                "Ring": hand_landmarks.landmark[16].y > hand_landmarks.landmark[14].y,
                "Pinky": hand_landmarks.landmark[20].y > hand_landmarks.landmark[18].y
            }
            hand_status = "Fist" if sum(folded.values()) >= 3 else "Open"
            if (not folded["Middle"] and all(folded[f] for f in ["Thumb", "Index", "Ring", "Pinky"])):
                message_alpha = 255
                message_timer = MESSAGE_DURATION
            cx = 1.0 - hand_landmarks.landmark[9].x
            cy = hand_landmarks.landmark[9].y
            x_offset = 80 if hand_landmarks.landmark[9].x > 0.9 else 0
            y_offset = -40 if hand_landmarks.landmark[9].y > 0.85 else 0
            hand_screen_pos = (int(cx * SCREEN_WIDTH - x_offset), int(cy * SCREEN_HEIGHT + y_offset))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = np.rot90(frame)

    # 최대 크기 기준 비율 잡기
    max_width = int(SCREEN_WIDTH * 0.3)
    max_height = int(SCREEN_HEIGHT * 0.3)

    cam_width = min(max_width, int((max_height * 4) / 3))
    cam_height = int((cam_width * 3) / 4)
    # print(f"Camera size: {cam_width}x{cam_height}")
    return pygame.transform.scale(pygame.surfarray.make_surface(frame), (cam_width*1.61, cam_height*1.4))

def evaluate_recipe():
    global score, current_recipe, total_accuracy_score, round_count, burger_start_time
    built = [item["type"] for item in reversed(items_on_screen)]
    correct = current_recipe
    match = 0
    for i in range(min(len(built), len(correct))):
        if built[i] == correct[i]:
            match += 1
    accuracy = match / len(correct)
    accuracy_score = int(accuracy * 100)

    elapsed_burger_time = int(time.time() - burger_start_time)
    time_bonus = max(0, BURGER_TIME_LIMIT - elapsed_burger_time)
    time_score = int(time_bonus * accuracy)

    if elapsed_burger_time > BURGER_TIME_LIMIT:
        print("TIME OUT! No score for this burger.")
        accuracy_score = 0
        time_score = 0

    total_accuracy_score += accuracy_score
    round_count += 1
    round_score = accuracy_score + time_score
    round_scores.append(round_score)
    score += round_score

    print(f"Submitted! Accuracy: {accuracy:.2f}, +{accuracy_score} points, Time bonus: {time_score}")

    if all_recipes:
        burger_start_time = time.time()
        return all_recipes.pop(random.randrange(len(all_recipes)))
    else:
        return None

def end_game():
    global running, menu_active, score, round_count, total_accuracy_score, current_recipe, all_recipes, cheat_index
    global input_active, user_input
    global saved_message_timer, saved_message_alpha
    global overwrite_prompt_active, overwrite_pending_name
    global menu_saved_message_timer, menu_saved_message_alpha, menu_saved_rank

    # 버튼 위치 (왼쪽 하단 "Leave a Record")
    button_width = int(SCREEN_WIDTH * 0.12)
    button_height = int(SCREEN_HEIGHT * 0.05)
    button_center = (int(SCREEN_WIDTH * 0.25), int(SCREEN_HEIGHT * 0.7))
    leave_record_button_rect = pygame.Rect(0, 0, button_width, button_height)
    leave_record_button_rect.center = button_center


    input_active = False
    user_input = ""
    auto_return_start = time.time()  # 자동 타이머 시작
    AUTO_RETURN_LIMIT = 10  # 자동 전환까지 10초

    clear_screen = pygame.image.load(resource_path('images/GameClearImage.png')).convert()
    clear_screen = pygame.transform.scale(clear_screen, (SCREEN_WIDTH, SCREEN_HEIGHT))
    screen.blit(clear_screen, (0, 0))

    scroll_offset = 0
    MAX_SCORES_DISPLAY = 5

    while True:
        screen.blit(clear_screen, (0, 0))

        # 라운드별 점수 표시 (스크롤 기능 추가)
        score_font_size = int(SCREEN_HEIGHT * 0.035)
        score_font = pygame.font.SysFont(None, score_font_size)
        score_list_x = SCREEN_WIDTH * 0.7 + 30

        visible_scores = round_scores[scroll_offset:scroll_offset + MAX_SCORES_DISPLAY]
        num_visible_scores = len(visible_scores)
        line_height = int(SCREEN_HEIGHT * 0.05)
        total_text_height = num_visible_scores * line_height
        
        block_start_y = (SCREEN_HEIGHT / 2) - (total_text_height / 2)

        if round_scores:
            padding = int(SCREEN_HEIGHT * 0.02)
            box_width = int(SCREEN_WIDTH * 0.15)
            box_height = total_text_height + (padding * 2)
            box_x = score_list_x - (box_width / 2)
            box_y = block_start_y - padding

            panel_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            panel_surface.fill((255, 255, 255, 0))
            screen.blit(panel_surface, (box_x, box_y))

            # 스크롤 화살표 표시
            scroll_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.04))
            if scroll_offset > 0:
                up_arrow = scroll_font.render("^", True, PINK)
                screen.blit(up_arrow, up_arrow.get_rect(center=(score_list_x, box_y - padding // 2)))
            if scroll_offset + MAX_SCORES_DISPLAY < len(round_scores):
                down_arrow = scroll_font.render("v", True, PINK)
                screen.blit(down_arrow, down_arrow.get_rect(center=(score_list_x, box_y + box_height + padding // 2)))

        for i, r_score in enumerate(visible_scores):
            score_text = score_font.render(f"Burger {scroll_offset + i + 1}: ${r_score}", True, BLACK)
            text_y = block_start_y + (i * line_height) + (line_height / 2)
            text_rect = score_text.get_rect(center=(score_list_x, text_y))
            screen.blit(score_text, text_rect)


        # 최종 점수 (오른쪽 하단)
        final_score = big_font.render(f"{score}", True, GREEN)
        screen.blit(final_score, final_score.get_rect(center=(SCREEN_WIDTH * 0.7, SCREEN_HEIGHT * 0.7)))

        # 중앙 안내 메시지 (창모드/전체화면 대응, 항상 중앙)
        center_msg_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.04))  # 반응형 텍스트 크기
        center_msg = center_msg_font.render("Press SPACE or ESC to return to Menu", True, DARK_GRAY)
        screen.blit(center_msg, center_msg.get_rect(center=(SCREEN_WIDTH * 0.4, SCREEN_HEIGHT * 0.5)))


        # 자동 복귀 안내 (하단 중앙)
        remaining = AUTO_RETURN_LIMIT - int(time.time() - auto_return_start)
        if remaining <= AUTO_RETURN_LIMIT and remaining > 0:
            # 겹침 방지를 위해 배경 박스를 먼저 그림
            dynamic_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.035))
            hint_text = dynamic_font.render(f"Returning to menu in {remaining} seconds", True, DARK_GRAY)
            hint_rect = hint_text.get_rect(center=(SCREEN_WIDTH * 0.48, SCREEN_HEIGHT * 0.7))
            background_surface = pygame.Surface((hint_rect.width + 20, hint_rect.height + 10))
            background_surface.fill(GRAY)  # 배경색과 동일하게 덮기
            screen.blit(background_surface, background_surface.get_rect(center=hint_rect.center))
            screen.blit(hint_text, hint_rect)


        # 레코드 저장 버튼 (왼쪽 하단)
        pygame.draw.rect(screen, BLUE, leave_record_button_rect, border_radius=8)
        
        record_text = dynamic_font.render("Leave a Record", True, WHITE)
        screen.blit(record_text, record_text.get_rect(center=(SCREEN_WIDTH * 0.25, SCREEN_HEIGHT * 0.7)))

        if input_active:
            draw_input_modal()

        if overwrite_prompt_active:
            draw_overwrite_prompt()

        if time.time() - auto_return_start > AUTO_RETURN_LIMIT:
            reset_game_state()
            menu_active = True
            return

        pygame.display.flip()

        for event in pygame.event.get():
            auto_return_start = time.time()
            if event.type == pygame.QUIT:
                return
            elif event.type == pygame.KEYDOWN:
                if input_active:
                    if event.key == pygame.K_RETURN and user_input.strip():
                        name = user_input.strip()
                        if os.path.exists(ranking_file):
                            with open(ranking_file, "r") as f:
                                try:
                                    data = json.load(f)
                                    if any(entry["name"] == name for entry in data):
                                        overwrite_pending_name = name
                                        overwrite_prompt_active = True
                                        input_active = False
                                        continue
                                except json.JSONDecodeError:
                                    pass
                        save_score(name, score)
                        input_active = False
                        user_input = ""

                        menu_saved_rank = get_player_rank(name)
                        menu_saved_message_timer = 50
                        menu_saved_message_alpha = 255

                        reset_game_state()
                        menu_active = True
                        return
                    elif event.key == pygame.K_BACKSPACE:
                        user_input = user_input[:-1]
                    else:
                        if len(user_input) < 10:
                            user_input += event.unicode
                else:
                    if event.key == pygame.K_SPACE or pygame.K_ESCAPE:
                        reset_game_state()
                        menu_active = True
                        return

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if leave_record_button_rect.collidepoint(event.pos):
                    click_sfx.play()
                    input_active = True
                elif overwrite_prompt_active:
                    if overwrite_buttons["yes"].collidepoint(event.pos):
                        save_score(overwrite_pending_name, score, overwrite=True)
                        overwrite_prompt_active = False
                        input_active = False
                        menu_saved_rank = get_player_rank(overwrite_pending_name)
                        menu_saved_message_timer = 50
                        menu_saved_message_alpha = 255
                        reset_game_state()
                        menu_active = True
                        return
                    elif overwrite_buttons["no"].collidepoint(event.pos):
                       # 모든 상태 초기화 후 게임 오버 화면 재시작
                        overwrite_prompt_active = False
                        input_active = False
                        user_input = ""
                        end_game()
                        return  # end_game 루프 탈출 → 외부에서 다시 호출
                
                # 스크롤 처리
                if len(round_scores) > MAX_SCORES_DISPLAY:
                    if event.button == 4:  # Scroll up
                        scroll_offset = max(0, scroll_offset - 1)
                    elif event.button == 5:  # Scroll down
                        scroll_offset = min(len(round_scores) - MAX_SCORES_DISPLAY, scroll_offset + 1)

# end_game 끝
# =======================================================================


while running:
    if menu_active:
        draw_menu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 룰 페이지 열려 있고 닫기 버튼 클릭 시
                if showing_rule_page and rule_close_button.collidepoint(event.pos):
                    click_sfx.play()
                    showing_rule_page = False

                # 말풍선 클릭 시 룰 페이지 열기
                elif talk_balloon_area.collidepoint(event.pos):
                    click_sfx.play()
                    showing_rule_page = True

                if start_button_rect.collidepoint(event.pos):
                    click_sfx.play()
                    menu_active = False
                    start_time = time.time()
                    burger_start_time = time.time()
                    if bgm_on:
                        pygame.mixer.music.play(-1)
                    
                elif exit_button_rect.collidepoint(event.pos):
                    click_sfx.play()
                    running = False
                    
                elif option_button_rect.collidepoint(event.pos):
                    click_sfx.play()
                    option_screen()  # 옵션 화면 진입
                    
                elif leaderboard_button_rect.collidepoint(event.pos):
                    click_sfx.play()
                    leaderboard_screen()
        continue

    screen.blit(game_bg, (0, 0))
    draw_status()

    for event in pygame.event.get():
        if event.type == pygame.QUIT :
                pygame.quit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c and current_recipe:
                if cheat_index < len(current_recipe):
                    items_on_screen.insert(0, {"type": current_recipe[cheat_index]})
                    cheat_index += 1
            elif event.key == pygame.K_ESCAPE:
                        pygame.mixer.music.stop()
                        end_game()
    # 접시 이미지 스케일 및 중앙 배치
    scaled_dish = pygame.transform.scale(dish_img, (PLATE_RADIUS * 2, PLATE_RADIUS * 2))
    screen.blit(scaled_dish, (plate_pos[0] - PLATE_RADIUS, plate_pos[1] - PLATE_RADIUS))


    for idx, item in enumerate(reversed(items_on_screen)):
        y_offset = -idx * (ITEM_RADIUS // 2)
        draw_pos = (plate_pos[0], plate_pos[1] + y_offset)
        # ── 이미지로 그리기 ──
        img = ingredient_images[item["type"]]["item"]
        img_s = pygame.transform.scale(img, (ITEM_RADIUS*2.2, ITEM_RADIUS*2))
        screen.blit(img_s, (draw_pos[0] - ITEM_RADIUS, draw_pos[1] - ITEM_RADIUS))

    if held_item:
        # ── 이미지로 그리기 ──
        img = ingredient_images[held_item["type"]]["item"]
        img_s = pygame.transform.scale(img, (ITEM_RADIUS*2.2, ITEM_RADIUS*2))
        pos = held_item["pos"]
        screen.blit(img_s, (pos[0] - ITEM_RADIUS, pos[1] - ITEM_RADIUS))

    for name, pos in ingredient_spawns.items():
        # ── _in_stain 이미지로 그리기 ──
        img = ingredient_images[name]["in_stain"]
        img_s = pygame.transform.scale(img, (ITEM_RADIUS*2, ITEM_RADIUS*2.2))
        screen.blit(img_s, (pos[0] - ITEM_RADIUS, pos[1] - ITEM_RADIUS))

    draw_buttons()
    if current_recipe:
        draw_recipe(current_recipe)

    if hand_screen_pos:
        if hand_status == "Fist":
            screen.blit(closed_hand_img, closed_hand_img.get_rect(center=hand_screen_pos))
        else:
            screen.blit(open_hand_img, open_hand_img.get_rect(center=hand_screen_pos))


    camera_surface = get_camera_surface()
    if camera_surface:
        # camera_x = int(SCREEN_WIDTH * 0.01)  # 좌측 여백 1%
        # camera_y = int(SCREEN_HEIGHT * 0.01)  # 상단 여백 1%
        # screen.blit(camera_surface, (camera_x, camera_y))
        screen.blit(camera_surface, (0, 0))

    if hand_screen_pos and hand_status == "Fist" and prev_hand_status != "Fist":
        if reset_button_rect.collidepoint(hand_screen_pos):
            items_on_screen.clear()
        if submit_button_rect.collidepoint(hand_screen_pos):
            current_recipe = evaluate_recipe()
            items_on_screen.clear()
            cheat_index = 0
            if current_recipe is None:
                end_game()
        for name, pos in ingredient_spawns.items():
            if np.linalg.norm(np.array(hand_screen_pos) - np.array(pos)) < ITEM_RADIUS + 10:
                held_item = {"type": name, "pos": hand_screen_pos}

    if held_item:
        if hand_screen_pos:
            if hand_status == "Fist":
                held_item["pos"] = hand_screen_pos
            else:
                if np.linalg.norm(np.array(hand_screen_pos) - np.array(plate_pos)) < PLATE_RADIUS + 10:
                    items_on_screen.insert(0, {"type": held_item["type"]})
                held_item = None

    if message_timer > 0:
        surface = big_font.render("Don't be rude!", True, (255, 0, 0))
        surface.set_alpha(message_alpha)
        screen.blit(surface, surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
        message_timer -= 1
        if message_timer < MESSAGE_DURATION:
            message_alpha = max(0, int(255 * (message_timer / MESSAGE_DURATION)))

    pygame.display.flip()
    clock.tick(30)
    prev_hand_status = hand_status

cap.release()
pygame.quit()
sys.exit()