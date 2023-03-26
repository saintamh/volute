#!/usr/bin/env python3

# standards
from argparse import ArgumentParser, FileType
import csv
from io import BytesIO
from pathlib import Path
from typing import Iterable

# 3rd parties
from flask import Flask, jsonify, request

# coulis
from coulis import Config, LatLng, LatLngBox, render_heatmap_to_image


def parse_args():
    parser = ArgumentParser()
    parser.add_argument('input_file', type=FileType('r', encoding='us-ascii'))
    return parser.parse_args()


def load_latlngs(input_file) -> Iterable[LatLng]:
    for lat_str, lng_str, _count_unused in csv.reader(input_file):
        yield LatLng(float(lat_str), float(lng_str))


ALL_LATLNGS = list(load_latlngs(parse_args().input_file))


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


@app.route('/render')
def render():
    args: dict[str, str] = dict(request.args)
    config = Config.from_string_args(args)
    box = LatLngBox(
        south=float(args.pop('south')),
        west=float(args.pop('west')),
        north=float(args.pop('north')),
        east=float(args.pop('east')),
    )
    zoom = int(args.pop('zoom'))
    image = render_heatmap_to_image(config, box, zoom, ALL_LATLNGS)
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue(), 200, {'Content-Type': 'image/png'}


if __name__ == '__main__':
    app.run('0.0.0.0', 2100)
