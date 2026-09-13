from pathlib import Path

import pygame

from entities import ATTACKS, ENEMY_COIN_REWARDS, Bee, Cricket, FireAnt, Hornet, MerchantFly, MothSwarm, QueenBee, ShrineLight
from level import Level
from level_data import LEVELS
from lighting import LightingEngine
from player import Player
from settings import BACKGROUND_COLOR, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TEXT_COLOR, WINDOW_TITLE


FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "VCR_OSD_MONO_1.001.ttf"
MERCHANT_PRICES = {"lantern": 2, "extra_life": 6, "tier_2": 4, "tier_3": 7, "tier_4": 12}


def merchant_buttons() -> dict[str, pygame.Rect]:
    return {
        "lantern": pygame.Rect(625, 310, 280, 38),
        "tier_2": pygame.Rect(625, 354, 280, 38),
        "tier_3": pygame.Rect(625, 398, 280, 38),
        "tier_4": pygame.Rect(625, 442, 280, 38),
        "extra_life": pygame.Rect(625, 486, 280, 38),
    }


def merchant_panel() -> pygame.Rect:
    return pygame.Rect(605, 258, 320, 286)


def draw_merchant(screen: pygame.Surface, font: pygame.font.Font, player: Player, moths: MothSwarm) -> None:
    panel = merchant_panel()
    pygame.draw.rect(screen, (20, 18, 29), panel, border_radius=8)
    pygame.draw.rect(screen, (184, 145, 72), panel, 2, border_radius=8)
    screen.blit(font.render(f"MERCHANT   COINS: {player.coins}", True, (245, 211, 128)), (panel.x + 18, panel.y + 16))
    labels = {
        "lantern": "LANTERN                 2",
        "tier_2": "UNLOCK SWARM BURST     4",
        "tier_3": "UNLOCK SOLAR SWARM     7",
        "tier_4": "UNLOCK ECLIPSE         12",
        "extra_life": "EXTRA LIFE              6",
    }
    for key, rect in merchant_buttons().items():
        tier = int(key[-1]) if key.startswith("tier_") else 0
        owned = tier and moths.unlocked_tier >= tier
        life_full = key == "extra_life" and player.lives >= 3
        available = (not tier or tier == moths.unlocked_tier + 1) and not life_full
        fill = (45, 40, 53) if available and not owned else (29, 27, 36)
        text_color = (235, 232, 219) if available and not owned else (105, 101, 115)
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        pygame.draw.rect(screen, (91, 86, 108), rect, 1, border_radius=5)
        label = "LIVES FULL" if life_full else "OWNED" if owned else labels[key]
        screen.blit(font.render(label, True, text_color), (rect.x + 12, rect.y + 10))


class Camera:
    def __init__(self) -> None:
        self.offset = pygame.Vector2()

    def update(self, dt: float, player: Player, move_direction: int) -> None:
        # A gentle look-ahead and vertical response makes movement readable
        # without pulling the player away from the centre of the action.
        target = pygame.Vector2(-move_direction * 24, max(-14, min(14, -player.velocity.y * 0.018)))
        self.offset += (target - self.offset) * min(1.0, dt * 7.0)

    def world_to_screen(self, position: tuple[int, int]) -> tuple[int, int]:
        return round(position[0] + self.offset.x), round(position[1] + self.offset.y)

    def screen_to_world(self, position: tuple[int, int]) -> tuple[int, int]:
        return round(position[0] - self.offset.x), round(position[1] - self.offset.y)


def find_bee_platform(level: Level, bee_position: tuple[int, int]) -> pygame.Rect:
    platforms = level.platform_rects
    return min(platforms, key=lambda rect: abs(rect.centerx - bee_position[0]) + abs(rect.top - bee_position[1]))


def find_platform_section(level: Level, position: tuple[int, int]) -> pygame.Rect:
    anchor = find_bee_platform(level, position)
    row = sorted(
        (rect for rect in level.platform_rects if rect.y == anchor.y),
        key=lambda rect: rect.x,
    )
    section = anchor.copy()
    expanded = True
    while expanded:
        expanded = False
        for tile in row:
            if tile.right == section.left or tile.left == section.right:
                section.union_ip(tile)
                expanded = True
    return section


