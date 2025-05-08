#!/bin/zsh

# Get current month and year
current_month=$(date '+%m')
current_year=$(date '+%Y')

# Calculate previous month
previous_month=$((10#$current_month - 1))

# Adjust year and month if necessary
if [ $previous_month -eq 0 ]; then
	previous_month=12
	previous_year=$((current_year - 1))
else
	previous_year=$current_year
fi

# Zero-pad the month if necessary
previous_month=$(printf "%02d" $previous_month)

# Get the number of days in the previous month
if [ $previous_month -eq 4 ] || [ $previous_month -eq 6 ] || [ $previous_month -eq 9 ] || [ $previous_month -eq 11 ]; then
	last_day=30
elif [ $previous_month -eq 2 ]; then
	# Check for leap year
	if [ $((previous_year % 4)) -eq 0 ] && { [ $((previous_year % 100)) -ne 0 ] || [ $((previous_year % 400)) -eq 0 ]; }; then
		last_day=29
	else
		last_day=28
	fi
else
	last_day=31
fi

# Construct the date string
DATE_STR="$previous_year-$previous_month"

# move to execution directory
cd $HOME/src/orangit/orangit-billing/billable-invoicing

# Construct and run the Python command
uv run python -m billable_invoicing util \
    --customer-data $HOME/laskutus/$DATE_STR/customer.csv \
    --raw-hours $HOME/laskutus/$DATE_STR/raw_hours.csv \
    --output $HOME/laskutus/$DATE_STR/utilization-$DATE_STR.txt \
    --start-date $DATE_STR-01 \
    --end-date $DATE_STR-$last_day 