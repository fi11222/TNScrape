#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

# Required packages

# MySQL server : sudo apt-get install mysql-server

# PhpMyAdmin : sudo apt-get install phpmyadmin

# Python MySQL Connector : sudo apt-get install python3-mysql.connector

# TB_GEO file made with data from:
# https://www.data.gouv.fr/fr/datasets/listes-des-communes-geolocalisees-par-regions-departements-circonscriptions-nd/
# http://www.nosdonnees.fr/wiki/index.php/Fichier:EUCircos_Regions_departements_circonscriptions_communes_gps.csv.gz
# http://datanova.legroupe.laposte.fr/explore/?refine.keyword=la-poste&refine.keyword=code+postal&sort=modified

# Voir aussi:
# http://blog.niap3d.com/fr/4,10,news-50-Liste-des-communes-francaises.html
# http://public.opendatasoft.com/explore/dataset/correspondance-code-insee-code-postal/

import argparse
import sys
import re
import os
import glob
import csv
import datetime

import mysql.connector

import CommonFunctions

# ------------------------------------------------- Globals -----------------------------------------------------
g_MergeDir = './Merge/'
g_defaultPassword = 'TNScrape'
g_defaultDatabase = 'TNScrapeDB'
g_categoryPath = 'Categorties.csv'
g_geoPath = 'TB_GEO.csv'

g_tableTemplateDrop = """
    DROP TABLE IF EXISTS `{0}`;
"""

g_viewTemplateDrop = """
    DROP VIEW IF EXISTS `{0}`;
"""

g_tableTemplateCreateA = """
    CREATE TABLE `{0}` (
      `ID` varchar(20) DEFAULT NULL,
      `MERGE_KEY` varchar(30) DEFAULT NULL,
      `NAME` varchar(200) DEFAULT NULL,
      `ADDRESS` varchar(200) DEFAULT NULL,
      `CP` varchar(10) DEFAULT NULL,
      `CITY` varchar(100) DEFAULT NULL,
      `CREATION` varchar(10) DEFAULT NULL,
      `SIRET` varchar(10) DEFAULT NULL,
      `TYPE` varchar(10) DEFAULT NULL,
      `COUNT` varchar(20) DEFAULT NULL,
      `OWNER` varchar(30) DEFAULT NULL,
      `TEL1` varchar(20) DEFAULT NULL,
      `TEL2` varchar(20) DEFAULT NULL,
      `TEL3` varchar(20) DEFAULT NULL,
      `TEL4` varchar(20) DEFAULT NULL,
      `MAIL` varchar(100) DEFAULT NULL,
      `WEB1` varchar(200) DEFAULT NULL,
      `WEB2` varchar(200) DEFAULT NULL,
      `WEB3` varchar(200) DEFAULT NULL,
      `WEB4` varchar(200) DEFAULT NULL,
      `HOURS` text DEFAULT NULL,
      `BUSINESS` text DEFAULT NULL,
      `ADDITIONAL` text DEFAULT NULL,
      KEY `MERGE_KEY` (`MERGE_KEY`),
      PRIMARY KEY `ID` (`ID`)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8;
"""

g_viewTemplateCreateA = """
    CREATE VIEW `{0}` as
    SELECT
      min(`ID`) as `ID`
      , `MERGE_KEY`
      , max(`NAME`) as `NAME`
      , max(`ADDRESS`) as `ADDRESS`
      , max(`CP`) as `CP`
      , max(`CITY`) as `CITY`
      , max(`CREATION`) as `CREATION`
      , max(`SIRET`) as `SIRET`
      , max(`TYPE`) as `TYPE`
      , max(`COUNT`) as `COUNT`
      , max(`OWNER`) as `OWNER`
      , max(`TEL1`) as `TEL1`
      , max(`TEL2`) as `TEL2`
      , max(`TEL3`) as `TEL3`
      , max(`TEL4`) as `TEL4`
      , max(`MAIL`) as `MAIL`
      , max(`WEB1`) as `WEB1`
      , max(`WEB2`) as `WEB2`
      , max(`WEB3`) as `WEB3`
      , max(`WEB4`) as `WEB4`
      , max(`HOURS`) as `HOURS`
      , max(`BUSINESS`) as `BUSINESS`
      , max(`ADDITIONAL`) as `ADDITIONAL`
    from `{1}`
    group by `MERGE_KEY`;
"""

