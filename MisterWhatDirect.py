#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

import argparse
import re
import os
import urllib.parse
import urllib.request
import requests
from lxml import html

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
from selenium.webdriver.common.action_chains import ActionChains

import CommonFunctions

# --------------------------------- Globals -----------------------------------------------------
g_url = 'http://www.misterwhat.fr/'

# --------------------------------- Functions ---------------------------------------------------
def doSearch(p_search, p_location, p_csvPathA, p_csvPathB):
    l_urlSearch = '{0}search?what={1}&where={2}'.format(
        g_url,
        urllib.parse.quote(p_search, safe=''),
        urllib.parse.quote(p_location, safe='')
    )

    l_count = 0

    l_finished = False
    while not l_finished:
        l_request = requests.get(l_urlSearch)
        # l_request.encoding = l_request.apparent_encoding

        print(l_urlSearch, '-->', len(l_request.content))

        # extract a full xml/html tree from the text returned
        l_tree = html.fromstring(l_request.text)

        for l_item in l_tree.xpath('//div[@class="box-company"]/div/a'):
            # print(html.tostring(l_item))
            l_itemLink = l_item.get('href')
            print('l_itemLink:', l_itemLink)
            getOneCompany(urllib.parse.urljoin(g_url, l_itemLink), l_count)
            l_count += 1

        l_nextLink = ''
        for l_next in l_tree.xpath('//ul[@class="pagination "]/li[last()]/a'):
            l_nextLink = l_next.get('href')
            print('l_nextLink:', l_nextLink)

        if l_nextLink == '':
            l_finished = True
        else:
            l_urlSearch = urllib.parse.urljoin(g_url, l_nextLink)

    print('Number of Items retrieved', l_count)


def getOneCompany(p_url, p_id):
    l_request = requests.get(p_url)
    # l_request.encoding = l_request.apparent_encoding

    print('---[{0}]---'.format(p_id))
    print(p_url, '-->', len(l_request.content))

    # extract a full xml/html tree from the text returned
    l_tree = html.fromstring(l_request.text)

    l_name = CommonFunctions.getUnique(l_tree, '//h2/span[@itemprop="name"]')
    print('   l_name      :', l_name)
    l_address = CommonFunctions.getUnique(l_tree, '//div/span[@itemprop="streetAddress"]')
    print('   l_address   :', l_address)
    l_zip = CommonFunctions.getUnique(l_tree, '//div/span[@itemprop="postalCode"]')
    print('   l_zip       :', l_zip)
    l_city = CommonFunctions.getUnique(l_tree, '//div/a[@itemprop="addressLocality"]/..')
    print('   l_city      :', l_city)

    for l_tel in l_tree.xpath('//div/span[@itemprop="telephone"]'):
        l_telNumber = l_tel.text_content()
        print('   l_telNumber :', l_telNumber)

    for l_fax in l_tree.xpath('//div/span[@itemprop="faxNumber"]'):
        l_faxNumber = l_fax.text_content()
        print('   l_faxNumber :', l_faxNumber)

    for l_web in l_tree.xpath('//span/i[@class="icon-globe"]/../../a'):
        l_webSite = l_web.text_content()
        print('   l_website   :', l_webSite)

    for l_mail in l_tree.xpath('//span/i[@class="icon-envelope-alt"]/../../a'):
        if l_mail.text_content() == "afficher l'email":
            l_mailImgUrl = getEmail(p_url)
            print('   mail img    :', l_mailImgUrl)

            l_mailImgPath = 'MisterWhatEmail/mail_{0}_{1}.png'.format(p_id, re.sub('\s+', '_', l_name))
            urllib.request.urlretrieve(l_mailImgUrl, l_mailImgPath)

def getEmail(p_url):
    # Create a new instance of the Firefox driver
    l_driver = webdriver.Firefox()

    # Resize the window to the screen width/height
    l_driver.set_window_size(1500, 1500)

    # Move the window to position x/y
    l_driver.set_window_position(1000, 1000)

    # go to the base Url
    l_driver.get(p_url)

    # locate the email link
    l_mailLink = WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//span/i[@class="icon-envelope-alt"]/../../a')))

    l_mailLink.click()

    l_mailImg = WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//span/i[@class="icon-envelope-alt"]/../../a/img')))

    l_mailImgUrl =  l_mailImg.get_attribute('src')

    l_driver.quit()

    return l_mailImgUrl

# ---------------------------------------------------- Main section ---------------------------------------------

if __name__ == "__main__":
    print('+------------------------------------------------------------+')
    print('|' + '{:<60}'.format(' Web Scraping of {0}'.format(g_url)) + '|')
    print('|                                                            |')
    print('| Contractor: Kabir Abdulhamid / Upwork                      |')
    print('|                                                            |')
    print('| Client: Teddy Nestor                                       |')
    print('|                                                            |')
    print('| v. 0.1 - 17/03/2016                                        |')
    print('+------------------------------------------------------------+')

    # list of départements, all formated as a string of 3 digits
    l_départements = [str(i+1).zfill(3) for i in range(95)] + ['971', '972', '973', '974', '976']

    # list of arguments
    l_parser = argparse.ArgumentParser(description='Crawl {0}.'.format(g_url))
    l_parser.add_argument('search', help='Search keyword(s)')
    l_parser.add_argument('location', help='Location criterion')

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.search = ''
            self.location = ''

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    # local variables (why did I do this ?)
    l_search = c.search
    l_location = c.location

    # A file type path and name
    l_pathA = './PagesJaunesA_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location))

    # B file type path and name
    l_pathB = './PagesJaunesB_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location))

    # displays parameters
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    print('          ---> Main File :', l_pathA)
    print('           ---> Tel File :', l_pathB)

    # do the per-département search if the location parameter is 'France'
    if l_location.lower() == 'france':
        print('Location = France --> search all départements')

        # one tmp file per dépârtements
        for l_dépNum in l_départements:
            l_tmpA = './__pjtmpA_{0}.csv'.format(l_dépNum)
            l_tmpB = './__pjtmpB_{0}.csv'.format(l_dépNum)

            if not os.path.isfile(l_tmpA) and not os.path.isfile(l_tmpA):
                doSearch(l_search, l_dépNum, l_tmpA, l_tmpB)

        # merge the tmp files
        CommonFunctions.concatDépartements(l_départements, l_pathA, l_pathB)

        # sort the result
        CommonFunctions.csvSort(l_pathA, p_départements=True)
    else:
        # otherwise, do an ordinary search
        doSearch(l_search, l_location, l_pathA, l_pathB)
        # and sort the results as well
        CommonFunctions.csvSort(l_pathA)

    # displays parameters again
    print('------------------------------------------------------')
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    print('          ---> Main File :', l_pathA)
    print('           ---> Tel File :', l_pathB)