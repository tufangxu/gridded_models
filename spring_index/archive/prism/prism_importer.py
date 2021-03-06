#!/usr/bin/python3

from datetime import date
from datetime import timedelta
from urllib import request
from cgi import parse_header
from zipfile import ZipFile
import os.path
import psycopg2
from psycopg2.extensions import AsIs
import subprocess
import re
import glob


# prism_path = "D:\\prism_data"
# database_server = "localhost"
# database_name = "prism"
# database_user = "postgres"
# database_password = "npn"
# database_port = 5432

prism_path = "/home/jswitzer/prism_data"
database_server = "150.135.175.19"
database_name = "prism"
database_user = "postgres"
database_password = "usanpn123"
database_port = 5432

conn = psycopg2.connect(dbname=database_name, port=database_port, user=database_user,
                        password=database_password, host=database_server)
curs = conn.cursor()


def unzip(source_filename, dest_dir):
    with ZipFile(source_filename) as zf:
        for member in zf.infolist():
            words = member.filename.split(os.sep)
            path = dest_dir
            for word in words[:-1]:
                drive, word = os.path.splitdrive(word)
                head, word = os.path.split(word)
                if word in (os.curdir, os.pardir, ''):
                    continue
                path = os.path.join(path, word)
            zf.extract(member, path)


def postgis_import(filename, raster_date, climate_variable):
    table_name = climate_variable + '_' + raster_date[:4]
    # check if we need to create a new table
    new_table = True
    query = "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = %s;"
    curs.execute(query, [table_name])
    if curs.fetchone()[0] == 1:
        new_table = False

    # insert the raster (either create a new table or append to previously created table)
    if new_table:
        import_command = "raster2pgsql -s 4269 -c -I -C -M -F -t auto {file} public.{table}"\
            .format(file=filename, table=table_name)
    else:
        import_command = "raster2pgsql -s 4269 -a -M -F -t auto {file} public.{table}"\
            .format(file=filename, table=table_name)
    import_command2 = "psql -h {host} -p {port} -d {database} -U {user} --no-password"\
        .format(host=database_server, port=database_port, database=database_name, user=database_user)
    ps = subprocess.Popen(import_command, stdout=subprocess.PIPE, shell=True)
    subprocess.check_output(import_command2, stdin=ps.stdout, shell=True)
    ps.wait()

    # possibly set up extra table structure
    if new_table:
        query = "ALTER TABLE %(table)s ADD rast_date date;"
        curs.execute(query, {"table": AsIs(table_name)})
        conn.commit()
    query = "UPDATE %(table)s SET rast_date = to_date(%(raster_date)s, 'YYYY-MM-DD') WHERE rast_date IS NULL;"
    data = {"table": AsIs(table_name), "raster_date": raster_date}
    curs.execute(query, data)
    conn.commit()

    # create entry in mosaic table (for geoserver to work)
    if new_table:
        query = """
          CREATE TABLE IF NOT EXISTS mosaic(
          name text,
          tiletable text,
          minx float,
          miny float,
          maxx float,
          maxy float,
          resx float,
          resy float);"""
        curs.execute(query)
        conn.commit()

        query = "DELETE FROM mosaic WHERE tiletable = %s"
        curs.execute(query, [table_name])
        conn.commit()

        query = """
          INSERT INTO mosaic (name, tiletable, minx, miny, maxx, maxy, resx, resy)
          VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"""
        data = (table_name, table_name, -125, 49.9166666666687, -66.9, 24.2, 0.04166666666667, 0.04166666666667)
        curs.execute(query, data)
        conn.commit()


def download_zips(start_date, end_date, climate_variables):

    # create directory structure to store zips
    for climate_variable in climate_variables:
        zipped_files_path = prism_path + os.sep + "zipped" + os.sep + climate_variable + os.sep
        os.makedirs(os.path.dirname(zipped_files_path), exist_ok=True)
    unzip_path = prism_path + os.sep + "zipped" + os.sep + "temp" + os.sep
    os.makedirs(os.path.dirname(unzip_path), exist_ok=True)

    # make sure unzipped files path is cleaned out
    unzipped_files_path = unzip_path + "*.*"
    for unzipped_file in glob.glob(unzipped_files_path):
        os.remove(unzipped_file)

    delta = end_date - start_date
    for climate_variable in climate_variables:
        zipped_files_path = prism_path + os.sep + "zipped" + os.sep + climate_variable + os.sep
        for i in range(delta.days + 1):
            day = start_date + timedelta(days=i)

            # only download files we don't already have
            if not os.path.isfile(zipped_files_path + 'PRISM_' + climate_variable + '_stable_4kmD1_' +
                                          day.strftime("%Y%m%d") + '_bil.zip'):
                request_url = "http://services.nacse.org/prism/data/public/4km/{climate_var}/{date}"\
                    .format(climate_var=climate_variable, date=day.strftime("%Y%m%d"))
                response = request.urlopen(request_url)
                filename, _ = parse_header(response.headers.get('Content-Disposition'))
                filename = filename.replace("filename=", "").replace("\"", "")

                # Open zip file for writing
                if not os.path.isfile(zipped_files_path + filename):
                    with open(os.path.join(zipped_files_path, filename), "wb") as local_file:
                        local_file.write(response.read())

                # unzip the file
                unzip(zipped_files_path + filename, unzip_path)

                # import bil file into database as a raster
                bil_files_path = unzip_path + "*.bil"
                for bil_file in glob.glob(bil_files_path):
                    raster_date = re.search('4kmD1_(.*)_bil.bil', bil_file).group(1)
                    raster_date = '-'.join([raster_date[:4], raster_date[4:6], raster_date[6:]])
                    postgis_import(bil_file, raster_date, climate_variable)

                # delete unzipped files
                unzipped_files_path = unzip_path + "*.*"
                for unzipped_file in glob.glob(unzipped_files_path):
                    os.remove(unzipped_file)

request_params = ['tmax', 'tmin']
start = date(2013, 1, 1)
end = date(2013, 12, 31)
download_zips(start, end, request_params)