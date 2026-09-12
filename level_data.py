"""manually editable level grids.

legend:
    # stone wall/floor (solid)
    - platform (solid for now)
    _ 1 (thin, non-solid placeholder)
    P player spawn
    B stationary bee placeholder
    M moving bee placeholder
    Q queen bee boss placeholder
    C cricket puzzle enemy
    E level exit
      empty space

Levels 1-5 currently cover bee encounters, the Queen Bee checkpoint boss,
and the non-lethal cricket timing puzzle.
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
    "# P               E#",
    "##########   #######",
    "##########___#######",
    "####################",
]

LEVEL_2 = [
    "####################",
    "#                  #",
    "#              M   #",
    "#                  #",
    "#        ----      #",
    "#                  #",
    "#   B              #",
    "#  ----            #",
    "# P               E#",
    "########   #########",
    "########___#########",
    "####################",
]

LEVEL_3 = [
    "####################",
    "#                  #",
    "#         M        #",
    "#       ----       #",
    "#                  #",
    "#   M          B   #",
    "#  ----      ----  #",
    "#                  #",
    "# P               E#",
    "######   ####   ####",
    "######___####___####",
    "####################",
]

LEVEL_4 = [
    "####################",
    "#                  #",
    "#                  #",
    "#         Q        #",
    "#       ------     #",
    "#                  #",
    "#    ----  ----    #",
    "#                  #",
    "# P               E#",
    "#######      #######",
    "#######______#######",
    "####################",
]

LEVEL_5 = [
    "####################",
    "#                  #",
    "#                  #",
    "#    C        C    #",
    "#   ----    ----   #",
    "#                  #",
    "#       ----       #",
    "#  ----      ----  #",
    "# P               E#",
    "######        ######",
    "######________######",
    "####################",
]

LEVEL_6 = [
    "####################",
    "#                  #",
    "#  C    C    C     #",
    "# ---  ---  ---    #",
    "#                  #",
    "#    ---  ---      #",
    "#                  #",
    "#  ----      ----  #",
    "# P               E#",
    "######        ######",
    "######________######",
    "####################",
]

LEVELS = [
    LEVEL_1,
    LEVEL_2,
    LEVEL_3,
    LEVEL_4,
    LEVEL_5,
    LEVEL_6,
]
