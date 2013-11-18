#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Some content in this script is covered under a Creative commons Attribution-ShareAlike 3.0 licence
Regexes were adapted from Wikipedia AFC Helper project
 *Submissions.js [1]
 *core.js [2]

[1] https://github.com/WPAFC/afch/blob/416c434b8d3db62339c5ed3e70a734da7aa1015a/src/submissions.js
[2] https://github.com/WPAFC/afch/blob/ef82979c391274dda0e0de795476fc1cf5d01157/src/core.js

Scripts to run the clean logic on AFC pending submissions.

Syntax: python afc_cleaner.py [-from:UNDERSCORED_CATEGORY]
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
from dateutil.relativedelta import relativedelta
import wikipedia as pywikibot
import catlib, config, pagegenerators
from pywikibot import i18n
#DB CONFIG
from db_handle import *

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
            clean_submission(article)
def clean_submission(page):
    global logger
    print '-*'*20
    print page.title()
    page_text = page.get()
    page_text = uncomment_categories(page_text)
    page_text = fix_afc_comment(page_text)
    page_text = afcHelper_cleanup(page_text)
    page_text = remove_bolding_in_headlines(page_text)
    page_text = disable_categories(page_text)
    page_text = line_1188_replacements(page_text)
    print '-'*20
    print page_text

