# The 13 pieces in a 4x4x4 cube

## Pieces

**A - 01-red** (5 cubes) - L pentomino  
confidence of the reading: high

```
z=0
##
#.
#.
#.
```

**B - 02-red** (4 cubes) - S tetromino - the four-cube piece  
confidence of the reading: high

```
z=0
#.
##
.#
```

**C - 03-red** (5 cubes) - W pentomino  
confidence of the reading: medium

```
z=0
#..
##.
.##
```

**D - 04-red** (5 cubes) - 3-bar, one cube beside one end, one cube on top of that end  
confidence of the reading: medium-high

```
z=0   z=1
##   #.
#.   ..
#.   ..
```

**E - 05-green** (5 cubes) - Y pentomino  
confidence of the reading: medium-high

```
z=0
#.
##
#.
#.
```

**F - 06-green** (5 cubes) - N pentomino  
confidence of the reading: medium

```
z=0
#.
#.
##
.#
```

**G - 07-green** (5 cubes) - S tetromino base with one cube on top of an inner cell  
confidence of the reading: medium

```
z=0   z=1
#.   ..
##   #.
.#   ..
```

**H - 08-blue** (5 cubes) - X pentomino (plus)  
confidence of the reading: high

```
z=0
.#.
###
.#.
```

**I - 09-blue** (5 cubes) - U pentomino  
confidence of the reading: high

```
z=0
##
#.
##
```

**J - 10-blue** (5 cubes) - Z/S pentomino  
confidence of the reading: medium

```
z=0
#..
###
..#
```

**K - 11-yellow** (5 cubes) - P pentomino (resting on edge in the photos)  
confidence of the reading: medium-high

```
z=0
##
##
#.
```

**L - 12-yellow** (5 cubes) - V pentomino  
confidence of the reading: medium

```
z=0
###
#..
#..
```

**M - 13-yellow** (5 cubes) - L tetromino base with one cube on top of the far end  
confidence of the reading: forced by the packing

```
z=0   z=1
#.   #.
#.   ..
##   ..
```

## Packing

Each grid is one layer of the cube, z = 0 (bottom) first; x runs across, y down.

```
    z=0      z=1      z=2      z=3 
    ACDD     ACDG     AMDG     AMMM
    AHDG     BCGG     BCFF     FFFM
    HHHK     LLLK     BCLK     BILI
    EHJJ     EEJK     EJJK     EIII
```

## Cell coordinates

| piece | cubes (x, y, z) |
| --- | --- |
| A 01-red | (0,0,0), (0,0,1), (0,0,2), (0,0,3), (0,1,0) |
| B 02-red | (0,1,1), (0,1,2), (0,2,2), (0,2,3) |
| C 03-red | (1,0,0), (1,0,1), (1,1,1), (1,1,2), (1,2,2) |
| D 04-red | (2,0,0), (2,0,1), (2,0,2), (2,1,0), (3,0,0) |
| E 05-green | (0,3,0), (0,3,1), (0,3,2), (0,3,3), (1,3,1) |
| F 06-green | (0,1,3), (1,1,3), (2,1,2), (2,1,3), (3,1,2) |
| G 07-green | (2,1,1), (3,0,1), (3,0,2), (3,1,0), (3,1,1) |
| H 08-blue | (0,2,0), (1,1,0), (1,2,0), (1,3,0), (2,2,0) |
| I 09-blue | (1,2,3), (1,3,3), (2,3,3), (3,2,3), (3,3,3) |
| J 10-blue | (1,3,2), (2,3,0), (2,3,1), (2,3,2), (3,3,0) |
| K 11-yellow | (3,2,0), (3,2,1), (3,2,2), (3,3,1), (3,3,2) |
| L 12-yellow | (0,2,1), (1,2,1), (2,2,1), (2,2,2), (2,2,3) |
| M 13-yellow | (1,0,2), (1,0,3), (2,0,3), (3,0,3), (3,1,3) |
