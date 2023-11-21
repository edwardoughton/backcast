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
                seen.add(pop_item['id_upper'])

    for pop_item in population_data:
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
        return 2000, 2014 
    elif radio == 'umts':
        return 2008, 2016
    elif radio == 'lte':
        return 2013, 2022


def generate_tile_backcast(country):
    """
    Generate tile backcast data.

    """
    filename = 'all_data.shp'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'])
    path_in = os.path.join(folder_in, filename)
    pop_lut = gpd.read_file(path_in, crs='epsg:4326')#[:5]

    pop_lut['attractiveness'] =  round(
        pop_lut['pop_km2'] + 
        (pop_lut['motorway'] * 10000) #+
        #(pop_lut['primary'] * 10000)  
        # (pop_lut['secondary'] * 2) + 
        # (pop_lut['tertiary']), 2
        )
    pop_lut = pop_lut.to_dict('records')

    pop_lut = sorted(pop_lut, key=lambda d: d['attractiveness'], reverse=True)#[:1] 

    cash_to_spend = { #1e8 # $100,000,000/year
        2000: 1e7, 
        2001: 1e7,
        2002: 1e7,
        2003: 1e7,
        2004: 1e8,
        2005: 1e8,
        2006: 1e8,
        2007: 1e8, 
        2008: 1e8,
        2009: 1e8,
        2010: 1e8,
        2011: 1e8,
        2012: 1e8,
        2013: 1e8,
        2014: 1e8,
        2015: 1e8,
        2016: 1e8,
        2017: 1e8,
        2018: 1e8,
        2019: 1e8,
        2020: 1e8,
        2021: 1e8,
    }
    cost_per_site = 100000
    pop_per_site = 10000
    market_share = 0.25

    for radio in ['gsm']:#,'umts','lte']:

        output = []
        built = set()
        start, end = start_year(radio)

        for year in range (start, end):

            spent = 0

            for tile in pop_lut:
        
                users = tile['population'] * market_share

                if tile['attractiveness'] == 0:
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
                    continue
        
                if not tile['id_lower'] in built:
                    if spent < cash_to_spend[year]:

                        if tile['pop_km2'] < 100 and tile['motorway'] == 0 or tile['attractiveness'] == 0:
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
                            continue

                        cells_to_build = math.ceil(users / pop_per_site)
                        cost = cells_to_build * cost_per_site

                        # if cost < 100000:
                        #     cost = 100000

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
                    else:
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
                                                    
        output = gpd.GeoDataFrame.from_features(output, crs='epsg:4326')

        filename = '{}_tiles.shp'.format(radio)
        folder_out = os.path.join(RESULTS, country['iso3'], 'by_radio')
        if not os.path.exists(folder_out):
            os.makedirs(folder_out)
        path_output = os.path.join(folder_out, filename)
        output.to_file(path_output, crs='epsg:4326')

    return


# def aggregate_results(country):
#     """
#     Aggregate the radio generation results to the region level.

#     """
#     output = []

#     for radio in ['gsm']:#,'umts','lte']:

#         filename = '{}_tiles.csv'.format(radio)
#         folder_in = os.path.join(RESULTS, country['iso3'], 'by_radio')
#         path_in = os.path.join(folder_in, filename)
#         data = pd.read_csv(path_in)
#         data = data.to_dict('records')
#         output = output + data

#     output = pd.DataFrame(output)

#     filename = 'results.csv'
#     folder_out = os.path.join(RESULTS, country['iso3'])
#     path_output = os.path.join(folder_out, filename)
#     output.to_csv(path_output, index=False)

#     return


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


def multiplot_tile_deployment(iso3):
    """
    Plot cells. 

    """
    filename = 'gsm_tiles.shp'
    folder = os.path.join(BASE_PATH, '..', 'results', iso3, 'radio')
    path = os.path.join(folder, filename)
    gsm = gpd.read_file(path, crs='epsg:4326')

    filename = 'umts_tiles.shp'
    folder = os.path.join(BASE_PATH, '..', 'results', iso3, 'radio')
    path = os.path.join(folder, filename)
    umts = gpd.read_file(path, crs='epsg:4326')

    filename = 'lte_tiles.shp'
    folder = os.path.join(BASE_PATH, '..', 'results', iso3, 'radio')
    path = os.path.join(folder, filename)
    lte = gpd.read_file(path, crs='epsg:4326')

    plt.rcParams["font.family"] = "Times New Roman"
    fig, (ax1, ax2) = plt.subplots(2, 2, figsize=(11,8))
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    #### start adapting from here
    ####
    ####
    ####
    for ax in [ax1, ax2]:
        for dim in [0,1]:
            data_subset.plot(ax=ax[dim], facecolor="none", edgecolor='lightgrey', linewidth=0.1)
            # ctx.add_basemap(ax[dim], crs=shapes_subset.crs, source=ctx.providers.CartoDB.Voyager)

    options = [
        ('gsm', ax1[0]),
        ('umts', ax1[1]),
        ('lte', ax2[0]),
        ('nr', ax2[1])
    ]

    for my_file in options:
        
        shapes_to_plot = shapes_subset[shapes_subset['radio'] == my_file[0]]

        if len(shapes_to_plot) > 0:
            shapes_to_plot.plot(
                column='cells_to_build', 
                color='red',
                linewidth=0.01, 
                alpha=.5,
                legend=True, 
                edgecolor='grey', 
                ax=my_file[1]
            )
            
    ax1[0].set_title('2G GSM', fontname='Times New Roman')
    ax1[1].set_title('3G UMTS', fontname='Times New Roman')
    ax2[0].set_title('4G LTE', fontname='Times New Roman')
    ax2[1].set_title('5G NR', fontname='Times New Roman')

    main_title = 'Backcasting cellular deployment in Mexico: {}'.format(str(year))
    plt.suptitle(main_title, fontsize=20, y=.98)

    fig.tight_layout()
    
    filename = '{}.png'.format(str(year))
    fig.savefig(os.path.join(VIS, filename))

    plt.close(fig)

    data_subset = data_subset.to_dict('records')

    return


if __name__ == "__main__":

    country = {
        'iso3': 'MEX',
        'gid_region': 2,
    }

    # print('Running load_data')
    # data = load_data(country)

    # print('Generating tile backcast results')
    # generate_tile_backcast(country)

    # print('Aggregating results')
    # aggregate_results(country)

    print("Working on plot_map")
    plot_map(country)

    # print('Working on multiplot_tile_deployment')
    # multiplot_tile_deployment(country['iso3'])
