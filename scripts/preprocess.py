"""
Preprocess sites data.

Ed Oughton

July 2023

"""
import sys
import os
import configparser
import json
import pandas as pd
import geopandas as gpd
import pyproj
from shapely.ops import transform
from shapely.geometry import shape, Point, mapping, LineString, MultiPolygon, box
import rasterio
from rasterio.mask import mask
from tqdm import tqdm

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__),'..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')


def run_preprocessing(country):
    """
    Meta function for running preprocessing.

    """
    iso3 = country['iso3']
    regional_level = int(country['gid_region'])

    print('Working on create_national_sites_csv')
    create_national_sites_csv(country)

    print('Working on process_country_shapes')
    process_country_shapes(iso3)

    print('Working on process_regions')
    process_regions(iso3, regional_level)

    print('Working on create_national_sites_shp')
    create_national_sites_shp(iso3)

    regions = get_regions(country, regional_level)
    regions = regions.to_dict('records')

    print('Working on regional disaggregation')
    for region in regions:

        region = region['GID_{}'.format(regional_level)]
        
        print("working on {}".format(region))

        gid_1 = get_gid_1(region)

        #print('Working on segment_by_gid_1')
        segment_by_gid_1(iso3, 1, gid_1)

        #print('Working on create_regional_sites_layer')
        create_regional_sites_layer(iso3, 1, gid_1)

        #print('Working on segment_by_gid_2')
        segment_by_gid_2(iso3, 2, region, gid_1)

        #print('Working on create_regional_sites_layer')
        create_regional_sites_layer(iso3, 2, region)

    print('Exporting cell counts by region')
    export_cell_counts(country, regions)

    print('Working on process_regional_coverage')
    process_regional_coverage(country)

    print('Working on convert_regional_coverage_to_shapes')
    convert_regional_coverage_to_shapes(country)

    return


def create_national_sites_csv(country):
    """
    Create a national sites csv layer for a selected country.

    """
    iso3 = country['iso3']#.values[0]

    filename = "mobile_codes.csv"
    path = os.path.join(DATA_RAW, filename)
    mobile_codes = pd.read_csv(path)
    mobile_codes = mobile_codes[['iso3', 'mcc', 'mnc']].drop_duplicates()
    all_mobile_codes = mobile_codes[mobile_codes['iso3'] == iso3]
    all_mobile_codes = all_mobile_codes.to_dict('records')

    output = []

    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path_csv = os.path.join(folder, filename)

    ### Produce national sites data layers
    if os.path.exists(path_csv):
        return

    print('-site.csv data does not exist')
    print('-Subsetting site data for {}'.format(iso3))

    if not os.path.exists(folder):
        os.makedirs(folder)

    filename = "cell_towers_2022-12-24.csv"
    path = os.path.join(DATA_RAW, filename)

    for row in all_mobile_codes:

        # if not row['mnc'] in [10,2,11,33,34,20,94,30,31,32,27,15,91,89]:
        #     continue

        mcc = row['mcc']
        seen = set()
        chunksize = 10 ** 6
        for idx, chunk in enumerate(pd.read_csv(path, chunksize=chunksize)):

            country_data = chunk.loc[chunk['mcc'] == mcc]#[:1]

            country_data = country_data.to_dict('records')

            for site in country_data:

                # if not -4 > site['lon'] > -6:
                #     continue

                # if not 49.8 < site['lat'] < 52:
                #     continue

                if site['cell'] in seen:
                    continue

                seen.add(site['cell'])

                output.append({
                    'radio': site['radio'],
                    'mcc': site['mcc'],
                    'net': site['net'],
                    'area': site['area'],
                    'cell': site['cell'],
                    'unit': site['unit'],
                    'lon': site['lon'],
                    'lat': site['lat'],
                    # 'range': site['range'],
                    # 'samples': site['samples'],
                    # 'changeable': site['changeable'],
                    # 'created': site['created'],
                    # 'updated': site['updated'],
                    # 'averageSignal': site['averageSignal']
                })
            # if len(output) > 0:
            #     break

    if len(output) == 0:
        return

    output = pd.DataFrame(output)
    output.to_csv(path_csv, index=False)

    return


