"""Command line interface for the billable invoicing system."""

import csv
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set

import click
from dateutil import parser

from .agileday import AgileDayClient
from .transformer import TimeEntryTransformer
from .workday_transformer import WorkdayTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def configure_logging(verbose: bool) -> None:
    """Configure logging level based on verbosity."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

def validate_date(ctx: click.Context, param: click.Parameter, value: str) -> datetime:
    """Validate and parse date string."""
    try:
        return parser.parse(value)
    except ValueError as e:
        raise click.BadParameter(f"Invalid date format: {e}")

@click.group()
def cli():
    """Transform hour marking system data to invoicing system data."""
    pass

def get_all_field_names(entries: List[Dict[str, Any]]) -> Set[str]:
    """Get all unique field names from a list of dictionaries."""
    field_names: Set[str] = set()
    for entry in entries:
        field_names.update(str(key) for key in entry.keys())
    return field_names

@cli.command()
@click.option(
    '--company',
    required=True,
    help='Company name to filter entries'
)
@click.option(
    '--output-path',
    required=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True),
    help='Directory where all output files will be written'
)
@click.option(
    '--customer-data',
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help='Path to customer data CSV file (e.g., customer.csv)'
)
@click.option(
    '--rates-file',
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help='Path to rates CSV file with internal hour rates'
)
@click.option(
    '--result-file',
    required=True,
    help='Name of the result file (e.g., fixed-fee-2025-03.csv)'
)
@click.option(
    '--start-date',
    required=True,
    callback=validate_date,
    help='Start date for time entries (YYYY-MM-DD)'
)
@click.option(
    '--end-date',
    required=True,
    callback=validate_date,
    help='End date for time entries (YYYY-MM-DD)'
)
@click.option(
    '--status',
    default='Submitted',
    help='Status of entries to fetch (default: Submitted)'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def fetch_hours(
    company: str,
    output_path: str,
    customer_data: str,
    rates_file: str,
    result_file: str,
    start_date: datetime,
    end_date: datetime,
    status: str,
    verbose: bool
) -> None:
    """Fetch time entries from AgileDay and save raw data to CSV."""
    configure_logging(verbose)
    
    # Create output directory if it doesn't exist
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define output file paths
    raw_output = output_dir / "raw_hours.csv"
    raw_output_complete = output_dir / "raw_hours_complete.csv"
    filtered_output = output_dir / "filtered_hours.csv"
    filtered_summary = output_dir / "filtered_hours_summary.csv"
    complete_summary = output_dir / "complete_hours_summary.csv"
    errors_file = output_dir / "errors.csv"
    missing_rates_file = output_dir / "missing_from_rates.txt"
    result_file_path = output_dir / result_file
    
    # Track failed entries
    failed_entries: List[Dict[str, Any]] = []
    
    try:
        # Initialize clients
        client = AgileDayClient()
        transformer = TimeEntryTransformer()
        workday_transformer = WorkdayTransformer()
        
        # Verify input files are readable
        customer_data_path = Path(customer_data)
        rates_file_path = Path(rates_file)
        if not customer_data_path.is_file():
            raise ValueError(f"Customer data file not found: {customer_data}")
        if not os.access(customer_data_path, os.R_OK):
            raise ValueError(f"Customer data file is not readable: {customer_data}")
        if not rates_file_path.is_file():
            raise ValueError(f"Rates file not found: {rates_file}")
        if not os.access(rates_file_path, os.R_OK):
            raise ValueError(f"Rates file is not readable: {rates_file}")
            
        # Fetch entries and project data
        entries = client.get_time_entries(start_date, end_date, status)
        
        # Write unfiltered data for debugging
        transformer.transform_to_csv(entries, raw_output)
        logger.info("Wrote %d raw entries to %s", len(entries), raw_output)
        
        # Log some stats about the raw data
        external_count = sum(1 for e in entries if e.get('projectType') == 'External')
        billable_count = sum(1 for e in entries if e.get('billable'))
        logger.info(
            "Raw data stats: %d total entries, %d external projects, %d billable entries",
            len(entries),
            external_count,
            billable_count
        )
        
        # Build project data cache
        project_data: Dict[str, Dict[str, Any]] = {}
        project_ids = {entry['projectId'] for entry in entries if entry.get('projectId')}
        logger.info("Found %d unique projects", len(project_ids))
        
        for project_id in project_ids:
            try:
                project = client.get_project(project_id)
                project_data[project_id] = project
                if verbose:
                    logger.debug(
                        "Project %s: type=%s, company=%s",
                        project_id,
                        project.get('type'),
                        project.get('company', {}).get('name')
                    )
            except Exception as e:
                logger.warning("Failed to fetch project %s: %s", project_id, e)
                # Add entries with failed project fetch to failed entries
                failed_entries.extend([
                    {**entry, 'error': f"Failed to fetch project data: {str(e)}"}
                    for entry in entries
                    if entry.get('projectId') == project_id
                ])
        
        # First show summary for the specified company (informational)
        try:
            filtered_entries = transformer.filter_entries(entries, company, project_data)
            logger.info("\nSummary for company: %s", company)
            logger.info("-" * 80)
            transformer.calculate_project_summaries(filtered_entries)
            
            # Save filtered data to CSV (for reference)
            transformer.transform_to_csv(filtered_entries, filtered_output)
            logger.info("Successfully exported %d filtered entries to %s", len(filtered_entries), filtered_output)
            
            # Read customer data for project validation
            customer_data_dict = {}
            with open(customer_data_path, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    project_id = row.get('AgileDay_projectId')
                    if project_id:
                        customer_data_dict[project_id] = row
            
            # Set customer data in transformer
            transformer.set_customer_data(customer_data_dict)
            
            # Write filtered summaries to CSV (for reference)
            transformer.write_summaries_to_csv(filtered_entries, filtered_summary)
            logger.info("Filtered project summaries written to %s", filtered_summary)
        except Exception as e:
            logger.error("Error processing filtered entries: %s", str(e))
            failed_entries.extend([
                {**entry, 'error': f"Failed during filtering: {str(e)}"}
                for entry in entries
            ])
        
        # Now process ALL entries for the actual workday transformation
        try:
            logger.info("\nProcessing complete summary for all projects")
            logger.info("-" * 80)
            transformer.calculate_project_summaries(entries)
            
            # Write complete summaries to CSV
            transformer.write_summaries_to_csv(entries, complete_summary)
            logger.info("Complete project summaries written to %s", complete_summary)
            
            # Transform complete data using customer data
            workday_transformer.transform_to_workday(
                customer_data_path=customer_data_path,
                raw_hours_path=filtered_output,  # Use filtered hours as input
                rates_file_path=rates_file_path,
                result_file_path=result_file_path
            )
            logger.info("Transformed data written to result file: %s", result_file_path)
        except Exception as e:
            logger.error("Error during workday transformation: %s", str(e), exc_info=True)
            failed_entries.extend([
                {**entry, 'error': f"Failed during workday transformation: {str(e)}"}
                for entry in entries
            ])
            raise  # Re-raise to ensure we see the full error
        
    except Exception as e:
        logger.error("Failed to process time entries: %s", str(e), exc_info=True)
        raise  # Re-raise to ensure we exit with error
    finally:
        # Write failed entries to errors.csv if any exist
        if failed_entries:
            try:
                with open(errors_file, 'w', newline='') as f:
                    if failed_entries:
                        # Get all possible field names from all entries
                        fieldnames = sorted(get_all_field_names(failed_entries))
                        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                        writer.writeheader()
                        writer.writerows(failed_entries)
                        logger.warning("Wrote %d failed entries to %s", len(failed_entries), errors_file)
            except Exception as write_error:
                logger.error("Failed to write errors.csv: %s", str(write_error))
        
        if failed_entries:
            sys.exit(1)

if __name__ == '__main__':
    cli() 