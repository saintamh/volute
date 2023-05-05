#!/usr/bin/env python3

# standards
from io import BytesIO
from typing import List, Tuple

# 3rd parties
import matplotlib.pyplot as plt
import numpy as np
from numpy.typing import NDArray
from PIL import Image

# coulis
from coulis.datastructures import Config, DataPoint, LatLngBox
from coulis.render import Geometry, compute_surface_matrix


def paint_histogram(surface: NDArray) -> Image.Image:
    counts, bins = np.histogram(surface, bins=25)

    plt.clf()  # "clear figure"
    plt.stairs(counts, bins, fill=True)
    fig = plt.gcf()  # "get current figure"

    buf = BytesIO()
    fig.savefig(buf)
    buf.seek(0)
    return Image.open(buf)


def render_histogram(
    config: Config,
    box: LatLngBox,
    zoom: int,
    data_points: List[DataPoint],
    image_size: Tuple[int, int] = (300, 150),
) -> Image.Image:
    geom = Geometry.compile(box, zoom, stretch_to_full_tiles=False)
    surface = compute_surface_matrix(config, box, zoom, data_points, geom)
    return paint_histogram(surface).resize(image_size)