g_tableTemplateCreateB = """
    CREATE TABLE `{0}` (
      `MERGE_KEY` varchar(30) DEFAULT NULL,
      `ID` varchar(20) DEFAULT NULL,
      `TYPE` varchar(30) DEFAULT NULL,
      `RAW` varchar(200) DEFAULT NULL,
      `CLEAN` varchar(200) DEFAULT NULL,
      `FLAG` varchar(10) DEFAULT NULL,
      KEY `ID` (`ID`)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8;
"""

# ---------------------------------------------------- Functions ------------------------------------------------
def createTableAndLoad(p_connector, p_file, p_table, p_tableId):
    l_cursor = p_connector.cursor()
    l_cursor.execute(g_tableTemplateDrop.format(p_table))
    if re.search('A_',p_file ):
        l_cursor.execute(g_tableTemplateCreateA.format(p_table))
    else:
        l_cursor.execute(g_tableTemplateCreateB.format(p_table))
    l_cursor.close()

    if re.search('A_',p_file ):
        l_cursor = p_connector.cursor()
        l_viewName = re.sub('^TB_', 'V_', p_table)
        l_cursor.execute(g_viewTemplateDrop.format(l_viewName))
        l_cursor.execute(g_viewTemplateCreateA.format(l_viewName, p_table))
        l_cursor.close()

    if os.path.isfile(p_file):
        # open csv reader
        with open(p_file, 'r') as l_csvFile:
            l_reader = csv.reader(l_csvFile, delimiter=';', quotechar='"', lineterminator='\n')

            # skip first row (col headers)
            next(l_reader, None)

            for l_row in l_reader:
                if re.search('A_',p_file ):
                    # first phone if available, otherwise second phone if available, otherwise company name
                    l_mergeKey = re.sub('\s+', '', l_row[10]) if l_row[10].strip() != '' else \
                        (re.sub('\s+', '', l_row[11]) if l_row[11].strip() != '' else
                         re.sub('\s+', '_', l_row[1])[0:30])

                    l_row.insert(1, l_mergeKey)
                    # print(l_mergeKey, '-->', l_row[0:4])
                # else:
                    # print(l_row[0:4])

                # make ID globally unique by adding the table ID
                l_row[0] = str(p_tableId).zfill(2) + '-' + l_row[0]

                if re.search('B_',p_file ):
                    # if B file, add a field (future MERGE_KEY)
                    l_row = [''] + l_row

                l_cursor = p_connector.cursor()
                l_query = """
                    INSERT INTO `{0}`
                    VALUES( "{1}" )
                """.format(
                    p_table,
                    '", "'.join([re.sub('"', '""', x) for x in l_row])
                )
                # print(l_query)
                l_cursor.execute(l_query)
                p_connector.commit()
                l_cursor.close()

def countContent(p_connector, p_tblorView):
    l_cursor = p_connector.cursor(buffered=True)
    l_cursor.execute('select count(1) as COUNT from `{0}`'.format(p_tblorView))
    l_count = 0
    for l_count, in l_cursor:
        l_count = int(l_count)
    l_cursor.close()

    return l_count

def cleanCat(p_cat):
    l_cat = re.sub('\s+', '__SPACE__', p_cat)
    l_cat = re.sub('\'', '__APO__', l_cat)
    l_cat = re.sub('\W+', '', l_cat)
    l_cat = re.sub('__SPACE__', ' ', l_cat).strip()
    l_cat = re.sub('__APO__', '\'', l_cat).lower()

    return l_cat

