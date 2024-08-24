#!/usr/bin/env python3

# standards
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import exp, hypot
from typing import Iterable, List, Tuple  # NB we use `List` and `Tuple` for compat with older Pythons

# 3rd parties
from haversine import Direction, inverse_haversine
import mercantile
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# this project
from .colors import compile_color_spectrum
from .datastructures import Config, DataPoint, LatLngBox


@dataclass(frozen=True)
class Geometry:
    """
    This internal data structure holds the pixel dimension, pixel coordinates and tile coordinates of the area we want to
    render.
    """

    top_left_tile: NDArray[np.int_]
    top_left_pixel: NDArray[np.int_]
    bottom_right_tile: NDArray[np.int_]
    bottom_right_pixel: NDArray[np.int_]
    pixel_size: Tuple[int, int]

    @classmethod
    def compile(
        cls,
        box: LatLngBox,
        zoom: int,
        stretch_to_full_tiles: bool = True,
    ) -> "Geometry":
        # Find the pixel coordinates of the given box.
        if stretch_to_full_tiles:
            # We stretch the box a little so that the pixels are at the (0,0) top-left corner of their respective tiles, i.e. we
            # don't have tiles with blank space in them at the margins of the canvas. This makes the pixel math a little easier
            # when painting the tiles.
            top_left_tile = np.array(mercantile.tile(box.west, box.north, zoom)[:2])
            top_left_pixel = top_left_tile * 256
            bottom_right_tile = np.array(mercantile.tile(box.east, box.south, zoom)[:2]) + 1
            bottom_right_pixel = bottom_right_tile * 256
        else:
            top_left_pixel = np.array(mercantile.tile(box.west, box.north, zoom + 8)[:2])
            top_left_tile = top_left_pixel / 256  # type: ignore
            bottom_right_pixel = np.array(mercantile.tile(box.east, box.south, zoom + 8)[:2])
            bottom_right_tile = bottom_right_pixel / 256 + 1  # type: ignore
            bottom_right_pixel += 1
        return cls(
            top_left_tile,
            top_left_pixel,
            bottom_right_tile,
            bottom_right_pixel,
            pixel_size=(
                bottom_right_pixel[0] - top_left_pixel[0],
                bottom_right_pixel[1] - top_left_pixel[1],
            ),
        )


def compute_surface_matrix(
    config: Config,
    box: LatLngBox,
    zoom: int,
    data_points: List[DataPoint],
    geom: Geometry,
) -> NDArray:
    """
    Core internal function for this whole package. Creates a numpy array whose elements correspond to invidual pixels in the
    output image, and whose values map directly to the colours of the rendered heatmap (the particulars depend on the Config, but
    e.g. high values here will become red in the output).

    The returned array has shape (w, h), where w and h are the width and height of the computed image, in pixels. If you're e.g.
    rendering a heatmap for a whole city, this will be one big image that covers the whole city.
    """

    surface = np.zeros(geom.pixel_size)

    # `pixel_base` is the top-left corner of the image. We use it to map absolute Mercator pixels, which identify a pixel with a
    # mercator image of the whole world, to coordinates within our surface matrix, which is just a small subset of that image
    pixel_base = np.array(geom.top_left_pixel[:2])

    for point in data_points:
        radius_pixels = _metres_to_pixels(box, zoom, point.radius_metres or config.default_radius_metres)
        kernel = _create_kernel(radius_pixels) * point.weight

        (lat, lng) = point.latlng
        (x, y) = np.array(mercantile.tile(lng, lat, zoom + 8)[:2]) - pixel_base - radius_pixels

        # trim the kernel if it overflows the edges of the surface matrix
        stamp = kernel
        if x < 0:
            stamp = stamp[-x:, :]
            x = 0
        elif x + (2 * radius_pixels) > surface.shape[0]:
            stamp = stamp[: (surface.shape[0] - x - (2 * radius_pixels)), :]
        if y < 0:
            stamp = stamp[:, -y:]
            y = 0
        elif y + (2 * radius_pixels) >= surface.shape[1]:
            stamp = stamp[:, : (surface.shape[1] - y - (2 * radius_pixels))]

        # stamp it
        surface[x : x + stamp.shape[0], y : y + stamp.shape[1]] += stamp

    # Taking the log a bunch of times accentuates the hotter areas. Otherwise you get a map that is all green, except for a few
    # reddish spots.
    for _ in range(config.num_loggings):
        surface = np.log(surface + 1)

    # Normalise the surface to values between 0 and 1. The lowest value on the surface becomes 0, the highest peak becomes 1.
    surface = (surface - np.amin(surface)) / np.amax(surface)

    # The "high trim" makes the red stand out more in the hottest areas
    surface[surface > config.high_trim] = config.high_trim
    surface /= config.high_trim

    return surface


