"""
YoRacer — 2D гонки на Python (pygame / pygame-ce).

Установка:   pip install pygame-ce
Запуск:      python racing.py

Управление на телефоне / мышью: экранные кнопки внизу
  ◄ ►  — руль,   ▲ — газ,   ▼ — тормоз,   значок II справа вверху — пауза.
Клавиатура: ← → / A D — руль, ↑ / W — газ, ↓ / S — тормоз,
            P или Esc — пауза, Enter / Пробел — старт, R — заново.
"""
import json
import os
import random
import sys

import pygame

# ---------- Настройки ----------
WIDTH, HEIGHT = 480, 720
FPS = 60

SCORE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "score.json")

ROAD_W = 360
ROAD_X = (WIDTH - ROAD_W) // 2
LANES = 4
LANE_W = ROAD_W // LANES

CAR_W, CAR_H = 46, 84

MIN_SPEED = 5.0
MAX_SPEED = 16.0

# Весь трафик едет с одной скоростью, поэтому машины никогда не наезжают друг
# на друга, а ряды всегда имеют свободную полосу и достаточный зазор.
ENEMY_SPEED_MIN = 3.0   # у каждой машины своя скорость из этого диапазона
ENEMY_SPEED_MAX = 6.0
ENEMY_SPEED_AVG = (ENEMY_SPEED_MIN + ENEMY_SPEED_MAX) / 2
FOLLOW_GAP = 50         # минимальный зазор между машинами в одной полосе
ROW_GAP_MIN = 400   # пикселей между рядами машин (хватает перестроиться на макс. скорости)
ROW_GAP_MAX = 520

GRASS = (46, 125, 50)
GRASS_DARK = (40, 112, 45)
ASPHALT = (60, 60, 66)
WHITE = (235, 235, 235)
YELLOW = (240, 200, 40)
RED = (230, 40, 40)

ENEMY_COLORS = [
    (220, 60, 60), (60, 140, 220), (240, 160, 40),
    (150, 80, 200), (60, 190, 140), (230, 230, 230),
]

# ---------- Экранные кнопки ----------
CTRL_H = 100
CTRL_Y = HEIGHT - CTRL_H - 14
CTRL = {
    "left": pygame.Rect(12, CTRL_Y, 100, CTRL_H),
    "right": pygame.Rect(124, CTRL_Y, 100, CTRL_H),
    "brake": pygame.Rect(256, CTRL_Y, 100, CTRL_H),
    "gas": pygame.Rect(368, CTRL_Y, 100, CTRL_H),
}
PAUSE_BTN = pygame.Rect(WIDTH - 52, 62, 42, 42)

# кнопки меню
BTN_A = pygame.Rect(WIDTH // 2 - 130, 400, 260, 66)
BTN_B = pygame.Rect(WIDTH // 2 - 130, 486, 260, 66)


def draw_car(surf, rect, color, flipped=False):
    """Рисует машинку (вид сверху) без внешних картинок."""
    x, y, w, h = rect
    dark = tuple(max(0, c - 60) for c in color)

    for wx in (x - 4, x + w - 6):
        for wy in (y + 10, y + h - 28):
            pygame.draw.rect(surf, (20, 20, 20), (wx, wy, 10, 20), border_radius=3)

    pygame.draw.rect(surf, color, rect, border_radius=12)
    pygame.draw.rect(surf, dark, rect, width=2, border_radius=12)

    glass = (170, 215, 240)
    if not flipped:
        pygame.draw.rect(surf, glass, (x + 7, y + 22, w - 14, 16), border_radius=4)
        pygame.draw.rect(surf, dark, (x + 7, y + 40, w - 14, 20), border_radius=4)
        pygame.draw.rect(surf, glass, (x + 8, y + 62, w - 16, 9), border_radius=3)
        pygame.draw.rect(surf, (255, 255, 200), (x + 5, y + 3, 9, 6), border_radius=2)
        pygame.draw.rect(surf, (255, 255, 200), (x + w - 14, y + 3, 9, 6), border_radius=2)
    else:
        pygame.draw.rect(surf, glass, (x + 7, y + h - 38, w - 14, 16), border_radius=4)
        pygame.draw.rect(surf, dark, (x + 7, y + h - 60, w - 14, 20), border_radius=4)
        pygame.draw.rect(surf, glass, (x + 8, y + h - 71, w - 16, 9), border_radius=3)
        pygame.draw.rect(surf, (255, 60, 60), (x + 5, y + h - 9, 9, 6), border_radius=2)
        pygame.draw.rect(surf, (255, 60, 60), (x + w - 14, y + h - 9, 9, 6), border_radius=2)


class Player:
    def __init__(self):
        self.x = WIDTH / 2 - CAR_W / 2
        self.y = CTRL_Y - CAR_H - 30
        self.vx = 0.0
        self.color = RED

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), CAR_W, CAR_H)

    @property
    def hitbox(self):
        return self.rect.inflate(-10, -14)

    def update(self, left, right, speed):
        accel = 0.9
        friction = 0.82
        if left:
            self.vx -= accel
        if right:
            self.vx += accel
        self.vx *= friction
        self.x += self.vx * (1.0 - (speed - MIN_SPEED) / 60)
        self.x = max(ROAD_X + 4, min(ROAD_X + ROAD_W - CAR_W - 4, self.x))

    def draw(self, surf):
        draw_car(surf, self.rect, self.color)


