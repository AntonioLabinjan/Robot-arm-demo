import math
import random
import pygame

WIDTH, HEIGHT = 1320, 780
PANEL_W = 350
FPS = 60
MAX_JOINTS = 8

BG = (7, 9, 16)
PANEL = (13, 17, 28)
PANEL_2 = (20, 27, 42)
GRID = (27, 34, 52)
TEXT = (226, 236, 255)
MUTED = (138, 151, 178)
ARM = (80, 205, 255)
ARM_DARK = (24, 74, 105)
JOINT = (255, 228, 118)
TARGET = (255, 85, 135)
TARGET_2 = (184, 120, 255)
GOOD = (105, 240, 170)
BAD = (255, 105, 120)
WARN = (255, 176, 85)

MODE_END_IK = "END IK"
MODE_JOINT_IK = "JOINT IK"
MODE_FK = "MANUAL FK"

SELF_COLLISION_ENABLED = True
MIN_BEND_DEG = 4.0

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Robot Kinematics Lab")
clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 17)
small_font = pygame.font.SysFont("consolas", 14)
big_font = pygame.font.SysFont("consolas", 25, bold=True)

BASE = pygame.Vector2(PANEL_W + (WIDTH - PANEL_W) // 2, HEIGHT - 95)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def normalize_angle(angle):
    while angle > 180:
        angle -= 360

    while angle < -180:
        angle += 360

    return angle


def signed_angle_deg(a, b):
    if a.length_squared() < 1e-9 or b.length_squared() < 1e-9:
        return 0

    dot = clamp(a.normalize().dot(b.normalize()), -1, 1)
    cross = a.cross(b)
    angle = math.degrees(math.acos(dot))

    return angle if cross >= 0 else -angle


def safe_dir(vector, fallback=pygame.Vector2(1, 0)):
    if vector.length_squared() < 1e-9:
        return fallback.copy()

    return vector.normalize()


def world_to_screen(pos):
    return pygame.Vector2(BASE.x + pos.x, BASE.y - pos.y)


def screen_to_world(pos):
    p = pygame.Vector2(pos)
    return pygame.Vector2(p.x - BASE.x, BASE.y - p.y)


def draw_text(surface, value, x, y, color=TEXT, used_font=None):
    img = (used_font or font).render(str(value), True, color)
    surface.blit(img, (x, y))


def wrap_text(text, used_font, max_width):
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else f"{current} {word}"

        if used_font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    return lines


def draw_tooltip(surface, text, anchor_rect):
    max_width = 280
    padding = 10
    lines = wrap_text(text, small_font, max_width)

    if not lines:
        return

    line_h = 18
    box_w = max(small_font.size(line)[0] for line in lines) + padding * 2
    box_h = len(lines) * line_h + padding * 2

    x = anchor_rect.right + 10
    y = anchor_rect.top - 6

    if x + box_w > WIDTH - 12:
        x = anchor_rect.left - box_w - 10

    if y + box_h > HEIGHT - 12:
        y = HEIGHT - box_h - 12

    if y < 12:
        y = 12

    rect = pygame.Rect(x, y, box_w, box_h)

    surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    pygame.draw.rect(surf, (8, 12, 22, 238), surf.get_rect(), border_radius=10)
    pygame.draw.rect(surf, (90, 210, 255, 180), surf.get_rect(), 1, border_radius=10)
    surface.blit(surf, rect.topleft)

    for i, line in enumerate(lines):
        draw_text(surface, line, rect.x + padding, rect.y + padding + i * line_h, TEXT, small_font)


class Slider:
    def __init__(self, x, y, w, label, min_value, max_value, value, integer=False, info=""):
        self.rect = pygame.Rect(x, y, w, 8)
        self.label = label
        self.min_value = min_value
        self.max_value = max_value
        self.value = value
        self.integer = integer
        self.dragging = False
        self.info = info
        self.pinned_info = False
        self.info_rect = pygame.Rect(0, 0, 22, 18)
        self.update_info_rect()
        self.set(value)

    def update_info_rect(self):
        self.info_rect.topleft = (self.rect.right - 24, self.rect.y - 28)

    def value_ratio(self):
        span = self.max_value - self.min_value

        if abs(span) < 1e-9:
            return 0

        return clamp((self.value - self.min_value) / span, 0, 1)

    def set(self, value):
        self.value = clamp(value, self.min_value, self.max_value)

        if self.integer:
            self.value = round(self.value)

    def update_from_mouse(self, mx):
        span = self.max_value - self.min_value

        if abs(span) < 1e-9:
            self.set(self.min_value)
            return

        t = clamp((mx - self.rect.left) / self.rect.width, 0, 1)
        value = self.min_value + t * span
        self.set(value)

    def info_hovered(self):
        return self.info_rect.collidepoint(pygame.mouse.get_pos())

    def handle_event(self, event):
        self.update_info_rect()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.info and self.info_rect.collidepoint(event.pos):
                self.pinned_info = not self.pinned_info
                return "info"

            mx, my = event.pos
            knob_x = self.rect.left + self.value_ratio() * self.rect.width
            knob = pygame.Rect(knob_x - 10, self.rect.centery - 10, 20, 20)
            hit_area = self.rect.inflate(10, 22)

            if hit_area.collidepoint(mx, my) or knob.collidepoint(mx, my):
                self.dragging = True
                self.update_from_mouse(mx)
                return "slider"

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if event.type == pygame.MOUSEMOTION and self.dragging:
            self.update_from_mouse(event.pos[0])
            return "slider"

        return None

    def draw(self, surface):
        self.update_info_rect()

        value_text = f"{int(self.value)}" if self.integer else f"{self.value:.2f}"
        draw_text(surface, f"{self.label}: {value_text}", self.rect.x, self.rect.y - 23, TEXT, small_font)

        if self.info:
            hovered = self.info_hovered()
            badge_color = ARM if hovered or self.pinned_info else (58, 70, 98)
            text_color = BG if hovered or self.pinned_info else TEXT

            pygame.draw.rect(surface, badge_color, self.info_rect, border_radius=5)
            pygame.draw.rect(surface, ARM, self.info_rect, 1, border_radius=5)

            img = small_font.render("[i]", True, text_color)
            surface.blit(img, img.get_rect(center=self.info_rect.center))

        pygame.draw.rect(surface, (45, 56, 82), self.rect, border_radius=4)

        t = self.value_ratio()
        fill = pygame.Rect(self.rect.x, self.rect.y, int(self.rect.width * t), self.rect.height)

        pygame.draw.rect(surface, ARM, fill, border_radius=4)

        knob_x = self.rect.left + t * self.rect.width
        pygame.draw.circle(surface, (245, 250, 255), (int(knob_x), self.rect.centery), 8)
        pygame.draw.circle(surface, ARM_DARK, (int(knob_x), self.rect.centery), 8, 2)


class Button:
    def __init__(self, x, y, w, h, label):
        self.rect = pygame.Rect(x, y, w, h)
        self.label = label

    def handle_event(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

    def draw(self, surface, active=False):
        color = ARM_DARK if active else PANEL_2
        border = ARM if active else (52, 64, 91)

        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, border, self.rect, 2, border_radius=10)

        img = small_font.render(self.label, True, TEXT)
        surface.blit(img, img.get_rect(center=self.rect.center))


def draw_slider_tooltips(surface, slider_list):
    active = None

    for slider in slider_list:
        if slider.pinned_info:
            active = slider
            break

    if active is None:
        for slider in slider_list:
            if slider.info_hovered():
                active = slider
                break

    if active and active.info:
        draw_tooltip(surface, active.info, active.info_rect)


def forward_kinematics(base, lengths, angles):
    points = [base.copy()]
    absolute = 0

    for length, angle in zip(lengths, angles):
        absolute += math.radians(angle)
        last = points[-1]
        direction = pygame.Vector2(math.cos(absolute), math.sin(absolute))
        points.append(last + direction * length)

    return points


def points_to_angles(points):
    result = []
    previous_absolute = 0

    for i in range(len(points) - 1):
        v = points[i + 1] - points[i]
        absolute = math.degrees(math.atan2(v.y, v.x))

        if i == 0:
            result.append(normalize_angle(absolute))
        else:
            result.append(normalize_angle(absolute - previous_absolute))

        previous_absolute = absolute

    return result


def get_bend_sides(points):
    sides = []

    for i in range(1, len(points) - 1):
        a = points[i] - points[i - 1]
        b = points[i + 1] - points[i]
        angle = signed_angle_deg(a, b)

        if abs(angle) < MIN_BEND_DEG:
            sides.append(0)
        else:
            sides.append(1 if angle > 0 else -1)

    return sides


def update_preferred_sides(points, old_sides):
    current = get_bend_sides(points)
    updated = []

    for i, side in enumerate(current):
        old = old_sides[i] if i < len(old_sides) else 0

        if side != 0:
            updated.append(side)
        else:
            updated.append(old)

    return updated


def bend_side_violations(points, preferred_sides):
    current = get_bend_sides(points)
    violations = []

    for i, side in enumerate(current):
        if i >= len(preferred_sides):
            continue

        preferred = preferred_sides[i]

        if preferred == 0 or side == 0:
            continue

        if side != preferred:
            violations.append(i + 1)

    return violations


def segment_intersection_strict(a, b, c, d, eps=1e-7):
    r = b - a
    s = d - c
    den = r.cross(s)

    if abs(den) < eps:
        if abs((c - a).cross(r)) > eps:
            return False

        rr = r.dot(r)

        if rr < eps:
            return False

        t0 = (c - a).dot(r) / rr
        t1 = (d - a).dot(r) / rr

        lo = max(0, min(t0, t1))
        hi = min(1, max(t0, t1))

        return hi - lo > eps

    t = (c - a).cross(s) / den
    u = (c - a).cross(r) / den

    return eps < t < 1 - eps and eps < u < 1 - eps


def find_self_intersections(points):
    pairs = []
    segment_count = len(points) - 1

    for i in range(segment_count):
        a = points[i]
        b = points[i + 1]

        for j in range(i + 1, segment_count):
            if abs(i - j) <= 1:
                continue

            c = points[j]
            d = points[j + 1]

            if segment_intersection_strict(a, b, c, d):
                pairs.append((i, j))

    return pairs


def evaluate_pose(points, preferred_sides, enforce_bend_lock=True):
    if not SELF_COLLISION_ENABLED:
        return True, [], []

    segment_pairs = find_self_intersections(points)
    bend_violations = bend_side_violations(points, preferred_sides) if enforce_bend_lock else []

    return len(segment_pairs) == 0 and len(bend_violations) == 0, segment_pairs, bend_violations


def mirror_point_across_line(p, a, b):
    ab = b - a

    if ab.length_squared() < 1e-9:
        return p.copy()

    u = ab.normalize()
    ap = p - a
    projection = a + u * ap.dot(u)

    return projection * 2 - p


def mirror_seed(points, a, b):
    return [mirror_point_across_line(p, a, b) for p in points]


def make_seed_from_curve(base, lengths, target, bend_deg):
    if not lengths:
        return [base.copy()]

    direction = safe_dir(target - base)
    theta = math.degrees(math.atan2(direction.y, direction.x))
    n = len(lengths)

    first_angle = theta - bend_deg * (n - 1) * 0.5
    rel_angles = [first_angle] + [bend_deg] * (n - 1)

    return forward_kinematics(base, lengths, rel_angles)


def make_ik_seeds(base, current_points, target, lengths, previous_points=None):
    seeds = []

    def add(seed):
        if seed and len(seed) == len(lengths) + 1:
            seeds.append([p.copy() for p in seed])

    add(current_points)

    if previous_points is not None:
        add(previous_points)

    add(mirror_seed(current_points, base, target))

    if previous_points is not None:
        add(mirror_seed(previous_points, base, target))

    for bend in [14, -14, 26, -26, 40, -40, 60, -60, 85, -85, 120, -120]:
        add(make_seed_from_curve(base, lengths, target, bend))

    return seeds


def fabrik(points, target, lengths, iterations):
    if not lengths:
        return points

    pts = [p.copy() for p in points]
    base = pts[0].copy()
    total_length = sum(lengths)

    if base.distance_to(target) >= total_length:
        direction = safe_dir(target - base)
        pts[0] = base.copy()

        for i, length in enumerate(lengths):
            pts[i + 1] = pts[i] + direction * length

        return pts

    for _ in range(iterations):
        pts[-1] = target.copy()

        for i in reversed(range(len(lengths))):
            direction = safe_dir(pts[i] - pts[i + 1])
            pts[i] = pts[i + 1] + direction * lengths[i]

        pts[0] = base.copy()

        for i, length in enumerate(lengths):
            direction = safe_dir(pts[i + 1] - pts[i])
            pts[i + 1] = pts[i] + direction * length

    return pts


def solve_end_ik_constrained(current_points, target, lengths, iterations, preferred_sides, previous_safe_points):
    seeds = make_ik_seeds(BASE, current_points, target, lengths, previous_safe_points)

    best_safe = None
    best_safe_cost = float("inf")
    best_bad_data = ([], [])
    best_bad_cost = float("inf")

    for seed in seeds:
        candidate = fabrik(seed, target, lengths, iterations)
        safe, segment_pairs, bend_violations = evaluate_pose(candidate, preferred_sides, True)

        end_error = candidate[-1].distance_to(target)
        movement = 0

        if previous_safe_points is not None and len(previous_safe_points) == len(candidate):
            movement = sum(a.distance_to(b) for a, b in zip(candidate, previous_safe_points))

        cost = end_error + movement * 0.025

        if safe and cost < best_safe_cost:
            best_safe = candidate
            best_safe_cost = cost

        if not safe and cost < best_bad_cost:
            best_bad_data = (segment_pairs, bend_violations)
            best_bad_cost = cost

    if best_safe is not None:
        return best_safe, points_to_angles(best_safe), False, [], []

    return None, None, True, best_bad_data[0], best_bad_data[1]


def solve_joint_ik_constrained(current_points, target, lengths, angles, selected_joint, iterations, preferred_sides, previous_safe_points):
    sub_lengths = lengths[:selected_joint]
    current_sub = current_points[: selected_joint + 1]

    previous_sub = None
    if previous_safe_points is not None and len(previous_safe_points) >= selected_joint + 1:
        previous_sub = previous_safe_points[: selected_joint + 1]

    seeds = make_ik_seeds(BASE, current_sub, target, sub_lengths, previous_sub)

    best_safe = None
    best_safe_angles = None
    best_safe_cost = float("inf")
    best_bad_data = ([], [])
    best_bad_cost = float("inf")

    for seed in seeds:
        solved_sub = fabrik(seed, target, sub_lengths, iterations)
        solved_sub_angles = points_to_angles(solved_sub)

        candidate_angles = angles.copy()

        for i, value in enumerate(solved_sub_angles):
            candidate_angles[i] = value

        candidate = forward_kinematics(BASE, lengths, candidate_angles)
        safe, segment_pairs, bend_violations = evaluate_pose(candidate, preferred_sides, True)

        joint_error = candidate[selected_joint].distance_to(target)
        movement = 0

        if previous_safe_points is not None and len(previous_safe_points) == len(candidate):
            movement = sum(a.distance_to(b) for a, b in zip(candidate, previous_safe_points))

        cost = joint_error + movement * 0.025

        if safe and cost < best_safe_cost:
            best_safe = candidate
            best_safe_angles = candidate_angles
            best_safe_cost = cost

        if not safe and cost < best_bad_cost:
            best_bad_data = (segment_pairs, bend_violations)
            best_bad_cost = cost

    if best_safe is not None:
        return best_safe, best_safe_angles, False, [], []

    return None, None, True, best_bad_data[0], best_bad_data[1]


def random_world_target(radius):
    r = random.uniform(80, radius * 0.9)
    a = random.uniform(math.radians(200), math.radians(340))
    return pygame.Vector2(math.cos(a) * r, -math.sin(a) * r)


def draw_grid():
    for x in range(PANEL_W, WIDTH, 40):
        pygame.draw.line(screen, GRID, (x, 0), (x, HEIGHT), 1)

    for y in range(0, HEIGHT, 40):
        pygame.draw.line(screen, GRID, (PANEL_W, y), (WIDTH, y), 1)

    pygame.draw.line(screen, (55, 71, 105), (PANEL_W, BASE.y), (WIDTH, BASE.y), 2)
    pygame.draw.line(screen, (55, 71, 105), (BASE.x, 0), (BASE.x, HEIGHT), 2)

    draw_text(screen, "x", WIDTH - 25, BASE.y + 8, MUTED, small_font)
    draw_text(screen, "y", BASE.x + 8, 12, MUTED, small_font)


def draw_reach_circle(radius, color):
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*color, 28), BASE, int(radius), 2)
    screen.blit(surf, (0, 0))


