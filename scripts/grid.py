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
from shapely.geometry import Polygon, Point 
from shapely.ops import transform
from tqdm import tqdm

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

    filename = 'gis_osm_roads_free_1.shp'
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


def segment_lower_into_upper_grid(country, side_length_lower, side_length_upper):
    """
    Segment the lower into the upper grid. 

    """
    directory = os.path.join(DATA_PROCESSED, iso3, 'grid')
    filename = 'grid_{}_{}_km.shp'.format(side_length_upper, side_length_upper)
    path_in = os.path.join(directory, filename)
    grid_upper = gpd.read_file(path_in, crs='epsg:4326')
    grid_upper = grid_upper.to_dict('records')#[2:3]

    directory = os.path.join(DATA_PROCESSED, iso3, 'grid')
    filename = 'grid_{}_{}_km.shp'.format(side_length_lower, side_length_lower)
    path_in = os.path.join(directory, filename)
    grid_lower = gpd.read_file(path_in, crs='epsg:4326')
    grid_lower = grid_lower.to_dict('records')

    for tile_upper in grid_upper:

        filename = '{}.shp'.format(tile_upper['GID_id'])
        folder = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
        if not os.path.exists(folder):
            os.mkdir(folder)
        path_output = os.path.join(folder, filename)

        # if os.path.exists(path_output):
        #     continue

        geom_upper = tile_upper['geometry']

        output = []

        for tile_lower in grid_lower:

            if geom_upper.intersects(tile_lower['geometry'].representative_point()):
                output.append({
                    'geometry': tile_lower['geometry'],
                    'properties':{
                        'GID_id': tile_lower['GID_id'],
                    }
                })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        output.to_file(path_output, crs="epsg:4326")

    return


def cut_roads_with_upper_grid(iso3, side_length_upper):
    """
    Cut roads with upper grid. 

    """
    filename = 'gis_osm_roads_free_1.shp'
    folder = os.path.join(DATA_RAW, 'osm')
    # folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure')
    path_in = os.path.join(folder, filename)
    roads_all = gpd.read_file(path_in, crs='epsg:4326')

    folder = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
    filenames = os.listdir(folder)
    for filename in tqdm(filenames):
        
        if not filename.endswith('.shp'):
            continue
        
        folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure', 'grid_{}'.format(side_length_upper))
        if not os.path.exists(folder):
            os.mkdir(folder)
        path_output = os.path.join(folder, filename)

        if os.path.exists(path_output):
            continue

        print('--Working on {}'.format(filename))

        folder = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
        path_in = os.path.join(folder, filename)

        if not os.path.exists(path_in):
            continue

        grid = gpd.read_file(path_in, crs='epsg:4326')#[:5]
        grid['col1'] = 0
        grid = grid.dissolve("col1")

        roads = gpd.overlay(roads_all, grid, how='intersection')

        if len(roads) == 0:
            continue

        roads.to_file(path_output, crs="epsg:4326")

    return


def segment_roads_to_lower(iso3, side_length_lower, side_length_upper):
    """
    Segment road network. 

    """
    folder = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
    filenames = os.listdir(folder)
    for filename in filenames:
        
        if not filename.endswith('.shp'):
            continue
        
        directory = os.path.join(DATA_PROCESSED, iso3, 'infrastructure', 'grid_{}'.format(side_length_upper))
        path_in = os.path.join(directory, filename)
        if not os.path.exists(path_in):
            continue
        road_network = gpd.read_file(path_in, crs='epsg:4326')

        directory = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
        path_in = os.path.join(directory, filename)
        if not os.path.exists(path_in):
            continue
        grid_lower = gpd.read_file(path_in, crs='epsg:4326')

        road_network = gpd.overlay(road_network, grid_lower, how='intersection', keep_geom_type=True)

        grid_lower = grid_lower.to_dict('records')
        road_network = road_network.to_dict('records')

        output = []

        for tile_lower in grid_lower:
            for road_tile in road_network:
                if tile_lower['geometry'].intersects(road_tile['geometry']):
                    output.append({
                        'geometry': road_tile['geometry'],
                        'properties':{
                            'id_upper': filename.replace('.shp',''),
                            'id_lower': tile_lower['GID_id'],
                            'fclass': road_tile['fclass'],
                        }
                    })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure', 'grid_{}'.format(side_length_lower))
        if not os.path.exists(folder):
            os.mkdir(folder)
        path_output = os.path.join(folder, filename)

        output.to_file(path_output, crs="epsg:4326")

    return


def export_road_network_metrics(country, side_length_lower):
    """
    Export regional metrics. 

    """
    folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure', 'grid_{}'.format(side_length_lower))
    filenames = os.listdir(folder)

    output = []
    
    for filename in filenames:
        
        if not filename.endswith('.shp'):
            continue

        print('Working on {}'.format(filename))

        path_in = os.path.join(folder, filename)
        if not os.path.exists(path_in):
            continue
        road_network = gpd.read_file(path_in, crs='epsg:4326')
        road_network = road_network.to_crs(3857)
        road_network['length_km'] = road_network['geometry'].length / 1e3
        
        unique_ids = road_network['id_lower'].unique()#[:1]

        for unique_id in unique_ids:

            subset = road_network[road_network['id_lower'] == unique_id]

            subset = subset[['fclass', 'length_km']]
            subset = round(subset.groupby('fclass').sum(), 1).reset_index()
            subset = dict(subset.values)

            if 'living_street' in subset.keys():
                living_street = subset['living_street']
            else:
                living_street = 0

            if 'primary' in subset.keys():
                primary = subset['primary']
            else:
                primary = 0

            if 'residential' in subset.keys():
                residential = subset['residential']
            else:
                residential = 0

            if 'secondary' in subset.keys():
                secondary = subset['secondary']
            else:
                secondary = 0

            if 'tertiary' in subset.keys():
                tertiary = subset['tertiary']
            else:
                tertiary = 0

            if 'trunk' in subset.keys():
                trunk = subset['trunk']
            else:
                trunk = 0

            if 'unclassified' in subset.keys():
                unclassified = subset['unclassified']
            else:
                unclassified = 0

            output.append({
                'iso3': iso3,
                'id_lower': unique_id,
                'living_street': living_street,
                'primary': primary,
                'residential': residential,
                'secondary': secondary,
                'tertiary': tertiary,
                'trunk': trunk,
                'unclassified': unclassified,
                'total': living_street + primary + residential + secondary + tertiary + trunk + unclassified
            })

    output = pd.DataFrame(output)

    filename = 'road_lengths_by_region.csv'
    folder = os.path.join(DATA_PROCESSED, iso3, 'infrastructure')
    path_out = os.path.join(folder, filename)

    output.to_csv(path_out, index=False)

    return


if __name__ == "__main__":

    countries = [
        ("MEX", 100000, 10000),
    ]

    for country in countries:

        iso3 = country[0]
        side_length_upper = country[1]
        side_length_lower = country[2]
    
        ##Generate grids
        generate_grid(iso3, side_length_lower) 
        generate_grid(iso3, side_length_lower) 

        segment_lower_into_upper_grid(iso3, side_length_lower, side_length_upper)

        cut_roads_with_upper_grid(iso3, side_length_upper)

        segment_roads_to_lower(iso3, side_length_lower, side_length_upper)

        export_road_network_metrics(iso3, side_length_lower)