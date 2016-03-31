#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

# REQUIRED PACKAGES & INPUTS

# selenium : pip3 install -U selenium (to get pip: sudo apt-get install python3-pip)

import random
import os
import argparse
import re
import urllib.parse
import lxml.html as html
import time
import csv

import CommonFunctions

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
from selenium.webdriver.common.action_chains import ActionChains

# --------------------------------- Globals -----------------------------------------------------
g_url = 'http://www.118218.fr/'
g_118218Dir = './118218/'

def waitFoFooter(p_driver):
    try:
        WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
            (By.XPATH, '//footer')))

        return True
    except EX.TimeoutException:
        print('Footer not found ... Something is not right')
        return False

def doSearch(p_search, p_location, p_pathA, p_pathB, p_minDelay, p_maxDelay, p_distance):
    # http://www.118218.fr/recherche?category_id=&geo_id=&distance=&category=&what=plombier&where=75013
    if p_distance > 0:
        l_baseUrl = '{0}recherche?category_id=&geo_id=&distance={3}&category=&what={1}&where={2}'.format(
            g_url,
            urllib.parse.quote(p_search, safe=''),
            urllib.parse.quote(p_location, safe=''),
            p_distance
        )
    else:
        l_baseUrl = '{0}recherche?category_id=&geo_id=&distance=&category=&what={1}&where={2}'.format(
            g_url,
            urllib.parse.quote(p_search, safe=''),
            urllib.parse.quote(p_location, safe='')
        )
    l_urlSearch = l_baseUrl

    # open output csv file (main)
    l_fOutMain = open(p_pathA, 'w')
    l_fOutMain.write('ID;NAME;ADDRESS;CP;CITY;CREATION;SIRET;TYPE;COUNT;OWNER;' +
                     'TEL1;TEL2;TEL3;TEL4;MAIL;WEB1;WEB2;WEB3;WEB4;HOURS;BUSINESS;ADDITIONAL\n')

    # open output csv file (secondary)
    l_fOutSecondary = open(p_pathB, 'w')
    l_fOutSecondary.write('ID;TYPE;RAW;CLEAN;FLAG\n')

    # Create a new instance of the Firefox driver
    l_driver = CommonFunctions.getDriver()

    # go to the base Url
    l_driver.get(l_urlSearch)

    l_finished = False
    l_linksList = []
    l_currentPage = 1

    l_wait = 60
    # get all links in the result set
    while not l_finished:
        print('Result page:', l_currentPage)

        # Wait for the footer to appear
        if not waitFoFooter(l_driver):
            l_finished = True
            continue

        try:
            l_messageDisplay = l_driver.find_element_by_xpath(
                '//article/section[@class="staticContent ieWrapperFix"]')
            l_message = l_messageDisplay.text
            if re.match('Nos systèmes ont détecté un trafic important', l_message):
                print('Abuse message:', l_message)

                if l_currentPage <= 20 and l_wait <= 300:
                    print('Waiting for {0} seconds ...'.format(l_wait))
                    time.sleep(l_wait)
                    l_wait += 60

                    l_driver.get(l_urlSearch)
                    continue

                l_finished = True
                continue

        except EX.NoSuchElementException:
            print('Ok apparently ...')

        l_wait = 60

        try:
            l_resultCountLocation = l_driver.find_element_by_xpath('//p[@class="resultCount"]')
            l_resultCount = l_resultCountLocation.text
            print('l_resultCount:', l_resultCount)
        except EX.NoSuchElementException:
            print('No Results')
            l_finished = True
            continue

        l_countLink = 0
        for l_link in l_driver.find_elements_by_xpath('//h2/a'):
            l_linkUrl = l_link.get_attribute('href')
            l_linksList += [l_linkUrl]
            print('l_linkUrl:', l_linkUrl)
            l_countLink += 1

        try:
            l_found = False
            for l_link in l_driver.find_elements_by_xpath('//a'):
                # find next page link page
                if l_link.get_attribute('data-page') == str(l_currentPage + 1):

                    l_found = True
                    l_currentPage += 1
                    l_urlSearch = l_link.get_attribute('href')
                    print('Link to next page:', l_urlSearch)

                    # scroll to it, to make it visible, and then click it
                    l_actions = ActionChains(l_driver)
                    l_actions.move_to_element(l_link)
                    l_actions.click()
                    l_actions.perform()

                    CommonFunctions.randomWait(p_minDelay, p_maxDelay)
                    break

            if not l_found:
                # if the link was not found --> Finished
                print('No More Results')
                l_finished = True

        except EX.NoSuchElementException:
            print('No More Results')
            l_finished = True
            continue

    l_count = 0
    for l_url in l_linksList:
        # Scrape one company and stops in case of failure
        if not doOneCompany(l_driver, l_url, l_fOutMain, l_fOutSecondary, p_minDelay, p_maxDelay, l_count):
            break

        l_count += 1
        CommonFunctions.randomWait(p_minDelay, p_maxDelay)

    l_driver.quit()
    print('Number of items retrieved:', l_count)

    l_fOutMain.close()
    l_fOutSecondary.close()

    return l_count