def draw_target_marker(pos, color, label):
    p = world_to_screen(pos)

    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    pygame.draw.circle(surf, (*color, 38), p, 42)
    screen.blit(surf, (0, 0))

    pygame.draw.circle(screen, color, p, 13, 2)
    pygame.draw.line(screen, color, (p.x - 18, p.y), (p.x + 18, p.y), 2)
    pygame.draw.line(screen, color, (p.x, p.y - 18), (p.x, p.y + 18), 2)

    draw_text(screen, label, p.x + 18, p.y - 28, color, small_font)


def draw_constraint_debug(points, bend_violations):
    for joint_index in bend_violations:
        if 0 <= joint_index < len(points):
            p = points[joint_index]

            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*WARN, 90), p, 34)
            screen.blit(surf, (0, 0))

            pygame.draw.circle(screen, WARN, p, 23, 3)


def draw_arm(points, selected_joint):
    pygame.draw.circle(screen, (31, 40, 61), BASE, 42)
    pygame.draw.circle(screen, (12, 18, 31), BASE, 32)
    pygame.draw.circle(screen, ARM, BASE, 7)

    for a, b in zip(points[:-1], points[1:]):
        for width, alpha in [(17, 26), (11, 45)]:
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(surf, (*ARM, alpha), a, b, width)
            screen.blit(surf, (0, 0))

        pygame.draw.line(screen, ARM, a, b, 5)

    for i, p in enumerate(points):
        is_selected = i == selected_joint
        color = TARGET_2 if is_selected else JOINT
        radius = 17 if is_selected else 14

        pygame.draw.circle(screen, (11, 15, 24), p, radius + 6)
        pygame.draw.circle(screen, color, p, radius)
        pygame.draw.circle(screen, (255, 255, 255), p, 4)

        label = "B" if i == 0 else f"J{i}"
        draw_text(screen, label, p.x + 12, p.y + 8, TEXT, small_font)

    end = points[-1]
    prev = points[-2]
    direction = safe_dir(end - prev)
    normal = pygame.Vector2(-direction.y, direction.x)

    claw_a = end + normal * 18 + direction * 16
    claw_b = end - normal * 18 + direction * 16

    pygame.draw.line(screen, TARGET, end, claw_a, 4)
    pygame.draw.line(screen, TARGET, end, claw_b, 4)


