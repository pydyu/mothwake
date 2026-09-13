from pathlib import Path

import pygame

from settings import (
    FLOOR_COLOR,
    STONE_COLOR,
    TILE_SIZE,
)


SPIKE_PATH = Path(__file__).resolve().parent / "assets" / "background" / "spike.png"
CAVE_BACKGROUND_PATH = Path(__file__).resolve().parent / "assets" / "background" / "image (4).png"
FLOOR_PATHS = tuple(
    Path(__file__).resolve().parent
    / "assets"
    / "background"
    / f"{index:02d}_pixilart-sprite (19).png"
    for index in range(3)
)
GREEN_PLATFORM_PATHS = (
    Path(__file__).resolve().parent / "assets" / "background" / "platform2.png",
    Path(__file__).resolve().parent / "assets" / "background" / "platform2(2).png",
    Path(__file__).resolve().parent / "assets" / "background" / "platform2(3).png",
)
SPIKE_RENDER_HEIGHT = TILE_SIZE + TILE_SIZE // 2


class Level:
    def __init__(self, grid: list[str], use_green_terrain: bool | None = None) -> None:
        self.grid = grid
        self.stone_rects: list[pygame.Rect] = []
        self.floor_tiles: list[tuple[pygame.Rect, int]] = []
        self.floor_fill_rects: list[pygame.Rect] = []
        self.platform_rects: list[pygame.Rect] = []
        self.hazard_rects: list[pygame.Rect] = []
        self.bee_positions: list[tuple[int, int]] = []
        self.bee_spawns: list[tuple[tuple[int, int], bool]] = []
        self.queen_spawns: list[tuple[int, int]] = []
        self.cricket_spawns: list[tuple[int, int]] = []
        self.fire_ant_spawns: list[tuple[int, int]] = []
        self.hornet_spawns: list[tuple[int, int]] = []
        self.merchant_spawn_point: tuple[int, int] | None = None
        self.exit_rect: pygame.Rect | None = None
        self.player_spawn = (TILE_SIZE, TILE_SIZE)
        level_size = (len(grid[0]) * TILE_SIZE, len(grid) * TILE_SIZE)
        self.background = self._load_cover_image(CAVE_BACKGROUND_PATH, level_size)
        spike_source = pygame.image.load(str(SPIKE_PATH)).convert_alpha()
        visible_bounds = spike_source.get_bounding_rect()
        if not visible_bounds.width or not visible_bounds.height:
            raise ValueError(f"Spike image has no visible pixels: {SPIKE_PATH}")
        self.spike_source = spike_source.subsurface(visible_bounds).copy()
        self.spike_images: dict[tuple[int, int], pygame.Surface] = {}
        self.floor_images = [self._load_floor_image(path) for path in FLOOR_PATHS]
        self.green_platform_images = [self._load_floor_image(path) for path in GREEN_PLATFORM_PATHS]
        self._parse_grid()
        if use_green_terrain is None:
            use_green_terrain = bool(
                self.cricket_spawns or self.fire_ant_spawns or self.merchant_spawn_point
            )
        self.platform_images = self.green_platform_images if use_green_terrain else self.floor_images
        self._find_floor_foundation()
        self.hazard_sections = self._merge_hazard_sections()

        if not self.bee_spawns and not self.queen_spawns and not self.cricket_spawns and not self.fire_ant_spawns and not self.hornet_spawns and self.merchant_spawn_point is None:
            raise ValueError("Level must contain an enemy or merchant room marker")

    @property
    def solids(self) -> list[pygame.Rect]:
        return self.stone_rects + self.platform_rects

    def _parse_grid(self) -> None:
        spawn_found = False
        for row_index, row in enumerate(self.grid):
            for column_index, tile in enumerate(row):
                x = column_index * TILE_SIZE
                y = row_index * TILE_SIZE
                tile_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

                if tile == "#":
                    self.stone_rects.append(tile_rect)
                    # Only exposed stone beneath open space is floor. This
                    # deliberately excludes platforms and vertical walls.
                    above = self.grid[row_index - 1][column_index] if row_index else "#"
                    if above != "#":
                        self.floor_tiles.append((tile_rect, column_index % len(self.floor_images)))
                elif tile == "-":
                    self.platform_rects.append(tile_rect)
                elif tile == "=":
                    thin_height = TILE_SIZE * 5 // 8
                    self.platform_rects.append(
                        pygame.Rect(x, y + TILE_SIZE - thin_height, TILE_SIZE, thin_height)
                    )
                elif tile == "_":
                    # The large cave spikes occupy much more than their thin
                    # base strip, so their collision reaches visibly upward.
                    height = max(18, TILE_SIZE * 5 // 8)
                    self.hazard_rects.append(
                        pygame.Rect(x, y + TILE_SIZE - height, TILE_SIZE, height)
                    )
                elif tile == "P":
                    if spawn_found:
                        raise ValueError("A level may contain only one player spawn (P)")
                    self.player_spawn = (x + TILE_SIZE // 2, y + TILE_SIZE)
                    spawn_found = True
                elif tile == "B":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.bee_positions.append(position)
                    self.bee_spawns.append((position, False))
                elif tile == "M":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.bee_positions.append(position)
                    self.bee_spawns.append((position, True))
                elif tile == "Q":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.bee_positions.append(position)
                    self.queen_spawns.append(position)
                elif tile == "C":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.cricket_spawns.append(position)
                elif tile == "A":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.fire_ant_spawns.append(position)
                elif tile == "H":
                    position = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.hornet_spawns.append(position)
                elif tile == "R":
                    self.merchant_spawn_point = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                elif tile == "E":
                    if self.exit_rect is not None:
                        raise ValueError("A level may contain only one exit (E)")
                    self.exit_rect = tile_rect
                elif tile != " ":
                    raise ValueError(f"Unknown level tile {tile!r} at row {row_index}")

        if not spawn_found:
            raise ValueError("Level must contain a player spawn (P)")
        if self.exit_rect is None:
            raise ValueError("Level must contain an exit (E)")

    def touches_hazard(self, player_rect: pygame.Rect) -> bool:
        return player_rect.collidelist(self.hazard_rects) != -1

    def touches_exit(self, player_rect: pygame.Rect) -> bool:
        return self.exit_rect is not None and self.exit_rect.colliderect(player_rect)

    def draw_exit(self, surface: pygame.Surface, unlocked: bool) -> None:
        if self.exit_rect is None:
            return
        color = (229, 191, 72) if unlocked else (76, 70, 82)
        doorway = self.exit_rect.inflate(-18, -4)
        pygame.draw.rect(surface, color, doorway, 3, border_radius=5)
        if unlocked:
            pygame.draw.circle(surface, color, (doorway.right - 7, doorway.centery), 2)

    def _find_floor_foundation(self) -> None:
        floor_columns = {
            rect.x // TILE_SIZE: rect.y // TILE_SIZE
            for rect, _ in self.floor_tiles
        }
        self.floor_fill_rects = [
            rect
            for rect in self.stone_rects
            if rect.x // TILE_SIZE in floor_columns
            and rect.y // TILE_SIZE >= floor_columns[rect.x // TILE_SIZE]
        ]

    @staticmethod
    def _load_floor_image(path: Path) -> pygame.Surface:
        source = pygame.image.load(str(path)).convert_alpha()
        visible_bounds = source.get_bounding_rect()
        if not visible_bounds.width or not visible_bounds.height:
            raise ValueError(f"Floor image has no visible pixels: {path}")
        strip = source.subsurface(visible_bounds).copy()
        # Enlarge the strip to a full tile in height while preserving its
        # proportions. Drawing crops from this wide surface avoids squashing
        # the brick artwork into a square.
        width = round(TILE_SIZE * strip.get_width() / strip.get_height())
        return pygame.transform.scale(strip, (width, TILE_SIZE))

    @staticmethod
    def _load_cover_image(path: Path, size: tuple[int, int]) -> pygame.Surface:
        source = pygame.image.load(str(path)).convert()
        scale = max(size[0] / source.get_width(), size[1] / source.get_height())
        scaled_size = (
            round(source.get_width() * scale),
            round(source.get_height() * scale),
        )
        scaled = pygame.transform.scale(source, scaled_size)
        crop = scaled.get_rect(center=(scaled_size[0] // 2, scaled_size[1] // 2))
        crop.size = size
        crop.center = scaled.get_rect().center
        return scaled.subsurface(crop).copy()

    def _merge_hazard_sections(self) -> list[pygame.Rect]:
        sections: list[pygame.Rect] = []
        for hazard in sorted(self.hazard_rects, key=lambda rect: (rect.y, rect.x)):
            if sections and hazard.y == sections[-1].y and hazard.left == sections[-1].right:
                sections[-1].width += hazard.width
            else:
                sections.append(hazard.copy())
        return sections

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.background, (0, 0))
        for rect in self.stone_rects:
            pygame.draw.rect(surface, STONE_COLOR, rect)
        for rect in self.floor_fill_rects:
            pygame.draw.rect(surface, FLOOR_COLOR, rect)
        for rect, variant in self.floor_tiles:
            terrain_variant = (rect.x // TILE_SIZE) % len(self.platform_images)
            self._draw_brick_tile(surface, rect, terrain_variant, self.platform_images)
        for rect in self.platform_rects:
            pygame.draw.rect(surface, FLOOR_COLOR, rect)
            variant = (rect.x // TILE_SIZE) % len(self.platform_images)
            self._draw_brick_tile(surface, rect, variant, self.platform_images)
        for rect in self.hazard_sections:
            size = (rect.width, SPIKE_RENDER_HEIGHT)
            if size not in self.spike_images:
                self.spike_images[size] = pygame.transform.scale(self.spike_source, size)
            spike_rect = self.spike_images[size].get_rect(midbottom=rect.midbottom)
            surface.blit(self.spike_images[size], spike_rect)

    def _draw_brick_tile(
        self,
        surface: pygame.Surface,
        rect: pygame.Rect,
        variant: int,
        images: list[pygame.Surface] | None = None,
    ) -> None:
        brick_image = (images or self.floor_images)[variant]
        available_width = brick_image.get_width() - TILE_SIZE
        source_x = (rect.x // TILE_SIZE * TILE_SIZE) % (available_width + 1)
        source = pygame.Rect(source_x, 0, TILE_SIZE, TILE_SIZE)
        tile_image = brick_image.subsurface(source)
        if rect.size != (TILE_SIZE, TILE_SIZE):
            tile_image = pygame.transform.scale(tile_image, rect.size)
        surface.blit(tile_image, rect.topleft)
