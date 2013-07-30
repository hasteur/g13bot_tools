g13bot_tools
============

Wikipedia Bot tools revolving around AfC/G13

Setup
===========
1. Have SQLite, Python, and Python SQLite db hooks
2. Set up G13 database
    sqlite3 g13.db < g13.sql
3. Run the G13 nudge bot over a category (i.e. AfC submissions by date/February 2009)
    to notify users and seed personal database with potential G13 candidates
    python g13_nudge_bot.py [-from:UNDERSCORED_CATEGORY]
4. (Optional) Run the G13 Nomination bot.  Bot pulls list of potential
    candidates based off the personal database where the notification date is
    at least 30 days ago (Give the creator time to fix their problem)
    python g13_nom_bot.py
5. (TODO) Run the G13 cleanup process every few days to clean out records from the
    database where either a the targeted page no longer exists (deleted) or the page
    has been converted into a redirect (Either promoted successfully out of AfC or 
    targeted to a mainspace article that the submission was for)