def draw_panel(mode, reachable, selected_joint, end_world, selected_world, total_reach, constraint_blocked):
    pygame.draw.rect(screen, PANEL, (0, 0, PANEL_W, HEIGHT))
    pygame.draw.line(screen, (55, 66, 90), (PANEL_W, 0), (PANEL_W, HEIGHT), 2)

    draw_text(screen, "Robot Kinematics Lab", 20, 18, TEXT, big_font)
    draw_text(screen, "IK/FK + no-crossing constraints", 20, 48, MUTED, small_font)

    btn_end.draw(screen, mode == MODE_END_IK)
    btn_joint.draw(screen, mode == MODE_JOINT_IK)
    btn_fk.draw(screen, mode == MODE_FK)
    btn_reset.draw(screen, False)
    btn_random.draw(screen, False)

    for slider in sliders:
        slider.draw(screen)

    y = 575
    status_color = GOOD if reachable or mode == MODE_FK else BAD
    constraint_color = BAD if constraint_blocked else GOOD
    constraint_text = "BLOCKED" if constraint_blocked else "SAFE"

    draw_text(screen, f"Mode: {mode}", 20, y, TEXT, small_font)
    draw_text(screen, f"Reach: {'OK' if reachable or mode == MODE_FK else 'UNREACHABLE'}", 20, y + 22, status_color, small_font)
    draw_text(screen, f"No-crossing guard: {constraint_text}", 20, y + 44, constraint_color, small_font)
    draw_text(screen, f"Max reach: {total_reach:.1f}px", 20, y + 66, MUTED, small_font)
    draw_text(screen, f"End effector: x={end_world.x:.1f}, y={end_world.y:.1f}", 20, y + 94, TEXT, small_font)
    draw_text(screen, f"Selected J{selected_joint}: x={selected_world.x:.1f}, y={selected_world.y:.1f}", 20, y + 116, TEXT, small_font)

    tips = [
        "Mouse: move active target",
        "I/J/F: end IK / joint IK / FK",
        "TAB: next joint    A/D: angle",
        "W/S: length        [ ]: joint count",
        "C: recalibrate bend side",
        "Right click: clear pinned help",
    ]

    for i, line in enumerate(tips):
        draw_text(screen, line, 20, 680 + i * 16, MUTED, small_font)

    draw_slider_tooltips(screen, sliders)


