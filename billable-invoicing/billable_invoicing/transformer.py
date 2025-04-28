"""Transform time entries data to CSV format."""

import csv
import logging
from pathlib import Path
from typing import Any, Dict, List, TypedDict, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=Dict[str, Any])

class ProjectSummary(TypedDict):
    """Type definition for project summary data."""
    customerName: str
    projectName: str
    projectTask: str
    projectId: str
    billable: str
    totalHours: float
    hourlyRate: float
    totalAmount: float

class TimeEntryTransformer:
    """Transform time entries to CSV format."""
    
    def __init__(self):
        """Initialize the transformer with the raw data field names."""
        self.fieldnames = [
            'customerName', 'customerExternalId', 'customerId', 'projectType',
            'projectSubtype', 'projectName', 'projectId', 'projectExternalId',
            'projectTask', 'entryType', 'OpeningName', 'openingId', 'date',
            'employeeName', 'employeeEmail', 'employeeExternalId', 'employeeId',
            'billable', 'actualMinutes', 'actualHours', 'actualDays',
            'allocatedMinutes', 'allocatedHours', 'allocatedDays',
            'deviationMinutes', 'deviationHours', 'deviationDays', 'notes',
            'status', 'openingHourlyPrice', 'openingBasedRevenue',
            'openingCurrency', 'taskHourlyPrice', 'taskBasedRevenue',
            'taskCurrency', 'standardCostRate', 'standardCosts',
            'standardCostCurrency', 'employeePrimaryTeam',
            'employeePrimaryTeamExternalId', 'employeePrimaryTeamId',
            'employeeBusinessUnit', 'employeeBusinessUnitExternalId',
            'employeeBusinessUnitId', 'employeeCompany',
            'employeeCompanyExternalId', 'employeeCompanyId', 'employeeCountry',
            'projectCommercialModel', 'taskId', 'taskExternalId', 'timeEntryId',
            'timeEntryExternalId', 'customerBusinessId', 'customerFinancialId'
        ]
        
        self.summary_fieldnames = [
            'customerName',
            'projectName',
            'projectTask',
            'projectId',
            'billable',
            'totalHours',
            'hourlyRate',
            'totalAmount'
        ]
        
        # Store customer data
        self.customer_data: Dict[str, Dict[str, Any]] = {}
    
    def set_customer_data(self, customer_data: Dict[str, Dict[str, Any]]) -> None:
        """
        Set the customer data for project validation.
        
        Parameters
        ----------
        customer_data : Dict[str, Dict[str, Any]]
            Dictionary of customer data keyed by project ID
        """
        self.customer_data = customer_data
    
    def calculate_project_summaries(self, entries: List[Dict[str, Any]]) -> None:
        """
        Calculate and display project-wise summaries.
        
        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of time entries from AgileDay
        """
        # Group entries by customer and project
        summaries: Dict[tuple[str, str], ProjectSummary] = {}
        
        for entry in entries:
            key = (entry.get('customerName', ''), entry.get('projectName', ''))
            if key not in summaries:
                summaries[key] = ProjectSummary(
                    customerName=entry.get('customerName', ''),
                    projectName=entry.get('projectName', ''),
                    projectTask=entry.get('projectTask', ''),
                    projectId=entry.get('projectId', ''),
                    billable=entry.get('billable', ''),
                    totalHours=0.0,
                    hourlyRate=0.0,
                    totalAmount=0.0
                )
            
            summary = summaries[key]
            
            # Add hours
            hours = float(entry.get('actualHours', 0) or 0)
            summary['totalHours'] += hours
            
            # Get hourly rate (prefer task rate over opening rate)
            rate = float(entry.get('taskHourlyPrice', 0) or entry.get('openingHourlyPrice', 0) or 0)
            if rate > 0:
                # Weighted average for hourly rate
                old_total = summary['totalHours'] - hours
                summary['hourlyRate'] = (
                    (old_total * summary['hourlyRate'] + hours * rate) / 
                    summary['totalHours'] if summary['totalHours'] > 0 else 0
                )
            
            # Calculate amount
            summary['totalAmount'] += hours * rate
        
        # Print summaries
        if not summaries:
            logger.info("No entries to summarize")
            return
        
        # Calculate totals
        total_hours = sum(s['totalHours'] for s in summaries.values())
        total_amount = sum(s['totalAmount'] for s in summaries.values())
        
        # Print header
        logger.info("\nProject Summaries:")
        logger.info("-" * 100)
        logger.info(
            "%-30s %-30s %10s %12s %15s",
            "Customer", "Project", "Hours", "Rate", "Amount"
        )
        logger.info("-" * 100)
        
        # Print each project
        for summary in sorted(summaries.values(), key=lambda x: (-x['totalAmount'], x['customerName'])):
            logger.info(
                "%-30s %-30s %10.2f %12.2f %15.2f",
                summary['customerName'][:30],
                summary['projectName'][:30],
                summary['totalHours'],
                summary['hourlyRate'],
                summary['totalAmount']
            )
        
        # Print totals
        logger.info("-" * 100)
        logger.info(
            "%-61s %10.2f %12s %15.2f",
            "TOTAL",
            total_hours,
            "",
            total_amount
        )
        logger.info("-" * 100)
    
    def write_summaries_to_csv(
        self,
        entries: List[Dict[str, Any]],
        output_path: str | Path
    ) -> None:
        """
        Write project summaries to CSV, grouped by customer, project, and task.
        Also logs warnings for projects with no hours.
        
        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of time entries from AgileDay
        output_path : str | Path
            Path to save the CSV file
        """
        # Group entries by customer, project, and task
        summaries: Dict[tuple[str, str, str, str], ProjectSummary] = {}
        
        # Track which projects have hours
        projects_with_hours: set[str] = set()
        
        for entry in entries:
            project_id = entry.get('projectId', '')
            if project_id:
                projects_with_hours.add(project_id)
            
            key = (
                entry.get('customerName', ''),
                entry.get('projectName', ''),
                entry.get('projectTask', ''),
                project_id
            )
            if key not in summaries:
                summaries[key] = ProjectSummary(
                    customerName=entry.get('customerName', ''),
                    projectName=entry.get('projectName', ''),
                    projectTask=entry.get('projectTask', ''),
                    projectId=project_id,
                    billable=entry.get('billable', ''),
                    totalHours=0.0,
                    hourlyRate=0.0,
                    totalAmount=0.0
                )
            
            summary = summaries[key]
            
            # Add hours
            hours = float(entry.get('actualHours', 0) or 0)
            summary['totalHours'] += hours
            
            # Get hourly rate (prefer task rate over opening rate)
            rate = float(entry.get('taskHourlyPrice', 0) or entry.get('openingHourlyPrice', 0) or 0)
            if rate > 0:
                # Weighted average for hourly rate
                old_total = summary['totalHours'] - hours
                summary['hourlyRate'] = (
                    (old_total * summary['hourlyRate'] + hours * rate) / 
                    summary['totalHours'] if summary['totalHours'] > 0 else 0
                )
            
            # Calculate amount
            summary['totalAmount'] += hours * rate
        
        # Log warnings for projects without hours
        for project_id, project in self.customer_data.items():
            if project.get('Active', '').lower() == 'yes' and project_id not in projects_with_hours:
                client = project.get('Client', 'Unknown')
                service = project.get('Service name', 'Unknown Service')
                logger.warning(
                    "No hours recorded for project - Client: %s, Service: %s (ID: %s)",
                    client,
                    service,
                    project_id
                )
        
        output_path = Path(output_path)
        logger.info("Writing summaries to %s", output_path)
        
        with output_path.open('w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.summary_fieldnames)
            writer.writeheader()
            
            # Write sorted summaries
            for summary in sorted(
                summaries.values(),
                key=lambda x: (
                    x['customerName'],
                    x['projectName'],
                    x['projectTask']
                )
            ):
                writer.writerow(summary)
            
            # Write total row
            total_hours = sum(s['totalHours'] for s in summaries.values())
            total_amount = sum(s['totalAmount'] for s in summaries.values())
            
            writer.writerow({
                'customerName': 'TOTAL',
                'projectName': '',
                'projectTask': '',
                'projectId': '',
                'billable': '',
                'totalHours': total_hours,
                'hourlyRate': '',
                'totalAmount': total_amount
            })
    
    def filter_entries(
        self,
        entries: List[T],
        company: str,
        project_data: Dict[str, Dict[str, Any]]
    ) -> List[T]:
        """
        Filter time entries based on billable status.
        
        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of time entries from AgileDay
        company : str
            Unused parameter, kept for backward compatibility
        project_data : Dict[str, Dict[str, Any]]
            Dictionary of project data keyed by project ID
            
        Returns
        -------
        List[Dict[str, Any]]
            Filtered list of time entries
        """
        filtered: List[T] = []
        
        for entry in entries:
            project_id = entry.get('projectId')
            if not project_id or project_id not in project_data:
                logger.debug(
                    "Skipping entry - no project data found for ID: %s",
                    project_id
                )
                continue
            
            # Only include billable entries
            if entry.get('billable') == True:
                filtered.append(entry)
        
        logger.info(
            "Filtered %d entries down to %d billable entries",
            len(entries),
            len(filtered)
        )
        return filtered
    
    def transform_to_csv(
        self,
        entries: List[Dict[str, Any]],
        output_path: str | Path
    ) -> None:
        """
        Write raw time entries to CSV format.
        
        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of time entries from AgileDay
        output_path : str | Path
            Path to save the CSV file
            
        Raises
        ------
        IOError
            If there's an error writing to the file
        """
        output_path = Path(output_path)
        logger.info("Writing %d entries to %s", len(entries), output_path)
        
        with output_path.open('w', newline='') as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=self.fieldnames,
                extrasaction='ignore'
            )
            writer.writeheader()
            
            for entry in entries:
                writer.writerow(entry)
        
        logger.debug("Successfully wrote entries to CSV file") 