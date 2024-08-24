#!/usr/bin/env python3

# standards
from argparse import ArgumentParser, FileType
import csv
from io import BytesIO
from pathlib import Path
from typing import Iterable, TextIO, Tuple

# 3rd parties
from flask import Flask, jsonify, request
from PIL import Image

# volute
from volute.datastructures import Config, DataPoint, LatLng, LatLngBox
from volute.render import render_heatmap_to_image
from .histogram import render_histogram


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('input_file', type=FileType('r', encoding='us-ascii'))
    return parser.parse_args()


def load_data_points(input_file: TextIO) -> Iterable[DataPoint]:
    for row in csv.DictReader(input_file):
        yield DataPoint(
            latlng=LatLng(float(row['lat']), float(row['lng'])),
            weight=float(row['weight']) if 'weight' in row else 1,
            radius_metres=int(row['radius_metres']) if 'radius_metres' in row else None,
        )


ALL_DATA_POINTS = list(load_data_points(parse_args().input_file))


app = Flask(__name__)


@app.route('/')
def get_index():
    index_html_file = Path(__file__).parent / 'index.html'
    return index_html_file.open('rb')  # it's in binary mode, pylint: disable=unspecified-encoding


@app.route('/config')
def get_config():
    return jsonify({
        'parameters': Config.json_definition(),
    })


def _parse_render_query() -> Tuple[Config, LatLngBox, int]:
    args: dict[str, str] = dict(request.args)
    config = Config.from_string_args(args)
    box = LatLngBox(
        south=float(args.pop('south')),
        west=float(args.pop('west')),
        north=float(args.pop('north')),
        east=float(args.pop('east')),
    )
    zoom = int(args.pop('zoom'))
    return config, box, zoom


ResponseTuple = Tuple[bytes, int, dict[str, str]]


def _image_response(image: Image.Image) -> ResponseTuple:
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue(), 200, {'Content-Type': 'image/png'}


@app.route('/render')
def render():
    config, box, zoom = _parse_render_query()
    image = render_heatmap_to_image(config, box, zoom, ALL_DATA_POINTS)
    return _image_response(image)


@app.route('/histogram')
def histogram():
    config, box, zoom = _parse_render_query()
    image = render_histogram(config, box, zoom, ALL_DATA_POINTS)
    return _image_response(image)


if __name__ == '__main__':
    app.run('0.0.0.0', 2100)
