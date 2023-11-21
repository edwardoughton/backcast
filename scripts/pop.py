"""
Estimate regional population.

Written by Ed Oughton.

July 2023.

"""
import os
import configparser
import json
import csv
import geopandas as gpd
import pandas as pd
import glob
import pyproj
import rasterio
from rasterio.mask import mask
from rasterstats import zonal_stats


CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_INTERMEDIATE = os.path.join(BASE_PATH, 'intermediate')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def process_settlement_layer(country):
    """
    Clip the settlement layer to the chosen country boundary
    and place in desired country folder.

    Parameters
    ----------
    country : dict
        Contains all desired country information.

    """
    iso3 = country['iso3']
    regional_level = country['regional_level']

    path_settlements = os.path.join(DATA_RAW,'settlement_layer',
        'ppp_2020_1km_Aggregated.tif')

    settlements = rasterio.open(path_settlements, 'r+')
    settlements.nodata = 255
    settlements.crs = {"init": "epsg:4326"}

    iso3 = country['iso3']
    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')
    
    if os.path.exists(path_country):
        country = gpd.read_file(path_country)
    else:
        return print('Must generate national_outline.shp first' )

    path_country = os.path.join(DATA_PROCESSED, iso3)

    folder_out = os.path.join(path_country, 'population')
    if not os.path.exists(folder_out):
        os.mkdir(folder_out)
    path_out = os.path.join(folder_out, 'settlements.tif')

    if os.path.exists(path_out):
        return print('Completed settlement layer processing')

    geo = gpd.GeoDataFrame()
    geo = gpd.GeoDataFrame({'geometry': country['geometry']})

    coords = [json.loads(geo.to_json())['features'][0]['geometry']]

    out_img, out_transform = mask(settlements, coords, crop=True)

    out_meta = settlements.meta.copy()

    out_meta.update({"driver": "GTiff",
                    "height": out_img.shape[1],
                    "width": out_img.shape[2],
                    "transform": out_transform,
                    "crs": 'epsg:4326'})

    with rasterio.open(path_out, "w", **out_meta) as dest:
            dest.write(out_img)

    return print('-- Completed processing of settlement layer')


def generate_population(country):
    """
    Extract regional data including luminosity and population.

    Parameters
    ----------
    country : dict
        Contains all desired country information.

    """
    iso3 = country['iso3']
    level = country['regional_level']
    gid_level = 'GID_{}'.format(level)

    filename = 'population.csv'
    folder_out = os.path.join(DATA_PROCESSED, iso3, 'population')
    path_output = os.path.join(folder_out, filename)

    # if os.path.exists(path_output):
    #     return print('Regional data already exists')

    path_country = os.path.join(DATA_PROCESSED, iso3,
        'national_outline.shp')

    single_country = gpd.read_file(path_country)

    folder_in = os.path.join(DATA_PROCESSED, iso3, 'population')
    filename = 'settlements.tif'
    path_settlements = os.path.join(folder_in, filename)        

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path)#[:1]
    regions = regions.to_dict('records')

    results = []

    for region in regions:

        with rasterio.open(path_settlements) as src:

            affine = src.transform
            array = src.read(1)
            array[array <= 0] = 0

            population_summation = [d['sum'] for d in zonal_stats(
                region['geometry'],
                array,
                stats=['sum'],
                nodata=0,
                affine=affine
                )][0]

            population_summation = round(population_summation)

        area_km2 = round(area_of_polygon(region['geometry']) / 1e6)

        if area_km2 == 0:
            continue

        if area_km2 > 0:
            population_km2 = (
                population_summation / area_km2 if population_summation else 0)
        else:
            population_km2 = 0

        results.append({
            'GID_0': region['GID_0'],
            'GID_id': region[gid_level],
            'GID_level': gid_level,
            'population': (population_summation if population_summation else 0),
            'area_km2': area_km2,
            'population_km2': population_km2,
        })

    results_df = pd.DataFrame(results)

    results_df.to_csv(path_output, index=False)

    print('Completed {}'.format(single_country.NAME_0.values[0]))

    return print('Completed night lights data querying')


def area_of_polygon(geom):
    """
    Returns the area of a polygon. Assume WGS84 as crs.

    """
    geod = pyproj.Geod(ellps="WGS84")

    poly_area, poly_perimeter = geod.geometry_area_perimeter(
        geom
    )

    return abs(poly_area)


def generate_tile_population(country):
    """
    Extract regional data including luminosity and population.

    Parameters
    ----------
    country : dict
        Contains all desired country information.

    """
    iso3 = country['iso3']
    level = country['regional_level']
    gid_level = 'GID_{}'.format(level)

    filename = 'population_tiles.shp'
    folder_out = os.path.join(DATA_PROCESSED, iso3, 'population')
    path_output = os.path.join(folder_out, filename)

    # if os.path.exists(path_output):
    #     return print('Regional data already exists')

    folder_in = os.path.join(DATA_PROCESSED, iso3, 'population')
    filename = 'settlements.tif'
    path_settlements = os.path.join(folder_in, filename)        

    folder = os.path.join(DATA_PROCESSED, iso3, 'grid', 'grid_lower')
    filenames = os.listdir(folder)#[:20]

    results = []

    for filename in filenames:

        if not filename.endswith('shp'):
            continue

        grid = gpd.read_file(os.path.join(folder, filename), crs='epsg:4326')
        grid = grid.to_dict('records')

        for tile in grid:

            # if not tile['GID_id'] == '-105.93988452480951_30.286475556817294':
            #     continue

            with rasterio.open(path_settlements) as src:

                affine = src.transform
                array = src.read(1)
                array[array <= 0] = 0

                population_summation = [d['sum'] for d in zonal_stats(
                    tile['geometry'],
                    array,
                    stats=['sum'],
                    nodata=0,
                    affine=affine
                    )][0]

                if population_summation == None:
                    population_summation = 0

                population_summation = round(population_summation)

                area_km2 = round(area_of_polygon(tile['geometry']) / 1e6)

                if area_km2 == 0:
                    continue

                if area_km2 > 0:
                    population_km2 = (
                        population_summation / area_km2 if population_summation else 0)
                else:
                    population_km2 = 0

                results.append({
                    'geometry': tile['geometry'],
                    'properties': {
                        'iso3': country['iso3'],
                        'id_upper': filename.replace('.shp',''),
                        'id_lower': tile['GID_id'],
                        'population': (population_summation if population_summation else 0),
                        'area_km2': area_km2,
                        'pop_km2': population_km2,
                    }
                })

    results_df = gpd.GeoDataFrame.from_features(results)

    results_df.to_file(path_output, index=False)

    print('Completed {}'.format(country['iso3']))

    return print('Completed population data querying')


if __name__ == '__main__':

    countries = [{
        'iso3': 'MEX',
        'regional_level': 2,
    }]

    for country in countries:#[:1]:

        print('Processing settlement layers')
        process_settlement_layer(country)

        print('Generating regional population')
        generate_population(country)

        print('Generating tile population')
        generate_tile_population(country)

    print('--Completed regional population data estimation')
