import math
import random
from pathlib import Path

import pygame

from settings import MOTH_COLOR


LANTERN_PATH = Path(__file__).resolve().parent / "assets" / "background" / "lantern.png"
BEE_FRAME_PATHS = tuple(
    Path(__file__).resolve().parent
    / "assets"
    / "enemies"
    / "bee"
    / f"{index:02d}_pixilart-sprite (20).png"
    for index in range(3)
)
BEE_FRAME_DURATION_MS = 140
MAX_MOTHS = 32
MERCHANT_FRAME_PATHS = tuple(
    Path(__file__).resolve().parent / "assets" / "merchant" / f"pixil-frame-{index}.png"
    for index in range(2)
)
MERCHANT_FRAME_DURATION_MS = 180
CRICKET_SHEET_PATH = Path(__file__).resolve().parent / "assets" / "enemies" / "cricket" / "cricket-hop-sheet.png"
FIRE_ANT_PATH = Path(__file__).resolve().parent / "assets" / "enemies" / "fireant" / "fireant.png"
HORNET_FRAME_PATHS = tuple(
    Path(__file__).resolve().parent / "assets" / "finalboss" / f"pixil-frame-{index}.png"
    for index in range(2)
)


ATTACKS = {
    1: {"name": "Light Dart", "cost": 3, "damage": 14, "stun": 250, "duration": 420},
    2: {"name": "Swarm Burst", "cost": 4, "damage": 32, "stun": 1100, "duration": 900},
    3: {"name": "Solar Swarm", "cost": 4, "damage": 60, "stun": 2200, "duration": 1300},
    4: {"name": "Eclipse", "cost": 4, "damage": 80, "stun": 2800, "duration": 1450},
}

