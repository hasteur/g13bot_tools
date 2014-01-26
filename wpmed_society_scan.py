#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
This script will display the list of pages transcluding a given list of
templates. It can also be used to simply count the number of pages (rather than
listing each individually).

Syntax: python templatecount.py command [arguments]

Command line options:

-count        Counts the number of times each template (passed in as an
              argument) is transcluded.

-list         Gives the list of all of the pages transcluding the templates
              (rather than just counting them).

-namespace:   Filters the search to a given namespace.  If this is specified
              multiple times it will search all given namespaces

Examples:

Counts how many times {{ref}} and {{note}} are transcluded in articles.

     python templatecount.py -count -namespace:0 ref note

Lists all the category pages that transclude {{cfd}} and {{cfdu}}.

     python templatecount.py -list -namespace:14 cfd cfdu

"""
#
# (c) Pywikipedia bot team, 2006-2012
# (c) xqt, 2009-2013
#
# Distributed under the terms of the MIT license.
#
__version__ = '$Id: fea8063ba1d66346408353cce5235ac936d5cbfa $'

import datetime
import wikipedia as pywikibot
import pagegenerators as pg

import re

templates = ['WPMED', 
             "WikiProject Medicine", 
             'CMedWikiProject', 
             'WPMEDICINE',
             'WP Medicine',
             'Wikiproject Medicines',
             'Wikiproject Medicine',
             'WPMedicine',
             'WPMed',
             'WikiProject Med'
            ]
templates = ['WPMED']


class TemplateCountRobot:

    @staticmethod
    def countTemplates(templates, namespaces):
        templateDict = TemplateCountRobot.template_dict(templates, namespaces)
        pywikibot.output(u'\nNumber of transclusions per template',
                         toStdout=True)
        pywikibot.output(u'-' * 36, toStdout=True)
        total = 0
        for key in templateDict:
            count = len(templateDict[key])
            pywikibot.output(u'%-10s: %5d' % (key, count),
                             toStdout=True)
            total += count
        pywikibot.output(u'TOTAL     : %5d' % total, toStdout=True)
        pywikibot.output(u'Report generated on %s'
                         % datetime.datetime.utcnow().isoformat(),
                         toStdout=True)

    @staticmethod
    def listTemplates(templates, namespaces):
        templateDict = TemplateCountRobot.template_dict(templates, namespaces)
        pywikibot.output(u'\nList of pages transcluding templates:',
                         toStdout=True)
        
        for key in templates:
            pywikibot.output(u'* %s' % key)
        pywikibot.output(u'-' * 36, toStdout=True)
        total = 0
        affected_pages = []
        for key in templateDict:
            for page in templateDict[key]:
                return_eval = TemplateCountRobot.evaluate_qualified(page)
                if return_eval != '':
                    affected_pages.append(return_eval)
                #pywikibot.output(page.title(), toStdout=True)
                total += 1
        pywikibot.output(affected_pages)
        pywikibot.output(u'Total page count: %d' % total)
        pywikibot.output(u'Report generated on %s'
                         % datetime.datetime.utcnow().isoformat(),
                         toStdout=True)
    @staticmethod
    def evaluate_qualified(page):
        page_text = page.get()
        match = False
        #Check Matching Cases
        match_list = [
            '{{WikiProject Biography',
            '{{WPBIO|',
            '{{WP Biography',
            '{{WPbiography',
            '{{Wikiproject Biography',
            '{{WP Bio|',
            '{{Bio|',
            '{{WPBiography',
            '{{WikiProject Biographies',
            '{{WikiProject biography',
            '{{Wpbio|',
            '{{Companies',
            '{{WPCO',
            '{{WP Companies',
            '{{WPCOMPANIES',
            '{{WikiProject Corporations',
            '{{WP Company',
            '{{WPCOMPANY',
            '{{WPCORP',
            '{{WikiProject Corp',
            '{{Wpco',
            '{{WikiProject Companies',
            '{{WikiProject Organizations',
            '{{WikiProject Organizations CoopBanner',
            '{{Organizations',
            '{{WikiProject Organization',
            '{{WikiProject Organizations',
            '{{WPORG',
            '{{WPOrganizations',
            '{{WPOrganisations',
            '{{WP Organizations',
            '{{WP Organisation',
            '{{WPORGANIZATIONS'
        ]
        for key in match_list:
            if key in page_text:
                match = True
        if 'CHARITY' in page.title().upper():
            match = True
        #Check Exclusions
        if match == False:
            return ''
        else:
            #Found a match
            print page.title()
            matched_template = ''
            for template in templates:
                matched_template = re.findall('{{'+template+'\|?.*}}',page_text)
                if 1 == len(matched_template):
                    #Found the instigating template
                    break
            if 'society=' not in matched_template:
                #Doesn't have the society parm, let's add it
                strip_template = matched_template[0]
                replace_template = strip_template[0:-2]+'|society=yes|society-imp=???}}'
                replacement_text = page_text.replace(strip_template,replace_template)
                comment = "[[Wikipedia:Bots/Requests for approval/HasteurBot 7|HasteurBot 7] Adding Society Task Force Parm"
                #page.put(replacement_text,comment = comment,maxTries=5)
                return page.title()
            else:
                return ''


    @staticmethod
    def template_dict(templates, namespaces):
        gen = TemplateCountRobot.template_dict_generator(templates, namespaces)
        templateDict = {}
        for template, transcludingArray in gen:
            templateDict[template] = transcludingArray
        return templateDict

    @staticmethod
    def template_dict_generator(templates, namespaces):
        mysite = pywikibot.getSite()
        # The names of the templates are the keys, and lists of pages
        # transcluding templates are the values.
        mytpl = mysite.getNamespaceIndex(mysite.template_namespace())
        for template in templates:
            transcludingArray = []
            gen = pg.ReferringPageGenerator(
                pywikibot.Page(mysite, template, defaultNamespace=mytpl),
                onlyTemplateInclusion=True)
            if namespaces:
                gen = pg.NamespaceFilterPageGenerator(gen, namespaces)
            for page in gen:
                transcludingArray.append(page)
            yield template, transcludingArray


def main():
    operation = None
    argsList = []
    namespaces = []

    for arg in pywikibot.handleArgs():
        if arg == '-count':
            operation = "Count"
        elif arg == '-list':
            operation = "List"
        elif arg.startswith('-namespace:'):
            try:
                namespaces.append(int(arg[len('-namespace:'):]))
            except ValueError:
                namespaces.append(arg[len('-namespace:'):])
        else:
            argsList.append(arg)

    if not operation:
        pywikibot.showHelp('templatecount')
    else:
        robot = TemplateCountRobot()
        if not argsList:
            argsList = templates
        choice = ''
        if 'reflist' in argsList:
            pywikibot.output(
                u'NOTE: it will take a long time to count "reflist".')
            choice = pywikibot.inputChoice(
                u'Proceed anyway?', ['yes', 'no', 'skip'], ['y', 'n', 's'], 'y')
            if choice == 's':
                argsList.remove('reflist')
        if choice == 'n':
            return
        elif operation == "Count":
            robot.countTemplates(argsList, namespaces)
        elif operation == "List":
            robot.listTemplates(argsList, namespaces)

if __name__ == "__main__":
    try:
        main()
    finally:
        pywikibot.stopme()