def process_country_shapes(iso3):
    """
    Creates a single national boundary for the desired country.

    Parameters
    ----------
    country : dict
        Contains all desired country information.

    """
    path = os.path.join(DATA_PROCESSED, iso3)

    if os.path.exists(os.path.join(path, 'national_outline.shp')):
        return 'Completed national outline processing'

    print('Processing country shapes')

    if not os.path.exists(path):
        os.makedirs(path)

    shape_path = os.path.join(path, 'national_outline.shp')

    path = os.path.join(DATA_RAW, 'gadm36_levels_shp', 'gadm36_0.shp')

    countries = gpd.read_file(path)

    single_country = countries[countries.GID_0 == iso3].reset_index()

    single_country = single_country.copy()
    single_country["geometry"] = single_country.geometry.simplify(
        tolerance=0.01, preserve_topology=True)

    single_country['geometry'] = single_country.apply(
        remove_small_shapes, axis=1)

    glob_info_path = os.path.join(DATA_RAW, 'countries.csv')
    load_glob_info = pd.read_csv(glob_info_path, encoding = "ISO-8859-1",
        keep_default_na=False)
    single_country = single_country.merge(
        load_glob_info, left_on='GID_0', right_on='iso3')

    single_country.to_file(shape_path)

    return


def remove_small_shapes(x):
    """
    Remove small multipolygon shapes.

    Parameters
    ---------
    x : polygon
        Feature to simplify.

    Returns
    -------
    MultiPolygon : MultiPolygon
        Shapely MultiPolygon geometry without tiny shapes.

    """
    if x.geometry.type == 'Polygon':
        return x.geometry

    elif x.geometry.type == 'MultiPolygon':

        area1 = 0.01
        area2 = 50

        if x.geometry.area < area1:
            return x.geometry

        if x['GID_0'] in ['CHL','IDN']:
            threshold = 0.01
        elif x['GID_0'] in ['RUS','GRL','CAN','USA']:
            threshold = 0.01
        elif x.geometry.area > area2:
            threshold = 0.1
        else:
            threshold = 0.001

        new_geom = []
        for y in list(x['geometry'].geoms):
            if y.area > threshold:
                new_geom.append(y)

        return MultiPolygon(new_geom)


def process_regions(iso3, level):
    """
    Function for processing the lowest desired subnational
    regions for the chosen country.

    Parameters
    ----------
    country : dict
        Contains all desired country information.

    """
    regions = []

    for regional_level in range(1, int(level) + 1):

        filename = 'regions_{}_{}.shp'.format(regional_level, iso3)
        folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
        path_processed = os.path.join(folder, filename)

        if os.path.exists(path_processed):
            continue

        print('Processing GID_{} region shapes'.format(regional_level))

        if not os.path.exists(folder):
            os.mkdir(folder)

        filename = 'gadm36_{}.shp'.format(regional_level)
        path_regions = os.path.join(DATA_RAW, 'gadm36_levels_shp', filename)
        regions = gpd.read_file(path_regions)

        regions = regions[regions.GID_0 == iso3]

        regions = regions.copy()
        regions["geometry"] = regions.geometry.simplify(
            tolerance=0.005, preserve_topology=True)

        regions['geometry'] = regions.apply(remove_small_shapes, axis=1)

        try:
            regions.to_file(path_processed, driver='ESRI Shapefile')
        except:
            print('Unable to write {}'.format(filename))
            pass

    return


