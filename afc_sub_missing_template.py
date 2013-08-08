#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Script to fix categories as needed

Syntax: python afc_sub_missing_template.py
"""

#
# (C) Rob W.W. Hooft, 2004
# (C) Daniel Herding, 2004
# (C) Wikipedian, 2004-2008
# (C) leogregianin, 2004-2008
# (C) Cyde, 2006-2010
# (C) Anreas J Schwab, 2007
# (C) xqt, 2009-2012
# (C) Pywikipedia team, 2008-2012
# (C) Hasteur, 2013
#
__version__ = '$Id$'
#
# Distributed under the terms of the MIT license.
#

import os, re, pickle, bz2, time, datetime, sys, logging
import wikipedia as pywikibot
import catlib, config, pagegenerators
from pywikibot import i18n

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
}

cfd_templates = {
    'wikipedia' : {
        'en':[u'cfd', u'cfr', u'cfru', u'cfr-speedy', u'cfm', u'cfdu'],
        'fi':[u'roskaa', u'poistettava', u'korjattava/nimi', u'yhdistettäväLuokka'],
        'he':[u'הצבעת מחיקה', u'למחוק'],
        'nl':[u'categorieweg', u'catweg', u'wegcat', u'weg2']
    },
    'commons' : {
        'commons':[u'cfd', u'move']
    }
}


class CategoryDatabase:
    '''This is a temporary knowledge base saving for each category the contained
    subcategories and articles, so that category pages do not need to be loaded
    over and over again

    '''
    def __init__(self, rebuild = False, filename = 'category.dump.bz2'):
        if rebuild:
            self.rebuild()
        else:
            try:
                if not os.path.isabs(filename):
                    filename = pywikibot.config.datafilepath(filename)
                f = bz2.BZ2File(filename, 'r')
                pywikibot.output(u'Reading dump from %s'
                                 % pywikibot.config.shortpath(filename))
                databases = pickle.load(f)
                f.close()
                # keys are categories, values are 2-tuples with lists as entries.
                self.catContentDB = databases['catContentDB']
                # like the above, but for supercategories
                self.superclassDB = databases['superclassDB']
                del databases
            except:
                # If something goes wrong, just rebuild the database
                self.rebuild()

    def rebuild(self):
        self.catContentDB={}
        self.superclassDB={}

    def getSubcats(self, supercat):
        '''For a given supercategory, return a list of Categorys for all its
        subcategories. Saves this list in a temporary database so that it won't
        be loaded from the server next time it's required.

        '''
        # if we already know which subcategories exist here
        if supercat in self.catContentDB:
            return self.catContentDB[supercat][0]
        else:
            subcatlist = supercat.subcategoriesList()
            articlelist = supercat.articlesList()
            # add to dictionary
            self.catContentDB[supercat] = (subcatlist, articlelist)
            return subcatlist

    def getArticles(self, cat):
        '''For a given category, return a list of Pages for all its articles.
        Saves this list in a temporary database so that it won't be loaded from the
        server next time it's required.

        '''
        # if we already know which articles exist here
        if cat in self.catContentDB:
            return self.catContentDB[cat][1]
        else:
            subcatlist = cat.subcategoriesList()
            articlelist = cat.articlesList()
            # add to dictionary
            self.catContentDB[cat] = (subcatlist, articlelist)
            return articlelist

    def getSupercats(self, subcat):
        # if we already know which subcategories exist here
        if subcat in self.superclassDB:
            return self.superclassDB[subcat]
        else:
            supercatlist = subcat.supercategoriesList()
            # add to dictionary
            self.superclassDB[subcat] = supercatlist
            return supercatlist

    def dump(self, filename = 'category.dump.bz2'):
        '''Saves the contents of the dictionaries superclassDB and catContentDB
        to disk.

        '''
        if not os.path.isabs(filename):
            filename = pywikibot.config.datafilepath(filename)
        if self.catContentDB or self.superclassDB:
            pywikibot.output(u'Dumping to %s, please wait...'
                             % pywikibot.config.shortpath(filename))
            f = bz2.BZ2File(filename, 'w')
            databases = {
                'catContentDB': self.catContentDB,
                'superclassDB': self.superclassDB
            }
            # store dump to disk in binary format
            try:
                pickle.dump(databases, f, protocol=pickle.HIGHEST_PROTOCOL)
            except pickle.PicklingError:
                pass
            f.close()
        else:
            try:
                os.remove(filename)
            except EnvironmentError:
                pass
            else:
                pywikibot.output(u'Database is empty. %s removed'
                                 % pywikibot.config.shortpath(filename))


class CategoryListifyRobot:
    '''Creates a list containing all of the members in a category.'''
    def __init__(self, catTitle, listTitle, editSummary, overwrite = False, showImages = False, subCats = False, talkPages = False, recurse = False):
        self.editSummary = editSummary
        self.overwrite = overwrite
        self.showImages = showImages
        self.site = pywikibot.getSite()
        self.cat = catlib.Category(self.site, 'Category:' + catTitle)
        self.catTitle = catTitle
        self.list = pywikibot.Page(self.site, listTitle)
        self.subCats = subCats
        self.talkPages = talkPages
        self.recurse = recurse

    def run(self):
        global logger
        listOfArticles = self.cat.articlesList(recurse = self.recurse)
        if self.subCats:
            listOfArticles += self.cat.subcategoriesList()
        listString = ""
        #Take this out once the full authorization has been given for this bot
        for article in listOfArticles:
          #Do Something
          article_text = article.get()
          if 'AFC submission' in article_text:
            logger.info(article.title())
            newtext = re.sub(u'\[\[Category:AfC_submissions_with_missing_AfC_template\]\]', \
              u'', \
              article_text \
            )
            summary = u'[[User:HasteurBot]] Task 3: Removing defect category on no longer valid submission'
            #article.put(newtext, summary, True)
def main(*args):
    global catDB
    global logger
    fromGiven = False
    toGiven = False
    batchMode = False
    editSummary = ''
    inPlace = False
    overwrite = False
    showImages = False
    talkPages = False
    recurse = False
    withHistory = False
    titleRegex = None
    pagesonly = False

    # This factory is responsible for processing command line arguments
    # that are also used by other scripts and that determine on which pages
    # to work on.
    genFactory = pagegenerators.GeneratorFactory()
    # The generator gives the pages that should be worked upon.
    gen = None

    # If this is set to true then the custom edit summary given for removing
    # categories from articles will also be used as the deletion reason.
    useSummaryForDeletion = True
    catDB = CategoryDatabase()
    action = None
    sort_by_last_name = False
    restore = False
    create_pages = False
    action = 'listify'
    fromGiven = True
    for arg in pywikibot.handleArgs(*args):
        if arg.startswith('-from:'):
            oldCatTitle = arg[len('-from:'):].replace('_', ' ')
            fromGiven = True
    if action == 'listify':
        if (fromGiven == False):
            oldCatTitle = pywikibot.input(
                u'Please enter the name of the category to listify:')
        oldCatTitle= u'AfC submissions with missing AfC template'
        newCatTitle = "User:HasteurBot/Log"
        recurse=True
        bot = CategoryListifyRobot(oldCatTitle, newCatTitle, editSummary,
                                   overwrite, showImages, subCats=True,
                                   talkPages=talkPages, recurse=recurse)
        bot.run()
    else:
        pywikibot.showHelp('category')


if __name__ == "__main__":
    logger = logging.getLogger('afc_sub_temp')
    logger.setLevel(logging.DEBUG)
    trfh = logging.handlers.TimedRotatingFileHandler('logs/afc_sub_template', \
        when='D', \
        interval = 14, \
        backupCount = 90, \
    )
    trfh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    trfh.setFormatter(formatter)
    logger.addHandler(trfh)
    try:
        main()
    finally:
        catDB.dump()
        pywikibot.stopme()
