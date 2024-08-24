#!/usr/bin/env python3

# standards
import re
from typing import Iterable, List, NamedTuple, Optional

# this project
from .colors import Gradient


# About the use of NamedTuple - in general we'd use dataclass rather than NamedTuple, but it's a minor convenience in a few places
# to have e.g. a latlng object actually be a tuple of its coordinates, we can then pass it through to libraries that expect a (lat,
# lng) tuple without conversion.


class LatLng(NamedTuple):
    """
    A latitude/longitude coordinate pair.
    """

    lat: float
    lng: float

    def __str__(self) -> str:
        return "%.05f,%.05f" % self

    @classmethod
    def from_str(cls, latlng_str: str) -> "LatLng":
        return cls(*map(float, re.split(r"\s*,\s*", latlng_str)))


class LatLngBox(NamedTuple):
    """
    A rectangular box defined in latitude and longitude. We live in a Web Mercator world, so this will be rendered as a
    rectangular box on screen.
    """

    south: float
    west: float
    north: float
    east: float

    @classmethod
    def bounding(cls, latlngs: Iterable[LatLng]) -> "LatLngBox":
        return cls(
            south=min(ll.lat for ll in latlngs),
            west=min(ll.lng for ll in latlngs),
            north=max(ll.lat for ll in latlngs),
            east=max(ll.lng for ll in latlngs),
        )


class DataPoint(NamedTuple):
    """
    One data point to be represented on the heatmap.
    """

    latlng: LatLng
    weight: float = 1
    radius_metres: Optional[int] = None


class Config(NamedTuple):
    """
    User-configurable parameters to the rendering algorithm, allowing the caller to tweak the output.

    The web-based configurator in `volute.configurator` lets you change the values here and see the output in real time.
    """

    gradient: Gradient = Gradient.GREEN_TO_RED
    default_radius_metres: int = 750
    num_colors: int = 200
    high_trim: float = 0.99
    num_loggings: int = 10

    @classmethod
    def json_definition(cls) -> List[dict]:
        all_items = []
        for field in cls._fields:
            field_type = cls.__annotations__[field]
            default_value = cls._field_defaults[field]  # it exists, pylint: disable=no-member
            if field_type is Gradient:
                options = [key for key in dir(Gradient) if re.search(r"^[A-Z][A-Z_]+$", key)]  # ugly but works
                item = {
                    "id": field,
                    "type": "select",
                    "options": options,
                    "defaultValue": next(key for key in options if getattr(Gradient, key) == default_value),
                }
            else:
                item = {
                    "id": field,
                    "type": field_type.__name__,
                    "defaultValue": default_value,
                }
            all_items.append(item)
        return all_items

    @classmethod
    def from_string_args(cls, args: dict[str, str]) -> "Config":
        values: dict[str, object] = {}
        for field in cls._fields:
            if field not in args:
                continue  # and fall back to the default
            field_type = cls.__annotations__[field]
            str_value = args[field]
            if field_type is Gradient:
                values[field] = getattr(Gradient, str_value)
            else:
                values[field] = field_type(str_value)
        return Config(**values)  # type: ignore
