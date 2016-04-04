#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

# REQUIRED PACKAGES & INPUTS

# Tesseract : sudo apt-get install tesseract-ocr

# ImageMagick : sudo apt-get install imagemagick

# selenium : pip3 install -U selenium (to get pip: sudo apt-get install python3-pip)

# For "france", queries, a file named "InseeCommunes.txt" must be present in the root dir
# This file comes from http://www.insee.fr/fr/methodes/nomenclatures/cog/telechargement.asp
# CAUTION: must be converted to utf8 before use

import argparse
import re
import os
import urllib.parse
import urllib.request
import random
import subprocess
import csv
from lxml import html

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX

import CommonFunctions

# --------------------------------- Globals -----------------------------------------------------
g_url = 'http://www.misterwhat.fr/'
g_misterWhatDir = './MisterWhat'
g_emailDir = os.path.join(g_misterWhatDir, 'MisterWhatEmail')

# --------------------------------- Functions ---------------------------------------------------
def doSearch(p_search, p_location, p_csvPathA, p_csvPathB, p_minDelay, p_maxDelay):
    l_urlSearch = '{0}search?what={1}&where={2}'.format(
        g_url,
        urllib.parse.quote(p_search, safe=''),
        urllib.parse.quote(p_location, safe='')
    )

    # open output csv file (main)
    l_fOutMain = open(p_csvPathA, 'w')
    l_fOutMain.write('ID;NAME;ADDRESS;CP;CITY;CREATION;SIRET;TYPE;COUNT;OWNER;' +
                     'TEL1;TEL2;TEL3;TEL4;MAIL;WEB1;WEB2;WEB3;WEB4;HOURS;BUSINESS;ADDITIONAL\n')

    # open output csv file (secondary)
    l_fOutSecondary = open(p_csvPathB, 'w')
    l_fOutSecondary.write('ID;TYPE;RAW;CLEAN;FLAG\n')

    # Create a new instance of the Firefox driver
    l_driver = webdriver.Firefox()

    # Resize the window to the screen width/height
    l_driver.set_window_size(1500, 1500)

    # Move the window to position x/y
    l_driver.set_window_position(1000, 1000)

    l_count = 0

    l_finished = False
    while not l_finished:
        # go to the base Url
        l_driver.get(l_urlSearch)

        try:
            WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, '//footer')))
        except EX.TimeoutException:
            l_finished = True
            continue

        l_itemList = []
        for l_article in l_driver.find_elements_by_xpath('//div[@class="listwrapper"]' +
                                                         '//div[@class="box-company"]/div/a'):
            l_itemLink = l_article.get_attribute('href')
            print('l_itemLink:', l_itemLink)
            l_itemList += [l_itemLink]

        l_nextLink = ''
        for l_next in l_driver.find_elements_by_xpath('//ul[@class="pagination "]/li[last()]/a'):
            l_nextLink = l_next.get_attribute('href')
            print('l_nextLink:', l_nextLink)

        for l_link in l_itemList:
            getOneCompany(l_driver, l_fOutMain, l_fOutSecondary, urllib.parse.urljoin(g_url, l_link), l_count)
            l_count += 1

            CommonFunctions.randomWait(p_minDelay, p_maxDelay)

        if l_nextLink == '':
            l_finished = True
        else:
            l_urlSearch = urllib.parse.urljoin(g_url, l_nextLink)

    print('Number of Items retrieved', l_count)
    l_driver.quit()

    l_fOutMain.close()
    l_fOutSecondary.close()
    return l_count