def create_national_sites_shp(iso3):
    """
    Create a national sites csv layer for a selected country.

    """
    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path_csv = os.path.join(folder, filename)

    filename = '{}.shp'.format(iso3)
    path_shp = os.path.join(folder, filename)

    if not os.path.exists(path_shp):

        print('-Writing site shapefile data for {}'.format(iso3))

        country_data = pd.read_csv(path_csv)#[:10]

        output = []

        for idx, row in country_data.iterrows():
            output.append({
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [row['lon'],row['lat']]
                },
                'properties': {
                    'radio': row['radio'],
                    'mcc': row['mcc'],
                    'net': row['net'],
                    'area': row['area'],
                    'cell': row['cell'],
                }
            })

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        output.to_file(path_shp)


def get_regions(country, region_type):
    """
    Get region information.

    """
    if region_type == 'use_csv':
        filename = 'regions_{}_{}.shp'.format(
            country['lowest'],
            country['iso3']
        )
        folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    elif region_type in [1, 2]:
        filename = 'regions_{}_{}.shp'.format(
            region_type,
            country['iso3']
        )
        folder = os.path.join(DATA_PROCESSED, country['iso3'], 'regions')
    elif region_type == 0:
        filename = 'national_outline.shp'
        folder = os.path.join(DATA_PROCESSED, country['iso3'])
    else:
        print("Did not recognize region_type arg provided to get_regions()")

    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        print('This path did not exist/load: {}'.format(path))
        return []

    regions = gpd.read_file(path, crs='epsg:4326')#[:1]

    return regions


def get_gid_1(region):
    """
    Get gid_1 handle from gid_2.
    
    """
    split = region.split('.')
    iso3 = split[0]
    item1 = split[1]
    item2 = split[2]
    item3 = split[2].split('_')[1]

    gid_2 = "{}.{}_{}".format(iso3, item1, item3)

    return gid_2


def segment_by_gid_1(iso3, level, region):
    """
    Segment sites by gid_1 bounding box.

    """
    gid_level = 'GID_1'#.format(level)

    filename = '{}.csv'.format(iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites')
    path = os.path.join(folder, filename)
    sites = pd.read_csv(path)#[:100]
    
    filename = 'regions_{}_{}.shp'.format(1, iso3)

    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path_regions = os.path.join(folder, filename)
    regions = gpd.read_file(path_regions, crs='epsg:4326')#[:1]
    region_df = regions[regions[gid_level] == region]['geometry'].values[0]

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
    if not os.path.exists(folder):
        os.makedirs(folder)
    path_out = os.path.join(folder, filename)
    if os.path.exists(path_out):
        return

    xmin, ymin, xmax, ymax = region_df.bounds

    output = []

    for idx, site in sites.iterrows():

        x, y = site['lon'], site['lat']

        if not xmin <= x <= xmax:
            continue

        if not ymin <= y <= ymax:
            continue

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'unit': site['unit'],
            'lon': site['lon'],
            'lat': site['lat'],
            # 'range': site['range'],
            # 'samples': site['samples'],
            # 'changeable': site['changeable'],
            # 'created': site['created'],
            # 'updated': site['updated'],
            # 'averageSignal': site['averageSignal']
        })

    if len(output) > 0:
        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)
    else:
        return

    return


def segment_by_gid_2(iso3, level, region, gid_1):
    """
    Segment sites by gid_2 bounding box.

    """
    gid_level = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')#[:1]

    region_df = regions[regions[gid_level] == region]
    region_df = region_df['geometry'].values[0]

    # filename = '{}.shp'.format(region['GID_1'])
    folder_out = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
    if not os.path.exists(folder_out):
        os.makedirs(folder_out)
    # path = os.path.join(folder_out, filename)
    if os.path.exists(path):
       return

    filename = '{}.csv'.format(region)
    path_out = os.path.join(folder_out, filename)

    if os.path.exists(path_out):
        return

    try:
        xmin, ymin, xmax, ymax = region_df.bounds
    except:
        return

    filename = '{}.csv'.format(gid_1)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_1', 'interim')
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return
    sites = pd.read_csv(path)

    output = []

    for idx, site in sites.iterrows():

        x, y = site['lon'], site['lat']

        if not xmin < x < xmax:
            continue

        if not ymin < y < ymax:
            continue

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'unit': site['unit'],
            'lon': site['lon'],
            'lat': site['lat'],
            # 'range': site['range'],
            # 'samples': site['samples'],
            # 'changeable': site['changeable'],
            # 'created': site['created'],
            # 'updated': site['updated'],
            # 'averageSignal': site['averageSignal']
        })

    if len(output) > 0:

        output = pd.DataFrame(output)

        filename = '{}.csv'.format(region)
        folder = os.path.join(DATA_PROCESSED, iso3, 'sites', 'gid_2', 'interim')
        path_out = os.path.join(folder, filename)
        output.to_csv(path_out, index=False)

    else:
        return

    return


