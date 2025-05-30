# Fixed Fee Invoicing

This tool helps process fixed fee invoices from AgileDay into Workday-compatible invoice format.

## Prerequisites

Script works in MacOS, Linux, Windows with linux subsystem (WSL2)

Before you begin, ensure you have:

1. Git installed on your machine

   ```bash
   # Check if Git is installed
   git --version
   
   # If not installed on macOS, install via Homebrew
   brew install git
   
   # If not installed on Ubuntu/Debian
   sudo apt-get install git
   ```

2. UV package manager installed

   ```bash
   # Install UV using curl
   curl -LsSf https://astral.sh/uv/install.sh | sh
   
   # Verify installation
   uv --version
   ```

3. Create directory for the code. The wrapper scripts expect specific directory structure

   Open terminal (Commandline)

   ```bash
   # Navigate to home
   cd
   
   # Navigate to the repository directory
   mkdir -p src/orangit/orangit-billing/
   ```

4. Repository cloned to your local machine

   ```bash
   # Navigate to the repository directory
   cd src/orangit/orangit-billing/

   # Clone the repository
   git clone https://github.com/orangit/fixed_fee_invoicing.git .
   
   # Navigate to the repository directory
   cd fixed_fee_invoicing
   ```

## Common User Workflow

Most users will use `fixed_fee_invoicing.sh` to process fixed fee invoices. Here's the step-by-step process:

### 1. Get AgileDay API Token

This may have been done, depending in which order you execute scripts.

Before starting the invoicing process, you need an AgileDay API token:

1. Contact AgileDay administrators for OrangIT
2. Retrive a new API token from AgileDay, Settings => Integrations => API Tokens. Expiration can be the default 12 hrs.
3. Once received, store the token securely in 1Password:
   - Vault: `orangit-billing`
   - Item: `agileday-api-token`
4. Retrieve token from 1Password:
   - Open 1Password
   - Navigate to vault `orangit-billing`
   - Find item `agileday-api-token`
   - Copy the token value

5. Store token as environment variable:

   ```bash
   # Set AGILEDAY_TOKEN environment variable
   export AGILEDAY_TOKEN='your-token-here'
   
   # Verify the token is set
   echo $AGILEDAY_TOKEN
   ```

### 2. Update Code

This may have been done, depending in which order you execute scripts.

Open terminal and update the code to the latest version:

```bash
# Navigate to the repository directory
cd $HOME/src/orangit/orangit-billing

# Pull latest changes
git pull
```

### 3. Directory Setup

This may have been done, depending in which order you execute scripts.

Create a directory structure for invoicing data:

```bash
# Create directory for the previous month (replace YYYY-MM with actual year-month)
mkdir -p $HOME/laskutus/YYYY-MM

# Example for April 2025:
mkdir -p $HOME/laskutus/2025-04
```

### 4. Get Required Data Files

You need two CSV files from the Client Master Data Google Sheet:

#### Customer Data File

This may have been done, depending in which order you execute scripts.

1. Open the Client Master Data sheet
2. Go to sheet "Taulukko1"
3. Download as CSV:
   - File menu → Download → Comma-separated values (.csv)
4. Rename the downloaded file to `customer.csv`


#### Passthrough Data File

1. Open the Nykyinen-laskutus Google Sheet
2. Go to sheet "Passthrough"
3. Download as CSV:
   - File menu → Download → Comma-separated values (.csv)
4. Rename the downloaded file to `passthrough.csv`

This file contains pass-through billables such as AWS subscriptions and other third-party services that need to be invoiced to clients.

### 5. Place Files in Directory

Copy both files to your month-specific directory:

```bash
# Replace YYYY-MM with actual year-month
cp customer.csv $HOME/laskutus/YYYY-MM/
cp passthrough.csv $HOME/laskutus/YYYY-MM/

# Example for April 2025:
cp customer.csv $HOME/laskutus/2025-04/
cp passthrough.csv $HOME/laskutus/2025-04/
```