def select_nearest_joint(points, mouse_pos):
    best_i = 1
    best_d = float("inf")
    mouse = pygame.Vector2(mouse_pos)

    for i, p in enumerate(points[1:], start=1):
        d = p.distance_to(mouse)

        if d < best_d:
            best_i = i
            best_d = d

    return best_i


joint_count = 4
lengths = [135, 115, 95, 75]
angles = [-90, 28, -38, 22]

selected_joint = 1
mode = MODE_END_IK
iterations = 16
motion_alpha = 0.38

target_world = pygame.Vector2(190, 250)
joint_target_world = pygame.Vector2(80, 270)

model_points = forward_kinematics(BASE, lengths, angles)
display_points = [p.copy() for p in model_points]

last_safe_points = [p.copy() for p in model_points]
last_safe_angles = angles.copy()
preferred_sides = get_bend_sides(model_points)

constraint_blocked = False
debug_bend_violations = []

drag_workspace = False

btn_end = Button(20, 86, 72, 34, "I: End")
btn_joint = Button(100, 86, 86, 34, "J: Joint")
btn_fk = Button(194, 86, 62, 34, "F: FK")
btn_reset = Button(264, 86, 62, 34, "Reset")
btn_random = Button(20, 130, 306, 32, "SPACE: Random reachable target")

