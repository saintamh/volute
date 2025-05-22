#!/usr/bin/env python3

# standards
from colorsys import hsv_to_rgb
from dataclasses import dataclass
from typing import ClassVar, Iterable, Tuple


RgbaColor = Tuple[int, int, int, int]


@dataclass(frozen=True)
class Gradient:
    lowest_hue: float
    highest_hue: float
    lowest_value: float
    highest_value: float

    BLUE_TO_RED: ClassVar["Gradient"]
    GREEN_TO_RED: ClassVar["Gradient"]


Gradient.BLUE_TO_RED = Gradient(
    lowest_hue=2.0 / 3.0,
    highest_hue=0.0,
    lowest_value=0.35,
    highest_value=0.85,
)


Gradient.GREEN_TO_RED = Gradient(
    lowest_hue=1.0 / 3.0,
    highest_hue=0.0,
    lowest_value=0.5,
    highest_value=0.9,
)


def compile_color_spectrum(gradient: Gradient, num_colors: int) -> Iterable[RgbaColor]:
    hue_range = gradient.highest_hue - gradient.lowest_hue
    value_range = gradient.highest_value - gradient.lowest_value

    for i in range(num_colors):
        pos = i / (num_colors - 1)
        red, green, blue = (
            int(c * 255)
            for c in hsv_to_rgb(
                gradient.lowest_hue + pos * hue_range,
                1,
                gradient.lowest_value + pos * value_range,
            )
        )
        yield (red, green, blue, 255)
