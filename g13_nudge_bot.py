#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Scripts to manage categories.

Syntax: python g13_nudge_bot.py [-from:UNDERSCORED_CATEGORY]
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

import os, re, pickle, bz2, time, datetime, sqlite3, sys
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
        self.list = pywikibot.Page(self.site, listTitle)
        self.subCats = subCats
        self.talkPages = talkPages
        self.recurse = recurse

    def run(self):
        listOfArticles = self.cat.articlesList(recurse = self.recurse)
        if self.subCats:
            listOfArticles += self.cat.subcategoriesList()
        listString = ""
        page_match = re.compile('Wikipedia talk:Articles for creation/')
        six_months_ago = ( \
          datetime.datetime.now() - datetime.timedelta(days=(180)) \
        ).timetuple()
        conn = sqlite3.connect('g13.db')
        #Take this out once the full authorization has been given for this bot
        limit = 50
        for article in listOfArticles:
            #Take 2 lines out once the full auth is given
            if limit <= 0:
              break
            if None != page_match.match(article.title()):
              pywikibot.output(article.title())
              edit_time = time.strptime( \
                article.getLatestEditors()[0]['timestamp'],
                "%Y-%m-%dT%H:%M:%SZ"
              )
              creator = article.getCreator()[0]
              if edit_time < six_months_ago:
                #Notify Creator
                #Check for already nagged
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM g13_records where " + \
                  "article = ? and editor = ?", (article.title(),creator))
                results = cur.fetchone()
                cur = None
                if results[0] > 0:
                  #We already have notified this user
                  pywikibot.output(u"Already notifified (%s,%s)" %(creator, article.title()))
                  continue
                #Perform a null edit to get the creative Category juices flowing
                add_text( \
                  page = article, \
                  addText = '', \
                  always = True, \
                  summary = 'Null Edit', \
                  up = True, \
                  create = False \
                )
                user_talk_page = pywikibot.Page(
                  self.site,
                  'User talk:%s' % creator
                )
                summary = '[[User:HasteurBot]]: Notification of '+\
                  '[[WP:G13|CSD:G13]] potential nomination of [[%s]]' % (article.title())
                notice = "==[[%s]] concern==\n" % (article.title()) +\
                  "Hi there, I'm [[User:HasteurBot|HasteurBot]]. I "+ \
                  "just wanted to let you know " + \
                  "that [[%s]]," %(article.title()) +\
                  " a page you created has not been edited in at least 180" + \
                  " days.  The Articles for Creation space is not an" + \
                  " indefinite storage location for content that is not " + \
                  "appropriate for articlespace.\n" + \
                  "If your submission is not edited soon, it could be " + \
                  "nominated for deletion.  If you would like to attempt " + \
                  "to save it, you will need to improve it.\nIf the " + \
                  "deletion has already occured, instructions on how you " + \
                  "may be able to retrieve it are available at " + \
                  "[[WP:REFUND/G13]].\n" + \
                  "Thank you for your attention. ~~~~"
                add_text( \
                  page = user_talk_page, \
                  addText = notice, \
                  always = True, \
                  summary = summary, \
                  up = False, \
                  create = True\
                )
                cur = conn.cursor()
                cur.execute("INSERT INTO g13_records (article,editor)" + \
                  "VALUES (?, ?)" , (article.title(),creator))
                conn.commit()
                cur = None
                #Take this out when finished
                limit = limit - 1
        conn.close()
def add_text(page=None, addText=None, summary=None, regexSkip=None,
             regexSkipUrl=None, always=False, up=False, putText=True,
             oldTextGiven=None, reorderEnabled=True, create=False):
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
        pywikibot.output(u"\n\n>>> \03{lightpurple}%s\03{default} <<<"
                         % page.title())
        pywikibot.showDiff(text, newtext)
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
        bot = CategoryListifyRobot(oldCatTitle, newCatTitle, editSummary,
                                   overwrite, showImages, subCats=True,
                                   talkPages=talkPages, recurse=recurse)
        bot.run()
    else:
        pywikibot.showHelp('category')


if __name__ == "__main__":
    try:
        main()
    finally:
        catDB.dump()
        pywikibot.stopme()