class Enemy:
    def __init__(self, lane):
        self.w, self.h = CAR_W, CAR_H
        self.x = ROAD_X + lane * LANE_W + (LANE_W - self.w) / 2
        self.y = -self.h - 10
        self.color = random.choice(ENEMY_COLORS)
        self.lane = lane
        self.own_speed = random.uniform(ENEMY_SPEED_MIN, ENEMY_SPEED_MAX)

    @property
    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    @property
    def hitbox(self):
        return self.rect.inflate(-10, -14)

    def update(self, speed):
        self.y += speed - self.own_speed

    def draw(self, surf):
        draw_car(surf, self.rect, self.color)


def load_best():
    try:
        with open(SCORE_FILE, "r", encoding="utf-8") as f:
            return int(json.load(f).get("best", 0))
    except (OSError, ValueError, AttributeError):
        return 0


def save_best(value):
    try:
        with open(SCORE_FILE, "w", encoding="utf-8") as f:
            json.dump({"best": int(value)}, f)
    except OSError:
        pass


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("YoRacer")
        try:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED | pygame.RESIZABLE)
        except Exception:
            self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas,arial", 22, bold=True)
        self.small = pygame.font.SysFont("consolas,arial", 16, bold=True)
        self.big = pygame.font.SysFont("consolas,arial", 52, bold=True)
        self.title_font = pygame.font.SysFont("consolas,arial", 76, bold=True)
        self.best = load_best()
        self.fingers = {}
        self.state = "menu"      # menu / play / pause / over
        self.road_offset = 0.0
        self.trees = [
            [random.choice((ROAD_X // 2, WIDTH - ROAD_X // 2)) + random.randint(-18, 18),
             random.randint(0, HEIGHT)]
            for _ in range(10)
        ]
        self.reset()

    # ---------- состояние ----------
    def reset(self):
        self.player = Player()
        self.enemies = []
        self.speed = 8.0
        self.score = 0.0
        self.row_dist = ROW_GAP_MIN - 220   # первая «пробка» появится скоро
        self.next_gap = ROW_GAP_MIN
        self.safe_lane = random.randrange(LANES)
        self.shake = 0

    def start(self):
        self.reset()
        self.state = "play"

    # ---------- ввод ----------
    def pointers(self):
        pts = list(self.fingers.values())
        if pygame.mouse.get_pressed()[0]:
            pts.append(pygame.mouse.get_pos())
        return pts

    def controls(self):
        keys = pygame.key.get_pressed()
        pts = self.pointers()

        def held(name):
            return any(CTRL[name].collidepoint(p) for p in pts)

        return {
            "left": keys[pygame.K_LEFT] or keys[pygame.K_a] or held("left"),
            "right": keys[pygame.K_RIGHT] or keys[pygame.K_d] or held("right"),
            "gas": keys[pygame.K_UP] or keys[pygame.K_w] or held("gas"),
            "brake": keys[pygame.K_DOWN] or keys[pygame.K_s] or held("brake"),
        }

    def handle_click(self, pos):
        if self.state == "menu":
            if BTN_A.collidepoint(pos):
                self.start()
            elif BTN_B.collidepoint(pos):
                pygame.quit()
                sys.exit()
        elif self.state == "play":
            if PAUSE_BTN.collidepoint(pos):
                self.state = "pause"
        elif self.state == "pause":
            if BTN_A.collidepoint(pos):
                self.state = "play"
            elif BTN_B.collidepoint(pos):
                self.state = "menu"
        elif self.state == "over":
            if BTN_A.collidepoint(pos):
                self.start()
            elif BTN_B.collidepoint(pos):
                self.state = "menu"

    # ---------- логика ----------
    def spawn_row(self):
        """Ряд машин, в котором всегда есть свободная полоса.
        Свободная полоса смещается максимум на 1 за ряд — проехать можно всегда."""
        self.safe_lane = max(0, min(LANES - 1, self.safe_lane + random.choice((-1, 0, 0, 1))))
        density = min(0.85, 0.5 + self.score / 6000)
        for lane in range(LANES):
            if lane == self.safe_lane or random.random() >= density:
                continue
            # не ставим машину, если в этой полосе у самого верха уже кто-то есть
            if any(e.lane == lane and e.y < CAR_H + FOLLOW_GAP for e in self.enemies):
                continue
            self.enemies.append(Enemy(lane))

    def limit_follow_speed(self):
        """Машина сзади не может ехать быстрее машины впереди, если они слишком близко
        (иначе они бы въезжали друг в друга)."""
        for lane in range(LANES):
            cars = sorted((e for e in self.enemies if e.lane == lane), key=lambda e: e.y)
            for front, rear in zip(cars, cars[1:]):
                if rear.y - front.y < CAR_H + FOLLOW_GAP + 30:
                    rear.own_speed = min(rear.own_speed, front.own_speed)

    def scroll(self, speed):
        self.road_offset = (self.road_offset + speed) % 80
        for t in self.trees:
            t[1] += speed
            if t[1] > HEIGHT + 30:
                t[1] = -30
                t[0] = random.choice((ROAD_X // 2, WIDTH - ROAD_X // 2)) + random.randint(-18, 18)

    def update(self):
        c = self.controls()

        if c["gas"]:
            self.speed = min(MAX_SPEED, self.speed + 0.08)
        elif c["brake"]:
            self.speed = max(MIN_SPEED, self.speed - 0.15)
        else:
            self.speed = max(MIN_SPEED + 1, self.speed - 0.01)

        self.player.update(c["left"], c["right"], self.speed)
        self.scroll(self.speed)

        # ряды спавнятся по пройденной дистанции, а не по времени
        self.row_dist += max(1.0, self.speed - ENEMY_SPEED_AVG)
        if self.row_dist >= self.next_gap:
            self.row_dist -= self.next_gap
            self.next_gap = random.uniform(ROW_GAP_MIN, ROW_GAP_MAX)
            self.spawn_row()

        self.limit_follow_speed()
        for e in self.enemies:
            e.update(self.speed)
        # убираем тех, кто уехал вниз, и тех, кто убежал далеко вверх
        self.enemies = [e for e in self.enemies if -HEIGHT < e.y < HEIGHT + 20]

        self.score += self.speed * 0.1

        hb = self.player.hitbox
        for e in self.enemies:
            if hb.colliderect(e.hitbox):
                self.state = "over"
                self.shake = 20
                self.best = max(self.best, int(self.score))
                save_best(self.best)
                break

    # ---------- отрисовка ----------
    def text(self, s, font, pos, color=(255, 255, 255), center=False):
        img = font.render(s, True, color)
        sh = font.render(s, True, (0, 0, 0))
        if center:
            pos = (pos[0] - img.get_width() // 2, pos[1])
        self.screen.blit(sh, (pos[0] + 2, pos[1] + 2))
        self.screen.blit(img, pos)

    def draw_road(self):
        s = self.screen
        s.fill(GRASS)
        for i in range(-1, HEIGHT // 80 + 2):
            y = i * 80 + self.road_offset
            pygame.draw.rect(s, GRASS_DARK, (0, y, ROAD_X, 40))
            pygame.draw.rect(s, GRASS_DARK, (ROAD_X + ROAD_W, y, ROAD_X, 40))

        pygame.draw.rect(s, ASPHALT, (ROAD_X, 0, ROAD_W, HEIGHT))
        pygame.draw.rect(s, WHITE, (ROAD_X, 0, 5, HEIGHT))
        pygame.draw.rect(s, WHITE, (ROAD_X + ROAD_W - 5, 0, 5, HEIGHT))

        for lane in range(1, LANES):
            x = ROAD_X + lane * LANE_W - 2
            color = YELLOW if lane == LANES // 2 else WHITE
            for i in range(-1, HEIGHT // 80 + 2):
                y = i * 80 + self.road_offset
                pygame.draw.rect(s, color, (x, y, 4, 40))

        for tx, ty in self.trees:
            pygame.draw.circle(s, (25, 90, 35), (int(tx), int(ty)), 18)
            pygame.draw.circle(s, (35, 115, 45), (int(tx) - 4, int(ty) - 4), 12)

    def draw_button(self, rect, label, color=(40, 140, 60)):
        hover = rect.collidepoint(pygame.mouse.get_pos())
        col = tuple(min(255, c + 30) for c in color) if hover else color
        pygame.draw.rect(self.screen, (0, 0, 0), rect.move(0, 4), border_radius=16)
        pygame.draw.rect(self.screen, col, rect, border_radius=16)
        pygame.draw.rect(self.screen, WHITE, rect, width=3, border_radius=16)
        img = self.font.render(label, True, (255, 255, 255))
        self.screen.blit(img, (rect.centerx - img.get_width() // 2,
                               rect.centery - img.get_height() // 2))

    def draw_controls(self):
        pts = self.pointers()
        keys = pygame.key.get_pressed()
        for name, rect in CTRL.items():
            pressed = any(rect.collidepoint(p) for p in pts)
            if name == "left":
                pressed = pressed or keys[pygame.K_LEFT] or keys[pygame.K_a]
                tint = (255, 255, 255)
            elif name == "right":
                pressed = pressed or keys[pygame.K_RIGHT] or keys[pygame.K_d]
                tint = (255, 255, 255)
            elif name == "gas":
                pressed = pressed or keys[pygame.K_UP] or keys[pygame.K_w]
                tint = (120, 255, 120)
            else:
                pressed = pressed or keys[pygame.K_DOWN] or keys[pygame.K_s]
                tint = (255, 120, 120)

            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            alpha = 150 if pressed else 70
            pygame.draw.rect(layer, (*tint, alpha), layer.get_rect(), border_radius=18)
            pygame.draw.rect(layer, (255, 255, 255, 160), layer.get_rect(), width=3, border_radius=18)

            cx, cy = rect.w // 2, rect.h // 2
            icon = (255, 255, 255, 235)
            if name == "left":
                pts_i = [(cx + 16, cy - 24), (cx - 18, cy), (cx + 16, cy + 24)]
            elif name == "right":
                pts_i = [(cx - 16, cy - 24), (cx + 18, cy), (cx - 16, cy + 24)]
            elif name == "gas":
                pts_i = [(cx, cy - 22), (cx - 26, cy + 18), (cx + 26, cy + 18)]
            else:
                pts_i = [(cx, cy + 22), (cx - 26, cy - 18), (cx + 26, cy - 18)]
            pygame.draw.polygon(layer, icon, pts_i)
            self.screen.blit(layer, rect.topleft)

        # подписи
        self.text("ГАЗ", self.small, (CTRL["gas"].centerx, CTRL["gas"].top - 20), center=True)
        self.text("ТОРМОЗ", self.small, (CTRL["brake"].centerx, CTRL["brake"].top - 20), center=True)

    def draw_hud(self):
        s = self.screen
        self.text(f"Счёт: {int(self.score)}", self.font, (10, 8))
        self.text(f"Рекорд: {max(self.best, int(self.score))}", self.font, (10, 34))
        kmh = f"{int(self.speed * 12)} км/ч"
        self.text(kmh, self.font, (WIDTH - self.font.size(kmh)[0] - 10, 8))

        ratio = (self.speed - MIN_SPEED) / (MAX_SPEED - MIN_SPEED)
        bar_w = 100
        bx = WIDTH - bar_w - 60
        pygame.draw.rect(s, (30, 30, 30), (bx, 36, bar_w, 10), border_radius=4)
        pygame.draw.rect(s, (255, 140 - int(120 * ratio), 40), (bx, 36, int(bar_w * ratio), 10), border_radius=4)

        # кнопка паузы
        pygame.draw.rect(s, (0, 0, 0), PAUSE_BTN, border_radius=10)
        pygame.draw.rect(s, WHITE, PAUSE_BTN, width=2, border_radius=10)
        pygame.draw.rect(s, WHITE, (PAUSE_BTN.x + 12, PAUSE_BTN.y + 11, 6, 20))
        pygame.draw.rect(s, WHITE, (PAUSE_BTN.x + 24, PAUSE_BTN.y + 11, 6, 20))

    def dim(self, alpha):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, alpha))
        self.screen.blit(overlay, (0, 0))

    def draw_menu(self):
        self.scroll(4)
        self.draw_road()
        self.dim(110)

        # название
        yo = self.title_font.render("Yo", True, YELLOW)
        racer = self.title_font.render("Racer", True, RED)
        total = yo.get_width() + racer.get_width()
        x0 = WIDTH // 2 - total // 2
        for word, col, dx in (("Yo", YELLOW, 0), ("Racer", RED, yo.get_width())):
            shadow = self.title_font.render(word, True, (0, 0, 0))
            self.screen.blit(shadow, (x0 + dx + 4, 124))
            self.screen.blit(self.title_font.render(word, True, col), (x0 + dx, 120))

        self.text("by Lan11ya", self.font, (WIDTH // 2, 205), center=True)

        # красная машинка в меню
        draw_car(self.screen, pygame.Rect(WIDTH // 2 - CAR_W // 2, 255, CAR_W, CAR_H), RED)

        self.draw_button(BTN_A, "ИГРАТЬ")
        self.draw_button(BTN_B, "ВЫХОД", (150, 50, 50))
        self.text(f"Рекорд: {self.best}", self.font, (WIDTH // 2, 580), center=True)
        self.text("Version 1.0.0 ai test", self.small, (WIDTH // 2, 690), (140, 140, 140), center=True)
        

    def draw_game(self):
        self.draw_road()
        for e in self.enemies:
            e.draw(self.screen)
        self.player.draw(self.screen)
        self.draw_hud()
        self.draw_controls()

        if self.state == "over":
            self.dim(150)
            self.text("АВАРИЯ!", self.big, (WIDTH // 2, 170), (255, 80, 80), center=True)
            self.text(f"Счёт: {int(self.score)}", self.font, (WIDTH // 2, 270), center=True)
            self.text(f"Рекорд: {self.best}", self.font, (WIDTH // 2, 305), center=True)
            self.draw_button(BTN_A, "ЗАНОВО")
            self.draw_button(BTN_B, "В МЕНЮ", (60, 90, 160))
        elif self.state == "pause":
            self.dim(130)
            self.text("ПАУЗА", self.big, (WIDTH // 2, 200), center=True)
            self.draw_button(BTN_A, "ПРОДОЛЖИТЬ")
            self.draw_button(BTN_B, "В МЕНЮ", (60, 90, 160))

        if self.shake > 0:
            dx, dy = random.randint(-6, 6), random.randint(-6, 6)
            frame = self.screen.copy()
            self.screen.fill((0, 0, 0))
            self.screen.blit(frame, (dx, dy))
            self.shake -= 1

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        else:
            self.draw_game()
        pygame.display.flip()

    # ---------- главный цикл ----------
    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif e.type == pygame.MOUSEBUTTONDOWN:
                    # касания на тачскринах приходят отдельно как FINGER*-события
                    if e.button == 1 and not getattr(e, "touch", False):
                        self.handle_click(e.pos)

                elif e.type == pygame.FINGERDOWN:
                    p = (e.x * WIDTH, e.y * HEIGHT)
                    self.fingers[e.finger_id] = p
                    self.handle_click(p)
                elif e.type == pygame.FINGERMOTION:
                    self.fingers[e.finger_id] = (e.x * WIDTH, e.y * HEIGHT)
                elif e.type == pygame.FINGERUP:
                    self.fingers.pop(e.finger_id, None)

                elif e.type == pygame.KEYDOWN:
                    if e.key in (pygame.K_RETURN, pygame.K_SPACE) and self.state in ("menu", "over"):
                        self.start()
                    elif e.key == pygame.K_r and self.state == "over":
                        self.start()
                    elif e.key in (pygame.K_p, pygame.K_ESCAPE):
                        if self.state == "play":
                            self.state = "pause"
                        elif self.state == "pause":
                            self.state = "play" if e.key == pygame.K_p else "menu"
                        elif self.state == "over":
                            self.state = "menu"
                        elif self.state == "menu" and e.key == pygame.K_ESCAPE:
                            pygame.quit()
                            sys.exit()

            if self.state == "play":
                self.update()

            self.draw()
            self.clock.tick(FPS)


if __name__ == "__main__":
    Game().run()