from pathlib import Path

import pygame

from settings import (
    GRAVITY,
    JUMP_SPEED,
    MAX_FALL_SPEED,
    PLAYER_HEIGHT,
    PLAYER_SPEED,
    PLAYER_WIDTH,
    PLAYER_SCALE_HEIGHT,
    PLAYER_SCALE_WIDTH
)

PLAYER_ANIMATION_FPS = 10
PLAYER_ASSET_DIR = Path(__file__).resolve().parent / "assets" / "player"


class Player:
    def __init__(self, spawn: tuple[int, int]) -> None:
        self.rect = pygame.Rect(0, 0, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.velocity = pygame.Vector2()
        self.grounded = False
        self.spawn = spawn
        self.health = 100
        self.lives = 3
        self.coins = 0
        self.death_reason = ""
        self.fire_hits = 0
        self.moth_stunned_until = 0
        self.frames_right = [
            pygame.transform.scale(
            pygame.image.load(str(path)).convert_alpha(),
            (PLAYER_SCALE_WIDTH, PLAYER_SCALE_HEIGHT)
            )
            for path in sorted(PLAYER_ASSET_DIR.glob("*.png"))
        ]
        if not self.frames_right:
            raise FileNotFoundError(f"No player sprites found in {PLAYER_ASSET_DIR}")
        self.frames_left = [pygame.transform.flip(frame, True, False) for frame in self.frames_right]
        self.animation_state = "idle"
        self.animation_time = 0.0
        self.facing = 1
        self.respawn(spawn)

    def respawn(self, spawn: tuple[int, int] | None = None) -> None:
        if spawn is not None:
            self.spawn = spawn
        self.rect.midbottom = self.spawn
        self.velocity.update(0, 0)
        self.grounded = False
        self.fire_hits = 0

    def update(
        self,
        dt: float,
        move_direction: int,
        jump_requested: bool,
        solids: list[pygame.Rect],
    ) -> None:
        self.velocity.x = move_direction * PLAYER_SPEED
        if jump_requested and self.grounded:
            self.velocity.y = -JUMP_SPEED
            self.grounded = False

        self._move_horizontal(dt, solids)
        self.velocity.y = min(self.velocity.y + GRAVITY * dt, MAX_FALL_SPEED)
        self._move_vertical(dt, solids)
        self._update_animation_state(move_direction)
        self._update_animation(dt, move_direction)

    def _move_horizontal(self, dt: float, solids: list[pygame.Rect]) -> None:
        self.rect.x += round(self.velocity.x * dt)
        for solid in solids:
            if self.rect.colliderect(solid):
                if self.velocity.x > 0:
                    self.rect.right = solid.left
                elif self.velocity.x < 0:
                    self.rect.left = solid.right

    def _move_vertical(self, dt: float, solids: list[pygame.Rect]) -> None:
        self.grounded = False
        self.rect.y += round(self.velocity.y * dt)
        for solid in solids:
            if self.rect.colliderect(solid):
                if self.velocity.y > 0:
                    self.rect.bottom = solid.top
                    self.velocity.y = 0
                    self.grounded = True
                elif self.velocity.y < 0:
                    self.rect.top = solid.bottom
                    self.velocity.y = 0

        # keep grounded stable when a small movement rounds to zero
        if self.velocity.y >= 0 and self.rect.move(0, 1).collidelist(solids) != -1:
            self.grounded = True
            self.velocity.y = 0

    def _update_animation_state(self, move_direction: int) -> None:
        if not self.grounded:
            self.animation_state = "jump" if self.velocity.y < 0 else "fall"
        elif move_direction:
            self.animation_state = "run"
        else:
            self.animation_state = "idle"

    def _update_animation(self, dt: float, move_direction: int) -> None:
        if move_direction:
            self.facing = move_direction
            self.animation_time += dt
        else:
            self.animation_time = 0.0

    def draw(self, surface: pygame.Surface) -> None:
        frames = self.frames_left if self.facing < 0 else self.frames_right
        frame_index = int(self.animation_time * PLAYER_ANIMATION_FPS) % len(frames)
        frame = frames[frame_index]
        frame_rect = frame.get_rect(midbottom=self.rect.midbottom)
        surface.blit(frame, frame_rect)

    def stun_moths(self, now: int, duration_ms: int = 3000) -> None:
        self.moth_stunned_until = max(self.moth_stunned_until, now + duration_ms)

    def moths_available(self, now: int) -> bool:
        return now >= self.moth_stunned_until

    def moths_paralyzed(self, now: int) -> bool:
        return now < self.moth_stunned_until
