# The 13 pieces in a 4x4x4 cube

## Pieces

**A - 01-red** (5 cubes) - L-tetromino base, cube on top of the foot cell  
confidence of the reading: medium - two levels; mirror P16 also packs

```
z=0   z=1
#..   #..
###   ...
```

**B - 02-red** (5 cubes) - N pentomino  
confidence of the reading: high - flat, 4x2 box, zigzag

```
z=0
#.
#.
##
.#
```

**C - 03-red** (4 cubes) - S tetromino - the four-cube piece  
confidence of the reading: high - flat, 3x2 box

```
z=0
#.
##
.#
```

**D - 04-red** (5 cubes) - L-tetromino base, cube on top of the corner  
confidence of the reading: medium - two levels

```
z=0   z=1
##   #.
#.   ..
#.   ..
```

**E - 05-green** (5 cubes) - Y pentomino  
confidence of the reading: high - flat, 4x2 box

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
confidence of the reading: medium - two levels; mirror P23 also packs

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

**M - 13-yellow** (5 cubes) - L-tetromino base, cube on top of the middle of the 3-bar  
confidence of the reading: confirmed by the owner; mirror P7 also packs

```
z=0   z=1
#.   #.
##   ..
#.   ..
```

## Packing

Each grid is one layer of the cube, z = 0 (bottom) first; x runs across, y down.

```
    z=0      z=1      z=2      z=3 
    MMMB     IIMF     AIIF     EILL
    KMHB     DHHH     ALHF     ELLF
    KKBB     DAGC     AACC     EECF
    KKBG     DDGG     DJGJ     EJJJ
```

## Cell coordinates

| piece | cubes (x, y, z) |
| --- | --- |
| A 01-red | (0,0,2), (0,1,2), (0,2,2), (1,2,1), (1,2,2) |
| B 02-red | (2,2,0), (2,3,0), (3,0,0), (3,1,0), (3,2,0) |
| C 03-red | (2,2,2), (2,2,3), (3,2,1), (3,2,2) |
| D 04-red | (0,1,1), (0,2,1), (0,3,1), (0,3,2), (1,3,1) |
| E 05-green | (0,0,3), (0,1,3), (0,2,3), (0,3,3), (1,2,3) |
| F 06-green | (3,0,1), (3,0,2), (3,1,2), (3,1,3), (3,2,3) |
| G 07-green | (2,2,1), (2,3,1), (2,3,2), (3,3,0), (3,3,1) |
| H 08-blue | (1,1,1), (2,1,0), (2,1,1), (2,1,2), (3,1,1) |
| I 09-blue | (0,0,1), (1,0,1), (1,0,2), (1,0,3), (2,0,2) |
| J 10-blue | (1,3,2), (1,3,3), (2,3,3), (3,3,2), (3,3,3) |
| K 11-yellow | (0,1,0), (0,2,0), (0,3,0), (1,2,0), (1,3,0) |
| L 12-yellow | (1,1,2), (1,1,3), (2,0,3), (2,1,3), (3,0,3) |
| M 13-yellow | (0,0,0), (1,0,0), (1,1,0), (2,0,0), (2,0,1) |