count_slider = Slider(
    20,
    205,
    306,
    "Joint count",
    1,
    MAX_JOINTS,
    joint_count,
    True,
    "Broj aktivnih segmenata/zglobova robotske ruke. Veci broj daje fleksibilniju ruku, ali i kompleksnije IK ponasanje.",
)

selected_slider = Slider(
    20,
    255,
    306,
    "Selected joint",
    1,
    joint_count,
    selected_joint,
    True,
    "Odabire zglob koji trenutno uredujes. Koristi se za promjenu duljine pripadnog segmenta, kuta i za JOINT IK target.",
)

length_slider = Slider(
    20,
    305,
    306,
    "Selected length",
    35,
    220,
    lengths[selected_joint - 1],
    True,
    "Duljina segmenta koji zavrsava u odabranom zglobu. Dulji segment povecava doseg ruke, ali mijenja geometriju cijelog sustava.",
)

angle_slider = Slider(
    20,
    355,
    306,
    "Selected angle",
    -180,
    180,
    angles[selected_joint - 1],
    False,
    "Relativni kut odabranog zgloba u FK modu. U IK modu solver ga izracunava, ali no-crossing constraint ne dopusta flip kroz prethodni clanak.",
)

target_x_slider = Slider(
    20,
    415,
    306,
    "Target X",
    -500,
    500,
    target_world.x,
    False,
    "X koordinata aktivnog targeta u koordinatnom sustavu ruke. Pozitivno je desno od baze, negativno lijevo.",
)

