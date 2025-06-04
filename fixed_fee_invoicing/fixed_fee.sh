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

# Construct the date string
DATE_STR="$previous_year-$previous_month"
echo "DATE_STR: $DATE_STR"
# move to execution directory
cd $HOME/src/orangit/orangit-billing/fixed_fee_invoicing
# Construct and run the Python command
uv run python -m fixed_fee_invoicing \
	 --config $HOME/laskutus/$DATE_STR/customer.csv \
	 --input $HOME/laskutus/$DATE_STR/passthrough.csv \
	 --output $HOME/laskutus/$DATE_STR/fixed-fee-$DATE_STR.csv \
	 --month $previous_month\
	 --year $previous_year\
