#!/usr/bin/python3
from climate.importer import *
from prism.importer import get_prism_data
from datetime import date
from datetime import timedelta
import logging
from util.log_manager import get_error_log
import time
import yaml
import os.path
from util.log_manager import get_error_log


with open(os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.yml')), 'r') as ymlfile:
    cfg = yaml.load(ymlfile)
log_path = cfg["log_path"]


# This script is ran nightly before gridded_models_nightly_update.py and grabs climate data from
# various data sources, uses it to generate geotiffs and imports it into a postgis database.
def main():
    t0 = time.time()

    today = date.today()
    current_year = today.year
    one_week_ago = today - timedelta(days=7)
    one_week_into_future = today + timedelta(days=7)
    beginning_of_this_year = date(current_year, 1, 1)
    one_year_ago = today - timedelta(days=365)

    logging.info(' ')
    logging.info('*****************************************************************************')
    logging.info('***********beginning script populate_climate_data.py*****************')
    logging.info('*****************************************************************************')

    # # download and import ndfd forecast temps for the next week
    # # overwrites all files previously downloaded files
    # download_forecast('conus')
    # download_forecast('alaska')
    #
    # # downloads hourly rtma/urma temps into our postgis db for the past 24 hours (each hour represents GMT)
    # # overwrites all files previously downloaded files
    # download_hourly_temps('rtma', 'conus')
    # download_hourly_temps('urma', 'conus')
    #
    # download_hourly_temps('rtma', 'alaska')
    # download_hourly_temps('urma', 'alaska')
    #
    # # downloads hourly rtma/urma uncertainty into our postgis db for the past 24 hours (each hour represents GMT)
    # # overwrites all files previously downloaded files
    # download_hourly_temp_uncertainty('rtma')
    # download_hourly_temp_uncertainty('urma')
    #
    # # download and import rtma data for the date range that was missed for any reason
    # # this looks back one week,
    # # another script is in place to delete rtma data older than two weeks for which we also have urma data
    # # won't overwrite any previously downloaded files
    # download_historic_climate_data(one_week_ago, today, 'rtma', 'conus')
    # # alaska historic rtma temps don't exist in the archive
    # # download_historic_climate_data(one_week_ago, today, 'rtma', 'alaska')

    # compute daily tmin/tmax based on hourly data
    # computation is based on mixture of rtma and urma data; rtma is only used when urma isn't available
    # overwrites files less than 7 days old so the flow of tmin/tmax through time goes from
    # urma -> urma/rtma -> forecast
    # hour_shift makes data match prism (prism day goes from -12 utc to +12 utc)
    hour_shift = -12
    # compute_tmin_tmax(min(beginning_of_this_year, one_week_ago), one_week_into_future, hour_shift, 7, 'conus')
    compute_tmin_tmax(min(beginning_of_this_year, one_week_ago), one_week_into_future, hour_shift, 7, 'alaska')

    # # POPULATE PRISM
    # # Specify the climate elements you want to download as well as the date range to download those elements for:
    # request_params = ['tmax', 'tmin']
    # get_prism_data(one_year_ago, today, request_params)

    t1 = time.time()
    logging.info('*****************************************************************************')
    logging.info('***********populate_climate_data.py finished in %s seconds***********', t1 - t0)
    logging.info('*****************************************************************************')


if __name__ == "__main__":
    logging.basicConfig(filename=log_path + 'populate_climate_data.log',
                        level=logging.INFO,
                        format='%(asctime)s %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    error_log = get_error_log()

    try:
        main()
    except (SystemExit, KeyboardInterrupt):
        raise
    except:
        error_log.error('populate_climate_data.py failed to finish: ', exc_info=True)

