#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

import csv
import os
import re
import random
import time
import urllib.parse
import urllib.request
import json
import unicodedata

from selenium import webdriver

# --------------------------------- Globals ----------------------------------------------------------------------------
# Google API management (to get key):
# https://console.developers.google.com/apis/credentials?project=resonant-fiber-126708
# account: kabir.abdulham@gmail.com

# https://maps.googleapis.com/maps/api/geocode/json?address=1600+Amphitheatre+Parkway,+Mountain+View,+CA&key=AIzaSyDJxO78EbjQ0hwhY3bK4_fsgB4Q1lmZG9o
g_latLongUrl = 'https://maps.googleapis.com/maps/api/geocode/json?'

g_googleKey = 'AIzaSyDJxO78EbjQ0hwhY3bK4_fsgB4Q1lmZG9o'

# --------------------------------- Functions --------------------------------------------------------------------------

# get a lat/long pair from Google Geolocalization API
def getLatLong(p_address):
    print('### Address to geolocate:', p_address)

    # build request url
    l_url = g_latLongUrl + urllib.parse.urlencode({'address': p_address}) + \
            '&region=fr&key=' + g_googleKey
    print(l_url, '-->')

    # get response
    l_response = urllib.request.urlopen(l_url)

    if l_response.status == 200:
        # response ok --> load json
        l_result = json.loads(l_response.read().decode('utf-8'))

        # get request status
        l_status = l_result['status']

        if l_status == 'OK':
            # status ok, retrieves lat/long
            l_lat = l_result['results'][0]['geometry']['location']['lat']
            l_long = l_result['results'][0]['geometry']['location']['lng']
            print('Lat :', l_lat)
            print('Long:', l_long)

            # wait for 1/5th of a second to remain within Google throughput limits (10 req/s.)
            time.sleep(.20)

            return l_lat, l_long
        else:
            print('Request succeeded but status is:', l_status)
    else:
        print('Request failed with code:', l_response.status)

    return None, None

# merges all tmp files into an A/B pair
def concatTmp(p_dirPath, p_listId, p_pathA, p_pathB):
    # open output A csv file
    l_fOutA = open(p_pathA, 'w')
    l_csvWriterA = \
        csv.writer(l_fOutA, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)

    # open output B csv file
    l_fOutB = open(p_pathB, 'w')
    l_csvWriterB = \
        csv.writer(l_fOutB, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)

    l_isFirst = True
    for l_id in p_listId:
        l_tmpA = os.path.join(p_dirPath, '__tmpA_{0}.csv'.format(l_id))

        # if this file exist
        if os.path.isfile(l_tmpA):
            # open csv reader
            with open(l_tmpA, 'r') as l_csvA:
                l_readerA = csv.reader(l_csvA, delimiter=';', quotechar='"', lineterminator='\n')

                # skip first row (col headers) except for the first one, so that the output has one
                # and only one header row
                if l_isFirst:
                    l_isFirst = False
                else:
                    next(l_readerA, None)

                for l_row in l_readerA:
                    # Add tmp file id to the item ID to keep it unique
                    if l_row[0] != 'ID': # Of course this is not done on a header row
                        l_row[0] = l_id + '-' + ('000000' + l_row[0])[-6:]
                    l_csvWriterA.writerow(l_row)

            # delete the tmp file
            os.remove(l_tmpA)

    # same for B files
    l_isFirst = True
    for l_id in p_listId:
        l_tmpB = os.path.join(p_dirPath, '__tmpB_{0}.csv'.format(l_id))

        # if this file exist
        if os.path.isfile(l_tmpB):
            # open csv reader
            with open(l_tmpB, 'r') as l_csvB:
                l_readerB = csv.reader(l_csvB, delimiter=';', quotechar='"', lineterminator='\n')

                # skip first row (col headers) except for the first one, so that the output has one
                # and only one header row
                if l_isFirst:
                    l_isFirst = False
                else:
                    next(l_readerB, None)

                for l_row in l_readerB:
                    # Add file id to the ID to keep it unique
                    if l_row[0] != 'ID': # Of course this is not done on a header row
                        l_row[0] = l_id + '-' + ('000000' + l_row[0])[-6:]
                    l_csvWriterB.writerow(l_row)

            # delete the tmp file
            os.remove(l_tmpB)