### 6. Run the Script

Execute the fixed fee invoicing script:

```bash
sh ./fixed_fee_invoicing.sh
```

### 5. Check Results

After running the script, check these files in your month directory:

- `errors.csv` - Review any failed entries
- `workday-YYYY-MM.csv` - The final output file
- `missing_from_fixed_fee_rates.txt` - Any missing fixed fee information
- Other CSV files for debugging if needed

## Directory Structure Example

```
$HOME/laskutus/
└── 2025-04/
    ├── customer.csv              # From "Taulukko1" sheet
    ├── fixed_fee_rates.csv      # From "fixed_fee_rates" sheet
    ├── passthrough.csv          # From "Passthrough" sheet
    ├── workday-2025-04.csv      # Generated output
    ├── errors.csv               # Any processing errors
    ├── missing_from_fixed_fee_rates.txt   # Missing fixed fee information
    ├── raw_fixed_fees.csv       # Raw data (for debugging)
    ├── filtered_fixed_fees.csv  # Filtered data
    └── complete_fixed_fees_summary.csv # Summary information
```

## Troubleshooting

1. If `errors.csv` contains entries:
   - Check the error messages for each failed entry
   - Verify the customer data and fixed fee rates in the source sheets
   - Make sure all required projects are properly configured

2. If `missing_from_fixed_fee_rates.txt` exists:
   - Review missing fixed fee information
   - Update the fixed_fee_rates sheet with missing entries
   - Re-download and try again

## Advanced Usage

For processing the current month's data (not common), use `current_fixed_fee_invoicing.sh` instead. The workflow is the same, just use the current month's directory.

## Support

For issues with:

- Missing projects or fixed fee rates: Update the Client Master Data sheet
- Script errors: Contact the development team
- Data discrepancies: Verify the source data in AgileDay

## Notes

- Always use fresh downloads of the CSV files for each run
- The script processes the previous month's data automatically
- Keep the directory structure organized by year-month
- Backup important output files before rerunning the script

## Developer Guide

### Package Management with UV

This project uses UV instead of pip for better dependency management and reproducible builds. Never use pip directly in this project.

#### UV Commands

```bash
# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format .
```

### Data Structures

#### customer.csv Fields

Fields from Taulukko1 sheet:

- `Client` - Client company name
- `Service name` - Service category name
- `AgileDay_projectId` - Project ID from AgileDay
- `Active` - Whether the project is active (yes/no)
- `Invoice Info A2 Ext Id` - External ID for invoicing
- `Account A2 Ext Id` - Account ID for invoicing
- `Our Reference` - Reference number for invoicing
- `Customer Reference` - Customer's reference number
- `Contract Number` - Contract identifier
- `Sales Item fixed_fee` - Sales item code for fixed fees
- `Billable Description` - Description template for invoice
- `Tax_Applicability` - Tax application type

#### passthrough.csv Fields

Fields from Passthrough sheet:

- `Client` - Client company name
- `Service` - Name of the service (e.g., AWS, Azure)
- `Description` - Description of the service
- `Amount` - Cost amount to be passed through
- `Currency` - Currency of the amount
- `BillingPeriod` - Period for which the charge applies
- `ProjectId` - AgileDay project ID
- `Status` - Status of the passthrough entry
- `InvoiceInfo` - Additional invoice information
- `TaxCode` - Tax code to apply

### Data Flow

1. **Customer Data Processing**
   - Match entries with customer.csv by AgileDay_projectId
   - Apply billing period filters
   - Determine passthrough amounts

2. **Passthrough Processing**
   - Look up passthrough entries in passthrough.csv
   - Apply billing frequency rules
   - Generate invoice entries

## Customer Master Data Format

The `customer.csv` file contains client and project configuration data from the Client Master Data Google Sheet. This file is downloaded from the "Taulukko1" sheet.

### Fields We Use

