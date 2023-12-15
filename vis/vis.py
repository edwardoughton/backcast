"""
Visualize data.

Written by Ed Oughton.

September 2023

"""
import os
import configparser
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
# import seaborn as sns
import contextily as ctx
from pylab import * #is this needed
# import imageio
import seaborn as sns

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
VIS = os.path.join(BASE_PATH, '..', 'vis', 'figures')


def plot_coverage(iso3):
    """
    Plot regions by geotype.

    """
    for radio in [
        ('gsm', '2G'),
        ('umts', '3G'),
        ('lte', '4G')
        ]:

        shapes = []

        folder_in = os.path.join(DATA_PROCESSED, iso3, 'coverage', 'coverage_{}_shps'.format(radio[1]))
        path = os.path.join(folder_in, '..', 'coverage_{}.shp'.format(radio[1]))
                            
        if not os.path.exists(path):
            filenames = os.listdir(folder_in)#[:10]
            for filename in filenames:
                if not filename.endswith('.shp'):
                    continue
                path_in = os.path.join(folder_in, filename)
                data = gpd.read_file(path_in, crs='epsg:4326')
                data = data.to_dict('records')
                for item in data:

                    value = item['value']
                    if item['value'] == 2:
                        value = 1
                    elif item['value'] == 3:
                        value = 0

                    shapes.append({
                        'geometry': item['geometry'],
                        'properties': {
                            'coverage': value
                        }
                    })

            shapes = gpd.GeoDataFrame.from_features(shapes, crs='epsg:4326')
            shapes.to_file(path, crs='epsg:4326')  

    path_in = os.path.join(DATA_PROCESSED, iso3, 'coverage', 'coverage_2G.shp')
    coverage_2G = gpd.read_file(path_in, crs='epsg:4326')

    path_in = os.path.join(DATA_PROCESSED, iso3, 'coverage', 'coverage_3G.shp')
    coverage_3G = gpd.read_file(path_in, crs='epsg:4326')

    path_in = os.path.join(DATA_PROCESSED, iso3, 'coverage', 'coverage_4G.shp')
    coverage_4G = gpd.read_file(path_in, crs='epsg:4326')

    coverage_2G = coverage_2G[coverage_2G['coverage'] == 1] 
    coverage_3G = coverage_3G[coverage_3G['coverage'] == 1] 
    coverage_4G = coverage_4G[coverage_4G['coverage'] == 1] 

    plt.rcParams["font.family"] = "Times New Roman"
    fig, (ax1, ax2) = plt.subplots(2, 2, figsize=(11,8))
    fig.subplots_adjust(hspace=.3, wspace=.1)
    fig.set_facecolor('gainsboro')

    country = gpd.read_file(os.path.join(DATA_PROCESSED, iso3, 'national_outline.shp'), crs='epsg:4326')
    minx, miny, maxx, maxy = country.total_bounds
       
    country.plot(ax=ax1[0], color='whitesmoke', linewidth=0.1, alpha=.2, edgecolor='grey', zorder=1)
    country.plot(ax=ax1[1], color='whitesmoke', linewidth=0.1, alpha=.2, edgecolor='grey', zorder=1)
    country.plot(ax=ax2[0], color='whitesmoke', linewidth=0.1, alpha=.2, edgecolor='grey', zorder=1)
    country.plot(ax=ax2[1], color='whitesmoke', linewidth=0.1, alpha=.2, edgecolor='grey', zorder=1)

    coverage_2G.plot(color='red', lw=.6, ax=ax1[0], zorder=20)
    coverage_3G.plot(color='orange', lw=.4, ax=ax1[1], zorder=15)
    coverage_4G.plot(color='blue', lw=.2, ax=ax2[0], zorder=10)

    ctx.add_basemap(ax1[0], crs=country.crs, source=ctx.providers.CartoDB.Voyager)    
    ctx.add_basemap(ax1[1], crs=country.crs, source=ctx.providers.CartoDB.Voyager)    
    ctx.add_basemap(ax2[0], crs=country.crs, source=ctx.providers.CartoDB.Voyager)    
    ctx.add_basemap(ax2[1], crs=country.crs, source=ctx.providers.CartoDB.Voyager)   

    ax1[0].set_title('2G GSM', fontname='Times New Roman')
    ax1[1].set_title('3G UMTS', fontname='Times New Roman')
    ax2[0].set_title('4G LTE', fontname='Times New Roman')
    ax2[1].set_title('5G NR', fontname='Times New Roman')

    main_title = 'Cellular coverage by generation in Mexico: {}'.format(str(2020))
    plt.suptitle(main_title, fontsize=20, y=.98, fontname='Times New Roman')

    fig.tight_layout()
    
    filename = 'coverage.png'
    fig.savefig(os.path.join(VIS, filename), dpi=600)

    plt.close(fig)


