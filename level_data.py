"""manually editable level grids.

legend:
    # stone wall/floor (solid)
    - platform (solid for now)
    _ hazard (thin, non-solid placeholder)
    P player spawn
    B stationary bee placeholder
      empty space

only level 1 is defined. planned enemy progression for later levels is: bees
(1/2/4), fire ants (5/6/7), queen bee (8), cricket (9), hornet boss (10).
those enemies and levels are intentionally not implemented here.
"""

LEVEL_1 = [
    "####################",
    "#                  #",
    "#                  #",
    "#              B   #",
    "#            ----  #",
    "#                  #",
    "#      ----        #",
    "#                  #",
    "# P                #",
    "##########   #######",
    "##########___#######",
    "####################",
]

LEVELS = [
    LEVEL_1,
]