# ---------------------------------------------------- Main section ---------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| Scraped Data Merging Script                                |')
    print('|                                                            |')
    print('| Contractor: Kabir Abdulhamid / Upwork                      |')
    print('|                                                            |')
    print('| Client: Teddy Nestor                                       |')
    print('|                                                            |')
    print('| v. 2.2 - 31/03/2016                                        |')
    print('| + export in Directory WP format                            |')
    print('| + lat/long scrapting from                                  |')
    print('+------------------------------------------------------------+')

    # create Merge dir if not exist
    if not os.path.isdir(g_MergeDir):
        os.makedirs(g_MergeDir)

    # list of arguments
    l_parser = argparse.ArgumentParser(description='Merge Script for TNScrape CSV files')
    l_parser.add_argument('result', help='Name of Result')
    l_parser.add_argument('--noText', help='Remove text content from items (default: False)',
                          action='store_true')
    l_parser.add_argument('--geo', help='Fetch lat/long from Google Geo API (default: False)',
                          action='store_true')
    l_parser.add_argument('--dir', help='Merge Directory (default: {0})'.format(g_MergeDir))
    l_parser.add_argument('--password',
                          help='MySQL root password (default: {0})'.format(g_defaultPassword),
                          default=g_defaultPassword)
    l_parser.add_argument('--database',
                          help='MySQL Database (default: {0})'.format(g_defaultDatabase),
                          default=g_defaultDatabase)

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.result = None
            self.noText = False
            self.geo = False
            self.dir = g_MergeDir
            self.password = g_defaultPassword
            self.database = g_defaultDatabase

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    # local variables (why did I do this ?)
    l_dir = c.dir
    l_geoLoc = c.geo
    l_noText = c.noText
    l_password = c.password
    l_database = c.database
    l_result = re.sub('\s+', '_', c.result).strip()
    l_resultPath = os.path.join('./', l_result + '.csv')

    # create database if not exists
    try:
        l_connector = mysql.connector.connect(
            user='root',
            password=l_password,
            host='localhost')

        l_cursor = l_connector.cursor()
        l_cursor.execute(
            'CREATE DATABASE if not exists`{0}` CHARACTER SET utf8 COLLATE utf8_general_ci;'.format(l_database))
        l_cursor.close()
        l_connector.close()
    except mysql.connector.Error as e:
        print(e)
        print('Connection to local MySQL server failed. Check installation and root password')
        sys.exit(0)
    except Exception as e:
        print(e)
        print('Unknown Error')
        sys.exit(0)

    # displays parameters
    print('Result Name         :', c.result)
    print('Input Directory     :', c.dir)
    print('MySQL root Password :', c.password)
    print('Database            :', c.database)
    print('Remove Item Text    :', l_noText)
    print('Geolocalization     :', l_geoLoc)
    print('--> Result Path     :', l_resultPath)

    l_connector = mysql.connector.connect(
        user='root',
        password=l_password,
        host='localhost',
        database=l_database)

    # load files
    l_tables = []

    print()
    l_tableCount = 0
    for l_fileA in glob.glob(os.path.join(l_dir, '*A_*.csv')):
        l_fileB = re.sub('A_', 'B_', l_fileA)
        if os.path.isfile(l_fileA) and os.path.isfile(l_fileB):
            l_tableA = 'TB_' + os.path.basename(re.sub('A_', '_A_', l_fileA)).upper()
            l_tableB = 'TB_' + os.path.basename(re.sub('B_', '_B_', l_fileB)).upper()

            l_tableA = re.sub('\.CSV$', '', l_tableA)
            l_tableB = re.sub('\.CSV$', '', l_tableB)

            l_tableA = re.sub('[^A-Za-z0-9]', '_', l_tableA)
            l_tableB = re.sub('[^A-Za-z0-9]', '_', l_tableB)
            print('Loading \n   {0} and \n   {1} into \n   {2} and \n   {3}'.format(
                l_fileA, l_fileB, l_tableA, l_tableB))

            # create tables
            createTableAndLoad(l_connector, l_fileA, l_tableA, l_tableCount)
            createTableAndLoad(l_connector, l_fileB, l_tableB, l_tableCount)

            # MERGE_KEY A -> B
            l_query = """
                update
                    `{0}` as B
                    join `{1}` as A
                    on B.ID = A.ID
                set B.MERGE_KEY = A.MERGE_KEY;
            """.format(l_tableB, l_tableA)

            l_cursor = l_connector.cursor()
            l_cursor.execute(l_query)
            l_connector.commit()
            l_cursor.close()

            l_tables += [(l_tableA, l_tableB)]
            l_tableCount += 1

    # create result tables
    l_resultTableA = 'TB_A_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()
    l_resultTableB = 'TB_B_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()

    l_cursor = l_connector.cursor()
    l_cursor.execute(g_tableTemplateDrop.format(l_resultTableA))
    l_cursor.execute(g_tableTemplateDrop.format(l_resultTableB))
    l_cursor.execute(g_tableTemplateCreateA.format(l_resultTableA))
    l_cursor.execute(g_tableTemplateCreateB.format(l_resultTableB))
    l_cursor.close()

    # load result table
    for l_tbA, l_tbB in l_tables:
        print('Transfering {0} into {1}'.format(l_tbA, l_resultTableA))
        l_cursor = l_connector.cursor()
        l_cursor.execute('insert into `{0}` select * from `{1}`;'.format(l_resultTableA, l_tbA))
        l_connector.commit()
        l_cursor.close()

        print('Transfering {0} into {1}'.format(l_tbB, l_resultTableB))
        l_cursor = l_connector.cursor()
        l_cursor.execute('insert into `{0}` select * from `{1}`;'.format(l_resultTableB, l_tbB))
        l_connector.commit()
        l_cursor.close()

    # creating result view
    l_resultView = re.sub('TB_A_', 'V_', l_resultTableA)

    print('Creating view', l_resultView)
    l_cursor = l_connector.cursor()
    l_cursor.execute(g_viewTemplateDrop.format(l_resultView))
    l_cursor.execute(g_viewTemplateCreateA.format(l_resultView, l_resultTableA))
    l_cursor.close()

    # results output
    print('Writing results to', l_resultPath)
    with open(l_resultPath, 'w') as l_fOutA:
        l_csvWriterA = \
            csv.writer(l_fOutA, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)
        l_csvWriterA.writerow(['ID', 'MERGE_KEY', 'NAME', 'ADDRESS', 'CP', 'CITY', 'CREATION',
                               'SIRET', 'TYPE', 'COUNT', 'OWNER', 'TEL1', 'TEL2', 'TEL3', 'TEL4',
                               'MAIL', 'WEB1', 'WEB2', 'WEB3', 'WEB4', 'HOURS', 'BUSINESS', 'ADDITIONAL'])

        l_cursor = l_connector.cursor(buffered=True)
        l_cursor.execute('select * from `{0}` order by left(CP,2),NAME'.format(l_resultView))

        for l_row in l_cursor:
            l_rowCsv = [CommonFunctions.cleanField(x) for x in list(l_row)]
            l_csvWriterA.writerow(l_row)

        l_cursor.close()

    # origin identification
    l_tbId = 0
    l_joinBlock = ''
    l_columnsBlock = ''
    for l_tbA, l_tbB in l_tables:
        l_viewName = re.sub('^TB_', 'V_', l_tbA)
        l_joinBlock += '            ' + \
            'left outer join `{0}` as `V{1}` on R.MERGE_KEY = `V{1}`.MERGE_KEY\n'.format(l_viewName, l_tbId)
        l_columnsBlock += '            ' + \
            ', if(isnull(`V{0}`.MERGE_KEY), "", "X") as `{1}`\n'.format(l_tbId, l_tbA)

        l_tbId += 1

    l_originView = l_resultView + '_ORIGIN'
    l_query = """
        create view `{3}` as
        select
            R.ID
            , R.MERGE_KEY
            , R.NAME
            , R.ADDRESS
            , R.CP\n{2}
        from
            `{0}` as R\n{1}
    """.format(l_resultView, l_joinBlock, l_columnsBlock, l_originView)

    print('Creating view', l_originView)
    l_cursor = l_connector.cursor()
    l_cursor.execute(g_viewTemplateDrop.format(l_originView))
    l_cursor.execute(l_query)
    l_cursor.close()

    l_resultOriginPath = re.sub('\.csv$', '_origin.csv', l_resultPath)
    print('Writing origin of results to', l_resultOriginPath)
    with open(l_resultOriginPath, 'w') as l_fOutA:
        l_csvWriter = \
            csv.writer(l_fOutA, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)
        l_csvWriter.writerow(['ID', 'MERGE_KEY', 'NAME', 'ADDRESS', 'CP'] + [t[0] for t in l_tables])

        l_cursor = l_connector.cursor(buffered=True)
        l_cursor.execute('select * from `{0}` order by left(CP,2),NAME'.format(l_originView))

        for l_row in l_cursor:
            l_rowCsv = [CommonFunctions.cleanField(x) for x in list(l_row)]
            l_csvWriter.writerow(l_row)

        l_cursor.close()

    # Export in Directory WP format ------------------------------------------------------------------------------------
    print()
    print('---------------------- WP Directory+ Output --------------------------')

    # Load category Dict ***********************************************************************************************
    l_catDict = dict()
    try:
        with open(g_categoryPath, 'r') as l_fCat:
            print('Loading category table from', g_categoryPath)
            l_reader = csv.reader(l_fCat, delimiter=',', lineterminator='\n')

            # skip first row (col headers)
            next(l_reader, None)

            for r in l_reader:
                l_catDict[cleanCat(r[0])] = cleanCat(r[1])

    except FileNotFoundError:
        pass

    # Load Geography Table *********************************************************************************************
    try:
        with open(g_geoPath, 'r') as l_fGeo:
            print('Loading geography table from', g_geoPath)
            l_reader = csv.reader(l_fGeo, delimiter=';', quotechar='"', lineterminator='\n')

            l_cursor = l_connector.cursor()
            l_cursor.execute(g_tableTemplateDrop.format('TB_GEO'))
            l_cursor.execute("""
                CREATE TABLE TB_GEO (
                  `ID` varchar(5) DEFAULT NULL,
                  `NAME` varchar(200) DEFAULT NULL,
                  `PARENT` varchar(5) DEFAULT NULL,
                  KEY `ID` (`ID`)
                ) ENGINE=MyISAM DEFAULT CHARSET=utf8;
            """)
            l_connector.commit()

            # skip first row (col headers)
            next(l_reader, None)

            for r in l_reader:
                l_query = """
                        INSERT INTO TB_GEO
                        VALUES( "{0}" )
                    """.format('", "'.join([re.sub('"', '""', x) for x in r]))
                l_cursor.execute(l_query)
                l_connector.commit()

            # Eliminate CP absent from the TB_GEO table (mostly CEDEX)
            l_cursor.execute("""
                update
                    `{0}` as R
                    left outer join TB_GEO as G
                    on R.CP = G.ID
                set
                    R.CP = concat(left(R.CP, 2), '000')
                where
                    G.ID is null
            """.format(l_resultTableA))
            l_connector.commit()

            l_cursor.close()
    except FileNotFoundError:
        pass


    l_itemsPath = re.sub('\.csv', '_items.csv', l_resultPath)
    print('Writing A results to', l_itemsPath)
    l_geoLocCount = 0
    with open(l_itemsPath, 'w') as l_fOutA:
        l_csvWriterA = \
            csv.writer(l_fOutA, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)
        l_csvWriterA.writerow(['sep=;'])
        l_csvWriterA.writerow(['post_name', 'post_title', 'post_status', 'post_content',
                               'post_excerpt', 'post_author', 'post_parent', 'post_date',
                               'comment_status', 'ping_status', 'post_image', 'ait-items',
                               'ait-locations', 'subtitle', 'featuredItem', 'headerImage',
                               'headerHeight', 'address', 'latitude', 'longitude', 'streetview',
                               'telephone', 'telephoneAdditional@number', 'email', 'showEmail', 'contactOwnerBtn',
                               'web', 'webLinkLabel', 'displayOpeningHours', 'openingHoursMonday',
                               'openingHoursTuesday', 'openingHoursWednesday', 'openingHoursThursday',
                               'openingHoursFriday', 'openingHoursSaturday', 'openingHoursSunday',
                               'openingHoursNote', 'displaySocialIcons', 'socialIconsOpenInNewWindow',
                               'socialIcons@icon', 'socialIcons@link', 'displayGallery', 'gallery@title',
                               'gallery@image', 'displayFeatures', 'features@icon', 'features@text', 'features@desc'])

        l_cursor = l_connector.cursor(buffered=True)
        # l_csvWriterA.writerow(['ID', 'MERGE_KEY', 'NAME', 'ADDRESS', 'CP', 'CITY', 'CREATION',
        #                        'SIRET', 'TYPE', 'COUNT', 'OWNER', 'TEL1', 'TEL2', 'TEL3', 'TEL4',
        #                        'MAIL', 'WEB1', 'WEB2', 'WEB3', 'WEB4', 'HOURS', 'BUSINESS', 'ADDITIONAL'])
        l_cursor.execute("""
            select MERGE_KEY
                , ID                       # 00 post_name
                , NAME                      # 01 post_title
                , 'publish'                 # 02 post_status
                , ADDITIONAL                # 03 post_content
                , left(ADDITIONAL, 100)     # 04 post_excerpt
                , '1'                       # 05 post_author
                , '0'                       # 06 post_parent
                , '{1}'                     # 07 post_date
                , 'closed'                  # 08 comment_status
                , 'open'                    # 09 ping_status
                , ''                        # 10 post_image
                , BUSINESS                  # 11 ait-items
                , CP                        # 12 ait-locations
                , ''                        # 13 subtitle
                , '1'                       # 14 featuredItem
                , ''                        # 15 headerImage
                , ''                        # 16 headerHeight
                , concat(ADDRESS, ', ', CP, ' ', CITY)   # 17 address
                , ''                        # 18 latitude
                , ''                        # 19 longitude
                , '0'                       # 20 streetview
                , TEL1                      # 21 telephone
                , concat(TEL2, ' ', TEL3)   # 22 telephoneAdditional
                , MAIL                      # 23 email
                , '1'                       # 24 showEmail
                , '1'                       # 25 contactOwnerBtn
                , WEB1                      # 26 web
                , ''                        # 27 webLinkLabel
                , '1'                       # 28 displayOpeningHours
                , HOURS                     # 29 openingHoursMonday
                , ''                        # 30 openingHoursTuesday
                , ''                        # 31 openingHoursWednesday
                , ''                        # 32 openingHoursThursday
                , ''                        # 33 openingHoursFriday
                , ''                        # 34 openingHoursSaturday
                , ''                        # 35 openingHoursSunday
                , ''                        # 36 openingHoursNote
                , '1'                       # 37 displaySocialIcons
                , '0'                       # 38 socialIconsOpenInNewWindow
                , ''                        # 39 socialIcons@icon
                , ''                        # 40 socialIcons@link
                , '0'                       # 41 displayGallery
                , ''                        # 42 gallery@title
                , ''                        # 43 gallery@image
                , '0'                       # 44 displayFeatures
                , ''                        # 45 features@icon
                , ''                        # 46 features@text
                , ''                        # 47 features@desc
            from `{0}`
            order by left(CP,2),NAME
        """.format(
            l_resultView,
            (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')))

        for l_row in l_cursor:
            l_row = list(l_row)

            l_mergeKey = l_row[0]
            l_row = l_row[1:]

            # item ID
            l_row[0] = l_result + '_' + l_row[0]

            # addres cleanup
            l_row[17] = re.sub('([;,:\.])[;,:\.]', r'\1', l_row[17])

            # geolocalization
            if l_geoLoc:
                # 17 address
                l_address = l_row[17]
                if not re.search('98000\s+MONACO', l_address):
                    l_address = re.sub('\s+', ' ', l_address + ' france').strip()
                else:
                    l_address = re.sub('\s+', ' ', l_address).strip()

                l_lat, l_long = CommonFunctions.getLatLong(l_address)
                if l_lat is not None:
                    # 18 latitude
                    # 19 longitude
                    l_row[18] = str(l_lat)
                    l_row[19] = str(l_long)

                    # 20 streetview
                    l_row[20] = '1'

                    l_geoLocCount += 1

            # Remove item text if required
            # 03 post_content
            # 04 post_excerpt
            if l_noText:
                l_row[3] = ''
                l_row[4] = ''

            # Opening hours --------------------------------------------------------------------------------------------
            l_hours = l_row[29]
            l_hoursDict = {
                'Mo': 0,
                'Tu': 1,
                'We': 2,
                'Th': 3,
                'Fr': 4,
                'Sa': 5,
                'Su': 6,
            }
            l_hoursList = [[], [], [], [], [], [], []]
            for l_hour in l_hours.split('|'):
                l_match = re.match('([A-Z][a-z])\s+(\d\d:\d\d-\d\d:\d\d)', l_hour)
                if l_match:
                    l_day = l_match.group(1)
                    l_open = l_match.group(2)

                    l_hoursList[l_hoursDict[l_day]] += [l_open]

            l_hoursList = [' '.join(d) for d in l_hoursList]
            l_row[29:36] = l_hoursList

            # Numéros de téléphone -------------------------------------------------------------------------------------
            l_query = """
                select
                    max(TYPE) as TYPE
                    , CLEAN
                from `{0}`
                where
                    MERGE_KEY = '{1}'
                    and (TYPE like '%Phone' or TYPE = 'Fax')
                    and length(CLEAN) > 0
                group by CLEAN
            """.format(l_resultTableB, re.sub('\'', r'\'', l_mergeKey))
            # print(l_query)

            l_cursorTel = l_connector.cursor(buffered=True)
            l_cursorTel.execute(l_query)

            # print(l_mergeKey)
            l_firstPhone = ''
            l_otherPhoneList = []
            for l_type, l_number in l_cursorTel:
                # print('   ', l_type, l_number)
                if re.sub('\s+', '', l_number) == l_mergeKey:
                    l_firstPhone = l_number
                else:
                    l_otherPhoneList += [l_number]
            # 21 telephone  22 telephoneAdditional
            l_row[21] = l_firstPhone
            l_row[22] = '|'.join(l_otherPhoneList)

            l_cursorTel.close()

            # Business Categories --------------------------------------------------------------------------------------
            l_query = """
                select CLEAN
                from `{0}`
                where
                    MERGE_KEY = '{1}'
                    and TYPE = 'BusinessCategory'
                    and length(CLEAN) > 0
            """.format(l_resultTableB, re.sub('\'', r'\'', l_mergeKey))
            # print(l_query)
            l_cursorCat = l_connector.cursor(buffered=True)
            l_cursorCat.execute(l_query)

            # print(l_mergeKey)
            l_catList = []
            for l_cat, in l_cursorCat:
                l_catList += [cleanCat(l_cat)]
            l_cursorCat.close()

            l_catList2 = []
            for l_cat in l_catList:
                if l_cat in l_catDict.keys():
                    # print(l_cat, '-->', l_catDict[l_cat])
                    l_cat = l_catDict[l_cat]
                else:
                    l_catDict[l_cat] = l_cat

                l_catList2 += [l_cat]

            l_catList2.sort()

            l_prevCat = ''
            l_categoryList = []
            for l_cat in l_catList2:
                if l_cat != l_prevCat:
                    l_prevCat = l_cat
                    l_categoryList += [l_cat]

            # 11 ait-items
            l_row[11] = '|'.join(l_categoryList)

            # Web Sites ------------------------------------------------------------------------------------------------
            l_query = """
                select CLEAN
                from `{0}`
                where
                    MERGE_KEY = '{1}'
                    and TYPE = 'WebSite'
                    and length(CLEAN) > 0
            """.format(l_resultTableB, re.sub('\'', r'\'', l_mergeKey))
            # print(l_query)
            l_cursorCat = l_connector.cursor(buffered=True)
            l_cursorCat.execute(l_query)

            l_webList = []
            l_socialList = []
            for l_web, in l_cursorCat:
                l_webList += [l_web]

            l_webList.sort()
            l_webList2 = []
            l_prevWeb = ''
            for l_web in l_webList:
                if l_web != l_prevWeb:
                    l_prevWeb = l_web
                    l_webList2 += [l_web]

                    for l_socialPattern in ['facebook', 'linkedin', 'twitter', 'snapchat', 'instagram', 'plus\.google']:
                        if re.search(l_socialPattern, l_web.lower()):
                            l_socialList += [l_web]

            # 26 web
            l_row[26] = '|'.join(l_webList2)
            # 40 socialIcons@link
            # l_row[40] = '|'.join(l_socialList)

            # Final row format -----------------------------------------------------------------------------------------
            l_rowCsv = [CommonFunctions.cleanField(x) for x in l_row]
            l_csvWriterA.writerow(l_rowCsv)

        l_cursor.close()
        # End 'With' Block

    # output category file -----------------------------------------------------------------------------------------
    print('Writing category file to', g_categoryPath)
    with open(g_categoryPath, 'w') as l_fOutCat:
        l_fOutCat.write('CategoryFrom,CategoryTo\n')
        l_listDic = list(l_catDict.items())
        l_listDic.sort()
        for l_cat, l_newCat in l_listDic:
            l_fOutCat.write('{0},{1}\n'.format(l_cat, l_newCat))

    # output location file -----------------------------------------------------------------------------------------
    l_cursor = l_connector.cursor()

    l_geoView1 = 'V_GEO1_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()
    l_cursor.execute(g_viewTemplateDrop.format(l_geoView1))
    l_cursor.execute("""
        create view `{0}` as
        SELECT G.*
        FROM `TB_GEO` G join `{1}` A on A.CP = G.ID
        group by G.ID, G.NAME, G.PARENT;
    """.format(l_geoView1, l_resultView))

    l_geoView2 = 'V_GEO2_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()
    l_cursor.execute(g_viewTemplateDrop.format(l_geoView2))
    l_cursor.execute("""
        CREATE VIEW `{0}` AS SELECT G . *
        FROM `TB_GEO` G
        JOIN `{1}` A ON A.PARENT = G.ID
        group by G.ID, G.NAME, G.PARENT;
    """.format(l_geoView2, l_geoView1))

    l_geoView3 = 'V_GEO3_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()
    l_cursor.execute(g_viewTemplateDrop.format(l_geoView3))
    l_cursor.execute("""
        CREATE VIEW `{0}` AS SELECT G . *
        FROM `TB_GEO` G
        JOIN `{1}` A ON A.PARENT = G.ID
        group by G.ID, G.NAME, G.PARENT;
    """.format(l_geoView3, l_geoView2))

    l_geoView = 'V_GEO_' + re.sub('[^A-Za-z0-9]', '_', l_result).upper()
    l_cursor.execute(g_viewTemplateDrop.format(l_geoView))
    l_cursor.execute("""
        create view `{0}` as
        select * from `{1}`
        union
        select * from `{2}`
        union
        select * from `{3}`;
    """.format(l_geoView, l_geoView1, l_geoView2, l_geoView3))

    l_locationPath = re.sub('\.csv', '_locations.csv', l_resultPath)
    print('Writing location file to', l_locationPath)
    with open(l_locationPath, 'w') as l_fOutLocation:
        l_csvWriter = \
            csv.writer(l_fOutLocation, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)
        l_csvWriter.writerow(['sep=;'])
        l_csvWriter.writerow(['slug', 'name', 'description', 'parent'])

        l_cursor = l_connector.cursor(buffered=True)
        l_cursor.execute("""
            select ID       # slug
                , case when LENGTH(ID) < 5 then NAME
                    else concat(NAME, ' (', ID, ')')
                    end
                , ''        # description
                , PARENT    # parent
            from `{0}`
            order by
                (case when PARENT = '-' then 1
                else
                    case when left(ID,1) = 'D' then 2
                    else 3
                    end
                end), ID;
        """.format(l_geoView))

        for r in l_cursor:
            l_csvWriter.writerow(r)

        l_cursor.close()

    # recap
    print()
    print('-------------------------- Recap -------------------------------------')
    l_totalCount = 0
    for l_tbA, b in l_tables:
        l_tbCount = countContent(l_connector, l_tbA)
        print('{0:<60}:  {1}'.format(l_tbA, l_tbCount))
        l_totalCount += l_tbCount

    print('{0:<60}  -{1}'.format(' ', '-------'))
    print('{0:<60}:  {1}'.format('Total items in input files', l_totalCount))

    l_totalMerged = countContent(l_connector, l_resultView)
    print('{0:<60}: -{1}'.format('Duplicates', l_totalCount-l_totalMerged))
    print('{0:<60}:  {1}'.format('Merged count (output to {0})'.format(l_resultPath), l_totalMerged))
    if l_geoLoc:
        print('{0:<60}:  {1}'.format('Successful geolocalizations', l_geoLocCount))
    print('----------------------------------------------------------------------')

    l_connector.close()