# sort an A type csv file
# adapted from http://stackoverflow.com/questions/2089036/sorting-csv-in-python
def csvSort(p_path, p_départements=False):
    """sort (and rewrite) a csv file.
    types:  data types (conversion functions) for each column in the file
    sort_key_columns: column numbers of columns to sort by"""

    if not os.path.isfile(p_path):
        return

    data = []       # list to hold, and sort, the data
    l_header = []   # the header row (not to be sorted)

    # read file into data variable
    with open(p_path, 'r') as f:
        l_first = True
        for l_row in csv.reader(f, delimiter=';', quotechar='"', lineterminator='\n'):
            # skip header row and stores it
            if l_first:
                l_header = l_row
                l_first = False
            else:
                data.append(l_row)

    # key function for ordinary files
    def keyCalc(p_row):
        return p_row[1].lower()

    # key function for per-département files
    def keyCalcDépartements(p_row):
        return p_row[0][0:3] + p_row[1].lower()

    # data.sort(key=operator.itemgetter(0, 2))

    # sort the data variable (list of lists)
    if p_départements:
        data.sort(key=keyCalcDépartements)
    else:
        data.sort(key=keyCalc)

    # output sorted result
    with open(p_path, 'w') as f:
        l_writer = csv.writer(f, delimiter=';', quotechar='"', lineterminator='\n', quoting=csv.QUOTE_NONNUMERIC)

        # write header
        l_writer.writerow(l_header)

        # write other rows
        l_writer.writerows(data)

# get a unique text element through lxml, with a warning mark ('¤') inside the string
# inside the string if more than one was found
def getUnique(p_frag, p_xpath):
    return '¤'.join([str(l_span.text_content()) for l_span in p_frag.xpath(p_xpath)]).strip()

# field cleanup before CSV output
def cleanField(p_unclean):
    l_clean = re.sub('^[\.;,:]', '', p_unclean)
    l_clean = re.sub('[;,:]$', '', l_clean)
    return re.sub('\s+', ' ', l_clean).strip()

# wait random time between given bounds
def randomWait(p_minDelay, p_maxDelay):
    if p_minDelay > 0 and p_maxDelay > p_minDelay:
        l_wait = p_minDelay + (p_maxDelay - p_minDelay)*random.random()
        print('Waiting for {0:.2f} seconds ...'.format(l_wait))
        time.sleep(l_wait)

def getDriver():
    # Create a new instance of the Firefox driver
    l_driver = webdriver.Firefox()

    # Resize the window to the screen width/height
    l_driver.set_window_size(1500, 1500)

    # Move the window to position x/y
    l_driver.set_window_position(1000, 1000)

    return l_driver

def makeSlug(p_name):
    l_slug = re.sub('\s+', ' ', p_name).strip()

    l_slug = ''.join((c for c in unicodedata.normalize('NFD', l_slug) if unicodedata.category(c) != 'Mn'))

    l_slug = re.sub('\W+', '-', l_slug)
    l_slug = re.sub('-$', '', l_slug)
    l_slug = re.sub('_', '-', l_slug).lower()

    return l_slug

# ---------------------------------------------------- Main section ----------------------------------------------------

if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('| Common Scraping functions                                  |')
    print('|                                                            |')
    print('| Contractor: Kabir Abdulhamid / Upwork                      |')
    print('|                                                            |')
    print('| Client: Teddy Nestor                                       |')
    print('|                                                            |')
    print('| v. 1.5 - 04/04/2016                                        |')
    print('+------------------------------------------------------------+')

    getLatLong('75 rue du javelot 75013 paris france')