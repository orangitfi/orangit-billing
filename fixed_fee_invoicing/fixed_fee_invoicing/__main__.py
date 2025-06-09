import argparse
import csv
import datetime
import re
import sys
import uuid
from collections import defaultdict

# Column index constants
PROCOUNTOR_FILE_CUSTOMER_ID_COLUMN: int = 4
CONFIG_BUSINESS_ID: int = 0
CONFIG_CLIENT: int = 1
CONFIG_SERVICE_NAME: int = 2
CONFIG_START_DATE: int = 3
CONFIG_END_DATE: int = 4
CONFIG_ACTIVE: int = 5
CONFIG_SERVICE_LEAD: int = 6
CONFIG_DEVELOPMENT_TEAM: int = 7
CONFIG_HARVEST_ID: int = 8
CONFIG_MONTHLY_FIXED_FEE: int = 9
CONFIG_INVOICING_CONTACT_PERSON: int = 10
CONFIG_CONTACT_EMAIL: int = 11
CONFIG_CONTACT_PHONE: int = 12
CONFIG_INVOICE_METHOD: int = 13
CONFIG_PAYMENT_TERM_DAYS: int = 14
CONFIG_PAYMENT_PERIOD_MONTHS: int = 15
CONFIG_GROUP_INVOICE: int = 16
CONFIG_INVOICE_LANGUAGE: int = 17
CONFIG_HOURLY_WORK_DIMENSION: int = 18
CONFIG_FIXED_FEE_DIMENSION: int = 19
CONFIG_VAT: int = 20
CONFIG_FIXED_FEE_DESCRIPTION: int = 21
CONFIG_BILLABLE_DESCRIPTION: int = 22
CONFIG_ACCOUNT_A2_EXT_ID: int = 23
CONFIG_INVOICE_INFO_A2_EXT_ID: int = 24
CONFIG_SALES_ITEM_HOURS: int = 25
CONFIG_SALES_ITEM_FIXED: int = 26
CONFIG_TAX_APPLICABILITY: int = 27
CONFIG_TAX_CODE: int = 28
CONFIG_TAX_CODE_FIXED: int = 29
CONFIG_FIXED_BILLED_ADVANCE: int = 30
CONFIG_FIXED_BILLING_MONTH: int = 31
CONFIG_CONTRACT_NUMBER: int = 32
CONFIG_ID: int = 33
CONFIG_CUSTOMER_REFERENCE = 34
CONFIG_OUR_REFERENCE = 35
CONFIG_PERIOD = 40  # New column for period (pre/post)


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Generate invoice transfer into Workday based on config and input files."
    )

    parser.add_argument("--input", required=True, help="Path to the input file.")
    parser.add_argument(
        "--config", required=True, help="Path to the configuration file."
    )
    parser.add_argument(
        "--output", required=True, help="Path to the output file (result)."
    )
    parser.add_argument(
        "--month", type=int, help="Month of invoicing (1-12). Optional."
    )
    parser.add_argument(
        "--year", type=int, help="Year of invoicing (e.g. 2025). Optional."
    )

    args = parser.parse_args()
    return args


def get_current_year_month():
    """Return current year and month as integers."""
    now = datetime.date.today()
    return now.year, now.month


def previous_month(year, month):
    """
    Given a year and month, return the (year, month) for the *previous* month.
    For example, if (year=2025, month=1) => returns (2024, 12).
    """
    if month == 1:
        return (year - 1, 12)
    else:
        return (year, month - 1)


