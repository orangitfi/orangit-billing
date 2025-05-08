#!/bin/zsh

# Get current month and year
current_month=$(date '+%m')
current_year=$(date '+%Y')

# Calculate last day of current month
last_day=$(date -v+1m -v1d -v-1d +%d)

# Construct the date string for current month
DATE_STR="$current_year-$current_month"

# move to execution directory
cd $HOME/src/orangit/orangit-billing/billable-invoicing

# Construct and run the Python command
uv run python -m billable_invoicing util \
    --customer-data $HOME/laskutus/$DATE_STR/customer.csv \
    --raw-hours $HOME/laskutus/$DATE_STR/raw_hours.csv \
    --output $HOME/laskutus/$DATE_STR/utilization-$DATE_STR.txt \
    --start-date $DATE_STR-01 \
    --end-date $DATE_STR-$last_day 