def create_bees(level: Level) -> list[Bee]:
    bees: list[Bee] = [
        Bee(position, find_bee_platform(level, position), chases_player)
        for position, chases_player in level.bee_spawns
    ]
    bees.extend(
        QueenBee(position, find_bee_platform(level, position))
        for position in level.queen_spawns
    )
    bees.extend(
        Cricket(position, find_platform_section(level, position))
        for position in level.cricket_spawns
    )
    bees.extend(
        FireAnt(position, find_platform_section(level, position))
        for position in level.fire_ant_spawns
    )
    bees.extend(
        Hornet(position, find_platform_section(level, position))
        for position in level.hornet_spawns
    )
    return bees


def spawn_hornet_wave(level: Level, wave: int, now: int) -> list[Bee]:
    if wave == 0:
        positions = ((220, 220), (480, 255), (740, 220))
        enemies = [Bee(position, find_bee_platform(level, position), True) for position in positions]
    elif wave == 1:
        positions = ((165, 235), (745, 235))
        enemies = [Cricket(position, find_platform_section(level, position)) for position in positions]
        for cricket in enemies:
            cricket.activate_lantern()
    else:
        positions = ((300, 330), (660, 330))
        enemies = [FireAnt(position, find_platform_section(level, position)) for position in positions]
        for fire_ant in enemies:
            fire_ant.drops_fire = False
    for enemy in enemies:
        enemy.next_attack_at = now + 900
    return enemies


def restart_button() -> pygame.Rect:
    return pygame.Rect(SCREEN_WIDTH // 2 - 105, SCREEN_HEIGHT // 2 + 58, 210, 52)


def draw_win_screen(screen: pygame.Surface, font: pygame.font.Font, alert_font: pygame.font.Font) -> None:
    veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    veil.fill((5, 4, 10, 225))
    screen.blit(veil, (0, 0))
    title = alert_font.render("YOU WIN!", True, (250, 201, 62))
    screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 45)))
    subtitle = font.render("THE HORNET HAS FALLEN", True, TEXT_COLOR)
    screen.blit(subtitle, subtitle.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 5)))
    button = restart_button()
    pygame.draw.rect(screen, (38, 34, 48), button, border_radius=7)
    pygame.draw.rect(screen, (250, 201, 62), button, 2, border_radius=7)
    label = font.render("RESTART", True, TEXT_COLOR)
    screen.blit(label, label.get_rect(center=button.center))