def read_config(config_path):
    """
    Read the config file (CP-1252).
    The config file has columns mapped to the constants above.
    Returns a list (or dict) with one entry per config row.
    """
    config_data = []
    with open(config_path, mode="r", encoding="utf-8", errors="replace") as cf:
        reader = csv.reader(cf, delimiter=",")  # or your actual delimiter
        for row in reader:
            value = re.sub(r"[^0-9.-]", "", row[CONFIG_MONTHLY_FIXED_FEE])
            if value == "":
                value = "0.0"
            unit_price = float(value)
            temp = row[CONFIG_SERVICE_NAME]
            if unit_price > 0.0 and row[CONFIG_ACTIVE] == "Yes":
                conf_record = {
                    "business_id": row[CONFIG_BUSINESS_ID],
                    "client": row[CONFIG_CLIENT],
                    "service_name": row[CONFIG_SERVICE_NAME],
                    "start_date": row[CONFIG_START_DATE],
                    "end_date": row[CONFIG_END_DATE],
                    "active": row[CONFIG_ACTIVE],
                    "group_invoice": row[CONFIG_GROUP_INVOICE],
                    "harvest_id": row[CONFIG_HARVEST_ID],
                    "monthly_fixed_fee": row[CONFIG_MONTHLY_FIXED_FEE],
                    "invoice_contact_person": row[CONFIG_INVOICING_CONTACT_PERSON],
                    "contact_email": row[CONFIG_CONTACT_EMAIL],
                    "tax_applicability": row[CONFIG_TAX_APPLICABILITY],
                    "tax_code": row[CONFIG_TAX_CODE_FIXED],
                    "fixed_fee_description": row[CONFIG_FIXED_FEE_DESCRIPTION],
                    "billable_description": row[CONFIG_BILLABLE_DESCRIPTION],
                    "sales_item_fixed": row[CONFIG_SALES_ITEM_FIXED],
                    "contract_number": row[CONFIG_CONTRACT_NUMBER],
                    "invoice_info_a2_ext_id": row[CONFIG_INVOICE_INFO_A2_EXT_ID],
                    "account_a2_ext_id": row[CONFIG_ACCOUNT_A2_EXT_ID],
                    "config_id": row[CONFIG_ID],
                    "contract_number": row[CONFIG_CONTRACT_NUMBER],
                    "customer_reference": row[CONFIG_CUSTOMER_REFERENCE],
                    "our_reference": row[CONFIG_OUR_REFERENCE],
                    "period": row[CONFIG_PERIOD] if len(row) > CONFIG_PERIOD else "post",  # Default to "post" if column doesn't exist
                }
                config_data.append(conf_record)
    print(f"Read {len(config_data)} active config rows.")
    return config_data


def read_input_file(input_path):
    """
    Read the pass-through billing input file in CP-1252 encoding.
    The input file has:
      - line 4 (index 3) from column 36 to 47 => the ID that ties the column to config
      - lines 7 to 200 => actual data
      - the first column in each data row => year.month (like "1.1.2025")

    Because this file has a custom, somewhat 'spreadsheet-like' layout,
    you will likely need to parse it carefully, e.g. using `csv` or direct reads.

    For demonstration, let's assume lines are also semicolon-separated,
    and we store them in some structure.
    """
    # Because the user specifically mentions "line 4 from column 36 to 47"
    # it implies data might be in columns. Possibly you need to open as a text file
    # and do fixed-width parsing for columns? This example is a placeholder.

    lines = []
    with open(input_path, mode="r", encoding="utf-8", errors="replace") as f:
        # Could do row-based or fixed-width. Let's assume row-based CSV for now.
        reader = csv.reader(f, delimiter=",")
        for idx, row in enumerate(reader):
            lines.append(row)

    return lines


