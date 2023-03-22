#!/usr/bin/env python3

# standards
from typing import List, Tuple

# 3rd parties
from haversine import Direction, inverse_haversine
import mercantile
import numpy as np
from numpy.typing import NDArray

# coulis
from .colors import Gradient, RgbaColor, compile_color_spectrum
from .datastructures import LatLngBox


class Config:

    color_spectrum: List[RgbaColor]
    box: LatLngBox
    kernel_radius_in_pixels: int
    zoom: int

    top_left_tile: NDArray[np.int_]
    top_left_pixel: NDArray[np.int_]
    bottom_right_tile: NDArray[np.int_]
    bottom_right_pixel: NDArray[np.int_]
    pixel_size: Tuple[int, int]

    def __init__(
        self,
        box: LatLngBox,
        zoom: int,
        kernel_radius_metres: int,
        gradient: Gradient = Gradient.GREEN_TO_RED,
        num_colors: int = 200,
        stretch_to_full_tiles: bool = True,
    ):
        self.color_spectrum = list(compile_color_spectrum(gradient, num_colors))
        self.box = box
        self.zoom = zoom

        self.kernel_radius_in_pixels = self._metres_to_pixels(box, kernel_radius_metres, zoom)

        # Find the pixel coordinates of the given box.
        if stretch_to_full_tiles:
            # We stretch the box a little so that the pixels are at the (0,0) top-left corner of their respective tiles, i.e. we
            # don't have tiles with blank space in them at the margins of the canvas. This makes the pixel math a little easier
            # when painting the tiles.
            self.top_left_tile = np.array(mercantile.tile(box.west, box.north, zoom)[:2])
            self.top_left_pixel = self.top_left_tile * 256
            self.bottom_right_tile = np.array(mercantile.tile(box.east, box.south, zoom)[:2]) + 1
            self.bottom_right_pixel = self.bottom_right_tile * 256
        else:
            self.top_left_pixel = np.array(mercantile.tile(box.west, box.north, zoom + 8)[:2])
            self.top_left_tile = self.top_left_pixel / 256  # type: ignore
            self.bottom_right_pixel = np.array(mercantile.tile(box.east, box.south, zoom + 8)[:2])
            self.bottom_right_tile = self.bottom_right_pixel / 256 + 1  # type: ignore
            self.bottom_right_pixel += 1

        self.pixel_size = (
            self.bottom_right_pixel[0] - self.top_left_pixel[0],
            self.bottom_right_pixel[1] - self.top_left_pixel[1],
        )

    @staticmethod
    def _metres_to_pixels(box: LatLngBox, metres: int, zoom: int) -> int:
        # We convert the kernel radius to pixels. Because we use a Mercator projection, this will give different values at
        # different latitudes. We use the middle of the box. For a box the size of a city this will have no discernible impact.
        # If the box had the size of a large country or bigger, it would start to be a problem, but this little script is going to
        # have other problems before then (memory consumption, for one).
        lng1 = (box.east + box.west) / 2
        lat1 = (box.north + box.south) / 2
        lat2, lng2 = inverse_haversine(
            (lat1, lng1),
            metres / 1000,
            Direction.EAST,
        )
        # Pixel coordinates are at zoom+8, because our tiles are 2**8 pixels square, and since every zoom level doubles the pixel
        # size of the world, our pixels live in a world 8 zoom levels deeper than the tiles.
        pt1 = mercantile.tile(lng1, lat1, zoom + 8)
        pt2 = mercantile.tile(lng2, lat2, zoom + 8)
        return pt2.x - pt1.x