def create_regional_sites_layer(iso3, level, region):
    """
    Create regional site layers.

    """
    project = pyproj.Transformer.from_proj(
        pyproj.Proj('epsg:4326'), # source coordinate system
        pyproj.Proj('epsg:3857')) # destination coordinate system

    gid_level = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path, crs='epsg:4326')#[:1]
    region_df = regions[regions[gid_level] == region]
    region_df = region_df['geometry'].values[0]

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower())
    if not os.path.exists(folder):
        os.mkdir(folder)
    path_out = os.path.join(folder, filename)

    if os.path.exists(path_out):
        return

    filename = '{}.csv'.format(region)
    folder = os.path.join(DATA_PROCESSED, iso3, 'sites', gid_level.lower(), 'interim')
    path = os.path.join(folder, filename)

    if not os.path.exists(path):
        return
    sites = pd.read_csv(path)

    output = []

    for idx, site in sites.iterrows():

        geom = Point(site['lon'], site['lat'])

        if not geom.intersects(region_df):
            continue

        geom_4326 = geom

        geom_3857 = transform(project.transform, geom_4326)

        output.append({
            'radio': site['radio'],
            'mcc': site['mcc'],
            'net': site['net'],
            'area': site['area'],
            'cell': site['cell'],
            'gid_level': gid_level,
            'gid_id': region,
            'cellid4326': '{}_{}'.format(
                round(geom_4326.coords.xy[0][0],6),
                round(geom_4326.coords.xy[1][0],6)
            ),
            'cellid3857': '{}_{}'.format(
                round(geom_3857.coords.xy[0][0],6),
                round(geom_3857.coords.xy[1][0],6)
            ),
        })

    if len(output) > 0:

        output = pd.DataFrame(output)
        output.to_csv(path_out, index=False)

    else:
        return

    return


def export_cell_counts(country, regions):
    """
    Aggregate cell counts.

    """
    gid_level = "GID_{}".format(country['gid_region'])

    output = []

    for region in regions:#[:1]:

        filename = '{}.csv'.format(region[gid_level])
        folder = os.path.join(DATA_PROCESSED, country['iso3'], 'sites', gid_level.lower())
        path = os.path.join(folder, filename)
        if not os.path.exists(path):
            continue
        cells = pd.read_csv(path)
        cells = cells.to_dict('records')
        
        # for radio in ['GSM','UMTS','LTE']:
        #     count = 0
        gsm = 0
        umts = 0
        lte = 0

        for cell in cells: 
            if cell['radio'] == 'GSM':
                gsm +=1
            elif cell['radio'] == 'UMTS':
                umts +=1
            elif cell['radio'] == 'LTE':
                lte +=1

        output.append({
            'gid_id': region[gid_level],
            'gid_level': gid_level,
            'gsm': gsm,
            'umts': umts,
            'lte': lte,
        })

    output = pd.DataFrame(output)

    filename = 'cells_by_region.csv'
    folder = os.path.join(DATA_PROCESSED, country['iso3'], 'sites')
    path_out = os.path.join(folder, filename)
    output.to_csv(path_out, index=False)

    return


