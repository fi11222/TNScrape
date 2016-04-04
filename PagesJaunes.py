#!/usr/bin/python3
# -*- coding: utf-8 -*-

__author__ = 'Kabir Abdulhamid / Upwork'

# REQUIRED PACKAGES & INPUTS

# selenium : pip3 install -U selenium (to get pip: sudo apt-get install python3-pip)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common import exceptions as EX
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

import argparse
import re
import os
import time

from lxml import html

import CommonFunctions

# ------------------------------------------------- Globals -----------------------------------------------------
g_url = 'http://www.pagesjaunes.fr/'
g_PagesJaunesDir = './PagesJaunes/'

# ------------------------------------------------- Function ----------------------------------------------------
def killPopup(p_driver):
    # <a title="Fermer" class="pjpopin-closer" href="javascript:">
    #   <span class="icon icon-fermer"></span>
    #   <span class="value">Fermer</span>
    # </a>
    try:
        p_driver.find_element_by_xpath('//a[@class="pjpopin-closer"]').click()
        return True
    except EX.NoSuchElementException:
        print('No popup (A) ...')

    # <button class="kclose kbutton button primary large-button" style="float:left;margin-right:20px;background-color:#dedede;">
    #   <span class=""></span>
    #   NON, MERCI
    # </button>
    try:
        p_driver.find_element_by_xpath('//button[@class="kclose kbutton button primary large-button"]').click()
        return True
    except EX.NoSuchElementException:
        print('No popup (B) ...')

    return False

def doSearch(p_search, p_location, p_pathA, p_pathB, p_minDelay, p_maxDelay):

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
    l_driver.get(g_url)

    try:
        # locate the keyword search input text box and enter the search string
        l_quoiQui = WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
                    (By.XPATH, '//input[@id="pj_search_quoiqui"]')))
        print('l_quoiQui placeholder:', l_quoiQui.get_attribute('placeholder'))
        l_quoiQui.send_keys(p_search)

        # locate the location input text box and enter the location string
        l_ou = l_driver.find_element_by_id('pj_search_ou')
        print('l_ou placeholder:', l_ou.get_attribute('placeholder'))
        l_ou.send_keys(p_location)

        # submit the form
        l_driver.find_element_by_xpath('//button[@class="button primary icon large-button"]').click()
    except EX.NoSuchElementException:
        print('[01] Something is badly wrong (Element not found) ...')
        return 0
    except EX.TimeoutException:
        print('[02] Something is badly wrong (Timeout) ...')
        return 0

    l_finished = False
    l_count = 0
    while not l_finished:
        try:
            # WebDriverWait(driver,5).until(
            # lambda driver: driver.find_elements(By.ID,"a") or driver.find_elements(By.ID,"b"))

            WebDriverWait(l_driver, 10).until(
                lambda p_driver: \
                    p_driver.find_elements(By.XPATH, '//h2[@class="company-name"]') \
                    or p_driver.find_elements(By.XPATH, '//div[@class="no-response"]'))

            #WebDriverWait(l_driver, 10).until(EC.presence_of_element_located(
            #    (By.XPATH, '//h2[@class="company-name"]')))
        except EX.TimeoutException:
            print('[03] Something is badly wrong (Timeout) ...')
            return 0

        if killPopup(l_driver):
            continue

        try:
            l_driver.find_element_by_xpath('//div[@class="no-response"]')
            print('No results')

            l_finished = True
            continue
        except EX.NoSuchElementException:
            print('There should be results')

        try:
            # reformulation
            l_reformulation = l_driver.find_element_by_xpath(
                '//span[@class="denombrement"]/strong[@id="SEL-nbresultat"]')

            l_resultCount = l_reformulation.text
            print('l_resultCount:', l_resultCount)

        except EX.NoSuchElementException:
            print('No reformulation ?! ...')

        l_articleList = []
        try:
            for l_company in l_driver.find_elements_by_xpath('//h2[@class="company-name"]/../../../..'):
                l_articleId = l_company.get_attribute('id')
                print('l_articleId:', l_articleId)
                l_articleList += [l_articleId]

        except EX.NoSuchElementException:
            print('[04] Something is badly wrong (Element not found) ...')
            return 0

        try:
            l_article = 0
            for l_articleId in l_articleList:
                if killPopup(l_driver):
                    print('Popup Killed, waiting for 10 s.')
                    time.sleep(10)

                print('+ l_articleId:', l_articleId)
                l_company = l_driver.find_element_by_xpath(
                    '//article[@id="{0}"]//h2[@class="company-name"]/a[2]'.format(l_articleId))

                #l_driver.execute_script("return arguments[0].scrollIntoView();", l_company)

                l_name = l_company.text
                print('Fetching:', l_name)

                l_driver.execute_script("return arguments[0].scrollIntoView();", l_company)
                l_driver.execute_script("window.scrollBy(0, -300);")

                # Save the window opener (current window, do not mistaken with tab... not the same)
                l_mainWindow = l_driver.current_window_handle

                # l_company.send_keys(Keys.CONTROL + Keys.RETURN)
                # scroll to it, to make it visible, and then click it
                l_actions = ActionChains(l_driver)
                l_actions.move_to_element(l_company)
                l_actions.context_click()
                l_actions.send_keys(Keys.ARROW_DOWN)
                l_actions.send_keys(Keys.ENTER)
                l_actions.perform()

                # Switch tab to the new tab, which we will assume is the next one on the right
                l_driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + Keys.TAB)

                # Put focus on current window which will, in fact, put focus on the current visible tab
                l_driver.switch_to_window(l_mainWindow)

                if doOneCompany(l_driver, l_fOutMain, l_fOutSecondary, l_count):
                    l_count += 1

                CommonFunctions.randomWait(p_minDelay, p_maxDelay)

                # Close current tab
                l_driver.find_element_by_tag_name('body').send_keys(Keys.CONTROL + 'w')

                # Put focus on current window which will be the window opener
                l_driver.switch_to_window(l_mainWindow)

        except EX.NoSuchElementException:
            print('[05] Something is badly wrong (Element not found) ...')
            return 0

        # locate the next button and click it
        try:
            l_next = l_driver.find_element_by_id('pagination-next')

            # scroll to it, to make it visible, and then click it
            l_actions = ActionChains(l_driver)
            l_actions.move_to_element(l_next)
            l_actions.click()
            l_actions.perform()
        except EX.NoSuchElementException:
            print('No more results')
            l_finished = True

    print('Number of items retrieved:', l_count)

    l_fOutMain.close()
    l_fOutSecondary.close()

    l_driver.quit()
    return l_count

