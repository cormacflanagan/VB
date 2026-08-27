# The 13 pieces in a 4x4x4 cube

## Pieces

**A - 01-red** (5 cubes) - L-tetromino base, cube on top of the foot cell  
confidence of the reading: medium - two levels (the raised cube is unmistakable in the low-angle views); top-down fit 0.911, mirror P16 at 0.900

```
z=0   z=1
#..   #..
###   ...
```

**B - 02-red** (5 cubes) - N pentomino  
confidence of the reading: high - flat, 4x2 bounding box, zigzag

```
z=0
#.
#.
##
.#
```

**C - 03-red** (4 cubes) - S tetromino - the four-cube piece  
confidence of the reading: high - flat, 3x2 box, two rows of two

```
z=0
#.
##
.#
```

**D - 04-red** (5 cubes) - L-tetromino base, cube on top of the corner  
confidence of the reading: medium - two levels, L footprint clear in four views

```
z=0   z=1
##   #.
#.   ..
#.   ..
```

**E - 05-green** (5 cubes) - Y pentomino  
confidence of the reading: high - flat, 4x2 box, 4-bar with a bump

```
z=0
#.
##
#.
#.
```

**F - 06-green** (5 cubes) - W pentomino  
confidence of the reading: high - flat, 3x3 box, staircase

```
z=0
#..
##.
.##
```

**G - 07-green** (5 cubes) - S-tetromino base, cube on top of an inner cell  
confidence of the reading: medium - two levels; P23 is the mirror alternative and also packs

```
z=0   z=1
#.   ..
##   #.
..   #.
```

**H - 08-blue** (5 cubes) - X pentomino (plus)  
confidence of the reading: high - flat, 3x3 box

```
z=0
.#.
###
.#.
```

**I - 09-blue** (5 cubes) - F pentomino  
confidence of the reading: high - flat, 3x3 box

```
z=0
#..
###
.#.
```

**J - 10-blue** (5 cubes) - U pentomino  
confidence of the reading: high - flat, 3x2 box

```
z=0
##
#.
##
```

**K - 11-yellow** (5 cubes) - P pentomino  
confidence of the reading: high - flat, 3x2 box

```
z=0
##
##
#.
```

**L - 12-yellow** (5 cubes) - S-tetromino base, cube on top of an end cell  
confidence of the reading: medium - two levels

```
z=0   z=1
#.   #.
..   ##
..   .#
```

**M - 13-yellow** (5 cubes) - L-tetromino base, cube on top of the foot cell (mirror of 01)  
confidence of the reading: medium - two levels

```
z=0   z=1
#.   ##
#.   ..
#.   ..
```

## Packing

Each grid is one layer of the cube, z = 0 (bottom) first; x runs across, y down.

```
    z=0      z=1      z=2      z=3 
    AMMM     AKBM     AKGG     EGGL
    AAJJ     IKBM     EKGL     EKHL
    IDDJ     IDBB     IDLL     EHHH
    IDJJ     CFFB     CCFF     ECHF
```

## Cell coordinates

| piece | cubes (x, y, z) |
| --- | --- |
| A 01-red | (0,0,0), (0,0,1), (0,0,2), (0,1,0), (1,1,0) |
| B 02-red | (2,0,1), (2,1,1), (2,2,1), (3,2,1), (3,3,1) |
| C 03-red | (0,3,1), (0,3,2), (1,3,2), (1,3,3) |
| D 04-red | (1,2,0), (1,2,1), (1,2,2), (1,3,0), (2,2,0) |
| E 05-green | (0,0,3), (0,1,2), (0,1,3), (0,2,3), (0,3,3) |
| F 06-green | (1,3,1), (2,3,1), (2,3,2), (3,3,2), (3,3,3) |
| G 07-green | (1,0,3), (2,0,2), (2,0,3), (2,1,2), (3,0,2) |
| H 08-blue | (1,2,3), (2,1,3), (2,2,3), (2,3,3), (3,2,3) |
| I 09-blue | (0,1,1), (0,2,0), (0,2,1), (0,2,2), (0,3,0) |
| J 10-blue | (2,1,0), (2,3,0), (3,1,0), (3,2,0), (3,3,0) |
| K 11-yellow | (1,0,1), (1,0,2), (1,1,1), (1,1,2), (1,1,3) |
| L 12-yellow | (2,2,2), (3,0,3), (3,1,2), (3,1,3), (3,2,2) |
| M 13-yellow | (1,0,0), (2,0,0), (3,0,0), (3,0,1), (3,1,1) |
