import spring_index.postgis_driver as driver
from datetime import *
import time
import logging
import yaml
import os.path
from spring_index.spring_index_util import *

with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.yml')), 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
log_path = cfg["log_path"]


def populate_yearly_prism_six(year):

    start_date = date(year, 1, 1)
    end_date = start_date + timedelta(days=250)

    climate_data_provider = 'prism'
    time_rez = 'year'

    plants = ['lilac', 'arnoldred', 'zabelli']
    phenophases = ['leaf', 'bloom']

    # compute individual plants
    driver.Six.load_daily_climate_data(start_date, end_date, climate_data_provider, 'conus')
    for plant in plants:
        for phenophase in phenophases:
            driver.Six.compute_daily_index(plant, phenophase)
            day = start_date
            driver.Six.create_raster(plant, phenophase, climate_data_provider, 'conus', day, time_rez)
            driver.Six.postgis_import(plant, phenophase, climate_data_provider, 'conus', day, time_rez)
            logging.info('calculated spring index for plant: %s phenophase: %s on day: %s', plant, phenophase, day)
    # compute averages
    driver.Six.leaf_average_array /= len(plants)
    driver.Six.bloom_average_array /= len(plants)
    for phenophase in phenophases:
        day = start_date
        driver.Six.create_raster("average", phenophase, climate_data_provider, 'conus', day, time_rez)
        driver.Six.postgis_import("average", phenophase, climate_data_provider, 'conus', day, time_rez)
        logging.info('calculated average spring index for phenophase: %s on day: %s', phenophase, day)
    driver.Six.cleanup()


def populate_yearly_prism_six_anomaly(years):
    phenophases = ['leaf', 'bloom']
    for year in years:
        for phenophase in phenophases:
            import_prism_on_prism_six_anomaly(year, phenophase)


# def populate_six_other(): # this function can be modified to populate daily prism or ncep si-x
#
#     today = date.today()
#     current_year = today.year
#     end_of_this_year = date(current_year, 12, 31)
#
#     start_date = date(2016, 1, 1)
#     end_date = today + timedelta(days=6)
#
#     # start_date = date(1980, 1, 1)
#     # end_date = end_of_this_year
#
#     climate_data_provider = 'prism' #'ncep'#"prism"
#     time_rez = 'year' #"day"
#
#     plants = ['lilac', 'arnoldred', 'zabelli']
#     phenophases = ['leaf', 'bloom']
#
#     # compute individual plants
#     driver.Six.load_daily_climate_data(start_date, end_date, climate_data_provider, 'conus')
#     for plant in plants:
#         for phenophase in phenophases:
#             driver.Six.compute_daily_index(plant, phenophase)
#             delta = end_date - start_date
#             for i in range(delta.days + 1):
#                 day = start_date + timedelta(days=i)
#                 driver.Six.create_raster(plant, phenophase, climate_data_provider, 'conus', day, time_rez)
#                 driver.Six.postgis_import(plant, phenophase, climate_data_provider, 'conus', day, time_rez)
#                 logging.info('calculated spring index for plant: %s phenophase: %s on day: %s', plant, phenophase, day)
#     # compute averages
#     driver.Six.leaf_average_array /= len(plants)
#     driver.Six.bloom_average_array /= len(plants)
#     for phenophase in phenophases:
#         delta = end_date - start_date
#         for i in range(delta.days + 1):
#             day = start_date + timedelta(days=i)
#             driver.Six.create_raster("average", phenophase, climate_data_provider, 'conus', day, time_rez)
#             driver.Six.postgis_import("average", phenophase, climate_data_provider, 'conus', day, time_rez)
#             logging.info('calculated average spring index for phenophase: %s on day: %s', phenophase, day)
#     driver.Six.cleanup()

# This script is used to populate the spring index for historic years. It is not ran nightly.
# Before running this script populate_prism.py must be ran for the years you want to generate spring index maps.
# Unless the prism climate data has been populated somewhere else.
def main():

    logging.basicConfig(filename=log_path + 'populate_six.log',
                        level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    t0 = time.time()

    logging.info(' ')
    logging.info('*****************************************************************************')
    logging.info('***********beginning script populate_six.py*****************')
    logging.info('*****************************************************************************')

    today = date.today()
    current_year = today.year
    previous_year = current_year - 1

    #populate prism spring index for previous year
    #populate_yearly_prism_six(previous_year) #todo uncomment

    # populate prism on prism anomaly for previous year
    years = list(range(1981, 2018)) #todo change these years after initial populate
    populate_yearly_prism_six_anomaly(years)

    t1 = time.time()
    logging.info('*****************************************************************************')
    logging.info('***********populate_six.py finished in %s seconds***********', t1-t0)
    logging.info('*****************************************************************************')

if __name__ == "__main__":
    main()
