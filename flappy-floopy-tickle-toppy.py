import colorsys
import json
import math
import os
import random
import sys

import pygame

# ============================== SETTINGS ==============================
W, H = 1000, 1000
FLOOR_H = 100
BIRD_X, BIRD_START_Y = 150, 750      # spawn position
BIRD_R = 20
GRAVITY = 1800
BASE_JUMP = 50                       # px risen per flap (smooth)
BOOST_JUMP = 85                      # px risen per flap with Jump Boost
TUBE_W = 90
TUBE_SPACING = 300                   # new tube every 300 px
ITEM_TIME = 10.0                     # seconds every item lasts
COINS_PER_SCORE = 2                  # 30 score -> 60 coins
SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flappy_save.json")

MODES = {
    "easy": dict(name="EASY", speed=250, gap=270, item=0.07, inc=22, cap=420,
                 tube=(76, 175, 80), sky=((88, 190, 232), (190, 236, 244))),
    "hard": dict(name="HARD", speed=300, gap=215, item=0.14, inc=35, cap=560,
                 tube=(230, 90, 50), sky=((60, 25, 120), (255, 150, 100))),
}
ITEMS = {
    "shield": dict(name="SHIELD", color=(66, 165, 245)),
    "slow": dict(name="SLOW-MO", color=(186, 104, 200)),
    "boost": dict(name="JUMP BOOST", color=(255, 160, 0)),
}
SKINS = [
    dict(id="classic", name="Classic", price=0, body=(247, 213, 29), wing=(232, 184, 0), beak=(245, 124, 0)),
    dict(id="crimson", name="Crimson", price=100, body=(229, 57, 53), wing=(183, 28, 28), beak=(255, 193, 7)),
    dict(id="ocean", name="Ocean", price=200, body=(41, 182, 246), wing=(2, 119, 189), beak=(255, 167, 38)),
    dict(id="toxic", name="Toxic", price=300, body=(118, 255, 3), wing=(67, 160, 71), beak=(255, 64, 129)),
    dict(id="royal", name="Royal", price=450, body=(171, 71, 188), wing=(106, 27, 154), beak=(255, 213, 79)),
    dict(id="gold", name="Golden", price=700, body=(255, 215, 0), wing=(255, 160, 0), beak=(255, 87, 34), trail=(255, 215, 0)),
    dict(id="rainbow", name="Rainbow", price=1000, rainbow=True),
]

pygame.init()
window = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("Flappy Bird Deluxe")
screen = pygame.Surface((W, H))      # everything is drawn here (allows screen shake)
clock = pygame.time.Clock()


# ============================== HELPERS ==============================
_fonts = {}


def font(size):
    if size not in _fonts:
        _fonts[size] = pygame.font.SysFont("arial", size, bold=True)
    return _fonts[size]


def text(s, size, pos, color=(255, 255, 255), anchor="center", alpha=255, o=3):
    main = font(size).render(str(s), True, color)
    edge = font(size).render(str(s), True, (20, 20, 30))
    if alpha < 255:
        main.set_alpha(alpha)
        edge.set_alpha(alpha)
    r = main.get_rect()
    setattr(r, anchor, pos)
    for dx, dy in ((-o, 0), (o, 0), (0, -o), (0, o), (o, o), (-o, -o), (o, -o), (-o, o)):
        screen.blit(edge, r.move(dx, dy))
    screen.blit(main, r)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c)


def gradient(top, bottom):
    s = pygame.Surface((W, H))
    for y in range(H):
        k = y / H
        s.fill(tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)), (0, y, W, 1))
    return s


SKY = {m: gradient(*MODES[m]["sky"]) for m in MODES}
_skin_cache = {}


