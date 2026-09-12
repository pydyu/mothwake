import pygame


# Light intensity shared by the player, lanterns, bee, and solar effects.
# Valid range: 0.0 (off) to 7.0 (maximum brightness).
LIGHT_BRIGHTNESS = 4.0
MAX_LIGHT_BRIGHTNESS = 7.0


def light_alpha(alpha: int) -> int:
    brightness = max(0.0, min(MAX_LIGHT_BRIGHTNESS, LIGHT_BRIGHTNESS))
    revealed_light = min(255, (255 - alpha) * brightness)
    return round(255 - revealed_light)


def draw_soft_light(
    target: pygame.Surface,
    position: tuple[int, int],
    radius: int,
    outer_alpha: int = 242,
    inner_alpha: int = 24,
    color: tuple[int, int, int] = (3, 2, 10),
) -> None:
    # Many narrow rings create a gradual falloff instead of visible flat bands.
    steps = max(12, radius // 4)
    for step in range(steps):
        progress = step / (steps - 1)
        ring_radius = max(2, round(radius * (1.0 - progress)))
        alpha = round(outer_alpha + (inner_alpha - outer_alpha) * progress)
        pygame.draw.circle(target, (*color, light_alpha(alpha)), position, ring_radius)


class LightingEngine:
    def __init__(self, size: tuple[int, int]) -> None:
        self.darkness = pygame.Surface(size, pygame.SRCALPHA)

    def draw(self, surface: pygame.Surface, light_position: tuple[int, int], deployed_moths: int = 0, solar_position: tuple[int, int] | None = None, bee_positions: list[tuple[int, int]] | None = None, lantern_positions: list[tuple[int, int]] | None = None) -> None:
        self.darkness.fill((3, 2, 10, 226))
        x, y = light_position
        visibility_loss = min(45, deployed_moths * 5)
        draw_soft_light(self.darkness, (x, y), max(40, 128 - visibility_loss), 240, 24)
        # placed lanterns have the same falloff thing of the player
        # only at a smaller radius.
        for lantern_position in lantern_positions or []:
            draw_soft_light(self.darkness, lantern_position, 48, 242, 52)
        if solar_position is not None:
            draw_soft_light(self.darkness, solar_position, 135, 210, 20)
        for bee_position in bee_positions or []:
            draw_soft_light(self.darkness, bee_position, 55, 224, 72)
        surface.blit(self.darkness, (0, 0))
