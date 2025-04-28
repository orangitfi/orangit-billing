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

# Construct the dates
DATE_STR="$previous_year-$previous_month"
START_DATE="$previous_year-$previous_month-01"
END_DATE="$previous_year-$previous_month-$last_day"

# move to execution directory
cd $HOME/src/orangit/tools/src/fixed_fee_invoicing/fixed-fee-invoicing
# Construct and run the Python command
uv run python -m billable_invoicing fetch-hours \
     --company "OrangIT Oy" \
    --start-date "$START_DATE" \
    --end-date "$END_DATE" \
    --output-path $HOME/laskutus/$DATE_STR/ \
	--customer-data "$HOME/laskutus/$DATE_STR/customer.csv" \
	--rates-file "$HOME/laskutus/$DATE_STR/rates.csv" \
	--result-file "$HOME/laskutus/$DATE_STR/workday-$DATE_STR.csv" 											