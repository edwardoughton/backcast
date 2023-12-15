"""
Process backcast. 

Ed Oughton

July 2023

"""
import sys
import os
import configparser
import json
import math
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as ctx
import seaborn as sns

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__),'..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

# # caution: path[0] is reserved for script path (or '' in REPL)
# sys.path.insert(1, os.path.join(BASE_PATH, '..', 'vis'))
# from vis import multiplot_tile_deployment

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')


def load_data(country):
    """
    Loads data. 

    """
    filename = 'population_tiles.shp'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'], 'population')
    path_in = os.path.join(folder_in, filename)
    population_data = gpd.read_file(path_in, crs='epsg:4326')
    population_data = population_data.to_dict('records')

    filename = 'road_lengths_by_region.csv'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'], 'infrastructure')
    path_in = os.path.join(folder_in, filename)
    road_data = pd.read_csv(path_in)
    road_data = road_data.to_dict('records')#[:3]

    output = []
    seen = set()

    for pop_item in population_data:
        # if not pop_item['id_lower'] == '-100.01100364962068_16.910656703520466':
        #     continue
        for road_item in road_data:
            if pop_item['id_lower'] == road_item['id_lower']:
                output.append({
                    'geometry': pop_item['geometry'],
                    'properties': {
                        'iso3': pop_item['iso3'],
                        'id_upper': pop_item['id_upper'],
                        'id_lower': pop_item['id_lower'],
                        'population': pop_item['population'],
                        'area_km2': pop_item['area_km2'],
                        'pop_km2': pop_item['pop_km2'],
                        'motorway': road_item['motorway'], 
                        'primary': road_item['primary'], 
                        'secondary': road_item['secondary'], 
                        'tertiary': road_item['tertiary'], 
                        'trunk': road_item['trunk'], 
                        'total': road_item['total'], 
                    }
                })
                seen.add(pop_item['id_lower'])

    for pop_item in population_data:
        # if not pop_item['id_lower'] == '-100.01100364962068_16.910656703520466':
        #     continue
        if pop_item['id_lower'] not in list(seen):
            output.append({
                'geometry': pop_item['geometry'],
                'properties': {
                    'iso3': pop_item['iso3'],
                    'id_upper': pop_item['id_upper'],
                    'id_lower': pop_item['id_lower'],
                    'population': pop_item['population'],
                    'area_km2': pop_item['area_km2'],
                    'pop_km2': pop_item['pop_km2'],
                    'motorway': 0, 
                    'primary': 0, 
                    'secondary': 0, 
                    'tertiary': 0, 
                    'trunk': 0, 
                    'total': 0, 
                }
            })

    output = gpd.GeoDataFrame.from_features(output)
    
    filename = 'all_data.shp'
    folder = os.path.join(DATA_PROCESSED, country['iso3'])
    path_out = os.path.join(folder, filename)
    output.to_file(path_out, crs='epsg:4326')

    return output


def get_total_cells(cells):
    """
    Get the total number of cells. 

    """
    gsm = 0
    umts = 0
    lte = 0

    for key, value in cells.items():

        gsm += value['gsm']
        umts += value['umts']
        lte += value['lte']

    return gsm, umts, lte


def start_year(radio):
    """
    Get the radio generation built type.
    
    """
    if radio == 'gsm':
        return 1996, 2014 
    elif radio == 'umts':
        return 2008, 2018
    elif radio == 'lte':
        return 2013, 2022


def spending_proportion(year):
    """
    Get the radio generation built type.
    
    """
    lut = {
        1996: 100,
        1997: 100,
        1998: 100,
        1999: 100,
        2000: 100,
        2001: 100,
        2002: 100,
        2003: 100,
        2004: 100,
        2005: 100,
        2006: 100,
        2007: 100,
        2008: 50,
        2009: 50,
        2010: 50,
        2011: 50,
        2012: 50,
        2013: 50,
        2014: 50,
        2015: 50,
        2016: 50,
        2017: 50,
        2018: 100,
        2019: 100,
        2020: 100,
    }

    return lut[year]
    

