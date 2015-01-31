# -*- coding: utf-8 -*-
"""
Script to notify interested users of pages that have become eligible for G13
Look at DB records
"""
import wikipedia as pywikibot
from pywikibot import i18n
#DB Config
from db_handle import *

def interested_notify():
    pywikibot.output("Starting Notify of editors interested in G13 eligiblity")
    cur = conn.cursor()
    cur.execute("SELECT notified,article FROM interested_notify ORDER BY notified,article")
    result_set = cur.fetchall()
    cur.close()
    if len(result_set) == 0:
        #No Results, don't bother with any more work
        return
    editor_current = result_set[0][0]
    list_current = ''
    for result in result_set:
        if editor_current != result[0]:
            #new record is a different editor, close out current notify list.
            write_notification(list_current,editor_current)
            editor_current = result[0]
            list_current = ''
        list_current += "\n*[[%s]]" % result[1]
    write_notification(list_current,editor_current)

def write_notification(list_current,editor_current):
    summary = "[[Wikipedia:Bots/Requests for approval/HasteurBot 9|HasteurBot 9]]: G13 Eligibility notices to interested editor"

    destination_page = pywikibot.Page(
        pywikibot.getSite(),
        'User talk:%s' % editor_current
    )
    header_line = '\n==G13 Eligibility Notice==\nThe following pages have become eligible for [[Wikipedia:Criteria_for_speedy_deletion#G13|CSD:G13]].'
    unified_notice = header_line + list_current + '\nThanks, ~~~~'
    try:
        user_talk_text = destination_page.get() + unified_notice
    except:
        user_talk_text = unified_notice
    destination_page.put(
        newtext = user_talk_text, 
        comment = summary,
        force=True
    )
    del_cur = conn.cursor()
    #del_cur.execute("DELETE from interested_notify where notified = %s",(editor_current))
    #conn.commit()
    del_cur.close()

interested_notify()
