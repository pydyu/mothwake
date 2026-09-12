from pathlib import Path

import pygame

from entities import ATTACKS, ENEMY_COIN_REWARDS, Bee, Cricket, MerchantFly, MothSwarm, QueenBee, ShrineLight
from level import Level
from level_data import LEVELS
from lighting import LightingEngine
from player import Player
from settings import BACKGROUND_COLOR, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TEXT_COLOR, WINDOW_TITLE


FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "VCR_OSD_MONO_1.001.ttf"


def merchant_buttons() -> dict[str, pygame.Rect]:
    return {
        "lantern": pygame.Rect(625, 310, 280, 38),
        "tier_2": pygame.Rect(625, 354, 280, 38),
        "tier_3": pygame.Rect(625, 398, 280, 38),
        "tier_4": pygame.Rect(625, 442, 280, 38),
    }


def draw_merchant(screen: pygame.Surface, font: pygame.font.Font, player: Player, moths: MothSwarm) -> None:
    panel = pygame.Rect(605, 258, 320, 242)
    pygame.draw.rect(screen, (20, 18, 29), panel, border_radius=8)
    pygame.draw.rect(screen, (184, 145, 72), panel, 2, border_radius=8)
    screen.blit(font.render(f"MERCHANT   COINS: {player.coins}", True, (245, 211, 128)), (panel.x + 18, panel.y + 16))
    labels = {
        "lantern": "LANTERN                 1",
        "tier_2": "UNLOCK SWARM BURST     3",
        "tier_3": "UNLOCK SOLAR SWARM     5",
        "tier_4": "UNLOCK ECLIPSE         10",
    }
    for key, rect in merchant_buttons().items():
        tier = int(key[-1]) if key.startswith("tier_") else 0
        owned = tier and moths.unlocked_tier >= tier
        available = not tier or tier == moths.unlocked_tier + 1
        fill = (45, 40, 53) if available and not owned else (29, 27, 36)
        text_color = (235, 232, 219) if available and not owned else (105, 101, 115)
        pygame.draw.rect(screen, fill, rect, border_radius=5)
        pygame.draw.rect(screen, (91, 86, 108), rect, 1, border_radius=5)
        label = "OWNED" if owned else labels[key]
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
    return bees


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
        title = font.render("QUEEN BEE", True, accent_color)
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
        if bee.is_boss:
            screen.blit(font.render("ROYAL BLAST  -10 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("WING GUST  -6 HP", True, muted_color), (panel.x + 14, panel.y + 87))
            screen.blit(font.render("QUEEN SHOCK  PARALYSIS", True, muted_color), (panel.x + 14, panel.y + 113))
        elif bee.is_cricket:
            screen.blit(font.render("SONIC CHIRP  -18 HP", True, TEXT_COLOR), (panel.x + 14, panel.y + 61))
            screen.blit(font.render("LANTERN BREAKS SHIELD", True, muted_color), (panel.x + 14, panel.y + 87))
            screen.blit(font.render("LANTERN: ANY PLATFORM SPOT", True, muted_color), (panel.x + 14, panel.y + 113))
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

    level_index = 4
    checkpoint_index = 0
    level = Level(LEVELS[level_index])
    player = Player(level.player_spawn)
    moths = MothSwarm()
    bees = create_bees(level)
    lighting = LightingEngine((SCREEN_WIDTH, SCREEN_HEIGHT))
    camera = Camera()
    scene = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    shrine_objects: list[ShrineLight] = []
    merchant: MerchantFly | None = None
    merchant_spawned = False
    shrine_lights = 3
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
                    living_bees = [bee for bee in bees if bee.alive]
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
                        if player.coins >= 1:
                            player.coins -= 1
                            shrine_lights += 1
                            message = "LANTERN +1"
                        else:
                            message = "NOT ENOUGH COINS"
                    elif clicked_item and clicked_item.startswith("tier_"):
                        handled = True
                        tier = int(clicked_item[-1])
                        costs = {2: 3, 3: 5, 4: 10}
                        if moths.unlocked_tier >= tier:
                            message = "ALREADY OWNED"
                        elif tier != moths.unlocked_tier + 1:
                            message = "BUY PREVIOUS TIER"
                        elif player.coins < costs[tier]:
                            message = "NOT ENOUGH COINS"
                        else:
                            player.coins -= costs[tier]
                            moths.unlocked_tier = tier
                            message = f"TIER {tier} UNLOCKED"
                    if handled:
                        message_until = now + 1300

                world_click = camera.screen_to_world(event.pos)
                if not handled and merchant is not None and merchant.handle_click(world_click):
                    handled = True
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
        moths.update(now)
        for bee in bees:
            bee.update(now, player, moths, dt)
            if bee.defeated_by_player and not bee.coin_awarded:
                reward_name = "Queen Bee" if bee.is_boss else "Bee"
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

        area_clear = bool(bees) and not any(bee.alive for bee in bees)
        if level_index == 2 and area_clear and not merchant_spawned:
            merchant = MerchantFly((735, 370))
            merchant_spawned = True
        if merchant is not None:
            merchant.update(dt)

        if (
            transition_phase is None
            and area_clear
            and level.touches_exit(player.rect)
            and level_index + 1 < len(LEVELS)
        ):
            transition_phase = "out"
            transition_started = now

        if transition_phase == "out" and now - transition_started >= fade_duration:
            level_index += 1
            if level_index % 3 == 0:
                checkpoint_index = level_index
            level = Level(LEVELS[level_index])
            player.respawn(level.player_spawn)
            bees = create_bees(level)
            shrine_objects.clear()
            merchant = None
            merchant_spawned = False
            area_clear = False
            transition_phase = "in"
            transition_started = now
            level_title_until = now + 1700
            message = ""
        elif transition_phase == "in" and now - transition_started >= fade_duration:
            transition_phase = None

        if level.touches_hazard(player.rect):
            player.health = 0

        if player.health <= 0:
            player.lives -= 1
            full_restart = player.lives <= 0
            if full_restart:
                level_index = 0
                checkpoint_index = 0
                player.coins = 0
                player.lives = 3
                shrine_lights = 3
                moths = MothSwarm()
            level = Level(LEVELS[level_index])
            player.health = 100
            player.moth_stunned_until = 0
            player.respawn(level.player_spawn)
            bees = create_bees(level)
            shrine_objects.clear()
            merchant = None
            merchant_spawned = False
            moths.deployed = 0
            moths.attack_target = None
            moths.attack_origin = None
            moths.solar_position = None
            moths.attack_tier = 0
            transition_phase = "in"
            transition_started = now
            level_title_until = now + 1500
            message = "RUN RESET" if full_restart else f"{player.lives} LIVES LEFT"
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

        if transition_phase is not None:
            progress = min(1.0, (now - transition_started) / fade_duration)
            fade_alpha = round(255 * (progress if transition_phase == "out" else 1.0 - progress))
            fade_surface.fill((0, 0, 0, fade_alpha))
            screen.blit(fade_surface, (0, 0))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
