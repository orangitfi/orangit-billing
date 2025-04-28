# Billable Hours Invoicing

This tool helps process billable hours from AgileDay into Workday-compatible invoice format.

## Prerequisites

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

3. Repository cloned to your local machine

   ```bash
   # Clone the repository
   git clone https://github.com/orangit/billable_invoicing.git
   
   # Navigate to the repository directory
   cd billable_invoicing
   ```

## Common User Workflow

Most users will use `hours_invoicing.sh` to process the previous month's billable hours. Here's the step-by-step process:

### 1. Directory Setup

Create a directory structure for invoicing data:

```bash
# Create directory for the previous month (replace YYYY-MM with actual year-month)
mkdir -p $HOME/laskutus/YYYY-MM

# Example for April 2025:
mkdir -p $HOME/laskutus/2025-04
```

### 2. Get Required Data Files

You need two CSV files from the Client Master Data Google Sheet:

#### Customer Data File

1. Open the Client Master Data sheet
2. Go to sheet "Taulukko1"
3. Download as CSV:
   - File menu → Download → Comma-separated values (.csv)
4. Rename the downloaded file to `customer.csv`

#### Rates File

1. Stay in the same Client Master Data sheet
2. Go to sheet "hour_rates"
3. Download as CSV:
   - File menu → Download → Comma-separated values (.csv)
4. Rename the downloaded file to `rates.csv`

### 3. Place Files in Directory

Copy both files to your month-specific directory:

```bash
# Replace YYYY-MM with actual year-month
cp customer.csv $HOME/laskutus/YYYY-MM/
cp rates.csv $HOME/laskutus/YYYY-MM/

# Example for April 2025:
cp customer.csv $HOME/laskutus/2025-04/
cp rates.csv $HOME/laskutus/2025-04/
```

### 4. Run the Script

Execute the hours invoicing script:

```bash
sh ./hours_invoicing.sh
```

### 5. Check Results

After running the script, check these files in your month directory:

- `errors.csv` - Review any failed entries
- `workday-YYYY-MM.csv` - The final output file
- `missing_from_rates.txt` - Any missing rate information
- Other CSV files for debugging if needed

## Directory Structure Example

```
$HOME/laskutus/
└── 2025-04/
    ├── customer.csv              # From "Taulukko1" sheet
    ├── rates.csv                # From "hour_rates" sheet
    ├── workday-2025-04.csv      # Generated output
    ├── errors.csv               # Any processing errors
    ├── missing_from_rates.txt   # Missing rate information
    ├── raw_hours.csv            # Raw data (for debugging)
    ├── filtered_hours.csv       # Filtered data
    └── complete_hours_summary.csv # Summary information
```

## Troubleshooting

1. If `errors.csv` contains entries:
   - Check the error messages for each failed entry
   - Verify the customer data and rates in the source sheets
   - Make sure all required projects are properly configured

2. If `missing_from_rates.txt` exists:
   - Review missing rate information
   - Update the hour_rates sheet with missing entries
   - Re-download and try again

## Advanced Usage

For processing the current month's data (not common), use `current_invoicing.sh` instead. The workflow is the same, just use the current month's directory.

## Support

For issues with:

- Missing projects or rates: Update the Client Master Data sheet
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
# Install all dependencies
uv pip install -e .

# Add a new package
uv pip install package_name

# Add a development dependency
uv pip install --dev package_name

# Update dependencies
uv pip compile pyproject.toml

# Run Python commands
uv run python script.py

# Run tests
uv run pytest