These are the fields that our invoicing process actively uses:

- `Client` - Client company name
- `Service name` - Service category name
- `AgileDay_projectId` - Project ID from AgileDay
- `Active` - Whether the project is active (yes/no)
- `included_hours` - Type of hours to include:
  - "All" - Include all billable hours
  - "Orangit" - Only include Orangit Oy employee hours
- `Invoice Info A2 Ext Id` - External ID for invoicing
- `Account A2 Ext Id` - Account ID for invoicing
- `hour_rates` - Rate type to use:
  - "internal" - Use rates from rates.csv
  - "agileday" - Use rates from AgileDay
- `Our Reference` - Reference number for invoicing
- `Customer Reference` - Customer's reference number
- `Contract Number` - Contract identifier
- `Sales Item hours` - Sales item code
- `Billable Description` - Description template for invoice
- `Tax_Applicability` - Tax application type
- `Tax_Code` - Tax code to apply

### All Available Fields

The complete list of fields in the customer.csv file:

- `Client` - Client company name
- `Service name` - Service category name
- `AgileDay_projectId` - Project ID from AgileDay
- `Active` - Whether the project is active (yes/no)
- `included_hours` - Type of hours to include
- `Invoice Info A2 Ext Id` - External ID for invoicing
- `Account A2 Ext Id` - Account ID for invoicing
- `hour_rates` - Rate type to use
- `Our Reference` - Reference number for invoicing
- `Customer Reference` - Customer's reference number
- `Contract Number` - Contract identifier
- `Sales Item hours` - Sales item code
- `Billable Description` - Description template for invoice
- `Tax_Applicability` - Tax application type
- `Tax_Code` - Tax code to apply
- `Project Manager` - Name of the project manager
- `Start Date` - Project start date
- `End Date` - Project end date
- `Billing Period` - Billing frequency (monthly/quarterly)
- `Currency` - Currency for invoicing
- `Payment Terms` - Payment terms in days
- `Notes` - Additional project notes
- `Last Updated` - When the record was last updated
- `Updated By` - Who last updated the record

### Example Data

```csv
Client,Service name,AgileDay_projectId,Active,included_hours,Invoice Info A2 Ext Id,Account A2 Ext Id,hour_rates,Our Reference,Customer Reference,Contract Number,Sales Item hours,Billable Description,Tax_Applicability,Tax_Code,Project Manager,Start Date,End Date,Billing Period,Currency,Payment Terms,Notes,Last Updated,Updated By
Client A,Development,12345,yes,All,INV-A-001,ACC-A-001,internal,REF-001,CUST-REF-001,CNT-001,SI-001,Development services for Client A,Standard,24%,John Manager,2024-01-01,2024-12-31,monthly,EUR,14,Main development project,2024-04-01,Admin User
Client B,Maintenance,12346,yes,Orangit,INV-B-001,ACC-B-001,agileday,REF-002,CUST-REF-002,CNT-002,SI-002,Maintenance and support services,Standard,24%,Jane Manager,2024-01-01,,monthly,EUR,30,24/7 support contract,2024-04-01,Admin User
Client C,Consulting,12347,no,All,INV-C-001,ACC-C-001,internal,REF-003,CUST-REF-003,CNT-003,SI-003,Consulting services,Standard,24%,Mike Manager,2024-01-01,2024-06-30,quarterly,EUR,14,Project completed,2024-04-01,Admin User
```

## Passthrough Data Format

The `passthrough.csv` file contains pass-through billables from the Nykyinen-laskutus Google Sheet. This file is downloaded from the "Passthrough" sheet. The column headers are located in row 5 of the sheet.

### Data Structure

The file contains three sets of amount columns for each entry:

1. Original amount in service's currency
2. Currency conversion to EUR
3. Final amount with service fee in EUR

### Fields Description

