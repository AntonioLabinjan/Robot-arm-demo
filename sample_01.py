import math
import random
import pygame

WIDTH, HEIGHT = 1100, 700
FPS = 60

BASE = pygame.Vector2(WIDTH // 2, HEIGHT - 120)
SEGMENTS = [130, 110, 90, 70]
TARGET_RADIUS = 14

BG = (8, 10, 18)
GRID = (25, 32, 48)
ARM = (90, 210, 255)
ARM_DARK = (30, 85, 120)
JOINT = (255, 230, 120)
TARGET = (255, 80, 130)
TEXT = (220, 235, 255)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Robot Arm IK Playground")
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 18)


def make_arm():
    points = [BASE.copy()]
    angle = -math.pi / 2
    for length in SEGMENTS:
        last = points[-1]
        points.append(last + pygame.Vector2(math.cos(angle), math.sin(angle)) * length)
    return points


def fabrik(points, target, lengths, iterations=12):
    total_length = sum(lengths)

    if BASE.distance_to(target) > total_length:
        direction = (target - BASE).normalize()
        points[0] = BASE.copy()
        for i, length in enumerate(lengths):
            points[i + 1] = points[i] + direction * length
        return points

    for _ in range(iterations):
        points[-1] = target.copy()

        for i in reversed(range(len(points) - 1)):
            direction = (points[i] - points[i + 1]).normalize()
            points[i] = points[i + 1] + direction * lengths[i]

        points[0] = BASE.copy()

        for i, length in enumerate(lengths):
            direction = (points[i + 1] - points[i]).normalize()
            points[i + 1] = points[i] + direction * length

    return points


def draw_grid():
    for x in range(0, WIDTH, 40):
        pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT), 1)
    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID, (0, y), (WIDTH, y), 1)


def draw_glow_line(a, b, color):
    for width, alpha in [(18, 40), (12, 55), (7, 90)]:
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.line(surf, (*color, alpha), a, b, width)
        screen.blit(surf, (0, 0))
    pygame.draw.line(screen, color, a, b, 5)


def draw_robot(points):
    pygame.draw.circle(screen, (35, 45, 65), BASE, 44)
    pygame.draw.circle(screen, ARM_DARK, BASE, 35)
    pygame.draw.circle(screen, ARM, BASE, 8)

    for a, b in zip(points[:-1], points[1:]):
        draw_glow_line(a, b, ARM)

    for p in points:
        pygame.draw.circle(screen, (20, 26, 38), p, 16)
        pygame.draw.circle(screen, JOINT, p, 10)
        pygame.draw.circle(screen, (255, 255, 255), p, 4)

    end = points[-1]
    prev = points[-2]
    direction = (end - prev).normalize()
    normal = pygame.Vector2(-direction.y, direction.x)

    claw_a = end + normal * 18 + direction * 16
    claw_b = end - normal * 18 + direction * 16

    pygame.draw.line(screen, TARGET, end, claw_a, 4)
    pygame.draw.line(screen, TARGET, end, claw_b, 4)


def draw_target(target, t):
    pulse = math.sin(t * 6) * 4
    pygame.draw.circle(screen, TARGET, target, int(TARGET_RADIUS + pulse), 2)
    pygame.draw.circle(screen, TARGET, target, 5)

    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*TARGET, 40), target, 45)
    screen.blit(surf, (0, 0))


def draw_hud(target, end):
    error = end.distance_to(target)
    lines = [
        "Robot Arm IK Playground",
        "Mouse: move target",
        "SPACE: random target",
        "R: reset arm",
        f"End-effector error: {error:.2f}px",
    ]

    y = 20
    for line in lines:
        img = font.render(line, True, TEXT)
        screen.blit(img, (20, y))
        y += 24


def random_target():
    return pygame.Vector2(
        random.randint(180, WIDTH - 180),
        random.randint(100, HEIGHT - 220),
    )


points = make_arm()
target = pygame.Vector2(WIDTH // 2, HEIGHT // 2)
trail = []

running = True
time_alive = 0

while running:
    dt = clock.tick(FPS) / 1000
    time_alive += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                target = random_target()
            elif event.key == pygame.K_r:
                points = make_arm()

    mouse = pygame.Vector2(pygame.mouse.get_pos())

    if pygame.mouse.get_focused():
        target = target.lerp(mouse, 0.18)

    points = fabrik(points, target, SEGMENTS)

    trail.append(points[-1].copy())
    if len(trail) > 35:
        trail.pop(0)

    screen.fill(BG)
    draw_grid()

    for i, p in enumerate(trail):
        alpha = int(255 * (i / len(trail)))
        radius = int(2 + 5 * (i / len(trail)))
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        pygame.draw.circle(surf, (90, 210, 255, alpha // 3), p, radius)
        screen.blit(surf, (0, 0))

    draw_target(target, time_alive)
    draw_robot(points)
    draw_hud(target, points[-1])

    pygame.display.flip()

pygame.quit()