def find_pass_through_for_month(input_lines, prev_year, prev_month):
    """
    Given the parsed input data, find the row that corresponds to the previous
    year-month (e.g. "1.1.2025"), and then read the columns 36..47 as needed.

    Return a dictionary or list of pass-through amounts keyed by some ID
    that matches up with the config's ID column (for example, 'harvest_id').
    """
    # The date in the first column might be "1.2.2025" to represent February 2025, etc.
    # We want the row that has e.g. 1.<prev_month>.<prev_year>.
    desired_string = f"{prev_month:02d}/{prev_year}"
    # print(f"desired_string: {desired_string}")
    pass_through_data = []

    for row in input_lines:
        if not row:
            continue
        # Example: row[0] might be "1.2.2025"
        if row[0].strip() == desired_string:
            print("Found the row for the previous month.")
            # This is the row we want. Now read columns [36..47]. Because it's not standard CSV,
            # you might actually need to do 'row[35]', 'row[36]', etc. Or read it from a fixed
            # width line.
            #
            # The user indicated that line 4 from column 36..47 has an ID that ties
            # the column to the config. Then lines from row[7..200] have the actual data.
            #
            # Because the format is somewhat unclear, we demonstrate the concept:
            for index in range(12):
                col_index: int = index + 35
                conf_record = {
                    "confid": input_lines[3][col_index],
                    "amount": row[col_index],
                    "description": row[col_index + 14],
                }
                # conf_line = ";".join(conf_record)
                pass_through_data.append(conf_record)
                # Suppose row 3 (line 4 in the file) had the ID,
                # row 7+ are the actual amounts in the same column. We might need them all.

                # This is just a placeholder; adapt to your structure:
                # Example key might be the ID from line 4, and the value might be
                # the numeric amount from line X.
                # pass_through_data[ <ID from line4> ] = <value from line7 or so>

                # The logic of "matching the column's ID from line 4" might need
                # the raw lines array. Possibly you'd do something like:
    return pass_through_data


