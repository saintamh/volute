A Python library for rendering heatmaps to Web Mercator tiles.

# Synopsis

This snippet generates PNG tiles for a heatmap where colours indicate data point density:

```python
# standards
from pathlib import Path

# volute
from volute import Config, DataPoint, Gradient, LatLng, LatLngBox, render_heatmap_to_tiles

# Configuration options. The web-based interactive tool in the "configurator"
# subdirectory can be used to iteratively find the best config.
config = Config(
    gradient=Gradient.GREEN_TO_RED,
    num_colors=200,
)

tiles_root = Path("/www/my/tiles")
for zoom in range(12, 16):

    # This will create all the tiles, as a sequence of (int, int, PIL.Image) tuples
    iter_tiles = render_heatmap_to_tiles(
        config,
        LatLngBox(south=55.8516, west=-3.4306, north=56.0059, east=-2.9480),
        zoom,
        [DataPoint(LatLng(lat, lng)) for lat, lng in my_data_points],
    )

    # Then we can save the tiles to disk
    for tile_x, tile_y, tile_image in iter_tiles:
        tile_file = tiles_root / f"{zoom}" / f"{tile_x}" / f"{tile_y}.png"
        tile_file.parent.mkdir(parents=True, exist_ok=True)
        tile_image.save(tile_file)
```

# Examples

See it in action: https://saintamh.org/maps/edinburgh-street-crime/
