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

import os, re, pickle, bz2, time, datetime, logging
import wikipedia as pywikibot
from pywikibot import i18n
#DB CONFIG
from db_handle import *

def g13_db_maintenance():
  """
    Go through the local DB and clean up any records that are no longer 
    appropriate
  """
  global logger
  logger.debug('Opened DB conn')
  cur = conn.cursor()
  cur.execute( \
    "SELECT article, editor" + \
    " from g13_records " + \
    " where notified is not null " + \
    " ORDER BY notified"
  )
  results = cur.fetchall()
  cur = None
  for article_item in results:
    try: 
        article = pywikibot.Page(
          pywikibot.getSite(),
          article_item[0]
        )
    except:
        print "Problem with %s" % article_item[0]
        continue
    print article_item[0]
    if False == article.exists():
        #Submission doesn't exisist any more, Remove it from the DB
        logger.info('Article %s doesn\'t exisist any more' % \
            article_item[0])
        curs = conn.cursor()
        sql_string = "DELETE from g13_records" + \
            " WHERE article = %s and editor = %s;"
        curs.execute(sql_string,article_item)
        conn.commit()
        curs = None
        logger.debug('Article %s removed from DB' % \
            article_item[0])
        continue
    if True == article.isRedirectPage():
        #Submission is now a redirect.  Happy Day, it got promoted to
        # article space!
        logger.info('Article %s was promoted to mainspace' % \
            article_item[0])
        curs = conn.cursor()
        sql_string = "DELETE from g13_records" + \
            " WHERE article = %s and editor = %s;"
        curs.execute(sql_string,article_item)
        conn.commit()
        curs = None
        logger.debug('Article %s was removed from DB' % \
            article_item[0])
        continue
    article_text = article.get()
    if '{{db-g13}}' not in article_text:
        #Check to see if we've ever nominated this article
        double_check_sql = "SELECT article, editor " + \
            "  from g13_records " + \
            "  where article = %s " + \
            "     and editor = %s " + \
            "     and nominated >= '1000-01-01 00:00:00';"
        curs = conn.cursor()
        curs.execute(double_check_sql,article_item)
        results = curs.fetchall()
        curs = None
        if 0 < len(results):
            #Hrm... Article no longer has my CSD template on it
            # and I've nominated it. Remove it from the DB
            logger.info('Article %s no longer has my csd template on it' % \
                article.title())
            curs = conn.cursor()
            sql_string = "DELETE from g13_records" + \
                " WHERE article = %s and editor = %s;"
            curs.execute(sql_string,article_item)
            conn.commit()
            curs = None
            logger.debug('Article %s was removed from DB' % \
                article_item[0])
            continue
  conn.close()
  logger.info('DB Maintenance completed')

def main():
    g13_db_maintenance()

if __name__ == "__main__":
    logger = logging.getLogger('g13_maintenance_bot')
    logger.setLevel(logging.DEBUG)
    trfh = logging.handlers.TimedRotatingFileHandler('logs/g13_db_maintenance', \
        when='D', \
        interval = 14, \
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
        pywikibot.stopme()
