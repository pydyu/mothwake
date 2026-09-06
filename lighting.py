import pygame


# light intensity shared by the player, lanterns, bee, and solar effects.

LIGHT_BRIGHTNESS = 2.0


def light_alpha(alpha: int) -> int:
    brightness = max(0.0, min(1.0, LIGHT_BRIGHTNESS))
    return round(255 - (255 - alpha) * brightness)


class LightingEngine:
    def __init__(self, size: tuple[int, int]) -> None:
        self.darkness = pygame.Surface(size, pygame.SRCALPHA)
        self.player_glow = pygame.Surface(size, pygame.SRCALPHA)

    def draw(self, surface: pygame.Surface, light_position: tuple[int, int], deployed_moths: int = 0, solar_position: tuple[int, int] | None = None, bee_position: tuple[int, int] | None = None, lantern_positions: list[tuple[int, int]] | None = None) -> None:
        self.darkness.fill((3, 2, 10, 226))
        x, y = light_position
        visibility_loss = min(45, deployed_moths * 5)
        for radius, alpha in ((128, 234), (103, 208), (79, 160), (55, 82), (32, 18)):
            pygame.draw.circle(self.darkness, (3, 2, 10, light_alpha(alpha)), (x, y), max(12, radius - visibility_loss))
        # placed lanterns have the same falloff thing of the player
        # only at a smaller radius.
        for lantern_position in lantern_positions or []:
            for radius, alpha in ((48, 238), (38, 205), (28, 145), (17, 52)):
                pygame.draw.circle(
                    self.darkness,
                    (3, 2, 10, light_alpha(alpha)),
                    lantern_position,
                    radius,
                )
        if solar_position is not None:
            for radius, alpha in ((135, 190), (90, 100), (48, 20)):
                pygame.draw.circle(self.darkness, (3, 2, 10, light_alpha(alpha)), solar_position, radius)
        if bee_position is not None:
            for radius, alpha in ((62, 198), (40, 125), (22, 42)):
                pygame.draw.circle(self.darkness, (8, 5, 8, light_alpha(alpha)), bee_position, radius)
        surface.blit(self.darkness, (0, 0))

        #  golden tint inside the player's lantern light.
        self.player_glow.fill((0, 0, 0, 0))
        for radius, color in (
            (80, (20, 16, 6, 0)),
            (55, (26, 20, 7, 0)),
            (30, (32, 25, 8, 0)),
        ):
            pygame.draw.circle(self.player_glow, color, (x, y), radius)
        surface.blit(self.player_glow, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
