"""Command line interface for billable invoicing."""

import argparse
import datetime
import logging
import sys
from pathlib import Path

from .second_summary_transformer import SecondSummaryTransformer

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
    parser = argparse.ArgumentParser(description='Transform time entries to invoice format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    
    # Common arguments
    parser.add_argument('--customer-data', '-c', type=Path, required=True,
                      help='Path to customer data CSV file')
    parser.add_argument('--raw-hours', '-r', type=Path, required=True,
                      help='Path to raw hours CSV file')
    parser.add_argument('--output', '-o', type=Path, required=True,
                      help='Path to write the result file')
    
    # Date filtering arguments
    parser.add_argument('--start-date', type=str,
                      help='Start date for filtering hours in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str,
                      help='End date for filtering hours in YYYY-MM-DD format')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    try:
        # Parse dates if provided
        start_date = parse_date(args.start_date) if args.start_date else None
        end_date = parse_date(args.end_date) if args.end_date else None
        
        # Always generate second summary
        transformer = SecondSummaryTransformer()
        transformer.transform_to_second_summary(
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