def generate_output(
    config_data,
    pass_through_data,
    output_path,
    invoice_year,
    invoice_month,
    execution_date,
):
    """
    Build the result file.

    1) Write the static starting lines (header with total sum placeholder).
    2) For each group_invoice in config_data, create:
       - A single 'Header' (H) line
       - Potentially multiple 'Row' (R) lines: one for the fixed fee from config,
         plus any pass-through lines from pass_through_data if applicable.
    3) Sum up all row amounts for the second line's big total (65656.95).
    """

    # We'll collect all lines in a list; then we'll compute the sum, fill it in,
    # and finally write them all out.
    output_lines = []

    # We'll gather row amounts here to compute the total for the second line.
    total_amount = 0.0
    invoice_count = 0
    invoice_line_count = 0

    # 1) The top lines (static text). We'll fill in the total later, so let's put a
    # placeholder for now. E.g. "##TOTAL##"
    line1 = "Invoice transfer into Workday;;;Company code:;263;;;Invoicing total;;;;;;;;;;;;;"
    # The second line has "Title information/Row information;;;Reply-to-email:;laskutus@barona.fi;;;65656.95;;;;;;;;;;;;;"
    # We'll replace "65656.95" with something after we sum up everything.
    line2_template = (
        "Title information/Row information;;;Reply-to-email:;laskutus@barona.fi;;;"
        "##TOTAL##;;;;;;;;;;;;;"
    )

    # The next two lines describing columns:
    line3 = (
        "Row type H= Title;ConnectID;Invoice A2 ID;Account A2 ID;Free text;"
        "Accounting date[YYYY-MM-DD];Invoicing date[YYYY-MM-DD];Our reference;"
        "Customer reference;Period Start date [YYYY-MM-DD];Period End date [YYYY-MM-DD];"
        "Contract number;PO number;Appendix 1;Appendix 2;Appendix 3;Appendix 4;;;Source System;"
    )
    line4 = (
        "Row type R= Row;ConnectID;Grouping info (Memo);Sales Item;Description;Quantity;"
        "Unit of measure;Unit price;Dim 1: Cost center;Dim 2: Business line (Function);"
        "Dim 3: Area;Dim 4: Service;Dim 5: Project;Dim 7: Counter company;Dim 8: Work type;"
        "Dim 10: Official;Dim 11: Employee;Dim 13: Company;Tax_Applicability;Tax_Code;"
    )

    output_lines.append(line1)
    output_lines.append(line2_template)
    output_lines.append(line3)
    output_lines.append(line4)
    print("Static lines are written ...")
    # 2) Build the invoice lines for each group_invoice. We group config_data by column 17.
    # Let's build a dictionary: group_id -> list of config rows

    grouped_config = defaultdict(list)
    for conf in config_data:
        # print(f"conf: {conf}")
        if conf["active"].lower() == "yes":  # or whatever logic for "Active"
            grouped_config[conf["group_invoice"]].append(conf)

    # We know the "Accounting date" is the 2nd day of the *next* month of invoice_month/year.
    # If we are invoicing for 2-2025, the accounting date is 2.3.2025.
    # So let's figure that out:
    # Next month from (invoice_year, invoice_month)
    if invoice_month == 12:
        next_year = invoice_year + 1
        next_month = 1
    else:
        next_year = invoice_year
        next_month = invoice_month + 1
    accounting_date = datetime.date(next_year, next_month, 2).strftime("%Y-%m-%d")

    # The "invoicing date" is the date when the script is executed => execution_date
    invoicing_date_str = execution_date.strftime("%Y-%m-%d")

    print("Config lines processing ...")
    # Now generate the lines (Header + Row) for each group
    for group_id, rows in grouped_config.items():
        # Generate a single ConnectID for this entire invoice
        connect_id = str(uuid.uuid4())

        # We also want to combine certain config data for the invoice Header line.
        first_conf_row = rows[0]

        # Get the period value from the first row in the group
        period = first_conf_row.get("period", "post")
        
        if period == "pre":
            # If period is "pre", use next month for period start/end
            if invoice_month == 12:
                next_month_for_end = 1
                next_year_for_end = invoice_year + 1
            else:
                next_month_for_end = invoice_month + 1
                next_year_for_end = invoice_year
            period_start = datetime.date(next_year_for_end, next_month_for_end, 1)
            if next_month_for_end == 12:
                end_month_for_end = 1
                end_year_for_end = next_year_for_end + 1
            else:
                end_month_for_end = next_month_for_end + 1
                end_year_for_end = next_year_for_end
        else:
            # If period is "post", use current month for period start/end
            period_start = datetime.date(invoice_year, invoice_month, 1)
            if invoice_month == 12:
                end_month_for_end = 1
                end_year_for_end = invoice_year + 1
            else:
                end_month_for_end = invoice_month + 1
                end_year_for_end = invoice_year

        period_start_str = period_start.strftime("%Y-%m-%d")
        first_of_next_month = datetime.date(end_year_for_end, end_month_for_end, 1)
        period_end = first_of_next_month - datetime.timedelta(days=1)
        period_end_str = period_end.strftime("%Y-%m-%d")

        # invoice_info_a2_ext_id => column 25 if zero-based
        invoice_a2_id = first_conf_row["invoice_info_a2_ext_id"]
        # account_a2_ext_id => column 24 if zero-based
        account_a2_id = first_conf_row["account_a2_ext_id"]
        customer_reference = first_conf_row[
            "invoice_contact_person"
        ]  # column 11 if that's correct
        our_reference = first_conf_row["our_reference"]  # column 35 if that's correct
        contract_number = first_conf_row["contract_number"]
        customer_reference = first_conf_row["customer_reference"]

        # contract number => column 32 in config => first_conf_row["contract_number"]

        header_fields = [
            "H",  # Row type
            connect_id,  # ConnectID
            invoice_a2_id,  # Invoice A2 ID
            account_a2_id,  # Account A2 ID
            "",  # Free text
            accounting_date,  # Accounting date
            invoicing_date_str,  # Invoicing date (execution date)
            our_reference,  # Our reference
            customer_reference,  # Customer reference
            period_start_str,  # Period Start date
            period_end_str,  # Period End date
            contract_number,  # Contract number
            "",  # PO number
            "",  # Appendix 1
            "",  # Appendix 2
            "",  # Appendix 3
            "",  # Appendix 4
            "",  # (unused column?), if needed
            "",  # (unused column?), if needed
            "Orangit",  # Source System
            "",  # (unused column?), if needed
        ]

        # Build the CSV-like string. We'll separate by semicolon.
        header_line = ";".join(header_fields)
        output_lines.append(header_line)
        invoice_count += 1

        # Now, for each row in the group, we add the "fixed fee" row
        # R;ConnectID;Grouping info (Memo) => col 2 from config?; Sales Item => col 27 from config;
        #    Description => col 22 from config; Quantity=1; Unit price => col 10 from config
        #    Dim 1=1999; Dim2=IT; Dim3=10091; Dim4=KON; ...
        for crow in rows:
            grouping_info = crow[
                "service_name"
            ]  # or whichever column is "Grouping info (Memo)"
            sales_item = crow["sales_item_fixed"]  # col 27 if zero-based
            description = (
                grouping_info + " - " + crow["fixed_fee_description"]
            )  # col 22 if zero-based
            try:
                value = re.sub(r"[^0-9.-]", "", crow["monthly_fixed_fee"])
                unit_price = float(value)
            except (ValueError, TypeError):
                unit_price = 0.0

            # Update the total
            total_amount += unit_price

            row_fields = [
                "R",  # Row type
                connect_id,  # ConnectID
                grouping_info,  # Grouping info (Memo)
                sales_item,  # Sales item
                description,  # Description
                "1",  # Quantity
                "",  # Unit of measure
                f"{unit_price:.2f}",  # Unit price
                "1999",  # Dim 1 (Cost center)
                "IT",  # Dim 2 (Business line)
                "10091",  # Dim 3 (Area)
                "KON",  # Dim 4 (Service)
                "",  # Dim 5 (Project)
                "",  # Dim 7 (Counter company)
                "",  # Dim 8 (Work type)
                "",  # Dim 10 (Official)
                "",  # Dim 11 (Employee)
                "",  # Dim 13 (Company)
                crow[
                    "tax_applicability"
                ],  # Tax_Applicability (col 28 if zero-based => [27])
                crow["tax_code"],  # Tax_Code (col 30 if zero-based => [29])
                "",  # Dim 13 (Company)
            ]
            row_line = ";".join(row_fields)
            output_lines.append(row_line)
            invoice_line_count += 1

            # Now check if we need to add pass-through lines from the input file for this conf row.
            # If the "harvest_id" or some other ID matches something in pass_through_data,
            # we'd add rows similarly:
            # Example:
            harv_id = crow["config_id"]
            # print(f"harv_id: {harv_id}")
            # print(f"pass_through_data: {pass_through_data}")
            for item in pass_through_data:
                if item["confid"] == harv_id:
                    pass_desc = item["description"]
                    pass_amount_str = item["amount"].replace(",", ".")
                    pass_amount_str = pass_amount_str.replace("€", "")
                    pass_amount_str = pass_amount_str.replace(" ", "")
                    pass_amount = float(pass_amount_str)
                    total_amount += pass_amount

                    row_fields_pt = [
                        "R",
                        connect_id,
                        grouping_info,
                        sales_item,
                        pass_desc,
                        "1",
                        "",
                        f"{pass_amount:.2f}",
                        "1999",
                        "IT",
                        "10091",
                        "KON",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        crow["tax_applicability"],
                        crow["tax_code"],
                        "",
                    ]
                    row_line_pt = ";".join(row_fields_pt)
                    output_lines.append(row_line_pt)
                    invoice_line_count += 1
                # Suppose pass_through_data[harv_id] is a list of { 'description': ..., 'amount': ... }
                # for item in pass_through_data[harv_id]:
                #     # Build row line for pass-through
                #     pass_desc = item["description"]  # e.g. from input file col+13
                #     pass_amount = float(item["amount"])
                #     total_amount += pass_amount

                #     row_fields_pt = [
                #         "R",  # Row type
                #         connect_id,  # same ConnectID
                #         grouping_info,  # same grouping
                #         sales_item,  # possibly the same or a different "Sales Item"?
                #         pass_desc,  # from the input file
                #         "1",  # Quantity
                #         "",  # Unit measure
                #         f"{pass_amount:.2f}",
                #         "1999",
                #         "IT",
                #         "10091",
                #         "KON",
                #         "",
                #         "",
                #         "",
                #         "",
                #         "",
                #         "",
                #         crow["tax_applicability"],
                #         crow["tax_code"],
                #     ]
                #     row_line_pt = ";".join(row_fields_pt)
                #     output_lines.append(row_line_pt)

        # End for each row in that group
    # End for each group

    # Now we have the total amount. We need to replace "##TOTAL##" in line2_template.
    line2_filled = line2_template.replace("##TOTAL##", f"{total_amount:.2f}")
    output_lines[1] = line2_filled  # place it back in the second line

    # Finally, write everything to the output file
    with open(
        output_path, mode="w", encoding="cp1252", errors="replace", newline=""
    ) as out:
        for line in output_lines:
            out.write(line + "\n")

    print(f"Total amount of invoices {invoice_count}")
    print(f"Total amount of lines in the invoices  {invoice_line_count}")
    print(f"Total count of units  {invoice_line_count}")
    print(f"Total euros without VAT {total_amount:.2f}")

    # Generate summary file
    summary_path = output_path.rsplit(".", 1)[0] + "_summary.csv"
    with open(summary_path, mode="w", encoding="utf-8", newline="") as summary_file:
        # Write header
        summary_writer = csv.writer(summary_file)
        summary_writer.writerow([
            "Customer Name",
            "Service Name",
            "ConnectID",
            "Invoice A2 ID",
            "Account A2 ID",
            "Grouping info (Memo)",
            "Sales Item",
            "Description",
            "Quantity",
            "Unit price",
            "Amount"
        ])

        # Write data rows - only process rows that start with "R"
        for line in output_lines:
            if line.startswith("R;"):
                fields = line.split(";")
                # Extract the relevant fields from the row
                connect_id = fields[1]
                grouping_info = fields[2]
                sales_item = fields[3]
                description = fields[4]
                quantity = fields[5]
                unit_price = fields[7]

                # Find the corresponding config row to get customer name and service name
                for group_id, rows in grouped_config.items():
                    for crow in rows:
                        if crow["service_name"] == grouping_info:
                            summary_writer.writerow([
                                crow["client"],  # Customer Name
                                crow["service_name"],  # Service Name
                                connect_id,  # ConnectID
                                crow["invoice_info_a2_ext_id"],  # Invoice A2 ID
                                crow["account_a2_ext_id"],  # Account A2 ID
                                grouping_info,  # Grouping info (Memo)
                                sales_item,  # Sales Item
                                description,  # Description
                                quantity,  # Quantity
                                unit_price,  # Unit price
                                unit_price  # Amount (same as unit price since quantity is 1)
                            ])
                            break

    print(f"Summary file written to {summary_path}")


