#!/bin/bash
#DB Maintenance splitter
cd $HOME/g13bot_tools && jsub -cwd -mem 512m -N g13_db_maint -o /dev/null -e /dev/null  python g13_db_maintenance.py 0
cd $HOME/g13bot_tools && jsub -cwd -mem 512m -N g13_db_maint -o /dev/null -e /dev/null  python g13_db_maintenance.py 1
cd $HOME/g13bot_tools && jsub -cwd -mem 512m -N g13_db_maint -o /dev/null -e /dev/null  python g13_db_maintenance.py 2
cd $HOME/g13bot_tools && jsub -cwd -mem 512m -N g13_db_maint -o /dev/null -e /dev/null  python g13_db_maintenance.py 3
cd $HOME/g13bot_tools && jsub -cwd -mem 512m -N g13_db_maint -o /dev/null -e /dev/null  python g13_db_maintenance.py 4