def generate_tile_backcast(country):
    """
    Generate tile backcast data.

    """
    filename = 'all_data.shp'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'])
    path_in = os.path.join(folder_in, filename)
    pop_lut = gpd.read_file(path_in, crs='epsg:4326')#[:5]
    # pop_lut = pop_lut.sort_values(by=['population'], ascending=False)[:1]

    pop_lut['attractiveness'] =  round(
        pop_lut['pop_km2'] + 
        (pop_lut['motorway'] * 10000) #+
        #(pop_lut['primary'] * 10000)  
        # (pop_lut['secondary'] * 2) + 
        # (pop_lut['tertiary']), 2
        )
    pop_lut = pop_lut.to_dict('records')

    pop_lut = sorted(pop_lut, key=lambda d: d['attractiveness'], reverse=True)#[:1] 

    path_in = os.path.join(DATA_PROCESSED, '..', 'raw','cash_to_spend.csv')
    cash_to_spend_data = pd.read_csv(path_in)#[:5]
    cash_to_spend_data = cash_to_spend_data.to_dict('records')

    cash_to_spend = {}

    for item in cash_to_spend_data:
        cash_to_spend[item['year']] = item['cash_to_spend']

    cost_per_site = 150000
    pop_per_site = 5000
    market_share = 0.25

    for radio in ['gsm','umts','lte']:

        output = []
        built = set()
        start, end = start_year(radio)

        for year in range(start, end+5):

            if year == 2021:
                break 

            spent = 0
            spending_factor = spending_proportion(year)

            to_spend = cash_to_spend[year] * (spending_factor/100)

            for tile in pop_lut:

                users = math.floor(tile['population'] * market_share)

                if tile['attractiveness'] == 0 and not tile['id_lower'] in built:
                    output.append({
                        'geometry': tile['geometry'],
                        'properties': {
                            'year': 'NA',
                            'id_lower': tile['id_lower'],
                            'id_upper': tile['id_upper'],
                            'population': tile['population'],
                            'area_km2': tile['area_km2'],
                            'pop_km2': tile['pop_km2'],
                            'users': users,
                            'cells_to_build': 0,
                            'radio': 'NA',
                            'cost': 0,
                            'population_served': 0,
                            'motorway': tile['motorway'], 
                            'primary': tile['primary'], 
                            'secondary': tile['secondary'], 
                            'tertiary': tile['tertiary'], 
                            'trunk': tile['trunk'], 
                            'total': tile['total'], 
                            'attractiveness': tile['attractiveness'],
                        }
                    })
                    built.add(tile['id_lower'])
                    continue
        
                if not tile['id_lower'] in built:
                    if spent < to_spend:
                        if tile['pop_km2'] < 50 and tile['motorway'] == 0 or tile['attractiveness'] == 0:
                            output.append({
                                'geometry': tile['geometry'],
                                'properties': {
                                    'year': 'NA',
                                    'id_lower': tile['id_lower'],
                                    'id_upper': tile['id_upper'],
                                    'population': tile['population'],
                                    'area_km2': tile['area_km2'],
                                    'pop_km2': tile['pop_km2'],
                                    'users': users,
                                    'cells_to_build': 0,
                                    'radio': 'NA',
                                    'cost': 0,
                                    'population_served': 0,
                                    'motorway': tile['motorway'], 
                                    'primary': tile['primary'], 
                                    'secondary': tile['secondary'], 
                                    'tertiary': tile['tertiary'], 
                                    'trunk': tile['trunk'], 
                                    'total': tile['total'], 
                                    'attractiveness': tile['attractiveness'],
                                }
                            })
                            built.add(tile['id_lower'])
                            continue

                        cells_to_build = math.ceil(users / pop_per_site)
                        cost = cells_to_build * cost_per_site

                        output.append({
                            'geometry': tile['geometry'],
                            'properties': {
                                'year': year,
                                'id_lower': tile['id_lower'],
                                'id_upper': tile['id_upper'],
                                'population': tile['population'],
                                'area_km2': tile['area_km2'],
                                'pop_km2': tile['pop_km2'],
                                'users': users,
                                'cells_to_build': cells_to_build,
                                'radio': radio,
                                'cost': cost,
                                'population_served': round(tile['population']),
                                'motorway': tile['motorway'], 
                                'primary': tile['primary'], 
                                'secondary': tile['secondary'], 
                                'tertiary': tile['tertiary'], 
                                'trunk': tile['trunk'], 
                                'total': tile['total'], 
                                'attractiveness': tile['attractiveness'],
                            }
                        })

                        built.add(tile['id_lower'])
                        spent += cost

        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        filename = '{}_tiles.shp'.format(radio)
        folder_out = os.path.join(RESULTS, country['iso3'], 'by_radio')
        if not os.path.exists(folder_out):
            os.makedirs(folder_out)
        path_output = os.path.join(folder_out, filename)
        output.to_file(path_output, crs='epsg:4326')

        filename = '{}.csv'.format(radio)
        folder_out = os.path.join(RESULTS, country['iso3'], 'by_radio')
        path_output = os.path.join(folder_out, filename)
        # output = output[output['year'] != 'NA']
        # output['gid_id'] = 'MEX'
        output = output[['id_lower','year','radio','population','users', 'attractiveness','cells_to_build']]
        output.to_csv(path_output, index=False)

    return