def getOneCompany(p_driver, p_fOutMain, p_fOutSecondary, p_url, p_id):
    print('---[{0}]---'.format(p_id))

    p_driver.get(p_url)
    # l_request.encoding = l_request.apparent_encoding

    WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//div[@class="shareButtons"]')))

    # get page HTML
    l_pageHtml = p_driver.find_element_by_xpath('//body').get_attribute('innerHTML')

    # extract a full xml/html tree from the page
    l_tree = html.fromstring(l_pageHtml)

    print(p_url, '-->', len(l_pageHtml))

    l_name = CommonFunctions.getUnique(l_tree, '//h2/span[@itemprop="name"]')
    print('   l_name        :', l_name)
    l_address = CommonFunctions.getUnique(l_tree, '//div/span[@itemprop="streetAddress"]')
    print('   l_address     :', l_address)
    l_zip = CommonFunctions.getUnique(l_tree, '//div/span[@itemprop="postalCode"]')
    print('   l_zip         :', l_zip)
    l_city = CommonFunctions.getUnique(l_tree, '//div/a[@itemprop="addressLocality"]/..')
    print('   l_city        :', l_city)

    l_creation = CommonFunctions.getUnique(l_tree, '//div/b[.="Créé:"]/../following-sibling::div[1]')
    print('   l_creation    :', l_creation)
    l_tvaSiret = CommonFunctions.getUnique(l_tree, '//div/b[.="TVA / SIRET:"]/../following-sibling::div[1]')
    print('   l_tvaSiret    :', l_tvaSiret)
    l_type = CommonFunctions.getUnique(l_tree, '//div/b[.="Type d\'entreprise:"]/../following-sibling::div[1]')
    print('   l_type        :', l_type)
    l_headCount = CommonFunctions.getUnique(l_tree, '//div/b[.="Nombre d\'employés:"]/../following-sibling::div[1]')
    print('   l_headCount   :', l_headCount)
    l_owner = CommonFunctions.getUnique(l_tree, '//div/b[.="Propriétaire / PDG:"]/../following-sibling::div[1]')
    print('   l_owner       :', l_owner)

    l_name = CommonFunctions.cleanField(l_name)
    l_address = CommonFunctions.cleanField(l_address)
    l_zip = CommonFunctions.cleanField(l_zip)
    l_city = CommonFunctions.cleanField(l_city)
    l_creation = CommonFunctions.cleanField(l_creation)
    l_tvaSiret = CommonFunctions.cleanField(l_tvaSiret)
    l_type = CommonFunctions.cleanField(l_type)
    l_headCount = CommonFunctions.cleanField(l_headCount)
    l_owner = CommonFunctions.cleanField(l_owner)

    l_telNumber = ''
    for l_tel in l_tree.xpath('//div/span[@itemprop="telephone"]'):
        l_telNumber = CommonFunctions.cleanField(l_tel.text_content())
        print('   l_telNumber   :', l_telNumber)

    l_faxNumber = ''
    for l_fax in l_tree.xpath('//div/span[@itemprop="faxNumber"]'):
        l_faxNumber = CommonFunctions.cleanField(l_fax.text_content())
        print('   l_faxNumber   :', l_faxNumber)

    l_mobileNumber = ''
    for l_mobile in l_tree.xpath('//span/i[@class="icon-mobile-phone"]/../../span'):
        l_mobileNumber = CommonFunctions.cleanField(l_mobile.text_content())
        print('   l_mobileNumber:', l_mobileNumber)

    l_webSite = ''
    for l_web in l_tree.xpath('//span/i[@class="icon-globe"]/../../a'):
        l_webSite = CommonFunctions.cleanField(l_web.text_content())
        print('   l_website     :', l_webSite)

    l_mailAddressRaw = ''
    l_mailAddress = ''
    for l_mail in l_tree.xpath('//span/i[@class="icon-envelope-alt"]/../../a'):
        if l_mail.text_content() == "afficher l'email":
            l_mailImgUrl = getEmail(p_driver, p_url)
            print('   mail img      :', l_mailImgUrl)

            l_mailImgPathRaw = os.path.join(g_emailDir, 'mail_{0}_{1}.png'.format(p_id, re.sub('\s+', '_', l_name)))
            l_mailImgPath = os.path.join(g_emailDir, 'mail_{0}_{1}-X.png'.format(p_id, re.sub('\s+', '_', l_name)))
            urllib.request.urlretrieve(l_mailImgUrl, l_mailImgPathRaw)

            # convert email.gif -resize 2000x -unsharp 0x8 -threshold 95% x.png
            subprocess.call([
                'convert',
                l_mailImgPathRaw,
                '-flatten',
                '-resize', '10000x',
                #'-morphology', 'erode:1', 'square',
                #'-unsharp', '0x8',
                '-threshold', '30%',
                l_mailImgPath
            ])
            l_mailAddressRaw = subprocess.check_output([
                'tesseract',
                l_mailImgPath,
                'stdout'
            ])
            print('   Mail raw      :', l_mailAddressRaw)

            l_work = repr(l_mailAddressRaw)
            l_work = re.sub(r'Q\\xef\\xac\\x81', '@', l_work).strip()
            l_work = re.sub('\\\\', r'\\', l_work).strip()
            l_mailAddressRaw = eval(l_work)

            l_mailAddress = l_mailAddressRaw.decode('utf-8')

            # l_mailAddress = re.sub('Qﬁ', '@', l_mailAddress).strip()
            l_mailAddress = re.sub('\s+', '', l_mailAddress).strip()
            l_mailAddress = re.sub('[‒–—―]', '-', l_mailAddress).strip()

            for l_end in ['com', 'fr', 'net']:
                l_mailAddress = re.sub('([^\.]){0}$'.format(l_end), r'\1.' + l_end, l_mailAddress).strip()

            # for b in l_mailAddressRaw:
            #    print(b, '--->', chr(b))
            l_mailAddress = CommonFunctions.cleanField(l_mailAddress)
            print('   l_mailAddress :', l_mailAddress)

    l_businessList = []
    for l_businessRow in l_tree.xpath('//dl/div[@class="col-sm-9"]/a'):
        l_businessCategoryRaw = l_businessRow.text_content()

        l_match = re.match('^([^-]+)\s-', l_businessCategoryRaw)
        if l_match:
            l_businessCategory = l_match.group(1)
        print('   Business      :', l_businessCategory)
        l_businessList += [l_businessCategory]

        # ID;;;;
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            # ID
            p_id,
            # TYPE
            'BusinessCategory',
            # RAW
            l_businessCategoryRaw,
            # CLEAN
            l_businessCategory,
            # FLAG
            '')
        )

    if l_telNumber != '':
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            p_id, 'FixedPhone', l_telNumber, l_telNumber, ''))
    if l_faxNumber != '':
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            p_id, 'Fax', l_faxNumber, l_faxNumber, ''))
    if l_mobileNumber != '':
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            p_id, 'MobilePhone', l_mobileNumber, l_mobileNumber, ''))
    if l_webSite != '':
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            p_id, 'WebSite', l_webSite, l_webSite, ''))
    if l_mailAddress != '':
        p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
            p_id, 'Email', l_mailAddressRaw, l_mailAddress, ''))

    # output to CSV file (main)
    p_fOutMain.write(
        ('{0};"{1}";"{2}";"{3}";"{4}";"{5}";"{6}";"{7}";"{8}";"{9}";' +
         '"{10}";"{11}";"{12}";"{13}";"{14}";"{15}";"{16}";' +
         '"{17}";"{18}";"{19}";"{20}";"{21}"\n').format(
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
        re.sub('"', '""', CommonFunctions.cleanField(l_creation)),
        # SIRET
        re.sub('"', '""', CommonFunctions.cleanField(l_tvaSiret)),
        # TYPE
        re.sub('"', '""', CommonFunctions.cleanField(l_type)),
        # COUNT
        re.sub('"', '""', CommonFunctions.cleanField(l_headCount)),
        # OWNER
        re.sub('"', '""', CommonFunctions.cleanField(l_owner)),
        # TEL1
        re.sub('"', '""', CommonFunctions.cleanField(l_telNumber)),
        # TEL2
        re.sub('"', '""', CommonFunctions.cleanField(l_faxNumber)),
        # TEL3
        re.sub('"', '""', CommonFunctions.cleanField(l_mobileNumber)),
        # TEL4
        '',
        # MAIL
        re.sub('"', '""', CommonFunctions.cleanField(l_mailAddress)),
        # WEB1
        re.sub('"', '""', CommonFunctions.cleanField(l_webSite)),
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

def getEmail(p_driver, p_url):
    # go to the base Url
    # p_driver.get(p_url)

    # locate the email link
    l_mailLink = WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//span/i[@class="icon-envelope-alt"]/../../a')))

    l_mailLink.click()

    l_mailImg = WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//span/i[@class="icon-envelope-alt"]/../../a/img')))

    l_mailImgUrl =  l_mailImg.get_attribute('src')

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
    print('| v. 1.5 - 04/04/2016                                        |')
    print('+------------------------------------------------------------+')

    random.seed()

    # create MisterWhat and email dirs if not exist
    if not os.path.isdir(g_misterWhatDir):
        os.makedirs(g_misterWhatDir)

    if not os.path.isdir(g_emailDir):
        os.makedirs(g_emailDir)

    # Load list of towns
    # from http://www.insee.fr/fr/methodes/nomenclatures/cog/telechargement.asp
    # CAUTION: must be converted to utf8 before use
    l_inseePath = 'InseeCommunes.txt'
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
                          (re.sub('[\)\(]+', '', l_row[10]) + ' ' + l_row[11]).strip() )
                    )

    # list of arguments
    l_parser = argparse.ArgumentParser(description='Crawl {0}.'.format(g_url))
    l_parser.add_argument('search', help='Search keyword(s)')
    l_parser.add_argument('location', help='Location criterion')
    l_parser.add_argument('--min', type=int, help='Minimum delay between requests (in seconds)', default=0)
    l_parser.add_argument('--max', type=int, help='Minimum delay between requests (in seconds)', default=0)

    # dummy class to receive the parsed args
    class C:
        def __init__(self):
            self.search = ''
            self.location = ''
            self.min = 0
            self.max = 0

    # do the argument parse
    c = C()
    l_parser.parse_args()
    parser = l_parser.parse_args(namespace=c)

    l_minDelay = 0
    l_maxDelay = 0

    # local variables (why did I do this ?)
    l_search = c.search
    l_location = c.location
    if c.min is not None:
        l_minDelay = c.min
    if c.max is not None:
        l_maxDelay = c.max

    # A file type path and name
    l_pathA = os.path.join(g_misterWhatDir, 'MisterWhatA_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))

    # B file type path and name
    l_pathB = os.path.join(g_misterWhatDir, 'MisterWhatB_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))


    # displays parameters
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    if l_minDelay > 0:
        print('Minimum delay (s.)       :', c.min)
    if l_maxDelay > 0:
        print('Maximum delay (s.)       :', c.max)
    print('          ---> Main File :', l_pathA)
    print('           ---> Tel File :', l_pathB)

    # do the per-département search if the location parameter is 'France'
    if l_location.lower() == 'france':
        print('Location = France --> search all Cities/Towns')

        l_totalCount = 0
        # one tmp file per commune
        for l_communeId, l_communeName in l_communes:
            l_tmpA = os.path.join(g_misterWhatDir, '__tmpA_{0}.csv'.format(l_communeId))
            l_tmpB = os.path.join(g_misterWhatDir, '__tmpB_{0}.csv'.format(l_communeId))

            if not os.path.isfile(l_tmpA) and not os.path.isfile(l_tmpA):
                print('Search for "{0}" in "{1}" ...'.format(l_search, l_communeName))

                l_count = doSearch(l_search, l_communeName, l_tmpA, l_tmpB, l_minDelay, l_maxDelay)
                l_totalCount += l_count

                print('Search for "{0}" in "{1}" Complete'.format(l_search, l_communeName))
                if l_count == 0:
                    CommonFunctions.randomWait(l_minDelay, l_maxDelay)

                # if l_totalCount > 300:
                #     break


        print('Total number of items retrieved:', l_totalCount)
        # merge the tmp files
        CommonFunctions.concatTmp(g_misterWhatDir, [i for i, c in l_communes], l_pathA, l_pathB)

        # sort the result
        CommonFunctions.csvSort(l_pathA, p_départements=True)
    else:
        # otherwise, do an ordinary search
        doSearch(l_search, l_location, l_pathA, l_pathB, l_minDelay, l_maxDelay)
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
    print('          ---> Main File :', l_pathA)
    print('           ---> Tel File :', l_pathB)