def main():
    args = parse_arguments()
    print("Start processing...")
    # Figure out the year/month for invoicing
    if args.year and args.month:
        invoice_year = args.year
        invoice_month = args.month
    else:
        # Use current year/month if not provided
        invoice_year, invoice_month = get_current_year_month()

    # We also want the "previous month" from that
    prev_year, prev_month = previous_month(invoice_year, invoice_month)

    # Read config
    if not args.config:
        print("Config file has not been provided.")
        sys.exit(1)
    config_data = read_config(args.config)
    print("Config is read ...")
    # Read input file
    if not args.input:
        print("Input file is not provided.")
        sys.exit(1)
    input_lines = read_input_file(args.input)
    print("Input is read ...")
    # Find pass-through data for that previous month
    pass_through_data = find_pass_through_for_month(
        input_lines, invoice_year, invoice_month
    )
    print("Passthrough is read ...")
    # pass_through_data ideally is a dict like:
    # {
    #   "harvest_id_1": [
    #       {"description": "AWS usage", "amount": 123.45},
    #       {"description": "Some other pass-through", "amount": 300.0},
    #    ],
    #   "harvest_id_2": [...],
    #   ...
    # }

    # The script execution date is "today" by default
    execution_date = datetime.date.today()

    # Generate the output
    generate_output(
        config_data=config_data,
        pass_through_data=pass_through_data,
        output_path=args.output,
        invoice_year=invoice_year,
        invoice_month=invoice_month,
        execution_date=execution_date,
    )
    print("processing is done ...")


if __name__ == "__main__":
    main()