def doOneCompany(p_driver, p_fOutMain, p_fOutSecondary, p_id):
    print('---[{0}]---'.format(p_id))

    l_finished = False
    l_name = ''
    while not l_finished:
        try:
            l_nameItem = WebDriverWait(p_driver, 10).until(EC.presence_of_element_located(
                (By.XPATH, '//h1[@itemprop="name"]')))

            l_name = l_nameItem.text
            l_name = re.sub('\s+Afficher le numéro$', '', l_name).strip()
            print('   l_name           :', l_name)
        except EX.TimeoutException:
            print('[06] Something is badly wrong (Timeout) ...')
            return False

        if killPopup(p_driver):
            continue

        l_finished = True

    try:
        l_html = p_driver.find_element_by_xpath('//body').get_attribute('innerHTML')
        l_tree = html.fromstring(l_html)

        l_address = CommonFunctions.getUnique(l_tree, '//span[@itemprop="streetAddress"]')
        print('   l_address        :', l_address)
        l_zip = CommonFunctions.getUnique(l_tree, '//span[@itemprop="postalCode"]')
        l_zip = re.sub('^[,;:\.]\s+', '', l_zip).strip()
        print('   l_zip            :', l_zip)
        l_city = CommonFunctions.getUnique(l_tree, '//span[@itemprop="addressLocality"]')
        print('   l_city           :', l_city)

        # extract a full xml/html tree from the fragment
        l_telList = []
        for l_telRow in l_tree.xpath('//div[@id="coord-list-container-1"]//ul/li'):
            l_telType = CommonFunctions.getUnique(l_telRow, './span[@class="num-tel-label"]')
            l_telType = re.sub('\s+:$', '', l_telType).strip()

            if l_telType == 'tél':
                l_telType = 'FixedPhone'
            elif l_telType == 'Mobile':
                l_telType = 'MobilePhone'
            elif l_telType == 'Fax':
                l_telType = 'Fax'
            else:
                l_telType = 'UnspecifiedPhone'

            print('   l_telType        :', l_telType)

            l_tel = CommonFunctions.getUnique(l_telRow, './span[@class="coord-numero"]')
            l_tel = re.sub('^\.', '', l_tel).strip()
            l_tel = re.sub('\s+$', '', l_tel).strip()
            l_tel = re.sub('^\s+', '', l_tel).strip()
            print('   l_tel            :', l_tel)
            l_tel = CommonFunctions.cleanField(l_tel)
            l_telList += [l_tel]

            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                p_id, l_telType, l_tel, l_tel, ''))


        l_webList = []
        # l_root = l_tree.getroottree()
        for l_webRow in l_tree.xpath(
                '//article/div/div/h3[text()="Sites et réseaux sociaux"]/..//ul/li/a/span[@class="value"]'):
            l_webSite = l_webRow.text_content().strip()
            # print('   l_webSite path   :', l_root.getpath(l_webRow))
            print('   l_webSite        :', l_webSite)
            l_webSite = CommonFunctions.cleanField(l_webSite)
            l_webList += [l_webSite]

            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                p_id, 'WebSite', l_webSite, l_webSite, ''))

        # bloc-info-horaires
        l_hoursList = []
        for l_hoursRow in l_tree.xpath(
                '//ul[@class="liste-horaires-principaux"]//ul/li[@itemprop="openingHours"]'):
            l_hours = l_hoursRow.get('content').strip()
            print('   l_hours          :', l_hours)
            l_hours = CommonFunctions.cleanField(l_hours)
            l_hoursList += [l_hours]

            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                p_id, 'OpeningHours', l_hours, l_hours, ''))

        l_businessList = []
        for l_businessRow in l_tree.xpath('//span[@class="activite-premiere-visibilite activite"]'):

            l_businessCategory = l_businessRow.text_content().strip()
            l_businessCategory = re.sub('\s+[\.;,:]$', '', l_businessCategory).strip()
            l_businessCategory = re.sub('^[\.;,:]\s+', '', l_businessCategory).strip()
            l_businessCategory = CommonFunctions.cleanField(l_businessCategory)
            print('   l_businessCat.   :', l_businessCategory)
            l_businessList += [l_businessCategory]

            p_fOutSecondary.write('{0};"{1}";"{2}";"{3}";"{4}"\n'.format(
                p_id, 'BusinessCategory', l_businessCategory, l_businessCategory, ''))

        # description
        l_additional = ''
        for l_description in l_tree.xpath('//div[@itemprop="description"]'):
            l_additional = l_description.text_content().strip()

            l_additional = re.sub('\s+', ' ', l_additional).strip()
            print('   l_additional     :', l_additional)

        l_telList = (l_telList + ['', '', '', ''])[0:4]
        l_webList = (l_webList + ['', '', '', ''])[0:4]

        # output to CSV file (main)
        p_fOutMain.write(
            ('{0};"{1}";"{2}";"{3}";"{4}";"{5}";"{6}";"{7}";"{8}";"{9}";' +
             '"{10}";"{11}";"{12}";"{13}";"{14}";"{15}"\n').format(
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
            '";"'.join([re.sub('"', '""', CommonFunctions.cleanField(t)) for t in l_telList]),
            # MAIL
            '',
            # WEB1 - WEB4
            '";"'.join([re.sub('"', '""', CommonFunctions.cleanField(w)) for w in l_webList]),
            # HOURS
            re.sub('"', '""', CommonFunctions.cleanField('|'.join(l_hoursList))),
            # BUSINESS
            re.sub('"', '""', CommonFunctions.cleanField('|'.join(l_businessList))),
            # ADDITIONAL
            re.sub('"', '""', CommonFunctions.cleanField(l_additional))
        ))
        p_fOutMain.flush()
        p_fOutSecondary.flush()

    except EX.NoSuchElementException:
        print('[07] Something is badly wrong (Element not found) ...')
        return False

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
    print('| v. 2.3 - 04/04/2016                                        |')
    print('| + réupération des horaires                                 |')
    print('+------------------------------------------------------------+')

    # list of départements, all formated as a string of 3 digits
    l_départements = [str(i+1).zfill(3) for i in range(95)] + ['971', '972', '973', '974', '976']

    # list of arguments
    l_parser = argparse.ArgumentParser(description='Crawl {0}.'.format(g_url))
    l_parser.add_argument('search', help='Search keyword(s)')
    l_parser.add_argument('location', help='Location criterion')
    l_parser.add_argument('--min', type=int, help='Minimum delay between requests (in seconds)', default=0)
    l_parser.add_argument('--max', type=int, help='Minimum delay between requests (in seconds)', default=0)

    # create 118218 dir and email if not exist
    if not os.path.isdir(g_PagesJaunesDir):
        os.makedirs(g_PagesJaunesDir)

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
    l_pathA = os.path.join(g_PagesJaunesDir, 'PagesJaunesA_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))

    # B file type path and name
    l_pathB = os.path.join(g_PagesJaunesDir, 'PagesJaunesB_{0}-{1}.csv'.format(
        re.sub('\s+', '_', l_search),
        re.sub('\s+', '_', l_location)))

    # displays parameters
    print('Search keyword(s)        :', c.search)
    print('Location                 :', c.location)
    if l_minDelay > 0:
        print('Minimum delay (s.)       :', c.min)
    if l_maxDelay > 0:
        print('Maximum delay (s.)       :', c.max)

    # do the per-département search if the location parameter is 'France'
    if l_location.lower() == 'france':
        print('Location = France --> search all départements')

        # one tmp file per département
        for l_dépNum in l_départements:
            l_tmpA = os.path.join(g_PagesJaunesDir, '__tmpA_{0}.csv'.format(l_dépNum))
            l_tmpB = os.path.join(g_PagesJaunesDir, '__tmpB_{0}.csv'.format(l_dépNum))

            if not os.path.isfile(l_tmpA) and not os.path.isfile(l_tmpA):
                doSearch(l_search, l_dépNum, l_tmpA, l_tmpB, l_minDelay, l_maxDelay)

        # merge the tmp files
        CommonFunctions.concatTmp(g_PagesJaunesDir, l_départements, l_pathA, l_pathB)

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