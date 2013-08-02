#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Syntax: python g13_db_maintenance_bot.py

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

import os, re, pickle, bz2, time, datetime, sqlite3
import wikipedia as pywikibot
from pywikibot import i18n

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
        conn = sqlite3.connect('g13.db')
        cur = conn.cursor()
        cur.execute( \
          "SELECT article, editor" + \
          " from g13_records " + \
          " where notified is not null " + \
          "   and nominated is not null" + \
          " ORDER BY nominated"
        )
        results = cur.fetchall()
        cur = None
        for article_item in results:
            article = pywikibot.Page(
              self.site,
              article_item[0]
            )
            curs = conn.cursor()
            sql_string = "UPDATE g13_records" + \
              " set nominated = current_timestamp" + \
              "  where " + \
              "   article = ? " + \
              "     and" + \
              "   editor = ?" 
            curs.execute(sql_string, article_item)
            conn.commit()
            curs = None
            user_talk_page = pywikibot.Page(
              self.site,
              'User talk:%s' % creator
            )
            summary = '[[User:HasteurBot]]: Notification of '+\
              '[[WP:G13|CSD:G13]] nomination on [[%s]]' % (article.title())
            add_text( \
              page = user_talk_page, \
              addText = '{{subst:db-afc-notice|%s}}\n' % (article.title()), \
              always = True, \
              up = False, \
              create = True\
            )

def g13_db_maintenance():
  """
    Go through the local DB and clean up any records that are no longer 
    appropriate
  """
  conn = sqlite3.connect('g13.db')
  cur = conn.cursor()
  cur.execute( \
    "SELECT article, editor" + \
    " from g13_records " + \
    " where notified is not null " + \
    "   and nominated is not null" + \
    " ORDER BY nominated"
  )
  results = cur.fetchall()
  cur = None
  for article_item in results:
    article = pywikibot.Page(
      pywikibot.getSite(),
      article_item[0]
    )
    if False == article.exists():
        #Submission doesn't exisist any more, Remove it from the DB
        curs = conn.cursor()
        sql_string = "DELETE from g13_records" + \
            " WHERE article = ? and editor = ?;"
        curs.execute(sql_string,article_item)
        conn.commit()
        curs = None
        pywikibot.output("Submission %s doesn't exisist." % article_item[0])
        continue
    if True == article.isRedirectPage():
        #Submission is now a redirect.  Happy Day, it got promoted to
        # article space!
        curs = conn.cursor()
        sql_string = "DELETE from g13_records" + \
            " WHERE article = ? and editor = ?;"
        curs.execute(sql_string,article_item)
        conn.commit()
        curs = None
        pywikibot.output("Submission % is now a redirect" % article_item[0])
        continue
  conn.close()

def main():
    g13_db_maintenance()

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