def doOneCompany(p_driver, p_url, p_fOutMain, p_fOutSecondary, p_minDelay, p_maxDelay, p_id):
    print('---[{0}]---'.format(p_id))

    l_wait = 60
    l_finished = False
    while not l_finished:
        # go to the base Url
        p_driver.get(p_url)

        try:
            WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, '//footer')))
        except EX.TimeoutException:
            print('Footer not found ... Something is not right')
            return

        # get page HTML
        l_pageHtml = p_driver.find_element_by_xpath('//body').get_attribute('innerHTML')

        # extract a full xml/html tree from the page
        l_tree = html.fromstring(l_pageHtml)

        print(p_url, '-->', len(l_pageHtml))

        l_name = CommonFunctions.getUnique(l_tree, '//h1[@itemprop="name"]')
        l_name = CommonFunctions.cleanField(l_name)
        print('   l_name        :', l_name)

        if l_name == '':
            print('Waiting for {0} seconds ...'.format(l_wait))
            time.sleep(l_wait)
            l_wait *= 2
            continue

        l_address = CommonFunctions.getUnique(l_tree, '//span[@itemprop="streetAddress"]')
        l_address = CommonFunctions.cleanField(l_address)
        print('   l_address     :', l_address)
        l_zip = CommonFunctions.getUnique(l_tree, '//span[@itemprop="postalCode"]')
        l_zip = re.sub('[^\d]', '', l_zip)
        l_zip = CommonFunctions.cleanField(l_zip)
        print('   l_zip         :', l_zip)
        l_city = CommonFunctions.getUnique(l_tree, '//span[@itemprop="addressLocality"]')
        l_city = CommonFunctions.cleanField(l_city)
        print('   l_city        :', l_city)
        l_web = CommonFunctions.getUnique(l_tree, '//p[@class="websiteAndShare"]/a')
        l_web = CommonFunctions.cleanField(l_web)
        print('   l_web         :', l_web)

        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            # ID
            p_id,
            # TYPE
            'WebSite',
            # RAW
            l_web,
            # CLEAN
            l_web,
            # FLAG
            '')
        )

        l_telList = []
        for l_telItem in l_tree.xpath('//p[@itemprop="telephone"]'):
            l_oneTel = l_telItem.text_content()
            print('   Tel           :', l_oneTel)
            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                # ID
                p_id,
                # TYPE
                'UnspecifiedPhone',
                # RAW
                l_oneTel,
                # CLEAN
                l_oneTel,
                # FLAG
                '')
            )
            l_telList += [l_oneTel]

        l_businessList = []
        for l_businessRow in l_tree.xpath('//li[@class="label-child"]'):
            l_businessCategory = l_businessRow.text_content()
            l_businessCategory = CommonFunctions.cleanField(l_businessCategory)
            print('   Business      :', l_businessCategory)

            l_businessList += [l_businessCategory]

            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                # ID
                p_id,
                # TYPE
                'BusinessCategory',
                # RAW
                l_businessCategory,
                # CLEAN
                l_businessCategory,
                # FLAG
                '')
            )

        l_telList = (l_telList + ['', '', '', ''])[0:4]

        # output to CSV file (main)
        p_fOutMain.write(
            ('{0};"{1}";"{2}";"{3}";"{4}";"{5}";"{6}";"{7}";"{8}";"{9}";' +
             '"{10}";"{11}";"{12}";"{13}";"{14}";"{15}";"{16}";"{17}";"{18}"\n').format(
            # ID
            p_id,
            # NAME
            re.sub('"', '""', CommonFunctions.cleanField(l_name)),
            # ADDRESS
            re.sub('"', '""', CommonFunctions.cleanField(l_address)),
            # CP
            re.sub('"', '""', CommonFunctions.cleanField(l_zip)),
            # CITY
            re.sub('"', '""', CommonFunctions.cleanField(l_city)),
            # CREATION
            '',
            # SIRET
            '',
            # TYPE
            '',
            # COUNT
            '',
            # OWNER
            '',
            # TEL1 - TEL4
            '";"'.join([re.sub('"', '""', CommonFunctions.cleanField(t)) for t in l_telList]) ,
            # MAIL
            '',
            # WEB1
            re.sub('"', '""', CommonFunctions.cleanField(l_web)),
            # WEB2
            '',
            # WEB3
            '',
            # WEB4
            '',
            # HOURS
            '',
            # BUSINESS
            re.sub('"', '""', CommonFunctions.cleanField('|'.join(l_businessList))),
            # ADDITIONAL
            ''
        ))
        p_fOutMain.flush()
        p_fOutSecondary.flush()

        l_finished = True

    return True


