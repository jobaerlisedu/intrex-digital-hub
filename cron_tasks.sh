#!/bin/bash
# Intrex Digital Hub — cPanel Cron Task Runner
# ==============================================
# 1. Upload this file to your server (chmod +x cron_tasks.sh)
# 2. Update the paths below to match your cPanel setup
# 3. Add to cPanel → Cron Jobs:
#
#    * * * * * /home/$(whoami)/app.dremotic.com/cron_tasks.sh >/dev/null 2>&1
#
#    Or for specific frequencies:
#    0 * * * * /home/$(whoami)/app.dremotic.com/cron_tasks.sh hourly
#    0 2 * * * /home/$(whoami)/app.dremotic.com/cron_tasks.sh daily
#    0 3 * * 1 /home/$(whoami)/app.dremotic.com/cron_tasks.sh weekly
#    0 4 1 * * /home/$(whoami)/app.dremotic.com/cron_tasks.sh monthly
# ==============================================

DJANGO_DIR=/home/$(whoami)/app.dremotic.com
VENV_DIR=/home/$(whoami)/virtualenv/app.dremotic.com/3.11

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual env not found at $VENV_DIR"
    exit 1
fi

export PATH=$VENV_DIR/bin:$PATH
cd $DJANGO_DIR || exit 1

# Load .env variables
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

FREQ=${1:-auto}
python manage.py run_scheduled_tasks $FREQ >> cron.log 2>&1
