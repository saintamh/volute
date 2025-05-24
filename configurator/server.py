#!/usr/bin/env python3

# standards
from argparse import ArgumentParser, FileType
import csv
from enum import Enum
from io import BytesIO
from pathlib import Path
import re
from statistics import median
from typing import Iterable, List, TextIO, Tuple

# 3rd parties
from flask import Flask, jsonify, request
from PIL import Image

# volute
from volute.colors import Gradient
from volute.datastructures import Config, DataPoint, LatLng, LatLngBox
from volute.render import render_heatmap_to_image
from .histogram import render_histogram


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("input_file", type=FileType("r", encoding="us-ascii"))
    return parser.parse_args()


def load_data_points(input_file: TextIO) -> Iterable[DataPoint]:
    for row in csv.DictReader(input_file):
        yield DataPoint(
            latlng=LatLng(float(row["lat"]), float(row["lng"])),
            weight=float(row["weight"]) if "weight" in row else 1,
            radius_metres=int(row["radius_metres"]) if "radius_metres" in row else None,
        )


ALL_DATA_POINTS = list(load_data_points(parse_args().input_file))
print(len(ALL_DATA_POINTS), "data points")


def config_json_definition() -> List[dict]:
    all_items = []
    for field in Config._fields:
        field_type = Config.__annotations__[field]
        default_value = Config._field_defaults[field]
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
            if issubclass(field_type, Enum):
                item["type"] = "select"
                item["options"] = [o.value for o in field_type]
        all_items.append(item)
    return all_items


def config_from_string_args(args: dict[str, str]) -> "Config":
    values: dict[str, object] = {}
    for field in Config._fields:
        if field not in args:
            continue  # and fall back to the default
        field_type = Config.__annotations__[field]
        str_value = args[field]
        if field_type is Gradient:
            values[field] = getattr(Gradient, str_value)
        else:
            values[field] = field_type(str_value)
    return Config(**values)  # type: ignore


app = Flask(__name__)


@app.route("/")
def get_index():
    index_html_file = Path(__file__).parent / "index.html"
    return index_html_file.open("rb")


@app.route("/config")
def get_config():
    return jsonify(
        {
            "parameters": config_json_definition(),
            "center": {
                "lat": median(p.latlng.lat for p in ALL_DATA_POINTS),
                "lng": median(p.latlng.lng for p in ALL_DATA_POINTS),
            },
        },
    )


def _parse_render_query() -> Tuple[Config, LatLngBox, int]:
    args: dict[str, str] = dict(request.args)
    config = config_from_string_args(args)
    box = LatLngBox(
        south=float(args.pop("south")),
        west=float(args.pop("west")),
        north=float(args.pop("north")),
        east=float(args.pop("east")),
    )
    zoom = int(args.pop("zoom"))
    return config, box, zoom


ResponseTuple = Tuple[bytes, int, dict[str, str]]


def _image_response(image: Image.Image) -> ResponseTuple:
    output = BytesIO()
    image.save(output, "PNG")
    return output.getvalue(), 200, {"Content-Type": "image/png"}


@app.route("/render")
def render():
    config, box, zoom = _parse_render_query()
    image = render_heatmap_to_image(config, box, zoom, ALL_DATA_POINTS)
    return _image_response(image)


@app.route("/histogram")
def histogram():
    config, box, zoom = _parse_render_query()
    image = render_histogram(config, box, zoom, ALL_DATA_POINTS)
    return _image_response(image)


if __name__ == "__main__":
    app.run("0.0.0.0", 2100)