def aggregate_results(country):
    """
    Aggregate the radio generation results to the region level.

    """
    output = []

    for radio in ['gsm','umts','lte']:

        filename = '{}.csv'.format(radio)
        folder_in = os.path.join(RESULTS, country['iso3'], 'by_radio')
        path_in = os.path.join(folder_in, filename)
        data = pd.read_csv(path_in)
        data = data.to_dict('records')
        output = output + data

    output = pd.DataFrame(output)

    filename = 'results.csv'
    folder_out = os.path.join(RESULTS, country['iso3'])
    path_output = os.path.join(folder_out, filename)
    output.to_csv(path_output, index=False)

    return


def plot_map(country):
    """
    Plot map. 

    """
    for radio in [
        ('gsm', '2G'), 
        ('umts', '3G'), 
        ('lte', '4G')
        ]:

        filename = '{}_tiles.shp'.format(radio[0])
        folder = os.path.join(BASE_PATH, '..', 'results', country['iso3'], 'by_radio')
        path = os.path.join(folder, filename)
        shapes = gpd.read_file(path, crs='epsg:4326')
        shapes = shapes[shapes['year'] != 'NA']
        shapes['year'] = pd.to_numeric(shapes['year'])

        bins = [1999,2002,2004,2006,2008,2010,2012, 2014, 2016, 2018,2021]
        labels = ['2000-02','2002-04','2004-06','2006-08','2008-10','2010-12','2012-14','2014-16','2016-18','2018-20']

        shapes['bin'] = pd.cut(
            shapes['year'],
            bins=bins,
            labels=labels
        )

        sns.set(font_scale=1, font="Times New Roman")
        sns.set_style("ticks")
        fig, ax = plt.subplots(1, 1, figsize=(8,5.85))
        fig.set_facecolor('gainsboro')

        minx, miny, maxx, maxy = shapes.total_bounds
        ax.set_xlim(minx-1, maxx+1)
        ax.set_ylim(miny-1.5, maxy+1.5)

        plt.figure()

        base = shapes.plot(
            column='bin', 
            ax=ax, 
            cmap='viridis_r', 
            linewidth=0.1,
            legend=True, 
            edgecolor='grey'
            )
        # country_shapes.plot(ax=base, facecolor="none", edgecolor='black', linewidth=0.75)

        handles, labels = ax.get_legend_handles_labels()

        fig.legend(handles[::-1], labels[::-1])

        ctx.add_basemap(ax, crs=shapes.crs, source=ctx.providers.CartoDB.Voyager)
        
        start, end = start_year(radio[0])
        fig.suptitle('Backcast of {} mobile infrastructure deployment {}-{}'.format(radio[1], start, end), 
                     fontsize=18, 
                     fontname='Times New Roman')

        fig.tight_layout()
        filename = '{}_deployment_schedule.png'.format(radio[1])
        folder = os.path.join(VIS)
        if not os.path.exists(folder):
            os.mkdir(folder)
        fig.savefig(os.path.join(folder, filename), dpi=600)

        plt.close(fig)



if __name__ == "__main__":

    country = {
        'iso3': 'MEX',
        'gid_region': 2,
    }

    # print('Running load_data')
    # data = load_data(country)

    print('Generating tile backcast results')
    generate_tile_backcast(country)

    print('Aggregating results')
    aggregate_results(country)

    print("Working on plot_map")
    plot_map(country)