def draw_ui(screen: pygame.Surface, font: pygame.font.Font, alert_font: pygame.font.Font, player: Player, moths: MothSwarm, shrine_lights: int, bees: list[Bee], level_index: int, level_title_until: int, now: int, message: str) -> None:
    panel_color = (20, 18, 29)
    border_color = (91, 86, 108)
    muted_color = (153, 148, 166)
    accent_color = (246, 196, 65)

    boss = next((bee for bee in bees if bee.is_boss and bee.alive), None)
    if boss is not None:
        player_panel = pygame.Rect(14, 14, 270, 54)
        pygame.draw.rect(screen, panel_color, player_panel, border_radius=7)
        pygame.draw.rect(screen, border_color, player_panel, 2, border_radius=7)
        screen.blit(font.render("HP", True, TEXT_COLOR), (player_panel.x + 12, player_panel.y + 9))
        player_bar = pygame.Rect(player_panel.x + 50, player_panel.y + 12, 204, 14)
        pygame.draw.rect(screen, (54, 45, 58), player_bar, border_radius=4)
        player_fill = player_bar.copy()
        player_fill.width = round(player_bar.width * max(0, player.health) / 100)
        pygame.draw.rect(screen, (197, 69, 83), player_fill, border_radius=4)
        hp_label = font.render(str(player.health), True, TEXT_COLOR)
        screen.blit(hp_label, hp_label.get_rect(center=player_bar.center))
        lives_label = font.render(f"LIVES {player.lives}", True, TEXT_COLOR)
        screen.blit(lives_label, (player_panel.x + 12, player_panel.y + 33))

        boss_panel = pygame.Rect(300, 14, SCREEN_WIDTH - 314, 54)
        pygame.draw.rect(screen, panel_color, boss_panel, border_radius=7)
        pygame.draw.rect(screen, accent_color, boss_panel, 2, border_radius=7)
        title = font.render(boss.name, True, accent_color)
        screen.blit(title, (boss_panel.x + 14, boss_panel.y + 8))
        boss_hp = font.render(f"{boss.health}/{boss.max_health}", True, TEXT_COLOR)
        screen.blit(boss_hp, (boss_panel.right - boss_hp.get_width() - 14, boss_panel.y + 8))
        boss_bar = pygame.Rect(boss_panel.x + 14, boss_panel.y + 32, boss_panel.width - 28, 10)
        pygame.draw.rect(screen, (54, 45, 58), boss_bar, border_radius=4)
        boss_fill = boss_bar.copy()
        boss_fill.width = round(boss_bar.width * boss.health / boss.max_health)
        pygame.draw.rect(screen, (190, 66, 126), boss_fill, border_radius=4)

        attack_panel = pygame.Rect(245, 78, 470, 38)
        pygame.draw.rect(screen, panel_color, attack_panel, border_radius=6)
        pygame.draw.rect(screen, border_color, attack_panel, 2, border_radius=6)
        attack_names = {1: "DART", 2: "BURST", 3: "SOLAR", 4: "ECLIPSE"}
        boss_attack_text = "  ".join(
            f"[{tier}]{attack_names[tier]}"
            for tier in ATTACKS
            if tier <= moths.unlocked_tier
        )
        attack_label = font.render(boss_attack_text, True, muted_color)
        screen.blit(attack_label, attack_label.get_rect(center=attack_panel.center))

        if not player.moths_available(now):
            remaining = (player.moth_stunned_until - now) / 1000
            status = alert_font.render(f"PARALYZED  {remaining:.1f}s", True, accent_color)
            screen.blit(status, status.get_rect(midtop=(SCREEN_WIDTH // 2, 126)))

        notice = message or boss.last_attack
        if notice:
            screen.blit(alert_font.render(notice, True, TEXT_COLOR), (16, SCREEN_HEIGHT - 42))

        if now < level_title_until:
            level_title = alert_font.render(f"LEVEL {level_index + 1}", True, TEXT_COLOR)
            title_back = level_title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90)).inflate(30, 18)
            pygame.draw.rect(screen, (12, 10, 18), title_back, border_radius=7)
            pygame.draw.rect(screen, border_color, title_back, 2, border_radius=7)
            screen.blit(level_title, level_title.get_rect(center=title_back.center))
        return

    status_panel = pygame.Rect(14, 14, 430, 78)
    pygame.draw.rect(screen, panel_color, status_panel, border_radius=7)
    pygame.draw.rect(screen, border_color, status_panel, 2, border_radius=7)
    screen.blit(font.render("HP", True, TEXT_COLOR), (26, 24))
    health_back = pygame.Rect(72, 27, 252, 12)
    pygame.draw.rect(screen, (54, 45, 58), health_back, border_radius=4)
    health_fill = health_back.copy()
    health_fill.width = round(health_back.width * max(0, player.health) / 100)
    pygame.draw.rect(screen, (197, 69, 83), health_fill, border_radius=4)
    screen.blit(
        font.render(
            f"MOTHS {moths.available}/{moths.max_count}  COINS {player.coins}  LIGHTS {shrine_lights}  LIVES {player.lives}",
            True,
            TEXT_COLOR,
        ),
        (26, 55),
    )

    attack_panel = pygame.Rect(14, 100, 470, 38)
    pygame.draw.rect(screen, panel_color, attack_panel, border_radius=6)
    pygame.draw.rect(screen, border_color, attack_panel, 2, border_radius=6)
    short_names = {1: "DART", 2: "BURST", 3: "SOLAR", 4: "ECLIPSE"}
    attack_labels = [
        f"[{tier}] {short_names[tier]} {attack['damage']}"
        for tier, attack in ATTACKS.items()
        if tier <= moths.unlocked_tier
    ]
    screen.blit(font.render("   ".join(attack_labels), True, muted_color), (24, 111))

    level_chip = pygame.Rect(492, 100, 100, 38)
    pygame.draw.rect(screen, panel_color, level_chip, border_radius=6)
    pygame.draw.rect(screen, border_color, level_chip, 2, border_radius=6)
    level_label = font.render(f"LEVEL {level_index + 1}", True, accent_color)
    screen.blit(level_label, level_label.get_rect(center=level_chip.center))

    if not player.moths_available(now):
        remaining = (player.moth_stunned_until - now) / 1000
        status = f"PARALYZED  {remaining:.1f}s"
        screen.blit(alert_font.render(status, True, accent_color), (16, 148))

    selected_bee = next((bee for bee in bees if bee.selected and bee.alive), None)
    if selected_bee is not None:
        bee = selected_bee
        panel_height = 142 if bee.is_boss or bee.is_cricket else 116
        panel = pygame.Rect(SCREEN_WIDTH - 300, 14, 286, panel_height)
        pygame.draw.rect(screen, panel_color, panel, border_radius=7)
        pygame.draw.rect(screen, accent_color, panel, 2, border_radius=7)
        screen.blit(font.render(bee.name, True, accent_color), (panel.x + 14, panel.y + 10))
        hp_text = font.render(f"{bee.health}/{bee.max_health}", True, TEXT_COLOR)
        screen.blit(hp_text, (panel.right - hp_text.get_width() - 14, panel.y + 10))
        health_back = pygame.Rect(panel.x + 14, panel.y + 39, panel.width - 28, 10)
        pygame.draw.rect(screen, (54, 45, 58), health_back, border_radius=4)
        health_fill = health_back.copy()
        health_fill.width = round(health_back.width * bee.health / bee.max_health)
        pygame.draw.rect(screen, (226, 170, 47), health_fill, border_radius=4)
        if bee.is_hornet:
            screen.blit(font.render("NEEDLE VOLLEY  -12 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("HORNET DIVE  -8 HP", True, muted_color), (panel.x + 14, panel.y + 87))
            screen.blit(font.render("CLEAR WAVES TO ATTACK", True, muted_color), (panel.x + 14, panel.y + 113))
        elif bee.is_boss:
            screen.blit(font.render("ROYAL BLAST  -10 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("WING GUST  -6 HP", True, muted_color), (panel.x + 14, panel.y + 87))
            screen.blit(font.render("QUEEN SHOCK  PARALYSIS", True, muted_color), (panel.x + 14, panel.y + 113))
        elif bee.is_cricket:
            screen.blit(font.render("SONIC CHIRP  -10 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("LANTERN BREAKS SHIELD", True, muted_color), (panel.x + 14, panel.y + 87))
            screen.blit(font.render("LANTERN: ANY PLATFORM SPOT", True, muted_color), (panel.x + 14, panel.y + 113))
        elif bee.is_fire_ant:
            screen.blit(font.render("FIRE ATTACK  -15 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("LEAVES BURNING GROUND", True, muted_color), (panel.x + 14, panel.y + 87))
        else:
            screen.blit(font.render("STING  -1/-2 MOTHS", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("PARALYSIS  25% FAIL", True, muted_color), (panel.x + 14, panel.y + 87))

    notice = message or next((bee.last_attack for bee in bees if bee.last_attack), "")
    if notice:
        screen.blit(alert_font.render(notice, True, TEXT_COLOR), (16, SCREEN_HEIGHT - 42))

    if now < level_title_until:
        title = alert_font.render(f"LEVEL {level_index + 1}", True, TEXT_COLOR)
        title_back = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 90)).inflate(30, 18)
        pygame.draw.rect(screen, (12, 10, 18), title_back, border_radius=7)
        pygame.draw.rect(screen, border_color, title_back, 2, border_radius=7)
        screen.blit(title, title.get_rect(center=title_back.center))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()


    # current level index variable so just search this comment to find it
    level_index = 8
    checkpoint_index = 0
    level = Level(LEVELS[level_index], use_green_terrain=level_index >= 4)
    player = Player(level.player_spawn)
    moths = MothSwarm()
    bees = create_bees(level)
    lighting = LightingEngine((SCREEN_WIDTH, SCREEN_HEIGHT))
    camera = Camera()
    scene = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    shrine_objects: list[ShrineLight] = []
    merchant: MerchantFly | None = None
    merchant_spawned = False
    merchant_visited = False
    moth_restore_started_at: int | None = None
    moth_restore_used = False
    final_merchant_rewarded = False
    hornet_phase = "intro" if level_index == 9 else ""
    hornet_wave = 0
    hornet_intro_started = pygame.time.get_ticks()
    hornet_intro_until = hornet_intro_started + 3600 if hornet_phase else 0
    game_won = False
    shrine_lights = 5
    message = ""
    message_until = 0
    font = pygame.font.Font(str(FONT_PATH), 16)
    alert_font = pygame.font.Font(str(FONT_PATH), 30)
    fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    fade_duration = 500
    transition_phase: str | None = None
    transition_started = 0
    # Level 1 starts quietly; later areas still receive a transition title.
    level_title_until = 0
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)
        now = pygame.time.get_ticks()
        jump_requested = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and game_won:
                if event.button == 1 and restart_button().collidepoint(event.pos):
                    level_index = 0
                    checkpoint_index = 0
                    level = Level(LEVELS[level_index], use_green_terrain=False)
                    player = Player(level.player_spawn)
                    moths = MothSwarm()
                    bees = create_bees(level)
                    shrine_objects.clear()
                    merchant = None
                    merchant_spawned = False
                    merchant_visited = False
                    moth_restore_started_at = None
                    moth_restore_used = False
                    final_merchant_rewarded = False
                    shrine_lights = 5
                    hornet_phase = ""
                    hornet_wave = 0
                    game_won = False
                    transition_phase = "in"
                    transition_started = now
                    level_title_until = 0
                    message = ""
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    jump_requested = True
                elif event.key == pygame.K_f and shrine_lights > 0:
                    if player.grounded:
                        crickets = [enemy for enemy in bees if isinstance(enemy, Cricket)]
                        if crickets:
                            platform_cricket = next(
                                (cricket for cricket in crickets if cricket.player_on_platform(player.rect)),
                                None,
                            )
                            if platform_cricket is None:
                                message = "DAMP FLOOR EXTINGUISHES LIGHT"
                                message_until = now + 1200
                            else:
                                shrine_objects.append(ShrineLight(player.rect.midbottom))
                                shrine_lights -= 1
                                if platform_cricket.alive:
                                    platform_cricket.activate_lantern()
                                moths.summon(player.rect.center, force=True)
                                message = "MOTHS ARRIVE!"
                                message_until = now + 1300
                        else:
                            shrine_objects.append(ShrineLight(player.rect.midbottom))
                            shrine_lights -= 1
                            moths.summon(player.rect.center)
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
                    tier = event.key - pygame.K_0
                    all_living_enemies = [bee for bee in bees if bee.alive]
                    living_bees = [
                        bee for bee in all_living_enemies
                        if not getattr(bee, "attack_locked", False)
                    ] or all_living_enemies
                    closest_bee = min(
                        living_bees,
                        key=lambda bee: bee.position.distance_to(player.rect.center),
                        default=None,
                    )
                    for bee in bees:
                        bee.selected = bee is closest_bee
                    message = moths.attack(tier, closest_bee, now, player.moths_paralyzed(now))
                    message_until = now + 1500
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handled = False
                if merchant is not None and merchant.open:
                    clicked_item = next(
                        (key for key, rect in merchant_buttons().items() if rect.collidepoint(event.pos)),
                        None,
                    )
                    if clicked_item == "lantern":
                        handled = True
                        if player.coins >= MERCHANT_PRICES["lantern"]:
                            player.coins -= MERCHANT_PRICES["lantern"]
                            shrine_lights += 1
                            message = "LANTERN +1"
                        else:
                            message = "NOT ENOUGH COINS"
                    elif clicked_item == "extra_life":
                        handled = True
                        if player.lives >= 3:
                            message = "LIVES FULL"
                        elif player.coins < MERCHANT_PRICES["extra_life"]:
                            message = "NOT ENOUGH COINS"
                        else:
                            player.coins -= MERCHANT_PRICES["extra_life"]
                            player.lives += 1
                            message = "EXTRA LIFE BOUGHT"
                    elif clicked_item and clicked_item.startswith("tier_"):
                        handled = True
                        tier = int(clicked_item[-1])
                        cost = MERCHANT_PRICES[clicked_item]
                        if moths.unlocked_tier >= tier:
                            message = "ALREADY OWNED"
                        elif tier != moths.unlocked_tier + 1:
                            message = "BUY PREVIOUS TIER"
                        elif player.coins < cost:
                            message = "NOT ENOUGH COINS"
                        else:
                            player.coins -= cost
                            moths.unlocked_tier = tier
                            message = f"TIER {tier} UNLOCKED"
                    if handled:
                        message_until = now + 1300
                    elif not merchant_panel().collidepoint(event.pos):
                        merchant.open = False
                        handled = True

                world_click = camera.screen_to_world(event.pos)
                if not handled and merchant is not None and merchant.handle_click(world_click):
                    handled = True
                    if level_index == 8 and not final_merchant_rewarded:
                        player.lives += 1
                        final_merchant_rewarded = True
                        message = "MERCHANT: CONGRATS ON MAKING IT THIS FAR! +1 LIFE"
                        message_until = now + 2800
                    merchant_visited = True
                if not handled:
                    clicked_bee = next(
                        (bee for bee in reversed(bees) if bee.alive and bee.rect.collidepoint(world_click)),
                        None,
                    )
                    for bee in bees:
                        bee.selected = bee is clicked_bee

        keys = pygame.key.get_pressed()
        move_direction = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        player.update(dt, move_direction, jump_requested, level.solids)
        camera.update(dt, player, move_direction)
        can_restore_moths = (
            level_index == 8
            and merchant is not None
            and merchant.arrived
            and not moth_restore_used
            and pygame.Vector2(player.rect.center).distance_to(merchant.position) < 125
        )
        if can_restore_moths and keys[pygame.K_p]:
            if moth_restore_started_at is None:
                moth_restore_started_at = now
            restore_progress = min(1.0, (now - moth_restore_started_at) / 1800)
            message = f"RESTORING MOTHS {round(restore_progress * 100)}%"
            message_until = now + 120
            if restore_progress >= 1.0:
                moths.restore_full(player.rect.center)
                moth_restore_used = True
                moth_restore_started_at = None
                message = "MOTHS RESTORED 32/32"
                message_until = now + 1800
        else:
            moth_restore_started_at = None
        moths.update(now)
        living_crickets = [enemy for enemy in bees if isinstance(enemy, Cricket) and enemy.alive]
        active_cricket = min(
            living_crickets,
            key=lambda cricket: cricket.position.distance_to(player.rect.center),
            default=None,
        )
        for cricket in living_crickets:
            cricket.attack_enabled = cricket is active_cricket
        for bee in bees:
            bee.update(now, player, moths, dt)
            if bee.defeated_by_player and not bee.coin_awarded:
                reward_name = "Hornet" if bee.is_hornet else "Queen Bee" if bee.is_boss else "Cricket" if bee.is_cricket else "Fire Ant" if bee.is_fire_ant else "Bee"
                reward = ENEMY_COIN_REWARDS[reward_name]
                player.coins += reward
                bee.coin_awarded = True
                message = f"{bee.name} DOWN! +{reward} COIN"
                message_until = now + 1500

        queens = [bee for bee in bees if isinstance(bee, QueenBee) and bee.alive]
        living_minions = sum(bee.alive and not bee.is_boss for bee in bees)
        for queen in queens:
            if queen.summons_pending:
                if living_minions < 2:
                    direction = -1 if living_minions % 2 == 0 else 1
                    spawn_position = (
                        round(queen.position.x + direction * 44),
                        round(queen.position.y + 18),
                    )
                    minion = Bee(
                        spawn_position,
                        find_bee_platform(level, spawn_position),
                        chases_player=True,
                    )
                    minion.next_attack_at = now + 1000
                    bees.append(minion)
                    living_minions += 1
                queen.summons_pending = 0

        hornet = next((enemy for enemy in bees if isinstance(enemy, Hornet)), None)
        if hornet is not None and not game_won:
            if hornet_phase == "intro" and now >= hornet_intro_until:
                bees.extend(spawn_hornet_wave(level, 0, now))
                hornet_phase = "wave"
                message = "WAVE 1 - BEES"
                message_until = now + 1800
            elif hornet_phase == "wave":
                wave_alive = any(enemy.alive and enemy is not hornet for enemy in bees)
                if not wave_alive:
                    health_floors = (480, 240, 0)
                    hornet.open_damage_phase(health_floors[hornet_wave])
                    hornet_phase = "damage"
                    message = "HORNET EXPOSED - ATTACK!"
                    message_until = now + 1800
            elif hornet_phase == "damage" and hornet.health <= hornet.health_floor:
                if hornet.health_floor == 0:
                    game_won = True
                    message = "YOU WIN!"
                else:
                    hornet.attack_locked = True
                    hornet_wave += 1
                    bees.extend(spawn_hornet_wave(level, hornet_wave, now))
                    hornet_phase = "wave"
                    wave_names = ("BEES", "CRICKETS", "FIRE ANTS")
                    message = f"WAVE {hornet_wave + 1} - {wave_names[hornet_wave]}"
                    message_until = now + 1800

        area_clear = not any(bee.alive for bee in bees)
        if level_index == 5 and area_clear and not merchant_spawned:
            merchant = MerchantFly((735, 370))
            merchant_spawned = True
        elif level.merchant_spawn_point is not None and not merchant_spawned:
            merchant = MerchantFly(level.merchant_spawn_point)
            merchant_spawned = True
        if merchant is not None:
            merchant.update(dt)

        merchant_required = level_index in (5, 8) and merchant_spawned and not merchant_visited
        if merchant_required and level.touches_exit(player.rect):
            message = "VISIT THE MERCHANT FIRST"
            message_until = now + 900

        if (
            transition_phase is None
            and area_clear
            and not merchant_required
            and level.touches_exit(player.rect)
            and level_index + 1 < len(LEVELS)
        ):
            transition_phase = "out"
            transition_started = now

        if transition_phase == "out" and now - transition_started >= fade_duration:
            level_index += 1
            if level_index % 3 == 0:
                checkpoint_index = level_index
            level = Level(LEVELS[level_index], use_green_terrain=level_index >= 4)
            player.respawn(level.player_spawn)
            bees = create_bees(level)
            shrine_objects.clear()
            merchant = None
            merchant_spawned = False
            merchant_visited = False
            moth_restore_started_at = None
            moth_restore_used = False
            final_merchant_rewarded = False
            hornet_phase = "intro" if level_index == 9 else ""
            hornet_wave = 0
            hornet_intro_started = now
            hornet_intro_until = now + 3600 if hornet_phase else 0
            game_won = False
            area_clear = False
            transition_phase = "in"
            transition_started = now
            level_title_until = now + 1700
            if level_index == 4:
                message = "SOAKED CAVE FLOOR SNUFFS LANTERNS"
                message_until = now + 2600
            elif level_index == 5:
                message = "TWO DRY PERCHES. LIGHT EACH ONE."
                message_until = now + 2200
            elif level_index == 6:
                message = ""
            elif level_index == 7:
                message = "KEEP MOVING - THE ANT IGNITES THE PLATFORM"
                message_until = now + 2600
            else:
                message = ""
        elif transition_phase == "in" and now - transition_started >= fade_duration:
            transition_phase = None

        if level.touches_hazard(player.rect):
            player.health = 0

        if player.health <= 0:
            death_reason = player.death_reason
            player.lives -= 1
            full_restart = player.lives <= 0
            if full_restart:
                level_index = 0
                checkpoint_index = 0
                player.coins = 0
                player.lives = 3
                shrine_lights = 5
                moths = MothSwarm()
                level = Level(LEVELS[level_index], use_green_terrain=level_index >= 4)
                bees = create_bees(level)
                shrine_objects.clear()
                merchant = None
                merchant_spawned = False
                merchant_visited = False
                moth_restore_started_at = None
                moth_restore_used = False
                final_merchant_rewarded = False
                hornet_phase = ""
                hornet_wave = 0
                hornet_intro_until = 0
                game_won = False
            player.health = 100
            player.death_reason = ""
            player.moth_stunned_until = 0
            player.respawn(level.player_spawn)
            moths.deployed = 0
            moths.attack_target = None
            moths.attack_origin = None
            moths.solar_position = None
            moths.attack_tier = 0
            transition_phase = "in"
            transition_started = now
            level_title_until = now + 1500
            message = death_reason or ("RUN RESET" if full_restart else f"{player.lives} LIVES LEFT")
            message_until = now + 1200
        if message and message_until and now >= message_until:
            message = ""

        scene.fill(BACKGROUND_COLOR)
        level.draw(scene)
        player.draw(scene)
        moths.draw(scene, player.rect, now, player.moths_available(now))
        for bee in bees:
            bee.draw(scene, now)
        if merchant is not None:
            merchant.draw(scene, now)
        lighting.draw(
            scene,
            player.rect.center,
            moths.deployed,
            moths.solar_position,
            [bee.position for bee in bees if bee.alive and bee.emits_light],
            [shrine.light_position for shrine in shrine_objects],
        )
        player.draw(scene)
        moths.draw(scene, player.rect, now, player.moths_available(now))
        moths.draw_attack_effects(scene, now)
        for bee in bees:
            bee.draw(scene, now)
        for shrine in shrine_objects:
            shrine.draw(scene)
        if merchant is not None:
            merchant.draw(scene, now)
        screen.fill(BACKGROUND_COLOR)
        screen.blit(scene, camera.offset)
        draw_ui(
            screen,
            font,
            alert_font,
            player,
            moths,
            shrine_lights,
            bees,
            level_index,
            level_title_until,
            now,
            message,
        )
        if merchant is not None and merchant.open:
            draw_merchant(screen, font, player, moths)

        if hornet_phase == "intro" and not game_won:
            intro_progress = min(1.0, (now - hornet_intro_started) / 3600)
            intro_veil = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            intro_veil.fill((0, 0, 0, round(205 * (1.0 - max(0.0, intro_progress - 0.72) / 0.28))))
            screen.blit(intro_veil, (0, 0))
            intro_line = font.render("THE FINAL HIVE FALLS SILENT", True, (185, 179, 164))
            screen.blit(intro_line, intro_line.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 48)))
            hornet_title = alert_font.render("HORNET", True, (250, 193, 45))
            screen.blit(hornet_title, hornet_title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 8)))

        if game_won:
            draw_win_screen(screen, font, alert_font)

        if transition_phase is not None:
            progress = min(1.0, (now - transition_started) / fade_duration)
            fade_alpha = round(255 * (progress if transition_phase == "out" else 1.0 - progress))
            fade_surface.fill((0, 0, 0, fade_alpha))
            screen.blit(fade_surface, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
