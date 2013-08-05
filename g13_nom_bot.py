#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Syntax: python g13_nom_bot.py<F3>

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

import os, re, pickle, bz2, time, datetime, logging
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
        self.list = pywikibot.Page(self.site, listTitle)
        self.subCats = subCats
        self.talkPages = talkPages
        self.recurse = recurse

    def run(self):
        global logger
        change_counter = 0
        csd_cat = catlib.Category(self.site, \
          'Category:Candidates for speedy deletion as abandoned AfC submissions' \
        )
        csd_cat_size = len(csd_cat.articlesList())
        max_noms_csd_cat = 50 - csd_cat_size
        logger.debug("Max Nominations from cat: %i" % max_noms_csd_cat)
        thirty_days_ago = ( datetime.datetime.now() - \
          datetime.timedelta(days=30)
        )
        bot_recheck_date = (
            datetime.datetime.now() - datetime.timedelta(days=(180+30))
        ).timetuple()
        notification_date = thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S')
        logger.debug("Notification Date: %s" % notification_date)
        cur = conn.cursor()
        sql_string = "SELECT article, editor" + \
          " from g13_records " + \
          " where notified <= %s " + \
          "   and nominated = '0000-00-00 00:00:00' LIMIT %i"
        cur.execute( sql_string, \
            (notification_date, max_noms_csd_cat)
        )
        results = cur.fetchall()
        logger.debug("Results Fetched: %i" % len(results))
        cur = None
        for article_item in results:
            if change_counter == max_noms_csd_cat:
              cat_limit_string = u"\n\n\03{lightred}***%s***\03{default}" \
                % "Hit max CSD category nominations limit"
              pywikibot.output(cat_limit_string)
              hasteur_talk = pywikibot.Page(
                self.site,
                'User talk:Hasteur'
              )
              summary = "[[User:HasteurBot]]: G13 category is '''full'''"
              add_text( \
                page = hasteur_talk, \
                addText = '\nG13 Category membership exceeded ~~~~\n', \
                summary = summary, \
                always = True, \
                up = False \
              )
              break
            article = pywikibot.Page(
              self.site,
              article_item[0]
            )
            if False == article.exists():
                #Submission doesn't exisist any more, Remove it from the DB
                curs = conn.cursor()
                sql_string = "DELETE from g13_records" + \
                    " WHERE article = %s " + \
                    " and editor = %s;"  
                curs.execute(sql_string,article_item)
                conn.commit()
                curs = None
                logger.info("Submission %s doesn't exisist." % article_item[0])
                continue
            if True == article.isRedirectPage():
                #Submission is now a redirect.  Happy Day, it got promoted to
                # article space!
                curs = conn.cursor()
                sql_string = "DELETE from g13_records" + \
                    " WHERE article = %s " + \
                    " and editor = %s;"  
                curs.execute(sql_string,article_item)
                conn.commit()
                curs = None
                logger.info("Submission %s is now a redirect" % article_item[0])
                continue
            #Re-check date on article for edits (to be extra sure)
            edit_time = time.strptime( \
                article.getLatestEditors()[0]['timestamp'],
                "%Y-%m-%dT%H:%M:%SZ"
            )
            if edit_time > bot_recheck_date:
                #Page has been updated since the nudge, Not valid any more
                curs = conn.cursor()
                sql_string = "DELETE from g13_records" + \
                    " WHERE article = %s " + \
                    " and editor = %s;"  
                curs.execute(sql_string,article_item)
                conn.commit()
                curs = None
                logger.info("Submission %s has been updated" % article_item[0])
                continue

            add_text( \
              page = article, \
              addText = '{{db-g13}}', \
              summary = '[[User:HasteurBot]]:Nominating for [[WP:G13|CSD:G13]]', \
              always = True, \
              up = True
            )
            logger.info("Nominated: %s" % article_item[0])
            creator = article_item[1]
            curs = conn.cursor()
            sql_string = "UPDATE g13_records" + \
              " set nominated = current_timestamp" + \
              "  where " + \
              "   article = %s " + \
              "     and" + \
              "   editor = %s; " 
            curs.execute(sql_string, article_item)
            conn.commit()
            curs = None
            logger.debug('Updated nominated timestamp')
            user_talk_page = pywikibot.Page(
              self.site,
              'User talk:%s' % creator
            )
            up_summary = '[[User:HasteurBot]]: Notification of '+\
              '[[WP:G13|CSD:G13]] nomination on [[%s]]' % (article.title())
            add_text( \
              page = user_talk_page, \
              summary = up_summary, \
              addText = '{{subst:db-afc-notice|%s}}~~~~\n' % (article.title()), \
              always = True, \
              up = False, \
              create = True\
            )
            logger.info("Notified %s for %s" % (creator, article_item[0]))
            change_counter = change_counter + 1
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
        #pywikibot.showDiff(text, newtext)
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
                                 minorEdit=False)
                    else:
                        page.put_async(newtext, summary,
                                       minorEdit=False)
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
    #for arg in pywikibot.handleArgs(*args):
    #    if arg == 'listify':
    #        action = 'listify'
    #    else:
    #        genFactory.handleArg(arg)

    if action == 'listify':
        oldCatTitle='test'
        #if (fromGiven == False):
        #    oldCatTitle = pywikibot.input(
        #        u'Please enter the name of the category to nominate over:')
        newCatTitle = "User:HasteurBot/Log"
        recurse=True
        bot = CategoryListifyRobot(oldCatTitle, newCatTitle, editSummary,
                                   overwrite, showImages, subCats=True,
                                   talkPages=talkPages, recurse=recurse)
        bot.run()
    else:
        pywikibot.showHelp('category')


if __name__ == "__main__":
    #TODO: Short Circuiting this untill the bot is more acceptable to the
    # community
    logger = logging.getLogger('g13_nom_bot')
    logger.setLevel(logging.DEBUG)
    trfh = logging.handlers.TimedRotatingFileHandler('logs/g13_nom', \
        when='D', \
        interval = 1, \
        backupCount = 90, \
    )
    trfh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    trfh.setFormatter(formatter)
    logger.addHandler(trfh)
    trfh.doRollover()
    try:
        main()
    finally:
        catDB.dump()
        pywikibot.stopme()
