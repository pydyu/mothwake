from pathlib import Path

import pygame

from entities import ATTACKS, ENEMY_COIN_REWARDS, Bee, MothSwarm, ShrineLight
from level import Level
from level_data import LEVELS
from lighting import LightingEngine
from player import Player
from settings import BACKGROUND_COLOR, FPS, SCREEN_HEIGHT, SCREEN_WIDTH, TEXT_COLOR, WINDOW_TITLE


FONT_PATH = Path(__file__).resolve().parent / "assets" / "fonts" / "VCR_OSD_MONO_1.001.ttf"


class Camera:
    def __init__(self) -> None:
        self.offset = pygame.Vector2()

    def update(self, dt: float, player: Player, move_direction: int) -> None:
        # A gentle look-ahead and vertical response makes movement readable
        # without pulling the player away from the centre of the action.
        target = pygame.Vector2(-move_direction * 24, max(-14, min(14, -player.velocity.y * 0.018)))
        self.offset += (target - self.offset) * min(1.0, dt * 5.5)

    def world_to_screen(self, position: tuple[int, int]) -> tuple[int, int]:
        return round(position[0] + self.offset.x), round(position[1] + self.offset.y)

    def screen_to_world(self, position: tuple[int, int]) -> tuple[int, int]:
        return round(position[0] - self.offset.x), round(position[1] - self.offset.y)


def find_bee_platform(level: Level, bee_position: tuple[int, int]) -> pygame.Rect:
    platforms = level.platform_rects
    return min(platforms, key=lambda rect: abs(rect.centerx - bee_position[0]) + abs(rect.top - bee_position[1]))


def draw_ui(screen: pygame.Surface, font: pygame.font.Font, alert_font: pygame.font.Font, player: Player, moths: MothSwarm, shrine_lights: int, bee: Bee, now: int, message: str) -> None:
    lines = [
        f"HP: {player.health}/100",
        f"Moths: {moths.available}/{moths.count}",
        f"Coins: {player.coins}",
        f"Shrine Lights: {shrine_lights}/20",
        "Attacks: [1] Light Dart  [2] Swarm Burst  [3] Solar Swarm",
    ]
    for index, line in enumerate(lines):
        screen.blit(font.render(line, True, TEXT_COLOR), (16, 14 + index * 24))

    if not player.moths_available(now):
        remaining = (player.moth_stunned_until - now) / 1000
        status = f"PARALYZED  {remaining:.1f}s"
        screen.blit(alert_font.render(status, True, (255, 220, 90)), (16, 14 + len(lines) * 24))

    if bee.selected and bee.alive:
        panel = pygame.Rect(SCREEN_WIDTH - 330, 16, 314, 126)
        pygame.draw.rect(screen, (24, 22, 34),
         panel, border_radius=6)
        pygame.draw.rect(screen, (110, 104, 126), panel, 2, border_radius=6)
        stats = [f"Bee: {bee.health}/{bee.max_health} HP", "Attacks:", "Sting: Dies and kills 1-2 moths (rare)", "Paralysis: 25% attack failure; movement continues"]
        for index, line in enumerate(stats):
            screen.blit(font.render(line, True, TEXT_COLOR), (panel.x + 12, panel.y + 10 + index * 26))

    notice = message or bee.last_attack
    if notice:
        screen.blit(alert_font.render(notice, True, TEXT_COLOR), (16, SCREEN_HEIGHT - 42))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(WINDOW_TITLE)
    clock = pygame.time.Clock()

    level = Level(LEVELS[0])
    player = Player(level.player_spawn)
    moths = MothSwarm()
    bee_position = level.bee_positions[0]
    bee = Bee(bee_position, find_bee_platform(level, bee_position))
    lighting = LightingEngine((SCREEN_WIDTH, SCREEN_HEIGHT))
    camera = Camera()
    scene = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    shrine_objects: list[ShrineLight] = []
    shrine_lights = 3
    message = ""
    message_until = 0
    coin_awarded = False
    font = pygame.font.Font(str(FONT_PATH), 20)
    alert_font = pygame.font.Font(str(FONT_PATH), 30)
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
                        shrine_objects.append(ShrineLight(player.rect.midbottom))
                        shrine_lights -= 1
                        moths.summon(player.rect.center)
                elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    tier = event.key - pygame.K_0
                    message = moths.attack(tier, bee, now, player.moths_paralyzed(now))
                    message_until = now + 2500
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                bee.handle_click(camera.screen_to_world(event.pos))

        keys = pygame.key.get_pressed()
        move_direction = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(
            keys[pygame.K_a] or keys[pygame.K_LEFT]
        )
        player.update(dt, move_direction, jump_requested, level.solids)
        camera.update(dt, player, move_direction)
        moths.update(now)
        bee.update(now, player, moths)
        if bee.defeated_by_player and not coin_awarded:
            player.coins += ENEMY_COIN_REWARDS["Bee"]
            coin_awarded = True
            message = "Bee defeated! +1 Coin."
            message_until = now + 3000
        if message and message_until and now >= message_until:
            message = ""

        if level.touches_hazard(player.rect):
            player.respawn(level.player_spawn)

        scene.fill(BACKGROUND_COLOR)
        level.draw(scene)
        player.draw(scene)
        moths.draw(scene, player.rect, now, player.moths_available(now))
        bee.draw(scene, now)
        lighting.draw(
            scene,
            player.rect.center,
            moths.deployed,
            moths.solar_position,
            bee.position if bee.alive else None,
            [shrine.light_position for shrine in shrine_objects],
        )
        player.draw(scene)
        moths.draw(scene, player.rect, now, player.moths_available(now))
        bee.draw(scene, now)
        for shrine in shrine_objects:
            shrine.draw(scene)
        screen.fill(BACKGROUND_COLOR)
        screen.blit(scene, camera.offset)
        draw_ui(screen, font, alert_font, player, moths, shrine_lights, bee, now, message)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