ENEMY_COIN_REWARDS = {
    "Bee": 1,
    "Fire Ant": 3,
    "Cricket": 2,
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
        self.max_count = MAX_MOTHS
        self.summoned = False
        self.positions: list[pygame.Vector2] = []
        self.unlocked_tier = 1
        self.deployed = 0
        self.attack_target: pygame.Vector2 | None = None
        self.attack_origin: pygame.Vector2 | None = None
        self.attack_ends_at = 0
        self.attack_started_at = 0
        self.attack_tier = 0
        self.solar_position: tuple[int, int] | None = None
        self.wander_angles: list[float] = []
        self.wander_radii: list[float] = []
        self.wander_speeds: list[float] = []

    @property
    def available(self) -> int:
        return self.count - self.deployed

    @property
    def damage_bonus(self) -> float:
        # Each moth adds 0.5% damage, capped at a modest 15% bonus.
        return min(0.15, self.count * 0.005)

    def summon(self, player_position: tuple[int, int], force: bool = False) -> None:
        if self.summoned and not force:
            return
        self.summoned = True
        self.count = 4
        self.deployed = 0
        self.attack_target = None
        self.attack_origin = None
        self.attack_tier = 0
        self.solar_position = None
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

    def restore_full(self, player_position: tuple[int, int]) -> None:
        """Restore the full swarm for the final preparation room."""
        self.summoned = True
        self.count = self.max_count
        self.deployed = 0
        self.attack_target = None
        self.attack_origin = None
        self.attack_tier = 0
        self.solar_position = None
        center = pygame.Vector2(player_position)
        self.positions = [
            center + pygame.Vector2(random.uniform(-70, 70), random.uniform(-45, 45))
            for _ in range(self.count)
        ]
        self.wander_angles = [random.uniform(0, math.tau) for _ in range(self.count)]
        self.wander_radii = [random.uniform(18, 52) for _ in range(self.count)]
        self.wander_speeds = [random.uniform(0.9, 1.8) * random.choice((-1, 1)) for _ in range(self.count)]

    def attack(self, tier: int, enemy, now: int, paralyzed: bool) -> str:
        # Like Pokemon paralysis adapted to real time: movement continues, but an
        # attempted move has a one-in-four chance to fail.
        if paralyzed and random.random() < 0.25:
            return "PARALYZED - MOVE FAILED!"
        if enemy is None or not enemy.alive:
            return "NO ENEMIES LEFT"
        if getattr(enemy, "attack_locked", False):
            enemy.selected = True
            return getattr(enemy, "locked_message", "DEFEAT THE WAVE FIRST")
        # A cricket's chirp bends echoes around its unlit perch. Moths can be
        # present, but cannot acquire that specific target until a lantern on
        # its own platform breaks the echo-dark. Rejecting here also prevents
        # an attack animation from starting.
        if getattr(enemy, "is_cricket", False) and not getattr(enemy, "lantern_placed", False):
            enemy.selected = True
            enemy.revealed_until = now + 700
            enemy.last_attack = "ECHO-DARK HIDES CRICKET"
            return "LIGHT THIS CRICKET'S PLATFORM FIRST"
        if tier > self.unlocked_tier:
            return f"Tier {tier} is locked."
        attack = ATTACKS[tier]
        if self.available < attack["cost"]:
            return f"Need {attack['cost']} moths for {attack['name']}."
        if self.deployed:
            return "Moths are still returning."

        self.deployed = attack["cost"]
        self.attack_target = pygame.Vector2(enemy.position)
        if self.positions:
            self.attack_origin = sum(self.positions, pygame.Vector2()) / len(self.positions)
        else:
            self.attack_origin = self.attack_target.copy()
        self.attack_started_at = now
        self.attack_tier = tier
        self.attack_ends_at = now + attack["duration"]
        self.solar_position = enemy.position if tier == 3 else None
        damage = round(attack["damage"] * (1.0 + self.damage_bonus))
        enemy.take_damage(damage, now, attack["stun"])
        return f"{attack['name']}! {damage} damage."

    def update(self, now: int) -> None:
        if self.deployed and now >= self.attack_ends_at:
            self.deployed = 0
            self.attack_target = None
            self.attack_origin = None
            self.solar_position = None
            self.attack_tier = 0

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

    def draw_attack_effects(self, surface: pygame.Surface, now: int) -> None:
        if not self.deployed or self.attack_target is None or not self.attack_tier:
            return
        duration = ATTACKS[self.attack_tier]["duration"]
        progress = max(0.0, min(1.0, (now - self.attack_started_at) / duration))
        target = (round(self.attack_target.x), round(self.attack_target.y))

        if self.attack_tier == 1:
            origin = self.attack_origin or self.attack_target
            travel = min(1.0, progress * 1.8)
            direction = self.attack_target - origin
            normal = pygame.Vector2(-direction.y, direction.x)
            if normal.length_squared():
                normal = normal.normalize()
            projectile = origin.lerp(self.attack_target, travel)
            projectile += normal * math.sin(travel * math.pi) * 14
            for trail_index in range(6, 0, -1):
                trail_progress = max(0.0, travel - trail_index * 0.035)
                trail = origin.lerp(self.attack_target, trail_progress)
                trail += normal * math.sin(trail_progress * math.pi) * 14
                radius = max(1, 5 - trail_index // 2)
                pygame.draw.circle(surface, (166, 119, 42), trail, radius)
            pygame.draw.circle(surface, (255, 198, 54), projectile, 8)
            pygame.draw.circle(surface, (255, 247, 188), projectile, 4)
            if travel >= 1.0:
                impact_radius = round(8 + (progress - 0.55) * 35)
                pygame.draw.circle(surface, (255, 218, 92), target, impact_radius, 3)
        elif self.attack_tier == 2:
            radius = round(10 + progress * 38)
            pygame.draw.circle(surface, (205, 158, 255), target, radius, 3)
            pygame.draw.circle(surface, (244, 221, 255), target, max(3, radius // 2), 2)
            for angle in range(0, 360, 45):
                mote = pygame.Vector2(radius, 0).rotate(angle + progress * 240)
                pygame.draw.circle(surface, (226, 191, 255), pygame.Vector2(target) + mote, 4)
        elif self.attack_tier == 3:
            radius = round(18 + math.sin(progress * math.pi) * 34)
            pygame.draw.circle(surface, (117, 70, 18), target, radius + 10)
            pygame.draw.circle(surface, (255, 205, 65), target, radius, 4)
            pygame.draw.circle(surface, (255, 242, 172), target, max(5, radius // 3))
            for angle in range(0, 360, 45):
                direction = pygame.Vector2(1, 0).rotate(angle)
                pygame.draw.line(surface, (255, 231, 135), target, pygame.Vector2(target) + direction * (radius + 12), 2)
        else:
            radius = round(16 + progress * 48)
            pygame.draw.circle(surface, (125, 75, 180), target, radius, 5)
            pygame.draw.circle(surface, (12, 8, 20), target, max(5, radius - 10))
            pygame.draw.circle(surface, (226, 190, 255), target, max(4, radius // 3), 2)
            for angle in range(0, 360, 60):
                mote = pygame.Vector2(radius + 9, 0).rotate(angle - progress * 300)
                pygame.draw.circle(surface, (174, 119, 220), pygame.Vector2(target) + mote, 3)


class Bee:
    def __init__(self, position: tuple[int, int], platform: pygame.Rect, chases_player: bool = False) -> None:
        self.position = pygame.Vector2(position)
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
        self.coin_awarded = False
        self.chases_player = chases_player
        self.name = "BEE"
        self.is_boss = False
        self.is_cricket = False
        self.is_fire_ant = False
        self.is_hornet = False
        self.emits_light = True
        self.animation_frames = [self._load_frame(path) for path in BEE_FRAME_PATHS]

    @staticmethod
    def _load_frame(path: Path) -> pygame.Surface:
        source = pygame.image.load(str(path)).convert_alpha()
        visible_bounds = source.get_bounding_rect()
        if not visible_bounds.width or not visible_bounds.height:
            raise ValueError(f"Bee frame has no visible pixels: {path}")
        frame = source.subsurface(visible_bounds).copy()
        return pygame.transform.scale(frame, (30, 25))

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

    def update(self, now: int, player, moths: MothSwarm, dt: float = 0.0) -> None:
        if not self.alive or now < self.stunned_until:
            return
        player_delta = pygame.Vector2(player.rect.center) - self.position
        distance = player_delta.length()
        if self.chases_player and distance > 8:
            self.position += player_delta.normalize() * 90 * dt
            self.rect.center = (round(self.position.x), round(self.position.y))
            player_delta = pygame.Vector2(player.rect.center) - self.position
            distance = player_delta.length()
        in_attack_range = distance < 220 if self.chases_player else self.platform_radius.colliderect(player.rect)
        if not in_attack_range:
            return
        if self.next_attack_at == 0:
            self.next_attack_at = now + 950
            return
        if now < self.next_attack_at:
            return

        can_sting = not self.chases_player or self.rect.colliderect(player.rect)
        if can_sting and moths.count > 0 and random.random() < 0.15:
            # Sting kills one moth 30% of the time and two moths 70% of the time.
            lost = min(moths.count, 1 if random.random() < 0.30 else 2)
            moths.lose(lost)
            self.alive = False
            self.selected = False
            self.last_attack = f"Sting! {lost} moth{'s' if lost != 1 else ''} lost."
        else:
            player.stun_moths(now, 3200)
            self.last_attack = "PARALYZED! 25% FAIL CHANCE"
            self.next_attack_at = now + 2900

    def draw(self, surface: pygame.Surface, now: int) -> None:
        if self.alive:
            frame_index = (now // BEE_FRAME_DURATION_MS) % len(self.animation_frames)
            frame = self.animation_frames[frame_index]
            frame_rect = frame.get_rect(center=self.position)
            surface.blit(frame, frame_rect)


class QueenBee(Bee):
    """A forgiving first-pass boss using enlarged bee art as a placeholder."""

    def __init__(self, position: tuple[int, int], platform: pygame.Rect) -> None:
        super().__init__(position, platform)
        self.name = "QUEEN BEE"
        self.is_boss = True
        self.max_health = 250
        self.health = self.max_health
        self.rect = pygame.Rect(0, 0, 42, 38)
        self.rect.center = position
        self.animation_frames = [
            pygame.transform.scale(frame, (45, 38))
            for frame in self.animation_frames
        ]
        self.next_summon_at = 0
        self.summons_pending = 0

    def update(self, now: int, player, moths: MothSwarm, dt: float = 0.0) -> None:
        if not self.alive or now < self.stunned_until:
            return

        target = pygame.Vector2(player.rect.centerx, player.rect.centery - 85)
        delta = target - self.position
        if delta.length() > 90:
            self.position += delta.normalize() * 60 * dt
            self.rect.center = (round(self.position.x), round(self.position.y))

        if self.next_summon_at == 0:
            self.next_summon_at = now + 7000
        elif now >= self.next_summon_at:
            self.summons_pending += 1
            self.next_summon_at = now + 7000
            self.last_attack = "QUEEN SUMMONS A BEE!"

        if self.position.distance_to(player.rect.center) > 340:
            return
        if self.next_attack_at == 0:
            self.next_attack_at = now + 1500
            return
        if now < self.next_attack_at:
            return

        attack_roll = random.random()
        if attack_roll < 0.33:
            player.stun_moths(now, 1800)
            self.last_attack = "QUEEN SHOCK! PARALYZED"
        elif attack_roll < 0.66:
            player.health = max(0, player.health - 6)
            player.velocity.y = -320
            self.last_attack = "WING GUST! -6 HP"
        else:
            player.health = max(0, player.health - 10)
            self.last_attack = "ROYAL BLAST! -10 HP"
        self.revealed_until = now + 350
        self.next_attack_at = now + 1900

    def draw(self, surface: pygame.Surface, now: int) -> None:
        super().draw(surface, now)
        if self.alive:
            x, y = round(self.position.x), round(self.position.y)
            crown_color = (255, 210, 62)
            pygame.draw.polygon(
                surface,
                crown_color,
                ((x - 9, y - 20), (x - 6, y - 28), (x, y - 22), (x + 6, y - 28), (x + 9, y - 20)),
            )
            pygame.draw.line(surface, crown_color, (x - 9, y - 20), (x + 9, y - 20), 3)


class Hornet(Bee):
    """Large final boss with wave-gated damage phases."""

    def __init__(self, position: tuple[int, int], platform: pygame.Rect) -> None:
        super().__init__(position, platform)
        self.name = "HORNET"
        self.is_boss = True
        self.is_hornet = True
        self.max_health = 720
        self.health = self.max_health
        self.rect = pygame.Rect(0, 0, 104, 68)
        self.rect.center = position
        self.animation_frames = [self._load_hornet_frame(path) for path in HORNET_FRAME_PATHS]
        self.attack_locked = True
        self.locked_message = "DEFEAT THE WAVE FIRST"
        self.health_floor = 720
        self.waves_complete = False

    @staticmethod
    def _load_hornet_frame(path: Path) -> pygame.Surface:
        source = pygame.image.load(str(path)).convert_alpha()
        bounds = source.get_bounding_rect()
        if not bounds.width or not bounds.height:
            raise ValueError(f"Hornet frame has no visible pixels: {path}")
        cropped = source.subsurface(bounds).copy()
        return pygame.transform.scale(cropped, (120, 99))

    def open_damage_phase(self, health_floor: int) -> None:
        self.health_floor = health_floor
        self.waves_complete = health_floor == 0
        self.attack_locked = False
        self.last_attack = "HORNET EXPOSED!"

    def take_damage(self, damage: int, now: int, stun_ms: int) -> None:
        if self.attack_locked:
            self.last_attack = self.locked_message
            return
        minimum_health = 0 if self.waves_complete else max(1, self.health_floor)
        self.health = max(minimum_health, self.health - damage)
        self.stunned_until = max(self.stunned_until, now + min(stun_ms, 700))
        self.revealed_until = max(self.revealed_until, now + 2500)
        if self.health == 0 and self.waves_complete:
            self.alive = False
            self.selected = False
            self.defeated_by_player = True

    def update(self, now: int, player, moths: MothSwarm, dt: float = 0.0) -> None:
        if not self.alive or now < self.stunned_until:
            return
        target = pygame.Vector2(player.rect.centerx, max(145, player.rect.centery - 150))
        delta = target - self.position
        if delta.length() > 35:
            self.position += delta.normalize() * 72 * dt
            self.rect.center = (round(self.position.x), round(self.position.y))
        if self.attack_locked or self.position.distance_to(player.rect.center) > 390:
            return
        if self.next_attack_at == 0:
            self.next_attack_at = now + 1300
        elif now >= self.next_attack_at:
            if random.random() < 0.5:
                player.health = max(0, player.health - 12)
                self.last_attack = "NEEDLE VOLLEY! -12 HP"
            else:
                player.health = max(0, player.health - 8)
                player.velocity.y = -380
                self.last_attack = "HORNET DIVE! -8 HP"
            self.next_attack_at = now + 1600

    def draw(self, surface: pygame.Surface, now: int) -> None:
        if not self.alive:
            return
        frame = self.animation_frames[(now // 150) % len(self.animation_frames)]
        surface.blit(frame, frame.get_rect(center=self.position))
        x, y = map(round, self.position)
        if self.attack_locked:
            pygame.draw.circle(surface, (224, 171, 47), (x, y), 65, 3)


class FireAnt(Bee):
    """Ground-chasing Fire Ant for Level 8."""

    def __init__(self, position: tuple[int, int], platform: pygame.Rect) -> None:
        super().__init__(position, platform)
        self.name = "FIRE ANT"
        self.is_fire_ant = True
        self.emits_light = False
        self.max_health = 85
        self.health = self.max_health
        self.home_platform = platform.copy()
        self.rect = pygame.Rect(0, 0, 42, 26)
        self.position.y = self.home_platform.top - self.rect.height // 2
        self.rect.center = (round(self.position.x), round(self.position.y))
        self.fire_patches: list[tuple[pygame.Rect, int]] = []
        self.next_patch_at = 0
        self.next_fire_damage_at = 0
        self.drops_fire = True
        self.tracked_target_x = self.position.x
        self.next_retarget_at = 0
        self.facing = 1
        source = pygame.image.load(str(FIRE_ANT_PATH)).convert_alpha()
        bounds = source.get_bounding_rect()
        if not bounds.width or not bounds.height:
            raise ValueError(f"Fire Ant image has no visible pixels: {FIRE_ANT_PATH}")
        sprite = pygame.transform.scale(source.subsurface(bounds).copy(), (48, 41))
        self.image_left = sprite
        self.image_right = pygame.transform.flip(sprite, True, False)

    def update(self, now: int, player, moths: MothSwarm, dt: float = 0.0) -> None:
        if not self.alive or now < self.stunned_until:
            return
        if now >= self.next_retarget_at:
            self.tracked_target_x = max(
                self.home_platform.left + self.rect.width // 2,
                min(self.home_platform.right - self.rect.width // 2, player.rect.centerx),
            )
            self.next_retarget_at = now + 850
        target_x = self.tracked_target_x
        direction = 1 if target_x > self.position.x else -1
        if abs(target_x - self.position.x) > 3:
            self.facing = direction
            self.position.x += direction * min(abs(target_x - self.position.x), 105 * dt)
            self.rect.centerx = round(self.position.x)
        self.fire_patches = [(patch, expiry) for patch, expiry in self.fire_patches if now < expiry]
        if self.drops_fire and self.next_patch_at == 0:
            self.next_patch_at = now + 1200
        elif self.drops_fire and now >= self.next_patch_at:
            patch = pygame.Rect(0, 0, 38, 12)
            patch.midbottom = (self.rect.centerx, self.home_platform.top)
            self.fire_patches.append((patch, now + 3200))
            self.next_patch_at = now + 2800
        if self.drops_fire and now >= self.next_fire_damage_at and any(patch.colliderect(player.rect) for patch, _ in self.fire_patches):
            player.fire_hits += 1
            player.health = max(0, player.health - 34)
            if player.fire_hits >= 3:
                player.health = 0
                player.death_reason = "BURNT BY FIRE!"
            self.last_attack = f"FIRE HIT {min(player.fire_hits, 3)}/3"
            self.next_fire_damage_at = now + 750
        if self.rect.colliderect(player.rect) and now >= self.next_attack_at:
            player.health = max(0, player.health - 15)
            self.last_attack = "BURNT BY FIRE! -15 HP"
            if player.health == 0:
                player.death_reason = "BURNT BY FIRE!"
            self.next_attack_at = now + 1000

    def draw(self, surface: pygame.Surface, now: int) -> None:
        if not self.alive:
            return
        for patch, expiry in self.fire_patches:
            flicker = 3 + ((now // 100 + patch.x) % 3)
            pygame.draw.ellipse(surface, (119, 35, 25), patch)
            for flame_x in range(patch.left + 5, patch.right, 9):
                pygame.draw.polygon(
                    surface,
                    (245, 112, 35),
                    ((flame_x - 4, patch.bottom - 2), (flame_x, patch.top - flicker), (flame_x + 4, patch.bottom - 2)),
                )
        image = self.image_right if self.facing > 0 else self.image_left
        surface.blit(image, image.get_rect(midbottom=self.rect.midbottom))


class Cricket(Bee):
    """Non-lethal timing obstacle used by the Level 5 lantern puzzle."""

    CHIRP_CYCLE_MS = 3000
    QUIET_WINDOW_MS = 900

    def __init__(self, position: tuple[int, int], platform: pygame.Rect) -> None:
        super().__init__(position, platform)
        self.name = "CRICKET"
        self.is_cricket = True
        self.emits_light = False
        self.max_health = 80
        self.health = self.max_health
        self.home_platform = platform.copy()
        self.rect = pygame.Rect(0, 0, 46, 27)
        self.position.y = self.home_platform.top - self.rect.height // 2
        self.rect.center = (round(self.position.x), round(self.position.y))
        self.lantern_placed = False
        self.attack_enabled = True
        self.hop_started_at = 0
        self.next_hop_at = 0
        self.hop_start_x = self.position.x
        self.hop_target_x = self.position.x
        self.hop_progress = 0.0
        self.animation_frames = self._load_cricket_frames()

    @staticmethod
    def _load_cricket_frames() -> list[pygame.Surface]:
        sheet = pygame.image.load(str(CRICKET_SHEET_PATH)).convert_alpha()
        cell_width = sheet.get_width() // 3
        sources = [
            sheet.subsurface((index * cell_width, 0, cell_width, sheet.get_height())).copy()
            for index in range(3)
        ]
        bounds = [source.get_bounding_rect() for source in sources]
        max_width = max(bound.width for bound in bounds)
        max_height = max(bound.height for bound in bounds)
        scale = min(72 / max_width, 44 / max_height)
        frames: list[pygame.Surface] = []
        for source, bound in zip(sources, bounds):
            cropped = source.subsurface(bound).copy()
            size = (max(1, round(bound.width * scale)), max(1, round(bound.height * scale)))
            sprite = pygame.transform.scale(cropped, size)
            frame = pygame.Surface((78, 48), pygame.SRCALPHA)
            frame.blit(sprite, sprite.get_rect(midbottom=(39, 46)))
            frames.append(frame)
        return frames

    def is_quiet(self, now: int) -> bool:
        return now % self.CHIRP_CYCLE_MS >= self.CHIRP_CYCLE_MS - self.QUIET_WINDOW_MS

    def player_on_platform(self, player_rect: pygame.Rect) -> bool:
        horizontally_over_platform = self.home_platform.left <= player_rect.centerx < self.home_platform.right
        standing_on_top = abs(player_rect.bottom - self.home_platform.top) <= 4
        return horizontally_over_platform and standing_on_top

    def take_damage(self, damage: int, now: int, stun_ms: int) -> None:
        if not self.lantern_placed:
            self.revealed_until = now + 700
            self.last_attack = "CHIRP SHIELD!"
            return
        super().take_damage(damage, now, stun_ms)

    def activate_lantern(self) -> None:
        self.lantern_placed = True
        self.last_attack = "CRICKET EXPOSED!"

    def update(self, now: int, player, moths: MothSwarm, dt: float = 0.0) -> None:
        if not self.alive:
            return

        distance = self.position.distance_to(player.rect.center)
        if not self.hop_started_at and distance < 360 and now >= self.next_hop_at:
            self.hop_started_at = now
            self.hop_start_x = self.position.x
            self.hop_target_x = max(
                self.home_platform.left + self.rect.width // 2,
                min(self.home_platform.right - self.rect.width // 2, player.rect.centerx),
            )
            self.next_hop_at = now + 1350

        if self.hop_started_at:
            hop_progress = min(1.0, (now - self.hop_started_at) / 620)
            self.hop_progress = hop_progress
            self.position.x = self.hop_start_x + (self.hop_target_x - self.hop_start_x) * hop_progress
            ground_y = self.home_platform.top - self.rect.height // 2
            self.position.y = ground_y - math.sin(hop_progress * math.pi) * 54
            self.rect.center = (round(self.position.x), round(self.position.y))
            if hop_progress >= 1.0:
                self.hop_started_at = 0
                self.hop_progress = 0.0

        if self.attack_enabled and not self.is_quiet(now) and self.position.distance_to(player.rect.center) < 180 and now >= self.next_attack_at:
            player.health = max(0, player.health - 10)
            self.last_attack = "SONIC CHIRP! -10 HP"
            self.next_attack_at = now + 1200

    def draw(self, surface: pygame.Surface, now: int) -> None:
        if not self.alive:
            return
        x, y = round(self.position.x), round(self.position.y)
        if not self.hop_started_at:
            frame_index = 0
        elif self.hop_progress < 0.34 or self.hop_progress > 0.78:
            frame_index = 1
        else:
            frame_index = 2
        frame = self.animation_frames[frame_index]
        surface.blit(frame, frame.get_rect(midbottom=(x, self.rect.bottom)))
        if not self.is_quiet(now):
            pulse = round(30 + (now % 700) / 700 * 42)
            pygame.draw.circle(surface, (127, 174, 143), (x, y), pulse, 2)


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


class MerchantFly:
    """Large temporary merchant art, ready to be replaced by a sprite later."""

    def __init__(self, target: tuple[int, int]) -> None:
        self.position = pygame.Vector2(1040, target[1] - 80)
        self.target = pygame.Vector2(target)
        self.animation_frames = self._load_frames()
        self.rect = pygame.Rect(0, 0, 70, 44)
        self.rect.center = self.position
        self.open = False

    @staticmethod
    def _load_frames() -> list[pygame.Surface]:
        sources = [pygame.image.load(str(path)).convert_alpha() for path in MERCHANT_FRAME_PATHS]
        visible_bounds = [source.get_bounding_rect() for source in sources]
        if any(not bounds.width or not bounds.height for bounds in visible_bounds):
            raise ValueError("Merchant animation contains an empty frame")
        shared_bounds = visible_bounds[0].unionall(visible_bounds[1:])
        frames = []
        for source in sources:
            frame = source.subsurface(shared_bounds).copy()
            frame = pygame.transform.flip(frame, True, False)
            frames.append(pygame.transform.scale(frame, (66, 36)))
        return frames

    @property
    def arrived(self) -> bool:
        return self.position.distance_to(self.target) < 3

    def update(self, dt: float) -> None:
        delta = self.target - self.position
        if delta.length() > 3:
            self.position += delta.normalize() * min(delta.length(), 190 * dt)
            self.rect.center = (round(self.position.x), round(self.position.y))

    def handle_click(self, position: tuple[int, int]) -> bool:
        if self.arrived and self.rect.collidepoint(position):
            self.open = not self.open
            return True
        return False

    def draw(self, surface: pygame.Surface, now: int) -> None:
        bob = round(math.sin(now * 0.006) * 2)
        frame_index = (now // MERCHANT_FRAME_DURATION_MS) % len(self.animation_frames)
        frame = self.animation_frames[frame_index]
        frame_rect = frame.get_rect(center=(self.rect.centerx, self.rect.centery + bob))
        surface.blit(frame, frame_rect)
