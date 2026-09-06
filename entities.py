import math
import random
from pathlib import Path

import pygame

from settings import BEE_COLOR, MOTH_COLOR


LANTERN_PATH = Path(__file__).resolve().parent / "assets" / "background" / "lantern.png"


ATTACKS = {
    1: {"name": "Light Dart", "cost": 3, "damage": 14, "stun": 250, "duration": 700},
    2: {"name": "Swarm Burst", "cost": 8, "damage": 32, "stun": 1200, "duration": 1400},
    3: {"name": "Solar Swarm", "cost": 15, "damage": 60, "stun": 2500, "duration": 2000},
}

ENEMY_COIN_REWARDS = {
    "Bee": 1,
    "Fire Ant": 3,
    "Cricket": 4,
    "Queen Bee": 5,
    "Hornet": 20,
}


def draw_glow(surface: pygame.Surface, position: tuple[int, int], color: tuple[int, int, int], radius: int) -> None:
    glow = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = radius * 2
    for size, alpha in ((radius * 2, 20), (radius + 5, 45), (radius, 90)):
        pygame.draw.circle(glow, (*color, alpha), (center, center), size)
    surface.blit(glow, (position[0] - center, position[1] - center), special_flags=pygame.BLEND_RGBA_ADD)


class MothSwarm:
    def __init__(self) -> None:
        self.count = 0
        self.summoned = False
        self.positions: list[pygame.Vector2] = []
        self.unlocked_tier = 1
        self.deployed = 0
        self.attack_target: pygame.Vector2 | None = None
        self.attack_ends_at = 0
        self.solar_position: tuple[int, int] | None = None
        self.wander_angles: list[float] = []
        self.wander_radii: list[float] = []
        self.wander_speeds: list[float] = []

    @property
    def available(self) -> int:
        return self.count - self.deployed

    def summon(self, player_position: tuple[int, int]) -> None:
        if self.summoned:
            return
        self.summoned = True
        self.count = 4
        _, y = player_position
        self.positions = [
            pygame.Vector2(-30, y - 90),
            pygame.Vector2(-70, y + 20),
            pygame.Vector2(990, y - 60),
            pygame.Vector2(1030, y + 35),
        ]
        self.wander_angles = [random.uniform(0, math.tau) for _ in range(self.count)]
        self.wander_radii = [random.uniform(18, 38) for _ in range(self.count)]
        self.wander_speeds = [random.uniform(0.9, 1.8) * random.choice((-1, 1)) for _ in range(self.count)]

    def lose(self, amount: int) -> None:
        self.count = max(0, self.count - amount)
        self.deployed = min(self.deployed, self.count)
        self.positions = self.positions[: self.count]

    def attack(self, tier: int, enemy, now: int, paralyzed: bool) -> str:
        # Like Pokemon paralysis adapted to real time: movement continues, but an
        # attempted move has a one-in-four chance to fail.
        if paralyzed and random.random() < 0.25:
            return "PARALYZED - MOVE FAILED!"
        if not enemy.selected or not enemy.alive:
            return "Click an enemy first."
        if tier > self.unlocked_tier:
            return f"Tier {tier} is locked."
        attack = ATTACKS[tier]
        if self.available < attack["cost"]:
            return f"Need {attack['cost']} moths for {attack['name']}."
        if self.deployed:
            return "Moths are still returning."

        self.deployed = attack["cost"]
        self.attack_target = pygame.Vector2(enemy.position)
        self.attack_ends_at = now + attack["duration"]
        self.solar_position = enemy.position if tier == 3 else None
        enemy.take_damage(attack["damage"], now, attack["stun"])
        return f"{attack['name']}! {attack['damage']} damage."

    def update(self, now: int) -> None:
        if self.deployed and now >= self.attack_ends_at:
            self.deployed = 0
            self.attack_target = None
            self.solar_position = None

    def draw(self, surface: pygame.Surface, player_rect: pygame.Rect, now: int, active: bool) -> None:
        color = MOTH_COLOR if active else (70, 58, 48)
        for index in range(self.count):
            if index < self.deployed and self.attack_target is not None:
                target = self.attack_target
            else:
                # Each moth meanders independently instead of occupying one of
                # four fixed points in a synchronized orbit.
                phase = now * 0.001 * self.wander_speeds[index]
                wobble = math.sin(now * 0.0031 + index * 2.37) * 9
                radius = self.wander_radii[index] + wobble
                angle = self.wander_angles[index] + phase + math.sin(now * 0.0017 + index) * 0.65
                offset_x = math.cos(angle) * radius
                offset_y = math.sin(angle * 1.31) * radius * 0.65
                target = pygame.Vector2(
                    player_rect.centerx + offset_x,
                    player_rect.centery + offset_y,
                )
            follow = 0.075 if active else 0.04
            self.positions[index] += (target - self.positions[index]) * follow
            pygame.draw.circle(surface, color, self.positions[index], 2)


class Bee:
    def __init__(self, position: tuple[int, int], platform: pygame.Rect) -> None:
        self.position = position
        self.rect = pygame.Rect(0, 0, 24, 24)
        self.rect.center = position
        self.max_health = 40
        self.health = self.max_health
        self.alive = True
        self.selected = False
        self.next_attack_at = 0
        self.stunned_until = 0
        self.revealed_until = 0
        self.platform_radius = platform.inflate(160, 120)
        self.last_attack = ""
        self.defeated_by_player = False

    def handle_click(self, position: tuple[int, int]) -> None:
        self.selected = self.alive and self.rect.collidepoint(position)

    def take_damage(self, damage: int, now: int, stun_ms: int) -> None:
        self.health = max(0, self.health - damage)
        self.stunned_until = max(self.stunned_until, now + stun_ms)
        self.revealed_until = max(self.revealed_until, now + 2500)
        if self.health == 0:
            self.alive = False
            self.selected = False
            self.defeated_by_player = True

    def update(self, now: int, player, moths: MothSwarm) -> None:
        if not self.alive or now < self.stunned_until or not self.platform_radius.colliderect(player.rect):
            return
        if self.next_attack_at == 0:
            self.next_attack_at = now + 1200
            return
        if now < self.next_attack_at:
            return

        if random.random() < 0.15:
            lost = min(moths.count, random.randint(1, 2))
            moths.lose(lost)
            self.alive = False
            self.selected = False
            self.last_attack = f"Sting! {lost} moth{'s' if lost != 1 else ''} lost."
        else:
            player.stun_moths(now, 4000)
            self.last_attack = "PARALYZED! 25% FAIL CHANCE"
            self.next_attack_at = now + 3500

    def draw(self, surface: pygame.Surface, now: int) -> None:
        if self.alive:
            color = (255, 230, 112) if now < self.revealed_until else BEE_COLOR
            draw_glow(surface, self.position, (255, 190, 55), 14)
            pygame.draw.circle(surface, color, self.position, 8)


class ShrineLight:
    def __init__(self, position: tuple[int, int]) -> None:
        self.position = position
        source = pygame.image.load(str(LANTERN_PATH)).convert_alpha()
        visible_bounds = source.get_bounding_rect()
        if not visible_bounds.width or not visible_bounds.height:
            raise ValueError(f"Lantern image has no visible pixels: {LANTERN_PATH}")
        self.image = source.subsurface(visible_bounds).copy()
        self.rect = self.image.get_rect(midbottom=position)

    @property
    def light_position(self) -> tuple[int, int]:
        return (self.rect.centerx, self.rect.top + self.rect.height // 3)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.image, self.rect)
