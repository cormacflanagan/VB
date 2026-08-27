# The 13 pieces in a 4x4x4 cube

## Pieces

**A - 01-red** (5 cubes) - V pentomino  
confidence of the reading: high - 3x3 bounding box, flat, right-angle bend

```
z=0
###
#..
#..
```

**B - 02-red** (5 cubes) - N pentomino  
confidence of the reading: high - 4x2 bounding box, flat zigzag

```
z=0
#.
#.
##
.#
```

**C - 03-red** (4 cubes) - S tetromino - the four-cube piece  
confidence of the reading: high - 3x2 box, flat, two rows of two

```
z=0
#.
##
.#
```

**D - 04-red** (5 cubes) - L-tetromino base with one cube on the corner  
confidence of the reading: medium - two levels, L footprint clear in four views

```
z=0   z=1
##   #.
#.   ..
#.   ..
```

**E - 05-green** (5 cubes) - Y pentomino  
confidence of the reading: high - 4x2 box, flat, 4-bar with a bump

```
z=0
#.
##
#.
#.
```

**F - 06-green** (5 cubes) - W pentomino  
confidence of the reading: high - 3x3 box, flat staircase

```
z=0
#..
##.
.##
```

**G - 07-green** (5 cubes) - S-tetromino base with one cube on an inner cell  
confidence of the reading: medium - two levels; P25 is the mirror alternative

```
z=0   z=1
#.   ..
##   #.
.#   ..
```

**H - 08-blue** (5 cubes) - X pentomino (plus)  
confidence of the reading: high - 3x3 box, flat plus

```
z=0
.#.
###
.#.
```

**I - 09-blue** (5 cubes) - F pentomino  
confidence of the reading: high - 3x3 box, flat

```
z=0
#..
###
.#.
```

**J - 10-blue** (5 cubes) - U pentomino  
confidence of the reading: high - 3x2 box, flat

```
z=0
##
#.
##
```

**K - 11-yellow** (5 cubes) - P pentomino  
confidence of the reading: high - 3x2 box, flat

```
z=0
##
##
#.
```

**L - 12-yellow** (5 cubes) - S-tetromino base with one cube on an end cell  
confidence of the reading: medium - two levels

```
z=0   z=1
#.   #.
..   ##
..   .#
```

**M - 13-yellow** (5 cubes) - L-tetromino base with one cube on the corner (mirror of 04)  
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
    ABID     ABDD     ABFK     JJJK
    AIII     CHFD     CBFK     JBJK
    AHFI     MHFD     CHGG     CLLK
    MMME     MHEE     LGGE     LLGE
```

## Cell coordinates

| piece | cubes (x, y, z) |
| --- | --- |
| A 01-red | (0,0,0), (0,0,1), (0,0,2), (0,1,0), (0,2,0) |
| B 02-red | (1,0,0), (1,0,1), (1,0,2), (1,1,2), (1,1,3) |
| C 03-red | (0,1,1), (0,1,2), (0,2,2), (0,2,3) |
| D 04-red | (2,0,1), (3,0,0), (3,0,1), (3,1,1), (3,2,1) |
| E 05-green | (2,3,1), (3,3,0), (3,3,1), (3,3,2), (3,3,3) |
| F 06-green | (2,0,2), (2,1,1), (2,1,2), (2,2,0), (2,2,1) |
| G 07-green | (1,3,2), (2,2,2), (2,3,2), (2,3,3), (3,2,2) |
| H 08-blue | (1,1,1), (1,2,0), (1,2,1), (1,2,2), (1,3,1) |
| I 09-blue | (1,1,0), (2,0,0), (2,1,0), (3,1,0), (3,2,0) |
| J 10-blue | (0,0,3), (0,1,3), (1,0,3), (2,0,3), (2,1,3) |
| K 11-yellow | (3,0,2), (3,0,3), (3,1,2), (3,1,3), (3,2,3) |
| L 12-yellow | (0,3,2), (0,3,3), (1,2,3), (1,3,3), (2,2,3) |
| M 13-yellow | (0,2,1), (0,3,0), (0,3,1), (1,3,0), (2,3,0) |