- `Client` - Client company name
- `Service` - Name of the service (e.g., AWS, Azure)
- `Description` - Description of the service
- `Amount` - Original amount in service's currency or each billable row
- `Currency` - Original currency of the amount
- `Amount in EUR` - Amount converted to EUR for each billable row
- `Amount with Service Fee` - Final amount in EUR including service fee or each billable row
- `BillingPeriod` - Period for which the charge applies
- `ProjectId` - AgileDay project ID
- `InvoiceInfo` - Information that is used for description

### Example Data

Toteutuneet kustannukset,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,51,52,53,54,55,56,57,58,59,60,61,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,0,1,2,3,4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,22,23,24,25,
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,Laskutettavat ,,,,,,,,,,,,,,,,,,,,,,,,,
,23,,23,,51,,55,,45,,38,,38,,5,,5,,5,,5,,,Eurohinta,,,,,,,,,,,23,23,52,55,45,38,38,5,5,5,5,5,,,,,,,,,,,,,,
,Books,,Books,,AcmeDigi,,Acme Pilvipalveluihin,,Acme webservice,,On the rocks AWS,,On the rocks github,,Acme finance,,Acme finance,,Acme finance,,Acme finance,,,Books,Books,AcmeDigi,Acme Pilvipalveluihin,Acme webservice,On the rocks AWS,On the rocks github,Acme finance,Acme finance,Acme finance,Acme finance,Books,Books,AcmeDigi,Acme Pilvipalveluihin,Acme webservice,On the rocks AWS,On the rocks github,Acme finance,Acme finance,Acme finance,Acme finance,x,Kpl,,Books,Books,AcmeDigi,Acme Pilvipalveluihin,Acme webservice,On the rocks AWS,On the rocks github,Acme finance,Acme finance,Acme finance,Acme finance,Acme finance
,Sparkpost,Currency,Google Cloud Platform,Cur,Netlify,cur,Auth0,Cur,ajoympäristöt,cur,,Cur,,Cur,Google Cloud Platform prod,Cur,Google Cloud Platform testing,Cur,Google Cloud Platform staging,Cur,Google Cloud Platform terraform,Cur,Kurssi,Sparkpost,Google Cloud Platform,Netlify,Auth0,ajoympäristöt,,,Google Cloud Platform prod,Google Cloud Platform testing,Google Cloud Platform staging,Google Cloud Platform terraform,Sparkpost,Google Cloud Platform,Netlify,Auth0,ajoympäristöt,,,Google Cloud Platform prod,Google Cloud Platform testing,Google Cloud Platform staging,Google Cloud Platform terraform,,,Acme finance terraform,Sparkpost,Google Cloud Platform,Netlify,Auth0,ajoympäristöt,,,Google Cloud Platform prod,Google Cloud Platform testing,Google Cloud Platform staging,Google Cloud Platform terraform,
01/2025,"20,00 €",$,"230,26 €",€,"76,00 €",$,"69,00 €",$,"173,75 €",$,"1075,81",$,48,$,"328,9",€,"121,94",€,"102,84",€,"46,03",€,"0,969743988","19,39 €","230,26 €","73,70 €","66,91 €","168,49 €","1043,26028","46,54771142","328,9","121,94","102,84","46,03","22,30 €","264,80 €","84,76 €","76,95 €","109,52 €","1199,749322","53,52986814","378,235","140,231","118,266","52,9345",0,"2 501,27 €",11,Books Sparkpost 2025-01 (15% laskutuslisä) ,Books Google cloud 2025-01 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-01 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-01 (15% laskutuslisä),Acme webservice AWS 2025-01 (15% laskutuslisä),On the rocks AWS 2025-01 (15% laskutuslisä),On the rocks GitHUb 1900-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform production 2025-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-01 (15% laskutuslisä),
02/2025,"20,00 €",$,"212,27 €",€,"95,00 €",$,"69,00 €",$,"159,49 €",€,"979,73",$,48,€,"303,06",€,"107,36",€,"83,34",€,"41,51",€,"0,95396","19,08 €","212,27 €","212,27 €","90,63 €","159,49 €","934,6232308",48,"303,06","107,36","83,34","41,51","21,94 €","244,11 €","244,11 €","104,22 €","103,67 €","1074,816715","55,2","348,519","123,464","95,841","47,7365",0,"2 463,63 €",11,Books Sparkpost 2025-02 (15% laskutuslisä) ,Books Google cloud 2025-02 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-02 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-02 (15% laskutuslisä),Acme webservice AWS 2025-02 (15% laskutuslisä),On the rocks AWS 2025-02 (15% laskutuslisä),On the rocks GitHUb 1900-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-02 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-02 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-02 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-02 (15% laskutuslisä),
03/2025,"20,00 €",$,"232,90 €",€,"95,00 €",$,"69,00 €",$,"174,76 €",€,"1036,56",$,48,€,"334,78",€,"126,16",€,"93,44",€,"45,62",€,"0,911203244","18,22 €","232,90 €","86,56 €","69,00 €","174,76 €","944,5168346",48,"334,78","126,16","93,44","45,62","20,96 €","267,84 €","99,55 €","79,35 €","113,59 €","1086,19436","55,2","384,997","145,084","107,456","52,463",0,"2 412,68 €",11,Books Sparkpost 2025-03 (15% laskutuslisä) ,Books Google cloud 2025-03 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-03 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-03 (15% laskutuslisä),Acme webservice AWS 2025-03 (15% laskutuslisä),On the rocks AWS 2025-03 (15% laskutuslisä),On the rocks GitHUb 1900-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-03 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-03 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-03 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-03 (15% laskutuslisä),
04/2025,"20,00 €",$,"232,90 €",€,"76,00 €",$,"69,00 €",$,"168,61 €",€,"970,96",$,48,€,"312,16",€,"119,02",€,"91,23",€,"43,07",€,"0,883950552","17,68 €","232,90 €","67,18 €","69,00 €","168,61 €","858,280628",48,"312,16","119,02","91,23","43,07","20,33 €","267,84 €","77,26 €","79,35 €","109,60 €","987,0227222","55,2","358,984","136,873","104,9145","49,5305",0,"2 246,89 €",11,Books Sparkpost 2025-04 (15% laskutuslisä) ,Books Google cloud 2025-04 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-04 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-04 (15% laskutuslisä),Acme webservice AWS 2025-04 (15% laskutuslisä),On the rocks AWS 2025-04 (15% laskutuslisä),On the rocks GitHUb 1900-01 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-04 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-04 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-04 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-04 (15% laskutuslisä),
05/2025,"0,00 €",$,"0,00 €",€,"0,00 €",$,"0,00 €",$,"0,00 €",€,0,$,0,€,0,€,0,€,0,€,0,€,"0,881805","0,00 €","0,00 €","0,00 €","0,00 €","0,00 €",0,0,0,0,0,0,"0,00 €","0,00 €","0,00 €","0,00 €","0,00 €",0,0,0,0,0,0,0,"0,00 €",11,Books Sparkpost 2025-05 (15% laskutuslisä) ,Books Google cloud 2025-05 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-05 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-05 (15% laskutuslisä),Acme webservice AWS 2025-05 (15% laskutuslisä),On the rocks AWS 2025-05 (15% laskutuslisä),On the rocks GitHUb 1899-12 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-05 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-05 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-05 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-05 (15% laskutuslisä),
06/2025,"0,00 €",$,"0,00 €",€,"0,00 €",$,"0,00 €",$,"0,00 €",€,0,$,0,€,0,€,0,€,0,€,0,€,"0,881805","0,00 €","0,00 €","0,00 €","0,00 €","0,00 €",0,0,0,0,0,0,"0,00 €","0,00 €","0,00 €","0,00 €","0,00 €",0,0,0,0,0,0,"0,00 €","0,00 €",11,Books Sparkpost 2025-06 (15% laskutuslisä) ,Books Google cloud 2025-06 (15% laskutuslisä),Suomen Biopankkien Osuuskunta /Digi Netlify 2025-06 (15% laskutuslisä) ,Suomen Biopankkien Osuuskunta / Acme Pilvipalveluihin Auth0 2025-06 (15% laskutuslisä),Acme webservice AWS 2025-06 (15% laskutuslisä),On the rocks AWS 2025-06 (15% laskutuslisä),On the rocks GitHUb 1899-12 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-06 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform staging 2025-06 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform testing 2025-06 (15% laskutuslisä),Acme finance-palvelu Google Cloud Platform terraform 2025-06 (15% laskutuslisä),

