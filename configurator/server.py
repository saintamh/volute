#!/usr/bin/env python3

# standards
from argparse import ArgumentParser, FileType
import csv
from io import BytesIO
from pathlib import Path
from typing import Iterable

# 3rd parties
from flask import Flask, request

# coulis
from coulis import Config, Gradient, LatLng, LatLngBox, compute_surface_matrix, paint_image


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
def index():
    index_html_file = Path(__file__).parent / 'index.html'
    return index_html_file.open('rb')  # it's in binary mode, pylint: disable=unspecified-encoding


@app.route('/render')
def render():
    args = dict(request.args)
    config = Config(
        box=LatLngBox(
            south=float(args['south']),
            west=float(args['west']),
            north=float(args['north']),
            east=float(args['east']),
        ),
        zoom=int(args['zoom']),
        kernel_radius_metres=int(args['kernel_radius_metres']),
        gradient=getattr(Gradient, args['gradient'].upper()),
        num_colors=int(args['num_colors']),
        stretch_to_full_tiles=False,
    )
    surface = compute_surface_matrix(config, ALL_LATLNGS)
    image = paint_image(config, surface)
    output = BytesIO()
    image.save(output, 'PNG')
    return output.getvalue(), 200, {'Content-Type': 'image/png'}


if __name__ == '__main__':
    app.run('0.0.0.0', 2100)