def bird_surface(skin, t=0.0):
    if skin.get("rainbow"):
        h = (t * 0.4) % 1
        body = tuple(int(v * 255) for v in colorsys.hsv_to_rgb(h, 0.8, 1))
        wing = tuple(int(v * 255) for v in colorsys.hsv_to_rgb((h + 0.15) % 1, 0.9, 0.85))
        beak = (255, 255, 255)
    else:
        if skin["id"] in _skin_cache:
            return _skin_cache[skin["id"]]
        body, wing, beak = skin["body"], skin["wing"], skin["beak"]
    s = pygame.Surface((80, 80), pygame.SRCALPHA)
    cx, cy, ink = 40, 40, (45, 45, 55)
    pygame.draw.ellipse(s, body, (cx - 26, cy - 20, 52, 40))
    pygame.draw.ellipse(s, ink, (cx - 26, cy - 20, 52, 40), 3)
    pygame.draw.circle(s, (255, 255, 255), (cx + 10, cy - 7), 8)
    pygame.draw.circle(s, ink, (cx + 10, cy - 7), 8, 2)
    pygame.draw.circle(s, (0, 0, 0), (cx + 13, cy - 7), 3)
    b = [(cx + 18, cy + 2), (cx + 36, cy + 6), (cx + 18, cy + 13)]
    pygame.draw.polygon(s, beak, b)
    pygame.draw.polygon(s, ink, b, 2)
    pygame.draw.ellipse(s, wing, (cx - 20, cy - 2, 24, 14))
    pygame.draw.ellipse(s, ink, (cx - 20, cy - 2, 24, 14), 2)
    if not skin.get("rainbow"):
        _skin_cache[skin["id"]] = s
    return s


def draw_bird(skin, x, y, angle, t, scale=1.0):
    s = bird_surface(skin, t)
    if scale != 1.0:
        s = pygame.transform.smoothscale(s, (int(80 * scale), int(80 * scale)))
    r = pygame.transform.rotate(s, -math.degrees(angle))
    screen.blit(r, r.get_rect(center=(x, y)))


def draw_coin(x, y, r=14):
    pygame.draw.circle(screen, (255, 193, 7), (x, y), r)
    pygame.draw.circle(screen, (255, 241, 118), (x, y), r - 4)
    pygame.draw.circle(screen, (255, 193, 7), (x, y), r - 7)
    pygame.draw.circle(screen, (150, 100, 0), (x, y), r, 2)


def button(rect, label, hover, color=(255, 255, 255), sub=None):
    r = pygame.Rect(rect)
    pygame.draw.rect(screen, (20, 20, 30), r.move(0, 8), border_radius=22)
    base = shade(color, 1.0 if hover else 0.82)
    pygame.draw.rect(screen, base, r.move(0, -4 if hover else 0), border_radius=22)
    pygame.draw.rect(screen, (20, 20, 30), r.move(0, -4 if hover else 0), 4, border_radius=22)
    text(label, 44, (r.centerx, r.centery - (4 if hover else 0) - (10 if sub else 0)))
    if sub:
        text(sub, 22, (r.centerx, r.centery + 22 - (4 if hover else 0)), (255, 255, 255), o=2)


def circle_hits_rect(cx, cy, rect):
    nx = max(rect.left, min(cx, rect.right))
    ny = max(rect.top, min(cy, rect.bottom))
    return (cx - nx) ** 2 + (cy - ny) ** 2 < BIRD_R ** 2


def draw_tube(x, y, h, cap_bottom, col):
    dark, edge = shade(col, 0.75), shade(col, 0.5)
    body = pygame.Rect(int(x), int(y), TUBE_W, int(h))
    pygame.draw.rect(screen, col, body)
    pygame.draw.rect(screen, shade(col, 1.25), (body.x + 12, body.y, 10, body.h))
    pygame.draw.rect(screen, dark, (body.right - 16, body.y, 16, body.h))
    cap = pygame.Rect(body.x - 7, body.bottom - 38 if cap_bottom else body.y, TUBE_W + 14, 38)
    pygame.draw.rect(screen, col, cap, border_radius=6)
    pygame.draw.rect(screen, shade(col, 1.25), (cap.x + 8, cap.y + 4, 10, 30), border_radius=4)
    pygame.draw.rect(screen, dark, (cap.right - 18, cap.y + 2, 14, 34), border_radius=4)
    pygame.draw.rect(screen, edge, body, 3)
    pygame.draw.rect(screen, edge, cap, 3, border_radius=6)


