"""Command line interface for billable invoicing."""

import argparse
import datetime
import logging
import sys
from pathlib import Path

from .utilization_transformer import UtilizationTransformer
from .workday_transformer import WorkdayTransformer

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool) -> None:
    """Set up logging configuration.
    
    Parameters
    ----------
    verbose : bool
        Whether to enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def parse_date(date_str: str) -> datetime.date:
    """Parse date string in YYYY-MM-DD format.
    
    Parameters
    ----------
    date_str : str
        Date string to parse
        
    Returns
    -------
    datetime.date
        Parsed date
        
    Raises
    ------
    ValueError
        If date string is not in YYYY-MM-DD format
    """
    try:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD") from e

def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description='Transform time entries to Workday invoice format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--mode', '-m', choices=['workday', 'util'], required=True,
                      help='Mode to run in: workday for invoice generation, util for utilization metrics')
    
    # Common arguments
    parser.add_argument('--customer-data', '-c', type=Path, required=True,
                      help='Path to customer data CSV file')
    parser.add_argument('--raw-hours', '-r', type=Path, required=True,
                      help='Path to raw hours CSV file')
    parser.add_argument('--output', '-o', type=Path, required=True,
                      help='Path to write the result file')
    
    # Workday-specific arguments
    parser.add_argument('--rates', type=Path,
                      help='Path to rates CSV file with internal hour rates (required for workday mode)')
    
    # Utilization-specific arguments
    parser.add_argument('--start-date', type=str,
                      help='Start date for filtering hours in YYYY-MM-DD format (for util mode)')
    parser.add_argument('--end-date', type=str,
                      help='End date for filtering hours in YYYY-MM-DD format (for util mode)')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    try:
        if args.mode == 'workday':
            if not args.rates:
                parser.error("--rates is required for workday mode")
            
            transformer = WorkdayTransformer()
            transformer.transform_to_workday(
                args.customer_data,
                args.raw_hours,
                args.rates,
                args.output
            )
        else:  # util mode
            # Parse dates if provided
            start_date = parse_date(args.start_date) if args.start_date else None
            end_date = parse_date(args.end_date) if args.end_date else None
            
            transformer = UtilizationTransformer()
            transformer.transform_to_utilization(
                args.customer_data,
                args.raw_hours,
                args.output,
                start_date,
                end_date
            )
            
    except Exception as e:
        logger.error("Failed to process data: %s", str(e))
        sys.exit(1)

if __name__ == '__main__':
    main() 