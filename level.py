from pathlib import Path

import pygame

from settings import (
    FLOOR_COLOR,
    PLATFORM_COLOR,
    STONE_COLOR,
    TILE_SIZE,
)


SPIKE_PATH = Path(__file__).resolve().parent / "assets" / "background" / "spike.png"
FLOOR_PATHS = tuple(
    Path(__file__).resolve().parent
    / "assets"
    / "background"
    / f"{index:02d}_pixilart-sprite (19).png"
    for index in range(3)
)
SPIKE_HEIGHT_SCALE = 2


class Level:
    def __init__(self, grid: list[str]) -> None:
        self.grid = grid
        self.stone_rects: list[pygame.Rect] = []
        self.floor_tiles: list[tuple[pygame.Rect, int]] = []
        self.floor_fill_rects: list[pygame.Rect] = []
        self.platform_rects: list[pygame.Rect] = []
        self.hazard_rects: list[pygame.Rect] = []
        self.bee_positions: list[tuple[int, int]] = []
        self.player_spawn = (TILE_SIZE, TILE_SIZE)
        spike_source = pygame.image.load(str(SPIKE_PATH)).convert_alpha()
        visible_bounds = spike_source.get_bounding_rect()
        if not visible_bounds.width or not visible_bounds.height:
            raise ValueError(f"Spike image has no visible pixels: {SPIKE_PATH}")
        self.spike_source = spike_source.subsurface(visible_bounds).copy()
        self.spike_images: dict[tuple[int, int], pygame.Surface] = {}
        self.floor_images = [self._load_floor_image(path) for path in FLOOR_PATHS]
        self._parse_grid()
        self._find_floor_foundation()
        self.hazard_sections = self._merge_hazard_sections()

        if len(self.bee_positions) != 1:
            raise ValueError("Level 1 must contain exactly one stationary bee (B)")

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
                elif tile == "_":
                    height = max(6, TILE_SIZE // 6)
                    self.hazard_rects.append(
                        pygame.Rect(x, y + TILE_SIZE - height, TILE_SIZE, height)
                    )
                elif tile == "P":
                    if spawn_found:
                        raise ValueError("A level may contain only one player spawn (P)")
                    self.player_spawn = (x + TILE_SIZE // 2, y + TILE_SIZE)
                    spawn_found = True
                elif tile == "B":
                    self.bee_positions.append(
                        (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    )
                elif tile != " ":
                    raise ValueError(f"Unknown level tile {tile!r} at row {row_index}")

        if not spawn_found:
            raise ValueError("Level must contain a player spawn (P)")

    def touches_hazard(self, player_rect: pygame.Rect) -> bool:
        return player_rect.collidelist(self.hazard_rects) != -1

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

    def _merge_hazard_sections(self) -> list[pygame.Rect]:
        sections: list[pygame.Rect] = []
        for hazard in sorted(self.hazard_rects, key=lambda rect: (rect.y, rect.x)):
            if sections and hazard.y == sections[-1].y and hazard.left == sections[-1].right:
                sections[-1].width += hazard.width
            else:
                sections.append(hazard.copy())
        return sections

    def draw(self, surface: pygame.Surface) -> None:
        for rect in self.stone_rects:
            pygame.draw.rect(surface, STONE_COLOR, rect)
        for rect in self.floor_fill_rects:
            pygame.draw.rect(surface, FLOOR_COLOR, rect)
        for rect, variant in self.floor_tiles:
            brick_image = self.floor_images[variant]
            available_width = brick_image.get_width() - TILE_SIZE
            source_x = (rect.x // TILE_SIZE * TILE_SIZE) % (available_width + 1)
            source = pygame.Rect(source_x, 0, TILE_SIZE, TILE_SIZE)
            surface.blit(brick_image, rect.topleft, source)
        for rect in self.platform_rects:
            pygame.draw.rect(surface, PLATFORM_COLOR, rect)
        for rect in self.hazard_sections:
            spike_height = max(
                rect.height,
                round(
                    rect.width
                    * self.spike_source.get_height()
                    / self.spike_source.get_width()
                    * SPIKE_HEIGHT_SCALE
                ),
            )
            size = (rect.width, spike_height)
            if size not in self.spike_images:
                self.spike_images[size] = pygame.transform.scale(self.spike_source, size)
            spike_rect = self.spike_images[size].get_rect(midbottom=rect.midbottom)
            surface.blit(self.spike_images[size], spike_rect)