# Workday Output Format

The `workday-YYYY-MM.csv` file is the final output file that contains the processed billables in Workday-compatible format. The file has a specific structure with header information and invoice entries.

## File Structure

1. First two lines contain invoice transfer information, the sum of all invoices are in the second line:

   ```
   Invoice transfer into Workday;;;Company code:;263;;;Invoicing total;;;;;;;;;;;;;
   Title information/Row information;;;Reply-to-email:;laskutus@barona.fi;;;260597.30;;;;;;;;;;;;;
   ```

2. Column definitions (line 3):

   ```
   Row type H= Title;ConnectID;Invoice A2 ID;Account A2 ID;Free text;Accounting date[YYYY-MM-DD];Invoicing date[YYYY-MM-DD];Our reference;Customer reference;Period Start date [YYYY-MM-DD];Period End date [YYYY-MM-DD];Contract number;PO number;Appendix 1;Appendix 2;Appendix 3;Appendix 4;;;Source System;
   ```

3. Row column definitions (line 4):

   ```
   Row type R= Row;ConnectID;Grouping info (Memo);Sales Item;Description;Quantity;Unit of measure;Unit price;Dim 1: Cost center;Dim 2: Business line (Function);Dim 3: Area;Dim 4: Service;Dim 5: Project;Dim 7: Counter company;Dim 8: Work type;Dim 10: Official;Dim 11: Employee;Dim 13: Company;Tax_Applicability;Tax_Code;
   ```

