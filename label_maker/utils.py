"""Provide utility functions"""
from os import path as op
from urllib.parse import urlparse

from mercantile import bounds
from pyproj import Proj
from PIL import Image
import numpy as np
import requests
import rasterio

def url(tile, imagery):
    """Return a tile url provided an imagery template and a tile"""
    return imagery.replace('{x}', tile[0]).replace('{y}', tile[1]).replace('{z}', tile[2])

def class_match(ml_type, label, i):
    """Determine if a label matches a given class index"""
    if ml_type == 'classification':
        return label[i] > 0
    elif ml_type == 'object-detection':
        return len(list(filter(lambda bb: bb[4] == i, label)))
    elif ml_type == 'segmentation':
        return np.count_nonzero(label == i)
    return None

def download_tile_tms(tile, imagery, dest_folder):
    """Download a satellite image tile from a tms endpoint"""
    o = urlparse(imagery)
    _, image_format = op.splitext(o.path)
    r = requests.get(url(tile.split('-'), imagery))
    tile_img = op.join(dest_folder, 'tiles', '{}{}'.format(tile, image_format))
    open(tile_img, 'wb').write(r.content)

def get_tile_tif(tile, imagery, dest_folder):
    """Read a GeoTIFF with a window corresponding to a TMS tile"""
    bound = bounds(*[int(t) for t in tile.split('-')])
    with rasterio.open(imagery) as src:
        x_res, y_res = src.transform[0], src.transform[4]
        proj_to = Proj(**src.crs)

        tile_ul_proj = proj_to(bound.west, bound.north)
        tile_lr_proj = proj_to(bound.east, bound.south)
        tif_ul_proj = (src.bounds.left, src.bounds.top)

        # y, x (rows, columns)
        top = int((tile_ul_proj[1] - tif_ul_proj[1]) / y_res)
        left = int((tile_ul_proj[0] - tif_ul_proj[0]) / x_res)
        bottom = int((tile_lr_proj[1] - tif_ul_proj[1]) / y_res)
        right = int((tile_lr_proj[0] - tif_ul_proj[0]) / x_res)

        window = ((top, bottom), (left, right))

        data = np.empty(shape=(3, 256, 256)).astype(src.profile['dtype'])
        for k in (1, 2, 3):
            src.read(k, window=window, out=data[k - 1], boundless=True)

        tile_img = op.join(dest_folder, 'tiles', '{}{}'.format(tile, '.jpg'))
        img = Image.fromarray(np.moveaxis(data, 0, -1), mode='RGB')
        img.save(tile_img)