target_y_slider = Slider(
    20,
    465,
    306,
    "Target Y",
    -80,
    620,
    target_world.y,
    False,
    "Y koordinata aktivnog targeta u koordinatnom sustavu ruke. Pozitivno je prema gore od baze.",
)

iter_slider = Slider(
    20,
    525,
    145,
    "IK iterations",
    1,
    45,
    iterations,
    True,
    "Broj FABRIK iteracija po frameu. Vise iteracija daje preciznije pracenje targeta, ali trosi vise racunanja.",
)

speed_slider = Slider(
    181,
    525,
    145,
    "Motion speed",
    0.05,
    1.0,
    motion_alpha,
    False,
    "Brzina vizualnog priblizavanja modela novoj poziciji. Manje vrijednosti daju mekse kretanje, vece daju brzi odziv.",
)

sliders = [
    count_slider,
    selected_slider,
    length_slider,
    angle_slider,
    target_x_slider,
    target_y_slider,
    iter_slider,
    speed_slider,
]


def accept_pose(points, new_angles, update_bend_preferences=True):
    global model_points, angles, last_safe_points, last_safe_angles
    global preferred_sides, constraint_blocked, debug_bend_violations

    model_points = [p.copy() for p in points]
    angles = [normalize_angle(a) for a in new_angles]

    last_safe_points = [p.copy() for p in model_points]
    last_safe_angles = angles.copy()

    if update_bend_preferences:
        preferred_sides = update_preferred_sides(model_points, preferred_sides)

    constraint_blocked = False
    debug_bend_violations = []


def reject_pose(bend_violations=None):
    global model_points, angles, constraint_blocked, debug_bend_violations

    model_points = [p.copy() for p in last_safe_points]
    angles = last_safe_angles.copy()
    constraint_blocked = True
    debug_bend_violations = bend_violations or []


def set_joint_count(value):
    global joint_count, selected_joint, lengths, angles, model_points, display_points
    global last_safe_points, last_safe_angles, preferred_sides

    value = int(clamp(value, 1, MAX_JOINTS))
    old_count = joint_count
    joint_count = value

    while len(lengths) < joint_count:
        lengths.append(90)
        angles.append(0)

    lengths = lengths[:joint_count]
    angles = angles[:joint_count]

    selected_joint = int(clamp(selected_joint, 1, joint_count))

    selected_slider.max_value = joint_count
    selected_slider.set(selected_joint)
    length_slider.set(lengths[selected_joint - 1])
    angle_slider.set(angles[selected_joint - 1])

    if old_count != joint_count:
        model_points = forward_kinematics(BASE, lengths, angles)
        display_points = [p.copy() for p in model_points]
        last_safe_points = [p.copy() for p in model_points]
        last_safe_angles = angles.copy()
        preferred_sides = get_bend_sides(model_points)