4. Invoice entries consist of:
   - One H (Header) line containing invoice-level information
   - One or more R (Row) lines containing the actual billable items

## Example Entry

```
H;dc3d77b3-9ac3-4d2d-8f42-fcf3dcad9422;69188617-235c-4663-b00a-28b1dfe66f6f;22c7154e-7b1a-4737-bd76-1de545e0d7f4;;2025-05-01;2025-05-07;;Jane Doe;2025-04-01;2025-04-30;;;;;;;;;Orangit;
R;dc3d77b3-9ac3-4d2d-8f42-fcf3dcad9422;Acme corp;MAINTENANCE AND DEVELOPMENT WORK;Acme Corp - maintenance and development work - Billable;90.50;;145.00;1999;IT;10091;KON;;;;;;;FIN_Export_of_Services;FIN_Zero_Rated;
```

## Important Notes

1. Each invoice starts with an H line containing:
   - Unique identifiers (ConnectID, Invoice A2 ID, Account A2 ID)
   - Accounting and invoicing dates
   - Customer reference
   - Billing period dates
   - Source system (Orangit)

2. R lines contain the actual billable items with:
   - ConnectID linking to the H line
   - Service description
   - Quantity and unit price
   - Cost center and business line information
   - Tax applicability and tax code

3. The second line contains the total invoicing amount for the period

4. All monetary values are in EUR

5. Dates are in YYYY-MM-DD format

6. Each invoice can have multiple billable items (R lines) associated with it

7. Tax codes indicate whether the service is:
   - Domestic (FIN_Standard_25_5)
   - Export (FIN_Zero_Rated)
   - EU sale (FIN_EU_Sale_of_Services)

This format is designed to be compatible with Workday's invoice import system, with each invoice properly structured with its header and line items.