def draw_item(kind, x, y, t):
    col = ITEMS[kind]["color"]
    y += math.sin(t * 4 + x * 0.01) * 6
    glow = pygame.Surface((100, 100), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*col, 70), (50, 50), 38 + int(math.sin(t * 6) * 4))
    screen.blit(glow, (x - 50, y - 50))
    pygame.draw.circle(screen, col, (x, y), 24)
    pygame.draw.circle(screen, (20, 20, 30), (x, y), 24, 3)
    w = (255, 255, 255)
    if kind == "shield":
        pygame.draw.polygon(screen, w, [(x - 11, y - 12), (x + 11, y - 12), (x + 10, y + 3), (x, y + 14), (x - 10, y + 3)])
    elif kind == "slow":
        pygame.draw.circle(screen, w, (x, y), 12, 3)
        pygame.draw.line(screen, w, (x, y), (x, y - 8), 3)
        pygame.draw.line(screen, w, (x, y), (x + 6, y + 3), 3)
    else:
        pygame.draw.polygon(screen, w, [(x, y - 13), (x + 12, y + 1), (x + 5, y + 1), (x + 5, y + 12), (x - 5, y + 12), (x - 5, y + 1), (x - 12, y + 1)])


# ============================== GAME ==============================
class Game:
    def __init__(self):
        self.save = self.load_save()
        self.scene = "menu"            # menu | shop | run
        self.sel = 0
        self.shop_sel = 0
        self.t = 0.0
        self.msg, self.msg_t = "", 0
        self.shake = 0.0
        self.banner = 0.0
        self.popups = []
        self.particles = []
        self.floor_scroll = 0.0
        self.clouds = [[random.uniform(0, W), random.uniform(40, 520), random.uniform(0.6, 1.5), random.uniform(8, 28)] for _ in range(7)]
        self.mode_key = "easy"

    # ---------- save ----------
    def load_save(self):
        d = {"coins": 0, "owned": ["classic"], "skin": "classic", "best": {"easy": 0, "hard": 0}}
        try:
            with open(SAVE_FILE) as f:
                d.update(json.load(f))
        except Exception:
            pass
        d["best"].setdefault("easy", 0)
        d["best"].setdefault("hard", 0)
        return d

    def write_save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(self.save, f)
        except Exception:
            pass

    @property
    def skin(self):
        return next(s for s in SKINS if s["id"] == self.save["skin"])

    # ---------- run ----------
    def start_run(self, mode_key):
        self.mode_key = mode_key
        self.mode = MODES[mode_key]
        self.scene = "run"
        self.reset_run()

    def reset_run(self):
        self.state = "ready"           # ready -> play -> over
        self.bird_y, self.vy, self.angle = float(BIRD_START_Y), 0.0, 0.0
        self.tubes, self.items, self.popups = [], [], []
        self.travelled = TUBE_SPACING
        self.score = 0
        self.speed = float(self.mode["speed"])
        self.since_up, self.next_up = 0, random.randint(5, 8)
        self.effects = {}
        self.banner = 0.0
        self.earned = 0
        self.new_best = False

    def flap(self):
        h = BOOST_JUMP if "boost" in self.effects else BASE_JUMP
        self.vy = -math.sqrt(2 * GRAVITY * h)
        self.burst(BIRD_X - 10, self.bird_y + 8, 4, (255, 255, 255), 90)

    def burst(self, x, y, n, color, power=200):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1) * power
            self.particles.append([x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0.3, 0.7), color, random.uniform(3, 7)])

    def on_score(self):
        self.score += 1
        self.since_up += 1
        if self.since_up >= self.next_up:                      # speed-up every 5-8 tubes
            self.speed = min(self.mode["cap"], self.speed + self.mode["inc"])
            self.since_up, self.next_up = 0, random.randint(5, 8)
            self.banner = 1.6

    def die(self):
        self.state = "over"
        self.shake = 0.45
        self.burst(BIRD_X, self.bird_y, 40, self.skin.get("body", (255, 200, 60)), 420)
        self.earned = self.score * COINS_PER_SCORE
        self.save["coins"] += self.earned
        if self.score > self.save["best"][self.mode_key]:
            self.save["best"][self.mode_key] = self.score
            self.new_best = self.score > 0
        self.write_save()

    def update_run(self, dt):
        if self.state == "ready":
            self.bird_y = BIRD_START_Y + math.sin(self.t * 4) * 8
            return
        if self.state == "over":
            return
        for k in list(self.effects):
            self.effects[k] -= dt
            if self.effects[k] <= 0:
                del self.effects[k]
        spd = self.speed * (0.6 if "slow" in self.effects else 1.0)
        self.vy += GRAVITY * dt
        self.bird_y += self.vy * dt
        if self.bird_y < BIRD_R:
            self.bird_y, self.vy = BIRD_R, 0
        target = max(-0.5, min(1.4, self.vy / 450))
        self.angle += (target - self.angle) * min(1, dt * 10)
        self.floor_scroll = (self.floor_scroll + spd * dt) % 48

        # trail
        tc = self.skin.get("trail") or ((255, 255, 255) if "boost" not in self.effects else ITEMS["boost"]["color"])
        if random.random() < 0.7:
            self.particles.append([BIRD_X - 18, self.bird_y + random.uniform(-6, 6), -spd * 0.4, random.uniform(-20, 20), 0.35, tc, 5])

        # spawn
        self.travelled += spd * dt
        if self.travelled >= TUBE_SPACING:
            self.travelled -= TUBE_SPACING
            gap = self.mode["gap"]
            gy = random.uniform(150, H - FLOOR_H - 150 - gap)
            self.tubes.append({"x": float(W), "gy": gy, "passed": False})
            if random.random() < self.mode["item"]:
                self.items.append({"x": W + TUBE_W / 2, "y": gy + gap / 2 + random.uniform(-gap / 2 + 45, gap / 2 - 45),
                                   "kind": random.choice(list(ITEMS))})

        for t in self.tubes:
            t["x"] -= spd * dt
            if not t["passed"] and t["x"] + TUBE_W < BIRD_X:
                t["passed"] = True
                self.on_score()
        for it in self.items:
            it["x"] -= spd * dt
            if math.hypot(it["x"] - BIRD_X, it["y"] - self.bird_y) < BIRD_R + 24:
                self.effects[it["kind"]] = ITEM_TIME
                self.burst(it["x"], it["y"], 25, ITEMS[it["kind"]]["color"], 300)
                self.popups.append([ITEMS[it["kind"]]["name"], BIRD_X, self.bird_y - 40, 1.2, ITEMS[it["kind"]]["color"]])
                it["dead"] = True
        self.items = [i for i in self.items if not i.get("dead") and i["x"] > -40]
        self.tubes = [t for t in self.tubes if t["x"] + TUBE_W > -20]

        # collisions
        shield = "shield" in self.effects
        if self.bird_y + BIRD_R >= H - FLOOR_H:
            self.bird_y = H - FLOOR_H - BIRD_R
            if shield:                                       # shield bounces you off the floor
                self.vy = -math.sqrt(2 * GRAVITY * 90)
                self.burst(BIRD_X, self.bird_y + 20, 15, ITEMS["shield"]["color"], 250)
            else:
                self.die()
                return
        if not shield:
            gap = self.mode["gap"]
            for t in self.tubes:
                top = pygame.Rect(t["x"], 0, TUBE_W, t["gy"])
                by = t["gy"] + gap
                bot = pygame.Rect(t["x"], by, TUBE_W, H - FLOOR_H - by)
                if circle_hits_rect(BIRD_X, self.bird_y, top) or circle_hits_rect(BIRD_X, self.bird_y, bot):
                    self.die()
                    return

    # ---------- generic update ----------
    def update(self, dt):
        self.t += dt
        self.msg_t = max(0, self.msg_t - dt)
        self.shake = max(0, self.shake - dt)
        self.banner = max(0, self.banner - dt)
        for c in self.clouds:
            c[0] -= c[3] * dt
            if c[0] < -200:
                c[0], c[1] = W + 100, random.uniform(40, 520)
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for p in getattr(self, "popups", []):
            p[2] -= 40 * dt
            p[3] -= dt
        if hasattr(self, "popups"):
            self.popups = [p for p in self.popups if p[3] > 0]
        if self.scene == "run":
            self.update_run(dt)

    # ---------- drawing ----------
    def draw_world(self, mode_key):
        screen.blit(SKY[mode_key], (0, 0))
        if mode_key == "hard":
            pygame.draw.circle(screen, (255, 210, 120), (780, 520), 90)
        for cx, cy, sc, _ in self.clouds:
            col = (245, 250, 255) if mode_key == "easy" else (255, 190, 170)
            for dx, dy, r in ((0, 0, 40), (45, 10, 32), (-45, 12, 30), (15, -22, 30)):
                pygame.draw.circle(screen, col, (int(cx + dx * sc), int(cy + dy * sc)), int(r * sc))

    def draw_floor(self, col_top):
        pygame.draw.rect(screen, (222, 216, 149), (0, H - FLOOR_H, W, FLOOR_H))
        for x in range(-48, W + 48, 48):
            ox = x - self.floor_scroll
            pygame.draw.polygon(screen, (205, 198, 130), [(ox, H - FLOOR_H + 16), (ox + 24, H - FLOOR_H + 16), (ox + 8, H), (ox - 16, H)])
        pygame.draw.rect(screen, col_top, (0, H - FLOOR_H, W, 16))
        pygame.draw.rect(screen, shade(col_top, 0.6), (0, H - FLOOR_H + 14, W, 4))

    def draw_coins_hud(self):
        draw_coin(W - 150, 50)
        text(self.save["coins"], 40, (W - 125, 50), (255, 224, 90), "midleft")

    def draw_run(self):
        m = self.mode
        self.draw_world(self.mode_key)
        for t in self.tubes:
            draw_tube(t["x"], 0, t["gy"], True, m["tube"])
            by = t["gy"] + m["gap"]
            draw_tube(t["x"], by, H - FLOOR_H - by, False, m["tube"])
        for it in self.items:
            draw_item(it["kind"], int(it["x"]), int(it["y"]), self.t)
        self.draw_floor((115, 191, 46) if self.mode_key == "easy" else (150, 110, 60))
        for x, y, _, _, life, col, sz in self.particles:
            pygame.draw.circle(screen, col, (int(x), int(y)), max(1, int(sz * min(1, life * 2.5))))
        if "slow" in self.effects:
            tint = pygame.Surface((W, H), pygame.SRCALPHA)
            tint.fill((150, 80, 200, 35))
            screen.blit(tint, (0, 0))
        if self.state != "over":
            draw_bird(self.skin, BIRD_X, self.bird_y, self.angle, self.t)
        if "shield" in self.effects and self.state != "over":
            left = self.effects["shield"]
            if left > 2 or int(self.t * 8) % 2 == 0:
                bub = pygame.Surface((110, 110), pygame.SRCALPHA)
                pygame.draw.circle(bub, (66, 165, 245, 70), (55, 55), 40)
                pygame.draw.circle(bub, (150, 210, 255, 220), (55, 55), 40, 4)
                screen.blit(bub, (BIRD_X - 55, self.bird_y - 55))
        for label, x, y, life, col in self.popups:
            text(label, 30, (x, y), col, alpha=int(255 * min(1, life * 2)))

        # HUD
        text(self.score, 100, (W // 2, 110))
        text(m["name"], 26, (20, 20), m["tube"], "topleft")
        text(f"Speed x{self.speed / m['speed']:.2f}", 22, (20, 52), (255, 255, 255), "topleft", o=2)
        self.draw_coins_hud()
        yy = 100
        for k, left in self.effects.items():
            col = ITEMS[k]["color"]
            r = pygame.Rect(20, yy, 230, 34)
            pygame.draw.rect(screen, (20, 20, 30), r, border_radius=10)
            pygame.draw.rect(screen, col, (r.x + 3, r.y + 3, int(224 * left / ITEM_TIME), 28), border_radius=8)
            text(f"{ITEMS[k]['name']}  {left:0.1f}s", 20, r.center, o=2)
            yy += 42
        if self.banner > 0:
            text("SPEED UP!", 90, (W // 2, 260), (255, 235, 59), alpha=int(255 * min(1, self.banner * 2)))
        if self.state == "ready":
            text("Press SPACE to start", 56, (W // 2, 330))
            text("ESC = menu", 28, (W // 2, 390))
        if self.state == "over":
            ov = pygame.Surface((W, H), pygame.SRCALPHA)
            ov.fill((0, 0, 0, 110))
            screen.blit(ov, (0, 0))
            text("GAME OVER", 110, (W // 2, 330), (255, 90, 80))
            text(f"Score {self.score}   Best {self.save['best'][self.mode_key]}", 52, (W // 2, 430))
            if self.new_best:
                text("NEW BEST!", 40, (W // 2, 490), (255, 235, 59))
            draw_coin(W // 2 - 110, 570, 20)
            text(f"+{self.earned} coins", 52, (W // 2 - 80, 570), (255, 224, 90), "midleft")
            text("SPACE = retry     M = menu", 38, (W // 2, 680))

    def draw_menu(self):
        self.draw_world("easy")
        self.draw_floor((115, 191, 46))
        text("FLAPPY BIRD", 130, (W // 2, 150), (255, 235, 59), o=5)
        text("D E L U X E", 44, (W // 2, 235), (255, 255, 255))
        draw_bird(self.skin, W // 2, 330 + math.sin(self.t * 3) * 14, math.sin(self.t * 3) * 0.25, self.t, 1.9)
        labels = [("EASY", (76, 175, 80), f"best {self.save['best']['easy']}"),
                  ("HARD", (229, 57, 53), f"best {self.save['best']['hard']}"),
                  ("SKINS", (66, 133, 244), "spend your coins"),
                  ("QUIT", (120, 120, 140), None)]
        self.menu_rects = []
        for i, (lab, col, sub) in enumerate(labels):
            r = pygame.Rect(W // 2 - 190, 440 + i * 105, 380, 88)
            self.menu_rects.append(r)
            button(r, lab, i == self.sel, col, sub)
        self.draw_coins_hud()
        text("UP/DOWN + ENTER or mouse", 24, (W // 2, H - 50), (255, 255, 255), o=2)

    def draw_shop(self):
        self.draw_world("easy")
        text("SKINS", 90, (W // 2, 90), (255, 235, 59), o=4)
        self.draw_coins_hud()
        self.card_rects = []
        for i, s in enumerate(SKINS):
            col, row = i % 4, i // 4
            r = pygame.Rect(55 + col * 230, 170 + row * 310, 200, 280)
            self.card_rects.append(r)
            owned = s["id"] in self.save["owned"]
            chosen = s["id"] == self.save["skin"]
            pygame.draw.rect(screen, (20, 20, 30), r.move(0, 7), border_radius=20)
            pygame.draw.rect(screen, (255, 255, 255) if i != self.shop_sel else (255, 245, 170), r, border_radius=20)
            pygame.draw.rect(screen, (66, 133, 244) if chosen else (20, 20, 30), r, 6 if (chosen or i == self.shop_sel) else 3, border_radius=20)
            draw_bird(s, r.centerx, r.y + 100 + math.sin(self.t * 3 + i) * 5, math.sin(self.t * 3 + i) * 0.2, self.t, 1.6)
            text(s["name"], 30, (r.centerx, r.y + 185))
            if chosen:
                text("SELECTED", 26, (r.centerx, r.y + 240), (60, 200, 90))
            elif owned:
                text("OWNED", 26, (r.centerx, r.y + 240), (60, 170, 255))
            else:
                draw_coin(r.centerx - 45, r.y + 240, 13)
                text(s["price"], 30, (r.centerx - 25, r.y + 240), (255, 224, 90), "midleft")
        self.back_rect = pygame.Rect(W // 2 - 130, 880, 260, 70)
        button(self.back_rect, "BACK", False, (120, 120, 140))
        if self.msg_t > 0:
            text(self.msg, 40, (W // 2, 820), (255, 235, 59), alpha=int(255 * min(1, self.msg_t * 2)))

    def draw(self):
        if self.scene == "menu":
            self.draw_menu()
        elif self.scene == "shop":
            self.draw_shop()
        else:
            self.draw_run()
        ox = oy = 0
        if self.shake > 0:
            amp = self.shake * 30
            ox, oy = random.uniform(-amp, amp), random.uniform(-amp, amp)
        window.fill((0, 0, 0))
        window.blit(screen, (ox, oy))
        pygame.display.flip()

    # ---------- input ----------
    def menu_activate(self, i):
        if i == 0:
            self.start_run("easy")
        elif i == 1:
            self.start_run("hard")
        elif i == 2:
            self.scene = "shop"
        else:
            pygame.quit()
            sys.exit()

    def shop_activate(self, i):
        s = SKINS[i]
        if s["id"] in self.save["owned"]:
            self.save["skin"] = s["id"]
        elif self.save["coins"] >= s["price"]:
            self.save["coins"] -= s["price"]
            self.save["owned"].append(s["id"])
            self.save["skin"] = s["id"]
            self.burst(W // 2, 500, 40, (255, 224, 90), 400)
            self.msg, self.msg_t = f"Bought {s['name']}!", 1.5
        else:
            self.msg, self.msg_t = "Not enough coins!", 1.5
        self.write_save()

    def handle(self, e):
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if self.scene == "menu":
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_UP, pygame.K_w):
                    self.sel = (self.sel - 1) % 4
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    self.sel = (self.sel + 1) % 4
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.menu_activate(self.sel)
            elif e.type == pygame.MOUSEMOTION:
                for i, r in enumerate(getattr(self, "menu_rects", [])):
                    if r.collidepoint(e.pos):
                        self.sel = i
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                for i, r in enumerate(getattr(self, "menu_rects", [])):
                    if r.collidepoint(e.pos):
                        self.menu_activate(i)
        elif self.scene == "shop":
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.scene = "menu"
                elif e.key == pygame.K_LEFT:
                    self.shop_sel = (self.shop_sel - 1) % len(SKINS)
                elif e.key == pygame.K_RIGHT:
                    self.shop_sel = (self.shop_sel + 1) % len(SKINS)
                elif e.key == pygame.K_UP:
                    self.shop_sel = max(0, self.shop_sel - 4)
                elif e.key == pygame.K_DOWN:
                    self.shop_sel = min(len(SKINS) - 1, self.shop_sel + 4)
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.shop_activate(self.shop_sel)
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                if self.back_rect.collidepoint(e.pos):
                    self.scene = "menu"
                for i, r in enumerate(self.card_rects):
                    if r.collidepoint(e.pos):
                        self.shop_sel = i
                        self.shop_activate(i)
        else:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_SPACE:
                    if self.state == "ready":
                        self.state = "play"          # starts on the first SPACE
                        self.flap()
                    elif self.state == "play":
                        self.flap()
                    else:
                        self.reset_run()
                elif e.key in (pygame.K_ESCAPE, pygame.K_m):
                    self.scene = "menu"
            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and self.state == "play":
                self.flap()


def main():
    g = Game()
    while True:
        dt = min(clock.tick(60) / 1000, 0.033)
        for e in pygame.event.get():
            g.handle(e)
        g.update(dt)
        g.draw()


if __name__ == "__main__":
    main()