def set_selected_joint(value):
    global selected_joint

    selected_joint = int(clamp(value, 1, joint_count))
    selected_slider.set(selected_joint)
    length_slider.set(lengths[selected_joint - 1])
    angle_slider.set(angles[selected_joint - 1])


def active_target():
    return joint_target_world if mode == MODE_JOINT_IK else target_world


def set_active_target(value):
    global target_world, joint_target_world

    value = pygame.Vector2(value)
    value.x = clamp(value.x, target_x_slider.min_value, target_x_slider.max_value)
    value.y = clamp(value.y, target_y_slider.min_value, target_y_slider.max_value)

    if mode == MODE_JOINT_IK:
        joint_target_world = value
    else:
        target_world = value

    target_x_slider.set(value.x)
    target_y_slider.set(value.y)


def sync_target_sliders():
    target = active_target()
    target_x_slider.set(target.x)
    target_y_slider.set(target.y)


running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if btn_end.handle_event(event):
            mode = MODE_END_IK
            sync_target_sliders()

        if btn_joint.handle_event(event):
            mode = MODE_JOINT_IK
            sync_target_sliders()

        if btn_fk.handle_event(event):
            mode = MODE_FK
            sync_target_sliders()

        if btn_reset.handle_event(event):
            joint_count = 4
            lengths = [135, 115, 95, 75]
            angles = [-90, 28, -38, 22]
            selected_joint = 1
            mode = MODE_END_IK
            model_points = forward_kinematics(BASE, lengths, angles)
            display_points = [p.copy() for p in model_points]

            last_safe_points = [p.copy() for p in model_points]
            last_safe_angles = angles.copy()
            preferred_sides = get_bend_sides(model_points)

            count_slider.set(joint_count)
            set_joint_count(joint_count)
            set_selected_joint(selected_joint)
            set_active_target(pygame.Vector2(190, 250))

            constraint_blocked = False
            debug_bend_violations = []

        if btn_random.handle_event(event):
            set_active_target(random_world_target(sum(lengths)))

        for slider in sliders:
            result = slider.handle_event(event)

            if result == "info":
                for other in sliders:
                    if other is not slider:
                        other.pinned_info = False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            for slider in sliders:
                slider.pinned_info = False

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_ESCAPE, pygame.K_q):
                running = False

            elif event.key == pygame.K_i:
                mode = MODE_END_IK
                sync_target_sliders()

            elif event.key == pygame.K_j:
                mode = MODE_JOINT_IK
                sync_target_sliders()

            elif event.key == pygame.K_f:
                mode = MODE_FK
                sync_target_sliders()

            elif event.key == pygame.K_c:
                preferred_sides = get_bend_sides(model_points)
                last_safe_points = [p.copy() for p in model_points]
                last_safe_angles = angles.copy()
                constraint_blocked = False
                debug_bend_violations = []

            elif event.key == pygame.K_TAB:
                set_selected_joint((selected_joint % joint_count) + 1)

            elif event.key == pygame.K_RIGHTBRACKET:
                count_slider.set(joint_count + 1)

            elif event.key == pygame.K_LEFTBRACKET:
                count_slider.set(joint_count - 1)

            elif event.key == pygame.K_a:
                angles[selected_joint - 1] = normalize_angle(angles[selected_joint - 1] - 3)
                angle_slider.set(angles[selected_joint - 1])

            elif event.key == pygame.K_d:
                angles[selected_joint - 1] = normalize_angle(angles[selected_joint - 1] + 3)
                angle_slider.set(angles[selected_joint - 1])

            elif event.key == pygame.K_w:
                lengths[selected_joint - 1] = clamp(lengths[selected_joint - 1] + 5, 35, 220)
                length_slider.set(lengths[selected_joint - 1])

            elif event.key == pygame.K_s:
                lengths[selected_joint - 1] = clamp(lengths[selected_joint - 1] - 5, 35, 220)
                length_slider.set(lengths[selected_joint - 1])

            elif event.key == pygame.K_SPACE:
                set_active_target(random_world_target(sum(lengths)))

            elif event.key == pygame.K_r:
                angles = [-90] + [0] * (joint_count - 1)
                set_selected_joint(selected_joint)

            elif event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_LEFT, pygame.K_RIGHT):
                delta = pygame.Vector2(0, 0)
                step = 10

                if event.key == pygame.K_UP:
                    delta.y += step

                if event.key == pygame.K_DOWN:
                    delta.y -= step

                if event.key == pygame.K_LEFT:
                    delta.x -= step

                if event.key == pygame.K_RIGHT:
                    delta.x += step

                set_active_target(active_target() + delta)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[0] > PANEL_W:
            if mode in (MODE_END_IK, MODE_JOINT_IK):
                set_active_target(screen_to_world(event.pos))
                drag_workspace = True
            else:
                set_selected_joint(select_nearest_joint(model_points, event.pos))

        if event.type == pygame.MOUSEMOTION and drag_workspace:
            set_active_target(screen_to_world(event.pos))

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            drag_workspace = False

    old_selected = selected_joint

    if int(count_slider.value) != joint_count:
        set_joint_count(count_slider.value)

    if int(selected_slider.value) != selected_joint:
        set_selected_joint(selected_slider.value)

    if old_selected == selected_joint:
        lengths[selected_joint - 1] = length_slider.value

        if mode == MODE_FK:
            angles[selected_joint - 1] = normalize_angle(angle_slider.value)

    iterations = int(iter_slider.value)
    motion_alpha = speed_slider.value

    if mode in (MODE_END_IK, MODE_JOINT_IK):
        set_active_target(pygame.Vector2(target_x_slider.value, target_y_slider.value))

    if not target_x_slider.dragging and not target_y_slider.dragging:
        sync_target_sliders()

    if mode == MODE_FK:
        candidate_points = forward_kinematics(BASE, lengths, angles)
        safe, _, bend_violations = evaluate_pose(candidate_points, preferred_sides, True)

        if safe:
            accept_pose(candidate_points, angles, True)
        else:
            reject_pose(bend_violations)

        reachable = True

    elif mode == MODE_END_IK:
        target_screen = world_to_screen(target_world)
        start_points = model_points if len(model_points) == joint_count + 1 else forward_kinematics(BASE, lengths, angles)

        solved_points, solved_angles, blocked, _, bend_violations = solve_end_ik_constrained(
            start_points,
            target_screen,
            lengths,
            iterations,
            preferred_sides,
            last_safe_points,
        )

        reachable = BASE.distance_to(target_screen) <= sum(lengths)

        if blocked:
            reject_pose(bend_violations)
        else:
            accept_pose(solved_points, solved_angles, True)

        if not angle_slider.dragging:
            angle_slider.set(angles[selected_joint - 1])

    else:
        target_screen = world_to_screen(joint_target_world)

        solved_points, solved_angles, blocked, _, bend_violations = solve_joint_ik_constrained(
            model_points,
            target_screen,
            lengths,
            angles,
            selected_joint,
            iterations,
            preferred_sides,
            last_safe_points,
        )

        reachable = BASE.distance_to(target_screen) <= sum(lengths[:selected_joint])

        if blocked:
            reject_pose(bend_violations)
        else:
            accept_pose(solved_points, solved_angles, True)

        if not angle_slider.dragging:
            angle_slider.set(angles[selected_joint - 1])

    if len(display_points) != len(model_points):
        display_points = [p.copy() for p in model_points]
    else:
        display_points = [a.lerp(b, motion_alpha) for a, b in zip(display_points, model_points)]

    count_slider.set(joint_count)
    selected_slider.max_value = joint_count
    selected_slider.set(selected_joint)

    if not length_slider.dragging:
        length_slider.set(lengths[selected_joint - 1])

    target_x_slider.label = "End target X" if mode != MODE_JOINT_IK else f"J{selected_joint} target X"
    target_y_slider.label = "End target Y" if mode != MODE_JOINT_IK else f"J{selected_joint} target Y"

    end_world = screen_to_world(model_points[-1])
    selected_world = screen_to_world(model_points[selected_joint])
    total_reach = sum(lengths) if mode != MODE_JOINT_IK else sum(lengths[:selected_joint])

    screen.fill(BG)
    draw_grid()
    draw_reach_circle(total_reach, TARGET_2 if mode == MODE_JOINT_IK else ARM)

    if mode == MODE_END_IK:
        draw_target_marker(target_world, TARGET, "end target")

    elif mode == MODE_JOINT_IK:
        draw_target_marker(joint_target_world, TARGET_2, f"J{selected_joint} target")

    draw_arm(display_points, selected_joint)

    if constraint_blocked:
        draw_constraint_debug(display_points, debug_bend_violations)

    draw_panel(
        mode,
        reachable,
        selected_joint,
        end_world,
        selected_world,
        total_reach,
        constraint_blocked,
    )

    pygame.display.flip()

pygame.quit()