@lru_cache
def _metres_to_pixels(box: LatLngBox, zoom: int, metres: int) -> int:
    # We convert the kernel radius to pixels. Because we use a Mercator projection, a given radius in metres will have
    # different lengths in pixels depending on the latitude we're at. We use the middle of the box as our reference point. For
    # a box the size of a city this will have no discernible impact. If the box had the size of a large country or even bigger,
    # it would start to be a problem, but this little script is going to have other problems before then (memory consumption,
    # for one).
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


@lru_cache
def _create_kernel(radius_in_pixels: int) -> NDArray:
    """
    Create a "kernel", a small matrix of dimension 2r * 2r. The centre has high values, and they taper off towards the edges.
    We'll then add that kernel to the surface matrix at every location in the dataset.
    """
    r2 = 2 * radius_in_pixels
    kernel = np.zeros([r2, r2])
    # The Gaussian we use (stdev=1) becomes zero-ish around 5, so this constant should be at least that
    gaussian_range = radius_in_pixels / 5
    for x, y in product(range(r2), repeat=2):
        dist = hypot(x - radius_in_pixels, y - radius_in_pixels)
        if dist < radius_in_pixels:
            v = dist / gaussian_range
            kernel[x, y] = exp(-0.5 * v * v)
    return kernel


def paint_image(config: Config, surface: NDArray) -> Image.Image:
    """
    Turns the surface array, which is just an array of numeric values indicating itensity at each pixel, into an image.
    """
    num_colors = config.num_colors
    color_spectrum = list(compile_color_spectrum(config.gradient, num_colors))
    all_values = np.sort(surface[surface > 0], axis=None)
    num_values = len(all_values)
    image = Image.new("RGBA", surface.shape)  # type: ignore
    pixels = image.load()  # type: ignore
    for pt, v in np.ndenumerate(surface):
        vi = bisect_left(all_values, v) / num_values  # type: ignore
        pixels[pt] = color_spectrum[int(vi * num_colors)]
    return image


def _split_into_tiles(geom: Geometry, image: Image.Image) -> Iterable[Tuple[int, int, Image.Image]]:
    # i and j are tile indexes within our canvas, so the top left tile has (i,j) == (0,0)
    # x and y are mercator tile numbers
    for (i, x), (j, y) in product(
        enumerate(range(geom.top_left_tile[0], geom.bottom_right_tile[0])),
        enumerate(range(geom.top_left_tile[1], geom.bottom_right_tile[1])),
    ):
        tile_img = image.crop(
            (
                i * 256,
                j * 256,
                (i + 1) * 256,
                (j + 1) * 256,
            )
        )
        yield x, y, tile_img


def render_heatmap_to_tiles(
    config: Config,
    box: LatLngBox,
    zoom: int,
    data_points: List[DataPoint],
) -> Iterable[Tuple[int, int, Image.Image]]:
    """
    Renders a heatmap for the given data points, at the given zoom level and with the given config, into a set of Web Mercator
    image tiles that cover the entirety of the given box. Returns a sequence of `(x, y, image)` tuples, where `x` and `y` are
    integers representing the coordinates of the tile (the coordinates that normally go in the tile URL), and `image` is a
    `Pillow.Image` that the caller can `.save()` into a file.
    """
    geom = Geometry.compile(box, zoom, stretch_to_full_tiles=True)
    surface = compute_surface_matrix(config, box, zoom, data_points, geom)
    image = paint_image(config, surface)
    return _split_into_tiles(geom, image)


def render_heatmap_to_image(
    config: Config,
    box: LatLngBox,
    zoom: int,
    data_points: List[DataPoint],
) -> Image.Image:
    """
    Renders a heatmap for the given data points, at the given zoom level and with the given config, into a single large image
    that covers the entirety of the given box.
    """
    geom = Geometry.compile(box, zoom, stretch_to_full_tiles=False)
    surface = compute_surface_matrix(config, box, zoom, data_points, geom)
    image = paint_image(config, surface)
    return image