# Run linting
uv run ruff check .
uv run ruff format .
```

### Data Structures

#### AgileDay Fields

Important fields from AgileDay API:

- `projectId` - Unique identifier for the project
- `projectName` - Name of the project
- `projectTask` - Task name within the project
- `actualMinutes` - Time spent in minutes
- `billable` - Whether the entry is billable (True/False)
- `employeeCompany` - Company name of the employee
- `taskHourlyPrice` - Hourly rate for the task
- `openingHourlyPrice` - Default hourly rate for the project

#### customer.csv Fields

Fields from Taulukko1 sheet:

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

#### rates.csv Fields

Fields from hour_rates sheet:

- Column 1: `projectId` - AgileDay project ID
- Column 2: `taskName` - Name of the task
- Column 3: `rate` - Hourly rate to apply

### Data Flow

1. **AgileDay Data Collection**
   - Fetch time entries for specified date range
   - Filter by company and billable status
   - Group entries by project

2. **Customer Data Processing**
   - Match entries with customer.csv by AgileDay_projectId
   - Apply included_hours filter
   - Determine rate source (internal vs AgileDay)

3. **Rate Application**
   - For internal rates: Look up in rates.csv by project ID and task
   - For AgileDay rates: Use taskHourlyPrice from time entry
   - Log missing rates to missing_from_rates.txt

4. **Output Generation**
   - Group entries by customer
   - Calculate totals and summaries
   - Generate Workday-compatible CSV
   - Create summary reports

### Error Handling

The system handles several types of errors:

- Missing project configurations
- Invalid rate configurations
- Missing customer data
- Data format issues

All errors are:

1. Logged to the application log
2. Written to errors.csv if entry-specific
3. Written to missing_from_rates.txt if rate-related

### Development Guidelines

1. **Code Style**
   - Use ruff for formatting and linting
   - Follow type hints and docstring conventions
   - Keep methods focused and single-purpose

2. **Testing**
   - Write tests for new features
   - Use pytest for testing
   - Include edge cases in test coverage

3. **Error Handling**
   - Log all errors with appropriate context
   - Maintain detailed error messages
   - Preserve failed entries for debugging

4. **Data Validation**
   - Validate all input data
   - Check for required fields
   - Verify data type consistency

### Using Ruff for Code Quality

This project uses Ruff for both linting and formatting. Ruff is configured to enforce consistent code style and catch common issues.

#### Running Ruff

```bash
# Check code style and find issues
uv run ruff check .

# Auto-fix issues where possible
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check and format in one command
uv run ruff check --fix . && uv run ruff format .
```

#### Ruff Configuration

The project's `.ruff.toml` enforces:

```toml
# Line length and formatting
line-length = 100
indent-width = 4

# Select rules to enforce
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "UP",  # pyupgrade
    "PL",  # pylint
    "RUF", # ruff-specific rules
    "TID", # flake8-tidy-imports
    "TCH", # flake8-type-checking
    "T20", # flake8-print
]

# Ignore specific rules
ignore = [
    "PLR0913", # Too many arguments to function call
]

# Import sorting
[isort]
force-single-line = true
lines-between-types = 1

# Type checking
[flake8-type-checking]
strict = true
```

#### Key Style Rules

1. **Imports**
   - One import per line
   - Grouped by standard lib, third-party, local
   - No wildcard imports

   ```python
   from typing import Dict, List
   
   import pandas as pd
   
   from .transformer import TimeEntryTransformer
   ```

2. **Type Hints**
   - Required for all function parameters
   - Required for function return types
   - Use built-in types or typing module

   ```python
   def process_entries(
       entries: List[Dict[str, Any]],
       customer_data: Dict[str, Dict[str, Any]]
   ) -> List[Dict[str, Any]]:
   ```

3. **Docstrings**
   - Required for all public functions/methods
   - NumPy style format
   - Include Parameters, Returns, Examples

   ```python
   def transform_to_workday(
       self,
       customer_data_path: Path,
       raw_hours_path: Path,
       rates_file_path: Path,
       result_file_path: Path
   ) -> None:
       """Transform time entries and customer data to Workday invoice format.
       
       Parameters
       ----------
       customer_data_path : Path
           Path to customer data CSV file
       raw_hours_path : Path
           Path to raw hours CSV file
       rates_file_path : Path
           Path to rates CSV file
       result_file_path : Path
           Path to write the result file
           
       Returns
       -------
       None
           Writes output to result_file_path
       """
   ```

4. **Error Handling**
   - Use specific exception types
   - Include context in error messages

   ```python
   if not customer_data_path.is_file():
       raise ValueError(f"Customer data file not found: {customer_data_path}")
   ```

5. **Logging**
   - Use logging instead of print
   - Include appropriate log levels

   ```python
   logger.info("Processing %d entries", len(entries))
   logger.debug("Project details: %s", project_info)
   logger.warning("Missing rate for project: %s", project_id)
   ```

#### Pre-commit Hooks

Set up pre-commit hooks to automatically check code:

```bash
# Install pre-commit
uv pip install pre-commit

# Install hooks
pre-commit install

# Manual run
pre-commit run --all-files
```

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
      - id: ruff-format
```

#### VS Code Integration

Add to `.vscode/settings.json`:

```json
{
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
        "source.fixAll.ruff": true,
        "source.organizeImports.ruff": true
    },
    "python.analysis.typeCheckingMode": "strict"
}
```
