#!/usr/bin/env python3

# standards
import re
from typing import Iterable, NamedTuple


class LatLng(NamedTuple):
    lat: float
    lng: float

    def __str__(self) -> str:
        return '%.05f,%.05f' % self

    @classmethod
    def from_str(cls, latlng_str: str) -> 'LatLng':
        return cls(*map(float, re.split(r'\s*,\s*', latlng_str)))



class LatLngBox(NamedTuple):
    south: float
    west: float
    north: float
    east: float

    @classmethod
    def bounding(cls, latlngs: Iterable[LatLng]) -> 'LatLngBox':
        return cls(
            south=min(ll.lat for ll in latlngs),
            west=min(ll.lng for ll in latlngs),
            north=max(ll.lat for ll in latlngs),
            east=max(ll.lng for ll in latlngs),
        )