def plot_regions_by_geotype(iso3):
    """
    Plot regions by geotype.

    """
    filename = 'all_data.shp'
    folder_in = os.path.join(DATA_PROCESSED, iso3)
    path_in = os.path.join(folder_in, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')#[:5]
    n = len(regions)

    metric = 'pop_km2'

    bins = [-1, 10, 50, 100, 250, 500, 750, 1000, 2000, 5000, 1e8]
    labels = [
        '<10 $\mathregular{km^2}$',
        '10-50 $\mathregular{km^2}$',
        '50-100 $\mathregular{km^2}$',
        '100-250 $\mathregular{km^2}$',
        '250-500 $\mathregular{km^2}$',
        '500-750 $\mathregular{km^2}$',
        '750-1000 $\mathregular{km^2}$',
        '1000-2000 $\mathregular{km^2}$',
        '2000-5000 $\mathregular{km^2}$',
        '>5000 $\mathregular{km^2}$'
    ]

    regions['bin'] = pd.cut(
        regions[metric],
        bins=bins,
        labels=labels
    )

    sns.set(font_scale=1, font="Times New Roman")
    sns.set_style("ticks")
    fig, ax = plt.subplots(1, 1, figsize=(8,5.85))
    fig.set_facecolor('gainsboro')
    minx, miny, maxx, maxy = regions.total_bounds

    ax.set_xlim(minx-1, maxx+1)
    ax.set_ylim(miny-1.5, maxy+1.5)

    regions.plot(column='bin', ax=ax, cmap='viridis_r', linewidth=0.2, alpha=0.8,
    legend=True, edgecolor='grey')

    handles, labels = ax.get_legend_handles_labels()

    fig.legend(handles[::-1], labels[::-1])

    ctx.add_basemap(ax, crs=regions.crs, source=ctx.providers.CartoDB.Voyager)    

    name = 'Population Density by Grid Tile (n={})'.format(n)
    fig.suptitle(name, fontsize=16, y=.97, fontname='Times New Roman')

    fig.tight_layout()
    path_out = os.path.join(VIS, 'population_density_km2')
    fig.savefig(path_out, dpi=600)

    plt.close(fig)


def plot_road_network(iso3):
    """
    Plot road network. 

    """
    filename = 'national_outline.shp'
    folder_in = os.path.join(DATA_PROCESSED, iso3)
    path_in = os.path.join(folder_in, filename)
    regions = gpd.read_file(path_in, crs='epsg:4326')#[:5]

    filename = 'road_network_processed.shp'
    folder_in = os.path.join(DATA_PROCESSED, iso3, 'infrastructure')
    path_in = os.path.join(folder_in, filename)
    roads = gpd.read_file(path_in, crs='epsg:4326')#[:5]

    motorway = roads[roads['fclass'] == 'motorway'] 
    primary = roads[roads['fclass'] == 'primary'] 
    secondary = roads[roads['fclass'] == 'secondary'] 
    tertiary = roads[roads['fclass'] == 'tertiary'] 

    sns.set(font_scale=1, font="Times New Roman")
    sns.set_style("ticks")
    fig, ax = plt.subplots(1, 1, figsize=(8,5.85))
    fig.set_facecolor('gainsboro')
    minx, miny, maxx, maxy = regions.total_bounds

    ax.set_xlim(minx-1, maxx+1)
    ax.set_ylim(miny-1.5, maxy+1.5)
    
    regions.plot(ax=ax, color='whitesmoke', linewidth=0.2, alpha=1, edgecolor='grey', zorder=1)
    motorway.plot(color='red', lw=.6, ax=ax, zorder=20)
    primary.plot(color='orange', lw=.4, ax=ax, zorder=15)
    secondary.plot(color='blue', lw=.2, ax=ax, zorder=10)
    tertiary.plot(color='grey', lw=0.2, ax=ax, zorder=5)

    handles, labels = ax.get_legend_handles_labels()

    fig.legend(handles[::-1], labels[::-1])

    ctx.add_basemap(ax, crs=regions.crs, source=ctx.providers.CartoDB.Voyager)    

    name = 'Key Segments of the Mexican Road Network'
    fig.suptitle(name, fontsize=16, y=.97, fontname='Times New Roman')

    plt.legend(['Motorway', 'Primary', 'Secondary', 'Tertiary'], loc='upper right', title='Road Types')

    fig.tight_layout()
    path_out = os.path.join(VIS, 'road_network.png')
    fig.savefig(path_out, dpi=600)

    plt.close(fig)


def plot_regions_by_investment_attractiveness(iso3):
    """
    Plot map. 

    """
    filename = 'gsm_tiles.shp'
    folder = os.path.join(BASE_PATH, '..', 'results', iso3, 'by_radio')
    path = os.path.join(folder, filename)
    shapes = gpd.read_file(path, crs='epsg:4326')

    bins = [-1, 10, 50, 100, 250, 500, 750, 1000, 2000, 5000, 1e8]
    labels = [
        '<10',
        '10-50',
        '50-100',
        '100-250',
        '250-500',
        '500-750',
        '750-1000',
        '1000-2000',
        '2000-5000',
        '>5000'
    ]

    shapes['bin'] = pd.cut(
        shapes['attractive'], 
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
        cmap='inferno_r', 
        linewidth=0.1,
        legend=True, 
        edgecolor='grey'
        )
    # country_shapes.plot(ax=base, facecolor="none", edgecolor='black', linewidth=0.75)

    handles, labels = ax.get_legend_handles_labels()

    fig.legend(handles[::-1], labels[::-1])

    ctx.add_basemap(ax, crs=shapes.crs, source=ctx.providers.CartoDB.Voyager)
    
    fig.suptitle('Investment attractiveness for mobile infrastructure deployment', 
                    fontsize=18, 
                    fontname='Times New Roman')

    fig.tight_layout()
    filename = 'investment_attractiveness.png'
    folder = os.path.join(VIS)
    if not os.path.exists(folder):
        os.mkdir(folder)
    fig.savefig(os.path.join(folder, filename), dpi=600)

    plt.close(fig)


if __name__ == '__main__':

    iso3 = 'MEX'

    plot_coverage(iso3)
    
    plot_regions_by_geotype(iso3)

    plot_road_network(iso3)

    plot_regions_by_investment_attractiveness(iso3)

    print('Complete')
