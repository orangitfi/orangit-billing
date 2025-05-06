#!/bin/zsh

# Get current month and year
current_month=$(date '+%m')
current_year=$(date '+%Y')

# Zero-pad the month if necessary
current_month=$(printf "%02d" $current_month)

# Get the number of days in the current month
if [ $current_month -eq 4 ] || [ $current_month -eq 6 ] || [ $current_month -eq 9 ] || [ $current_month -eq 11 ]; then
    last_day=30
elif [ $current_month -eq 2 ]; then
    # Check for leap year
    if [ $((current_year % 4)) -eq 0 ] && { [ $((current_year % 100)) -ne 0 ] || [ $((current_year % 400)) -eq 0 ]; }; then
        last_day=29
    else
        last_day=28
    fi
else
    last_day=31
fi

# Construct the dates
DATE_STR="$current_year-$current_month"
START_DATE="$current_year-$current_month-01"
END_DATE="$current_year-$current_month-$last_day"

# move to execution directory
cd $HOME/src/orangit/orangit-billing/billable-invoicing
# Construct and run the Python command
uv run python -m billable_invoicing fetch-hours \
    --company "OrangIT Oy" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --output-path $HOME/laskutus/$DATE_STR/ \
    --customer-data "$HOME/laskutus/$DATE_STR/customer.csv" \
    --rates-file "$HOME/laskutus/$DATE_STR/rates.csv" \
    --result-file "$HOME/laskutus/$DATE_STR/workday-$DATE_STR.csv" 