def line_1188_replacements(page_text):
    global logger
    imp_text = re.sub('\<\!--Please don't change anything and press save --\>','',page_text)
    imp_text = re.sub('\<\!-- Just press the \"Save page\" button below without changing anything! Doing so will submit your article submission for review. Once you have saved this page you will find a new yellow 'Review waiting' box at the bottom of your submission page. If you have submitted your page previously, the old pink 'Submission declined' template or the old grey 'Draft' template will still appear at the top of your submission page, but you should ignore them. Again, please don't change anything in this text box. Just press the \"Save page\" button below. --\>','',imp_text)
    imp_text = re.sub('== Request review at \[\[WP:AFC\]\] ==\n','',imp_text)
    imp_text = re.sub('(?:<\s*references\s*>([\S\s]*)<\/references>|<\s*references\s*\/\s*>)','{{reflist|refs=\g<1>',imp_text)
    imp_text = re.sub('{{reflist|refs=}}','{{reflist}}',imp_text)
    imp_text = re.sub('\{\{(userspacedraft|userspace draft|user sandbox|Please leave this line alone \(sandbox heading\))(?:\{\{[^{}]*\}\}|[^}{])*\}\}','',imp_text)
    imp_text = re.sub('<!--\s*-->','',imp_text)
    imp_text = re.sub('^----+$','',imp_text)
    imp_text = re.sub('\[\[:?Category:AfC(_|\s*)+submissions(_|\s*)+with(_|\s*)+missing(_|\s*)+AfC(_|\s*)+template\]\]','',imp_text)
    if imp_text != page_text:
        print "Line 1188 replacements triggered"
        return imp_text
    return page_text

def remove_bolding_in_headlines(page_text):
    global logger
    #Line 1178 test
    imp_text = re.sub('[\s\n]*(={2,})\s*(?:\s*<big>|\s*\'\'\')*\s*(.*?)\s*(?:\s*<\/big>|\s*\'\'\')*\s*?(={2,})[\n\s]*',
        "\n\n \g<1> \g<2> \g<1>", page_text)
    if imp_text != page_text:
        print "Removed some bolding"
        return imp_text
    return page_text

def disable_categories(page_text):
    global logger
    #Line 1110 test
    imp_text = re.sub('\[\[Category:', '[[:Category:',page_text)
    if imp_text != page_text:
        print "Disabled some categories"
        return imp_text
    return page_text

def fix_afc_comment(page_text):
    global logger
    #Line 1070 test
    imp_text = re.sub('\{\{afc comment(?!\s*\|\s*1\s*=)\s*\}\}\s*(.*?)\s*[\r\n]',
        '{{afc comment|1=\g<1>}}',page_text)
    if imp_text != page_text:
        print "Fixed AFC comments"
        return imp_text
    return page_text

def afcHelper_cleanup(page_text):
    global logger
    #Line 258 (core.js) test
    imp_text = re.sub('(\[){1,2}(?:https?:)?\/\/(en.wikipedia.org\/wiki|enwp.org)\/([^\s\|\]\[]+)(\s|\|)?((?:\[\[[^\[\]]*\]\]|[^\]\[])*)(\]){1,2}', internal_rewrite, page_text)
    if imp_text != page_text:
        print "Rewriting internal links"
        return imp_text
    return page_text

def internal_rewrite(matchobj):
    global logger
    pagename = matchobj.group(3).replace('_',' ')
    displayname = matchobj.group(5).replace('_', ' ')
    if pagename == displayname:
        displayname = ''
    if displayname != '':
        replacetext = '[[%s|%s]]' % (pagename,displayname)
        return replacetext
    return '[[%s]]' % pagename
def uncomment_categories(page_text):
    global logger
    #Line 1067 test
    imp_text = re.sub('\<!--\s*((\[\[:{0,1}(Category:.*?)\]\]\s*)+)--\>',
        '\g<2>',page_text)
    if imp_text != page_text:
        print "Categories uncommented"
        return imp_text
    return page_text
def add_text(page=None, addText=None, summary=None, regexSkip=None,
             regexSkipUrl=None, always=False, up=False, putText=True,
             oldTextGiven=None, reorderEnabled=True, create=False):
    global logger
    # When a page is tagged as "really well written" it has a star in the
    # interwiki links. This is a list of all the templates used (in regex
    # format) to make the stars appear.
    starsList = [
        u'bueno',
        u'bom interwiki',
        u'cyswllt[ _]erthygl[ _]ddethol', u'dolen[ _]ed',
        u'destacado', u'destaca[tu]',
        u'enllaç[ _]ad',
        u'enllaz[ _]ad',
        u'leam[ _]vdc',
        u'legătură[ _]a[bcf]',
        u'liamm[ _]pub',
        u'lien[ _]adq',
        u'lien[ _]ba',
        u'liên[ _]kết[ _]bài[ _]chất[ _]lượng[ _]tốt',
        u'liên[ _]kết[ _]chọn[ _]lọc',
        u'ligam[ _]adq',
        u'ligoelstara',
        u'ligoleginda',
        u'link[ _][afgu]a', u'link[ _]adq', u'link[ _]f[lm]', u'link[ _]km',
        u'link[ _]sm', u'linkfa',
        u'na[ _]lotura',
        u'nasc[ _]ar',
        u'tengill[ _][úg]g',
        u'ua',
        u'yüm yg',
        u'רא',
        u'وصلة مقالة جيدة',
        u'وصلة مقالة مختارة',
    ]

    errorCount = 0
    site = pywikibot.getSite()
    pathWiki = site.family.nicepath(site.lang)
    site = pywikibot.getSite()
    if oldTextGiven is None:
        try:
            text = page.get()
        except pywikibot.NoPage:
            if create:
                pywikibot.output(u"%s doesn't exist, creating it!"
                                 % page.title())
                text = u''
            else:
                pywikibot.output(u"%s doesn't exist, skip!" % page.title())
                return (False, False, always)
        except pywikibot.IsRedirectPage:
            pywikibot.output(u"%s is a redirect, skip!" % page.title())
            return (False, False, always)
    else:
        text = oldTextGiven
    # If not up, text put below
    if not up:
        newtext = text
        # Translating the \\n into binary \n
        addText = addText.replace('\\n', '\n')
        if (reorderEnabled):
            # Getting the categories
            categoriesInside = pywikibot.getCategoryLinks(newtext, site)
            # Deleting the categories
            newtext = pywikibot.removeCategoryLinks(newtext, site)
            # Getting the interwiki
            interwikiInside = pywikibot.getLanguageLinks(newtext, site)
            # Removing the interwiki
            newtext = pywikibot.removeLanguageLinks(newtext, site)

            # Adding the text
            newtext += u"\n%s" % addText
            # Reputting the categories
            newtext = pywikibot.replaceCategoryLinks(newtext,
                                                     categoriesInside, site,
                                                     True)
            # Dealing the stars' issue
            allstars = []
            starstext = pywikibot.removeDisabledParts(text)
            for star in starsList:
                regex = re.compile('(\{\{(?:template:|)%s\|.*?\}\}[\s]*)'
                                   % star, re.I)
                found = regex.findall(starstext)
                if found != []:
                    newtext = regex.sub('', newtext)
                    allstars += found
            if allstars != []:
                newtext = newtext.strip() + '\r\n\r\n'
                allstars.sort()
                for element in allstars:
                    newtext += '%s\r\n' % element.strip()
            # Adding the interwiki
            newtext = pywikibot.replaceLanguageLinks(newtext, interwikiInside,
                                                     site)
        else:
            newtext += u"\n%s" % addText
    else:
        newtext = addText + '\n' + text
    if putText and text != newtext:
        #pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
        #                 % page.title())
        #pywikibot.showDiff(text, newtext)
        logger.debug("Editing: %s" % page.title())
    # Let's put the changes.
    while True:
        # If someone load it as module, maybe it's not so useful to put the
        # text in the page
        if putText:
            if always or choice == 'y':
                try:
                    pass
                    if always:
                        page.put(newtext, summary,
                                 minorEdit=page.namespace() != 3)
                    else:
                        page.put_async(newtext, summary,
                                       minorEdit=page.namespace() != 3)
                except pywikibot.EditConflict:
                    pywikibot.output(u'Edit conflict! skip!')
                    return (False, False, always)
                except pywikibot.ServerError:
                    errorCount += 1
                    if errorCount < 5:
                        pywikibot.output(u'Server Error! Wait..')
                        time.sleep(5)
                        continue
                    else:
                        raise pywikibot.ServerError(u'Fifth Server Error!')
                except pywikibot.SpamfilterError, e:
                    pywikibot.output(
                        u'Cannot change %s because of blacklist entry %s'
                        % (page.title(), e.url))
                    return (False, False, always)
                except pywikibot.PageNotSaved, error:
                    pywikibot.output(u'Error putting page: %s' % error.args)
                    return (False, False, always)
                except pywikibot.LockedPage:
                    pywikibot.output(u'Skipping %s (locked page)'
                                     % page.title())
                    return (False, False, always)
                else:
                    # Break only if the errors are one after the other...
                    errorCount = 0
                    return (True, True, always)
        else:
            return (text, newtext, always)

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
    for arg in pywikibot.handleArgs(*args):
        if arg.startswith('-from:'):
            oldCatTitle = arg[len('-from:'):].replace('_', ' ')
            fromGiven = True
    if action == 'listify':
        if (fromGiven == False):
            oldCatTitle = pywikibot.input(
                u'Please enter the name of the category to listify:')
        newCatTitle = "User:HasteurBot/Log"
        recurse=True
        logger.info('Starting Nudge run over %s' % oldCatTitle)
        bot = CategoryListifyRobot(oldCatTitle, newCatTitle, editSummary,
                                   overwrite, showImages, subCats=True,
                                   talkPages=talkPages, recurse=recurse)
        bot.run()
    else:
        pywikibot.showHelp('category')


if __name__ == "__main__":
    logger = logging.getLogger('g13_nudge_bot')
    logger.setLevel(logging.DEBUG)
    trfh = logging.handlers.TimedRotatingFileHandler('logs/g13_nudge', \
        when='D', \
        interval = 3, \
        backupCount = 90, \
    )
    trfh.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    trfh.setFormatter(formatter)
    logger.addHandler(trfh)
    trfh.doRollover()
    try:
        main()
    finally:
        catDB.dump()
        pywikibot.stopme()
