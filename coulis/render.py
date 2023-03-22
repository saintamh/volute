#!/usr/bin/env python3

# standards
from bisect import bisect_left
from itertools import product
from math import exp, hypot
from pathlib import Path
from typing import List

# 3rd parties
import mercantile
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# coulis
from .config import Config
from .datastructures import LatLng


def compute_surface_matrix(
    config: Config,
    latlngs: List[LatLng],
) -> NDArray:
    density = np.zeros(config.pixel_size)
    kernel = _create_kernel(config.kernel_radius_in_pixels)
    r2 = kernel.shape[0]

    # `pixel_base` is the top-left corner of the image. We use it to map absolute Mercator pixels to coordinates within our density
    # matrix. We also add `kernel_radius_in_pixels` to it, so that subtracting it from the absolute Mercator pixel gives us the
    # top-left corner of the kernel, centered on that pixel
    pixel_base = np.array(config.top_left_pixel[:2]) + config.kernel_radius_in_pixels

    for lat, lng in latlngs:
        (x, y) = np.array(mercantile.tile(lng, lat, config.zoom + 8)[:2]) - pixel_base

        # trim the kernel if it overflows the edges of the density matrix
        stamp = kernel
        if x < 0:
            stamp = stamp[-x:, :]
            x = 0
        elif x + r2 > density.shape[0]:
            stamp = stamp[:(density.shape[0] - x - r2), :]
        if y < 0:
            stamp = stamp[:, -y:]
            y = 0
        elif y + r2 >= density.shape[1]:
            stamp = stamp[:, :(density.shape[1] - y - r2)]

        # stamp it
        density[x:x+stamp.shape[0], y:y+stamp.shape[1]] += stamp

    return density


def _create_kernel(radius_in_pixels: int) -> NDArray:
    """
    Create a "kernel", a small matrix of dimension 2r * 2r. The centre has high values, and they taper off towards the edges.
    We'll then add that kernel to the density matrix at every location in the dataset.
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
    # pylint: disable=too-many-locals
    all_values = np.sort(surface[surface>0], axis=None)
    num_colors = len(config.color_spectrum)
    num_values = len(all_values)
    image = Image.new('RGBA', surface.shape)  # type: ignore
    pixels = image.load()  # type: ignore
    for pt, v in np.ndenumerate(surface):
        vi = bisect_left(all_values, v) / num_values  # type: ignore
        pixels[pt] = config.color_spectrum[int(vi * num_colors)]
    return image


def save_tiles(config: Config, output_root: Path, image: Image.Image) -> None:
    # i and j are tile indexes within our canvas, so the top left tile has (i,j) == (0,0)
    # x and y are mercator tile numbers
    for (i, x), (j, y) in product(
        enumerate(range(config.top_left_tile[0], config.bottom_right_tile[0])),
        enumerate(range(config.top_left_tile[1], config.bottom_right_tile[1])),
    ):
        tile_file = output_root / f'{x}' / f'{y}.png'
        tile_img = image.crop((
            i * 256,
            j * 256,
            (i + 1) * 256,
            (j + 1) * 256,
        ))
        tile_file.parent.mkdir(parents=True, exist_ok=True)
        tile_img.save(tile_file)


def render_heatmap(
    config: Config,
    latlngs: List[LatLng],
    output_root: Path,
) -> None:
    surface = compute_surface_matrix(config, latlngs)
    image = paint_image(config, surface)
    save_tiles(config, output_root, image)