def process_regional_coverage(country):
    """
    Cut coverage by region. 
    
    """
    level = 2
    iso3 = country['iso3']
    gid_level = 'GID_{}'.format(level)

    filename = 'regions_{}_{}.shp'.format(level, iso3)
    folder = os.path.join(DATA_PROCESSED, iso3, 'regions')
    path = os.path.join(folder, filename)
    regions = gpd.read_file(path)
    regions = regions.to_crs(3857)
    regions = regions.to_dict('records')#[:1]

    technologies = [
        '2G',
        '3G',
        '4G'
    ]

    output = {}

    for tech in technologies:

        folder_name = 'MCE_{}'.format(tech)
        folder = os.path.join(DATA_RAW, 'Mobile Coverage Explorer v2020 - GeoTIFF', 'ByCountry', folder_name)
        path =  os.path.join(folder, 'MCE_MX{}_2020.tif'.format(tech))

        data = rasterio.open(path, 'r+')
        data.nodata = 255
        data.crs = {"init": "epsg:3857"}

        for region in regions:

            folder_out = os.path.join(DATA_PROCESSED, iso3, 'coverage', "coverage_{}_tifs".format(tech))
            if not os.path.exists(folder_out):
                os.makedirs(folder_out)
            path_out = os.path.join(folder_out, '{}.tif'.format(region['GID_2']))

            if os.path.exists(path_out):
                continue

            list_of_dicts = [{
                    'geometry': region['geometry'], 
                    'properties': {
                        'gid_id': region['GID_2']
                    }
                }]
            geo = gpd.GeoDataFrame.from_features(list_of_dicts, crs='epsg:3857')

            coords = [json.loads(geo.to_json())['features'][0]['geometry']]

            out_img, out_transform = mask(data, coords, crop=True)

            out_meta = data.meta.copy()

            out_meta.update({"driver": "GTiff",
                            "height": out_img.shape[1],
                            "width": out_img.shape[2],
                            "transform": out_transform,
                            "crs": 'epsg:4326'})

            with rasterio.open(path_out, "w", **out_meta) as dest:
                    dest.write(out_img)

    return output


def convert_regional_coverage_to_shapes(country):
    """
    Convert to shapes. 

    """
    level = 2
    iso3 = country['iso3']
    gid_level = 'GID_{}'.format(level)

    technologies = [
        '2G',
        '3G',
        '4G'
    ]

    output = {}

    for tech in technologies:

        folder_name = 'coverage_{}_tifs'.format(tech)
        folder = os.path.join(DATA_PROCESSED, iso3, 'coverage', folder_name)
        tif_files = os.listdir(folder)#[:1]

        for tif_file in tif_files:

            if not tif_file.endswith('.tif'):
                continue

            filename_out = tif_file.replace('.tif','.shp')
            folder_name = 'coverage_{}_shps'.format(tech)
            folder_out = os.path.join(DATA_PROCESSED, iso3, 'coverage', folder_name)
            if not os.path.exists(folder_out):
                os.mkdir(folder_out)
            path_out = os.path.join(folder_out, filename_out)

            # if os.path.exists(path_out):
            #     continue

            with rasterio.open(os.path.join(folder, tif_file)) as src:

                affine = src.transform
                array = src.read(1)

                output = []

                for vec in rasterio.features.shapes(array):

                    if vec[1] > 0 and not vec[1] == 255:

                        coordinates = [i for i in vec[0]['coordinates'][0]]

                        coords = []

                        for i in coordinates:

                            x = i[0]
                            y = i[1]

                            x2, y2 = src.transform * (x, y)

                            coords.append((x2, y2))

                        output.append({
                            'type': vec[0]['type'],
                            'geometry': {
                                'type': 'Polygon',
                                'coordinates': [coords],
                            },
                            'properties': {
                                'value': vec[1],
                            }
                        })
            if len(output) == 0:
                continue

            output = gpd.GeoDataFrame.from_features(output, crs='epsg:3857')
            output = output.to_crs(4326)
            output.to_file(path_out, driver='ESRI Shapefile')
    

if __name__ == "__main__":

    MEX = {
        'iso3': 'MEX',
        'gid_region': 2,
    }
    run_preprocessing(MEX)