# ---------------------------------------------------- Main section ---------------------------------------------
if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('|' + '{:<60}'.format(' Web Scraping of {0}'.format(g_url)) + '|')
    print('|                                                            |')
    print('| Contractor: Kabir Abdulhamid / Upwork                      |')
    print('|                                                            |')
    print('| Client: Teddy Nestor                                       |')
    print('|                                                            |')
    print('| v. 1.4 - 30/03/2016                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

    # Load list of towns
    # from http://www.insee.fr/fr/methodes/nomenclatures/cog/telechargement.asp
    # CAUTION: must be converted to utf8 before use
    l_inseePath = 'InseeCommunes118218.txt'
    l_communes = []
    if os.path.isfile(l_inseePath):
        with open(l_inseePath, 'r') as f:
            l_first = True
            for l_row in csv.reader(f, delimiter='\t'):
                # skip header row and stores it
                if l_first:
                    l_first = False
                else:
                    l_communes.append(
                        ( ('000' + l_row[3])[-3:] + '-' + ('0000' + l_row[4])[-4:],
                          (re.sub('[\)\(]+', '', l_row[10]) + ' ' + re.sub('-', ' ', l_row[11])).strip() )
                    )

    # create 118218 dir and email if not exist
    if not os.path.isdir(g_118218Dir):
        os.makedirs(g_118218Dir)

    # list of arguments
    l_parser = argparse.ArgumentParser(description='Crawl {0}.'.format(g_url))
    l_parser.add_argument('search', help='Search keyword(s)')
    l_parser.add_argument('location', help='Location criterion')
    l_parser.add_argument('--min', type=int, help='Minimum delay between requests (in seconds)', default=0)
    l_parser.add_argument('--max', type=int, help='Minimum delay between requests (in seconds)', default=0)
    l_parser.add_argument('-d', type=int, help='Distance (in Km) parameter of 118218', default=0)

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.search = ''
            self.location = ''
            self.min = 0
            self.max = 0
            self.d = 0

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    l_minDelay = 0
    l_maxDelay = 0
    l_distance = 0

    # local variables (why did I do this ?)
    l_search = c.search
    l_location = c.location
    if c.min is not None:
        l_minDelay = c.min
    if c.max is not None:
        l_maxDelay = c.max
    if c.d is not None:
        l_distance = c.d

    # A file type path and name
    l_pathA = os.path.join(g_118218Dir, '118218A_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))

    # B file type path and name
    l_pathB = os.path.join(g_118218Dir, '118218B_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))


    # displays parameters
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    if l_minDelay > 0:
        print('Minimum delay (s.)       :', c.min)
    if l_maxDelay > 0:
        print('Maximum delay (s.)       :', c.max)
    if l_distance > 0:
        print('Distance (km)            :', c.d)
    print('          ---> Main File :', l_pathA)
    print('          ---> Tel File  :', l_pathB)

    # do the per-département search if the location parameter is 'France'
    if l_location.lower() == 'france':
        print('Location = France --> search all Cities/Towns')

        l_totalCount = 0
        # one tmp file per commune
        for l_communeId, l_communeName in l_communes:
            l_tmpA = os.path.join(g_118218Dir, '__tmpA_{0}.csv'.format(l_communeId))
            l_tmpB = os.path.join(g_118218Dir, '__tmpB_{0}.csv'.format(l_communeId))

            if not os.path.isfile(l_tmpA) and not os.path.isfile(l_tmpA):
                print('Search for "{0}" in "{1}" ...'.format(l_search, l_communeName))

                l_count = doSearch(l_search, l_communeName, l_tmpA, l_tmpB, l_minDelay, l_maxDelay, l_distance)
                l_totalCount += l_count

                print('Search for "{0}" in "{1}" Complete'.format(l_search, l_communeName))
                if l_count == 0:
                    CommonFunctions.randomWait(l_minDelay, l_maxDelay)


        print('Total number of items retrieved:', l_totalCount)
        # merge the tmp files
        CommonFunctions.concatTmp(g_118218Dir, [i for i, c in l_communes], l_pathA, l_pathB)

        # sort the result
        CommonFunctions.csvSort(l_pathA, p_départements=True)
    else:
        # otherwise, do an ordinary search
        doSearch(l_search, l_location, l_pathA, l_pathB, l_minDelay, l_maxDelay, l_distance)
        # and sort the results as well
        CommonFunctions.csvSort(l_pathA)

    # displays parameters again
    print('------------------------------------------------------')
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    if l_minDelay > 0:
        print('Minimum delay (s.)       :', c.min)
    if l_maxDelay > 0:
        print('Maximum delay (s.)       :', c.max)
    if l_distance > 0:
        print('Distance (km)            :', c.d)
    print('          ---> Main File :', l_pathA)
    print('          ---> Tel File  :', l_pathB)
