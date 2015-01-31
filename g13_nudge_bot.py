
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

import os, re, pickle, bz2, time, datetime, sys, logging
from dateutil.relativedelta import relativedelta
import wikipedia as pywikibot
import catlib, config, pagegenerators
from pywikibot import i18n
#DB CONFIG
from db_handle import *

afc_notify_list = []

# This is required for the text that is shown when you run this script
# with the parameter -help.
docuReplacements = {
    '&params;': pagegenerators.parameterHelp
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
        page_text = pywikibot.Page(pywikibot.getSite(),
                'User:HasteurBot/G13 OptIn Notifications').get()
        afc_notify_list = re.findall('\#\[\[User\:(?P<name>.*)\]\]',page_text)
        listOfArticles = self.cat.articlesList(recurse = self.recurse)
        if self.subCats:
            listOfArticles += self.cat.subcategoriesList()
        listString = ""
        page_match = re.compile('Wikipedia talk:Articles for creation/')
        page_match2 = re.compile('Draft:')
        ip_regexp = re.compile(r'^(?:(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
                               r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)|'
                               r'(((?=(?=(.*?(::)))\3(?!.+\4)))\4?|[\dA-F]{1,4}:)'
                               r'([\dA-F]{1,4}(\4|:\b)|\2){5}'
                               r'(([\dA-F]{1,4}(\4|:\b|$)|\2){2}|'
                               r'(((2[0-4]|1\d|[1-9])?\d|25[0-5])\.?\b){4}))\Z',
                               re.IGNORECASE)
        six_months_ago = ( 
          datetime.datetime.now() + relativedelta(months=-6) 
        ).timetuple()
        logger.debug('Opened DB conn')
        #Take this out once the full authorization has been given for this bot
        potential_article = False
        interested_insert = "INSERT INTO interested_notify (article,notified) VALUES (%s, %s)"
        for article in listOfArticles:
            if None != page_match.match(article.title()) or \
               None != page_match2.match(article.title()) :
              pywikibot.output(article.title())
              edit_time = time.strptime( \
                article.getLatestEditors()[0]['timestamp'],
                "%Y-%m-%dT%H:%M:%SZ"
              )
              potential_article = True
              creator = article.getCreator()[0]
              if edit_time < six_months_ago:
                #Notify Creator
                #Check for already nagged
                cur = conn.cursor()
                sql_string = "SELECT COUNT(*) FROM g13_records where " + \
                  "article = %s" + \
                  " and editor = %s;"
                try:
                  cur.execute(sql_string, (article.title(), creator))
                except:
                  logger.critical("Problem with %s" % article.title())
                  continue
                results = cur.fetchone()
                cur = None
                if results[0] > 0:
                  #We already have notified this user
                  logger.info(u"Already notifified (%s,%s)" %(creator, article.title()))
                  continue
                #Perform a null edit to get the creative Category juices flowing
                logger.info('Starting to process %s' % article.title())
                article.put(newtext = article.get(), comment="Null Edit")
                logger.debug('Null Edit complete')
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
                  " a page you created, has not been edited in 6 months" +\
                  ".  The Articles for Creation space is not an" + \
                  " indefinite storage location for content that is not " + \
                  "appropriate for articlespace.\n\n" + \
                  "If your submission is not edited soon, it could be " + \
                  "nominated for deletion.  If you would like to attempt " + \
                  "to save it, you will need to improve it.\n\n"
                if ip_regexp.match(creator) is None:
                  notice = notice + "You may request " + \
                    "[[WP:USERFY|Userfication]] of the content if it " + \
                    "meets requirements.\n\n"
                notice = notice + "If the " + \
                  "deletion has already occured, instructions on how you " + \
                  "may be able to retrieve it are available at " + \
                  "[[WP:REFUND/G13]].\n\n" + \
                  "Thank you for your attention. ~~~~"
                try:
                    user_talk_text = user_talk_page.get() +"\n"+ notice
                except:
                    user_talk_text = notice
                user_talk_page.put(newtext = user_talk_text,
                    comment = summary,
                    force=True)
                logger.debug('User Notified')
                cur = conn.cursor()
                sql_string = "INSERT INTO g13_records (article,editor)" + \
                  "VALUES (%s, %s)" 
                cur.execute(sql_string, (article.title(),creator))
                conn.commit()
                logger.debug('DB stored')
                cur = None
                #Notify Interested parties
                #Get List of Editors to the page
                editor_list = []
                for rev in article.getVersionHistory():
                    editor_list.append(rev[2])
                #Now let's intersect these to see who we get to notify
                intersection = set(editor_list) & set(afc_notify_list)
                message = '\n==G13 Eligibility==\n[[%s]] has become eligible for G13. ~~~~' % article.title()
                while intersection:
                    editor = intersection.pop()
                    cur = conn.cursor()
                    cur.execute(interested_insert, (article.title(),editor)
                    conn.commit()
                #Take this out when finished
        if False == potential_article:
            log_page = pywikibot.Page(
                self.site,
                'User:HasteurBot/Notices'
            )
            msg = "%s no longer has potential nominations\n\n" % self.catTitle
            page_text = log_page.get() + msg
            log_page.put(newtext = page_text,comment="Date empty")
            logger.critical(msg)
        conn.close()

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
