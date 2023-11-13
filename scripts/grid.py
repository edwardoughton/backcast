"""
Generate grid.

Ed Oughton

July 2023

"""
import os
import configparser
import pandas as pd
import numpy as np
import pyproj
import geopandas as gpd
from shapely.geometry import Polygon 
from shapely.ops import transform

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__),'..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def generate_grid(iso3, side_length):
    """
    Generate a spatial grid for the chosen country.
    """
    directory = os.path.join(DATA_PROCESSED, iso3, 'grid')

    if not os.path.exists(directory):
        os.makedirs(directory)

    filename = 'grid_{}_{}_km.shp'.format(side_length, side_length)
    path_output = os.path.join(directory, filename)

    if os.path.exists(path_output):
        return

    filename = 'national_outline.shp'
    path = os.path.join(DATA_PROCESSED, iso3, filename)
    country_outline = gpd.read_file(path, crs="epsg:4326")

    country_outline.crs = "epsg:4326"
    country_outline_3857 = country_outline.to_crs("epsg:3857")

    xmin, ymin, xmax, ymax = country_outline_3857.total_bounds

    polygons = manually_create_grid(
        xmin, ymin, xmax, ymax, side_length, side_length
    )

    project = pyproj.Transformer.from_crs(
        'EPSG:3857', 'EPSG:4326', always_xy=True).transform

    output = []

    for geom in polygons:

        area_km2 = geom.area / 1e6

        geom = transform(project, geom)

        representative_point = geom.representative_point()

        output.append({
            'geometry': geom,
            'properties': {
                'GID_id': "{}_{}".format(representative_point.x, representative_point.y),
                'area_km2': area_km2,
            }
        })

    grid = gpd.GeoDataFrame.from_features(output, crs="epsg:4326")#[:100]
    intersection = gpd.overlay(grid, country_outline, how='intersection')
    intersection.to_file(path_output, crs="epsg:4326")

    return intersection


def manually_create_grid(xmin, ymin, xmax, ymax, length, wide):
    """

    """
    cols = list(range(int(np.floor(xmin)), int(np.ceil(xmax - int(wide))), int(wide)))
    rows = list(range(int(np.floor(ymin)), int(np.ceil(ymax)), int(length)))

    polygons = []

    for x in cols:
        for y in rows:
            polygons.append(
                Polygon([(x, y), (x+wide, y), (x+wide, y-length), (x, y-length)])
            )

    return polygons


def combined_with_roads(iso3, side_length):
    """
    Combine grid and road network. 

    """
    filename = 'grid_{}_{}_km.shp'.format(side_length, side_length)
    folder = os.path.join(DATA_PROCESSED, iso3, 'grid')
    path_in = os.path.join(folder, filename)
    grid = gpd.read_file(path_in, crs='epsg:4326')
    grid = grid.to_dict('records')

    filename = 'road_network_processed.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure')
    path_in = os.path.join(folder, filename)
    roads = gpd.read_file(path_in, crs='epsg:4326')
    roads = roads.to_dict('records')#[:100]

    output = []
    # all_data = gpd.overlay(roads, grid, how='intersection', keep_geom_type=True)

    for item in grid:
        for road in roads:
            if item['geometry'].intersects(road['geometry']):
                output.append({
                    'geometry': item['geometry'],
                    'properties':{
                        'GID_id': item['GID_id'],
                        # 'GID_id': item['GID_id'],
                        # 'GID_id': item['GID_id'],
                        # 'GID_id': item['GID_id'],
                        # 'GID_id': item['GID_id'],
                        # 'GID_id': item['GID_id'],
                    }
                })

    output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

    filename = 'grid_and_roads.shp'
    folder = os.path.join(DATA_PROCESSED, iso3, 'grid')
    path_output = os.path.join(folder, filename)
    output.to_file(path_output, crs="epsg:4326")

    return


if __name__ == "__main__":

    countries = [
        ("MEX", 10000),
    ]

    for country in countries:

        iso3 = country[0]
        side_length = country[1]
    
        # ##Generate grids
        # generate_grid(iso3, side_length) 

        combined_with_roads(iso3, side_length)
