"""
Process backcast. 

Ed Oughton

July 2023

"""
import sys
import os
import configparser
import json
import pandas as pd

CONFIG = configparser.ConfigParser()
CONFIG.read(os.path.join(os.path.dirname(__file__),'..', 'scripts', 'script_config.ini'))
BASE_PATH = CONFIG['file_locations']['base_path']

DATA_RAW = os.path.join(BASE_PATH, '..', '..', 'data_raw')
DATA_PROCESSED = os.path.join(BASE_PATH, 'processed')
RESULTS = os.path.join(BASE_PATH, '..', 'results')


def load_population(country):
    """
    Load population data. 
    
    """
    filename = 'population.csv'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'], 'population')
    path_in = os.path.join(folder_in, filename)
    data_pop = pd.read_csv(path_in)
    data_pop = data_pop.to_dict('records')
    output = data_pop

    return output


def load_cells(country):
    """
    Loads cells data. 

    """
    filename = 'cells_by_region.csv'
    folder_in = os.path.join(DATA_PROCESSED, country['iso3'], 'sites')
    path_in = os.path.join(folder_in, filename)
    data_cells = pd.read_csv(path_in)
    data_cells = data_cells.to_dict('records')

    output = {}

    for cells in data_cells:
        output[cells['gid_id']] = {
            'gsm': cells['gsm'],
            'umts': cells['umts'],
            'lte': cells['lte'],
        }

    return output


def generate_backcast(country, pop_lut, cells):
    """
    Generate backcast data.

    """
    pop_lut = sorted(pop_lut, key=lambda d: d['population_km2'], reverse=True) 

    cash_to_spend = 1e8
    cost_per_cell = 30000
    gsm, umts, lte = get_total_cells(cells)

    for radio in ['gsm','umts','lte']:

        output = []
        built = set()
        start = start_year(radio)

        for year in range (start, 2021):

            spent = 0
            cost_per_cell = 30000

            for region in pop_lut:
                if not region['GID_id'] in built:
                    if spent < cash_to_spend:
                        if region['GID_id'] in cells.keys():
                            cells_to_build = cells[region['GID_id']][radio]
                            cost = cells_to_build * cost_per_cell
                        else:
                            continue

                        output.append({
                            'year': year,
                            'gid_id': region['GID_id'],
                            'cells_to_build': cells_to_build,
                            'radio': radio,
                            'cost': cost,
                            'population_served': round(region['population'])
                        })

                        built.add(region['GID_id'])
                        spent += cost

        output = pd.DataFrame(output)

        filename = '{}.csv'.format(radio)
        folder_out = os.path.join(RESULTS, country['iso3'], 'by_radio')
        if not os.path.exists(folder_out):
            os.makedirs(folder_out)
        path_output = os.path.join(folder_out, filename)
        output.to_csv(path_output, index=False)

    return


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
        return 2000 
    elif radio == 'umts':
        return 2008
    elif radio == 'lte':
        return 2013


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


if __name__ == "__main__":

    MEX = {
        'iso3': 'MEX',
        'gid_region': 2,
    }
    
    print('Loading population data')
    pop_lut = load_population(MEX)

    print('Loading cell data')
    cells = load_cells(MEX)

    print('Generating backcast results')
    generate_backcast(MEX, pop_lut, cells)

    print('Aggregating results')
    aggregate_results(MEX)
