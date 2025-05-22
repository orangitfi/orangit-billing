"""Transform time entries data to utilization metrics."""

import csv
import datetime
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .agileday import AgileDayClient
from .config import ROLE_EMAILS

logger = logging.getLogger(__name__)

class UtilizationTransformer:
    """Transform time entries to utilization metrics."""

    def __init__(self):
        """Initialize the transformer."""
        self.company_code = "263"
        self.source_system = "Orangit"
        self.agileday_client = AgileDayClient()

    def _fetch_hours(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        status: str = "Submitted"
    ) -> List[Dict[str, Any]]:
        """Fetch time entries from AgileDay.
        
        Parameters
        ----------
        start_date : datetime.date
            Start date for time entries
        end_date : datetime.date
            End date for time entries
        status : str, optional
            Status of entries to fetch, defaults to "Submitted"
            
        Returns
        -------
        List[Dict[str, Any]]
            List of time entries matching the criteria
        """
        logger.info(
            "Fetching time entries between %s and %s with status %s",
            start_date,
            end_date,
            status
        )
        
        try:
            entries = self.agileday_client.get_time_entries(
                start_date=datetime.datetime.combine(start_date, datetime.time.min),
                end_date=datetime.datetime.combine(end_date, datetime.time.max),
                status=status
            )
            
            # Convert minutes to hours and get hourly rate
            for entry in entries:
                if entry.get('actualMinutes'):
                    try:
                        entry['actualHours'] = float(entry['actualMinutes']) / 60.0
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to convert minutes to hours for entry {entry}: {e}")
                        entry['actualHours'] = 0.0
                else:
                    entry['actualHours'] = 0.0
                
                # Get hourly rate from taskHourlyPrice only
                task_rate = entry.get('taskHourlyPrice', '')
                if task_rate:
                    entry['hourlyRate'] = float(task_rate)
                else:
                    entry['hourlyRate'] = 0.0
                
                # Log the entry to see what fields we have
                logger.debug(f"Entry fields: {list(entry.keys())}")
                if 'employeeEmail' in entry:
                    logger.debug(f"Found employeeEmail: {entry['employeeEmail']}")
                elif 'employeeEmailAddress' in entry:
                    logger.debug(f"Found employeeEmailAddress: {entry['employeeEmailAddress']}")
                else:
                    logger.warning(f"No email field found in entry: {entry}")
            
            logger.info("Fetched %d time entries from AgileDay", len(entries))
            return entries
            
        except Exception as e:
            logger.error("Failed to fetch time entries from AgileDay: %s", str(e))
            raise

    def _format_decimal(self, value: float) -> str:
        """Format decimal number with period as separator.
        
        Parameters
        ----------
        value : float
            Number to format
            
        Returns
        -------
        str
            Formatted number with period as decimal separator
        """
        return f"{value:.2f}"

    def _read_customer_data(self, customer_data_path: Path) -> Dict[str, Dict[str, Any]]:
        """Read customer data from CSV file.

        Parameters
        ----------
        customer_data_path : Path
            Path to customer data CSV file

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary of customer data keyed by AgileDay project ID
        """
        customer_data: Dict[str, Dict[str, Any]] = {}
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with customer_data_path.open('r', newline='', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    # Log the available fields from CSV
                    logger.info("Customer CSV fields: %s", reader.fieldnames)
                    for row in reader:
                        agileday_project_id = row.get('AgileDay_projectId')
                        if agileday_project_id:
                            # Log each mapping we create
                            logger.debug(
                                "Mapping project ID %s to client '%s', service '%s'",
                                agileday_project_id,
                                row.get('Client', 'Unknown'),
                                row.get('Service name', 'Unknown Service')
                            )
                            customer_data[agileday_project_id] = row
                logger.info("Successfully read customer data with encoding: %s", encoding)
                break
            except UnicodeDecodeError:
                logger.debug("Failed to read with encoding %s, trying next", encoding)
                continue
            except Exception as e:
                logger.error("Failed to read customer data: %s", str(e))
                raise
        
        if not customer_data:
            raise ValueError(f"Failed to read customer data with any of the attempted encodings: {encodings}")
        
        logger.info("Loaded %d customer records", len(customer_data))
        return customer_data

    def _process_hours(
        self,
        customer_data: Dict[str, Dict[str, Any]],
        entries: List[Dict[str, Any]]
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Process hours for all projects.

        Parameters
        ----------
        customer_data : Dict[str, Dict[str, Any]]
            Dictionary of customer data
        entries : List[Dict[str, Any]]
            List of time entries from AgileDay

        Returns
        -------
        Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]
            Tuple containing:
            - Dictionary of processed entries grouped by task
            - List of projects not found in customer data
        """
        processed_entries: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        projects_not_found: List[Dict[str, Any]] = []
        
        # Group entries by project
        hours_by_project: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for entry in entries:
            project_id = entry.get('projectId')
            if project_id:
                hours_by_project[project_id].append(entry)
        
        # Process each project
        for project_id, project_entries in hours_by_project.items():
            customer_info = customer_data.get(project_id, {})
            
            # Filter hours based on included_hours setting
            included_hours = customer_info.get('included_hours', '').strip()
            filtered_entries = []
            
            for entry in project_entries:
                # If project is in customer data, check included_hours setting
                if customer_info:
                    if included_hours.lower() == 'all':
                        filtered_entries.append(entry)
                    elif included_hours.lower() == 'orangit':
                        employee_company = entry.get('employeeCompany', '')
                        if employee_company.lower() == 'orangit oy'.lower():
                            filtered_entries.append(entry)
                else:
                    # If project is not in customer data, include all Orangit Oy hours
                    employee_company = entry.get('employeeCompany', '')
                    if employee_company.lower() == 'orangit oy'.lower():
                        filtered_entries.append(entry)
            
            # Group entries by task
            hours_by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for entry in filtered_entries:
                task_name = entry.get('projectTask', '')
                hours_by_task[task_name].append(entry)
            
            # Process each task
            for task_name, task_entries in hours_by_task.items():
                try:
                    total_hours = sum(float(entry.get('actualHours', 0)) for entry in task_entries)
                    billable_hours = sum(
                        float(entry.get('actualHours', 0))
                        for entry in task_entries
                        if entry.get('billable') == 'True'
                    )
                    
                    # Get project details from the first entry
                    first_entry = task_entries[0]
                    hourly_rate = float(first_entry.get('hourlyRate', 0))
                    
                    # Only calculate euro amounts for billable hours
                    euro_amount = billable_hours * hourly_rate
                    billable_euro_amount = euro_amount  # Same as euro_amount since we only count billable
                    
                    # Get email from the first entry that has it
                    email = None
                    for entry in task_entries:
                        email = entry.get('employeeEmail') or entry.get('employeeEmailAddress')
                        if email:
                            break
                    
                    processed_entry = {
                        'projectId': project_id,
                        'projectName': first_entry.get('projectName', ''),
                        'projectTask': task_name,
                        'actualHours': total_hours,
                        'billable': billable_hours > 0,  # Mark as billable if any hours are billable
                        'hourlyRate': hourly_rate,
                        'euroAmount': euro_amount,
                        'billableEuroAmount': billable_euro_amount,
                        'customer_info': customer_info,
                        'date': first_entry.get('date', ''),
                        'employeeEmail': email  # Add the email to the processed entry
                    }
                    
                    # Add to processed entries
                    processed_entries[task_name].append(processed_entry)
                    
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to process task {task_name} for project {project_id}: {e}"
                    )
            
            # If project not found in customer data, add to projects_not_found
            if not customer_info and project_entries:
                first_entry = project_entries[0]
                total_hours = sum(
                    float(entry.get('actualHours', 0))
                    for entry in project_entries
                    if entry.get('employeeCompany', '').lower() == 'orangit oy'.lower()
                )
                billable_hours = sum(
                    float(entry.get('actualHours', 0))
                    for entry in project_entries
                    if entry.get('employeeCompany', '').lower() == 'orangit oy'.lower()
                    and entry.get('billable') == 'True'
                )
                hourly_rate = float(first_entry.get('hourlyRate', 0))
                
                # Only calculate euro amounts for billable hours
                euro_amount = billable_hours * hourly_rate
                billable_euro_amount = euro_amount  # Same as euro_amount since we only count billable
                
                projects_not_found.append({
                    'projectId': project_id,
                    'projectName': first_entry.get('projectName', 'Unknown'),
                    'totalHours': total_hours,
                    'billableHours': billable_hours,
                    'hourlyRate': hourly_rate,
                    'euroAmount': euro_amount,
                    'billableEuroAmount': billable_euro_amount
                })
        
        return processed_entries, projects_not_found

    def _write_utilization_summary(
        self,
        processed_entries: Dict[str, List[Dict[str, Any]]],
        result_file_path: Path,
        first_day: Optional[datetime.date],
        last_day: Optional[datetime.date],
        start_date: Optional[datetime.date],
        end_date: Optional[datetime.date]
    ) -> None:
        """Write a summary of utilization data.
        
        Parameters
        ----------
        processed_entries : Dict[str, List[Dict[str, Any]]]
            Dictionary of processed entries grouped by task
        result_file_path : Path
            Path to the result file, used to determine summary file path
        first_day : Optional[datetime.date]
            First day of hours
        last_day : Optional[datetime.date]
            Last day of hours
        start_date : Optional[datetime.date]
            Start date used for filtering
        end_date : Optional[datetime.date]
            End date used for filtering
        """
        summary_file = result_file_path.with_stem(f"{result_file_path.stem}_summary")
        
        try:
            with open(summary_file, 'w', encoding='utf-8', newline='') as f:
                # Write period information
                f.write("PERIOD INFORMATION\n")
                f.write("=" * 80 + "\n")
                if start_date and end_date:
                    f.write(f"Filtered period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}\n")
                if first_day and last_day:
                    f.write(f"Data period: {first_day.strftime('%Y-%m-%d')} to {last_day.strftime('%Y-%m-%d')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Write task summaries
                for task_name, entries in sorted(processed_entries.items()):
                    f.write(f"Task: {task_name}\n")
                    f.write("-" * 80 + "\n")
                    
                    # Calculate totals for this task
                    total_hours = sum(entry['actualHours'] for entry in entries)
                    billable_hours = sum(
                        entry['actualHours']
                        for entry in entries
                        if entry['billable']
                    )
                    non_billable_hours = total_hours - billable_hours
                    
                    total_euro = sum(entry['euroAmount'] for entry in entries)
                    billable_euro = sum(
                        entry['billableEuroAmount']
                        for entry in entries
                        if entry['billable']
                    )
                    non_billable_euro = total_euro - billable_euro
                    
                    # Write task totals
                    f.write(f"Total Hours: {self._format_decimal(total_hours)}\n")
                    f.write(f"Billable Hours: {self._format_decimal(billable_hours)}\n")
                    f.write(f"Non-Billable Hours: {self._format_decimal(non_billable_hours)}\n")
                    f.write(f"Billable Percentage: {self._format_decimal((billable_hours / total_hours * 100) if total_hours > 0 else 0)}%\n")
                    f.write(f"Total Euro Amount: {self._format_decimal(total_euro)} €\n")
                    f.write(f"Billable Euro Amount: {self._format_decimal(billable_euro)} €\n")
                    f.write(f"Non-Billable Euro Amount: {self._format_decimal(non_billable_euro)} €\n")
                    f.write("\n")
                    
                    # Write project details
                    f.write("Projects:\n")
                    for entry in sorted(entries, key=lambda x: (x['customer_info'].get('Client', 'Unknown'), x['projectName'])):
                        client_name = entry['customer_info'].get('Client', 'Unknown')
                        f.write(f"  {client_name} - {entry['projectName']}: {self._format_decimal(entry['actualHours'])} hours")
                        if entry['billable']:
                            f.write(" (Billable)")
                        f.write(f" @ {self._format_decimal(entry['hourlyRate'])} €/h = {self._format_decimal(entry['euroAmount'])} €\n")
                    f.write("\n")
                
                # Write overall summary
                f.write("\nOVERALL SUMMARY\n")
                f.write("=" * 80 + "\n")
                
                # Calculate overall totals
                total_hours = sum(
                    entry['actualHours']
                    for entries in processed_entries.values()
                    for entry in entries
                )
                billable_hours = sum(
                    entry['actualHours']
                    for entries in processed_entries.values()
                    for entry in entries
                    if entry['billable']
                )
                non_billable_hours = total_hours - billable_hours
                
                total_euro = sum(
                    entry['euroAmount']
                    for entries in processed_entries.values()
                    for entry in entries
                )
                billable_euro = sum(
                    entry['billableEuroAmount']
                    for entries in processed_entries.values()
                    for entry in entries
                    if entry['billable']
                )
                non_billable_euro = total_euro - billable_euro
                
                f.write(f"Total Hours: {self._format_decimal(total_hours)}\n")
                f.write(f"Billable Hours: {self._format_decimal(billable_hours)}\n")
                f.write(f"Non-Billable Hours: {self._format_decimal(non_billable_hours)}\n")
                f.write(f"Billable Percentage: {self._format_decimal((billable_hours / total_hours * 100) if total_hours > 0 else 0)}%\n")
                f.write(f"Total Euro Amount: {self._format_decimal(total_euro)} €\n")
                f.write(f"Billable Euro Amount: {self._format_decimal(billable_euro)} €\n")
                f.write(f"Non-Billable Euro Amount: {self._format_decimal(non_billable_euro)} €\n")
                
                f.write("=" * 80 + "\n")
                
            logger.info("Wrote utilization summary to %s", summary_file)
            logger.info(
                "Summary totals - Total Hours: %.2f, Billable Hours: %.2f, Non-Billable Hours: %.2f",
                total_hours, billable_hours, non_billable_hours
            )
            logger.info(
                "Summary totals - Total Euro: %.2f €, Billable Euro: %.2f €, Non-Billable Euro: %.2f €",
                total_euro, billable_euro, non_billable_euro
            )
            if start_date and end_date:
                logger.info(
                    "Filtered period - Start: %s, End: %s",
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
            if first_day and last_day:
                logger.info(
                    "Data period - First day: %s, Last day: %s",
                    first_day.strftime('%Y-%m-%d'),
                    last_day.strftime('%Y-%m-%d')
                )
        except Exception as e:
            logger.error("Failed to write utilization summary: %s", str(e))
            raise

    def _write_projects_not_found(
        self,
        projects_not_found: List[Dict[str, Any]],
        result_file_path: Path
    ) -> None:
        """Write projects not found in customer data to CSV file.
        
        Parameters
        ----------
        projects_not_found : List[Dict[str, Any]]
            List of projects not found in customer data
        result_file_path : Path
            Path to the result file, used to determine the output path
        """
        if not projects_not_found:
            return
            
        not_found_file = result_file_path.with_stem(f"{result_file_path.stem}_projects_not_found")
        with not_found_file.open('w', newline='') as csvfile:
            writer = csv.DictWriter(
                csvfile,
                fieldnames=[
                    'projectId',
                    'projectName',
                    'totalHours',
                    'billableHours',
                    'hourlyRate',
                    'euroAmount',
                    'billableEuroAmount'
                ]
            )
            writer.writeheader()
            for project in sorted(projects_not_found, key=lambda x: x['projectName']):
                writer.writerow(project)
        logger.info("Wrote %d projects not found to %s", len(projects_not_found), not_found_file)

    def _write_weekly_summary(
        self,
        processed_entries: Dict[str, List[Dict[str, Any]]],
        result_file_path: Path,
        start_date: Optional[datetime.date],
        end_date: Optional[datetime.date]
    ) -> None:
        """Write a weekly summary of hours by task to CSV file.
        
        Parameters
        ----------
        processed_entries : Dict[str, List[Dict[str, Any]]]
            Dictionary of processed entries grouped by task
        result_file_path : Path
            Path to the result file, used to determine summary file path
        start_date : Optional[datetime.date]
            Start date used for filtering
        end_date : Optional[datetime.date]
            End date used for filtering
        """
        # Determine date range for columns
        if start_date and end_date:
            current_date = start_date
            end = end_date
        else:
            # Find min and max dates from entries
            all_dates = []
            for entries in processed_entries.values():
                for entry in entries:
                    date_str = entry.get('date', '')
                    if date_str:
                        try:
                            entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            all_dates.append(entry_date)
                        except ValueError:
                            continue
            if not all_dates:
                logger.warning("No valid dates found in entries")
                return
            current_date = min(all_dates)
            end = max(all_dates)
        
        # Generate week columns
        weeks = []
        while current_date <= end:
            week_start = current_date - datetime.timedelta(days=current_date.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            weeks.append((week_start, week_end))
            current_date += datetime.timedelta(days=7)
        
        # Prepare data for CSV
        weekly_data = []
        for task_name, entries in sorted(processed_entries.items()):
            row_data = {'Task': task_name}
            
            # Initialize hours for each week
            for week_start, week_end in weeks:
                week_key = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
                row_data[week_key] = 0.0
            
            # Sum hours for each week
            for entry in entries:
                date_str = entry.get('date', '')
                if date_str:
                    try:
                        entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        for week_start, week_end in weeks:
                            if week_start <= entry_date <= week_end:
                                week_key = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
                                row_data[week_key] += float(entry.get('actualHours', 0))
                                break
                    except ValueError:
                        continue
            
            weekly_data.append(row_data)
        
        # Write to CSV
        weekly_file = result_file_path.with_stem(f"{result_file_path.stem}_weekly")
        with weekly_file.open('w', newline='') as csvfile:
            fieldnames = ['Task'] + [f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" 
                                  for start, end in weeks]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in weekly_data:
                writer.writerow(row)
        
        logger.info("Wrote weekly summary to %s", weekly_file)

    def _read_raw_hours(
        self,
        raw_hours_path: Path,
        start_date: Optional[datetime.date],
        end_date: Optional[datetime.date]
    ) -> List[Dict[str, Any]]:
        """Read raw hours from CSV file.

        Parameters
        ----------
        raw_hours_path : Path
            Path to raw hours CSV file
        start_date : Optional[datetime.date]
            Start date for filtering hours (inclusive)
        end_date : Optional[datetime.date]
            End date for filtering hours (inclusive)

        Returns
        -------
        List[Dict[str, Any]]
            List of time entries
        """
        entries: List[Dict[str, Any]] = []
        total_entries = 0
        filtered_entries = 0
        encodings = ['utf-8', 'latin1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with raw_hours_path.open('r', newline='', encoding=encoding) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        total_entries += 1
                        
                        # Check date if filtering is enabled
                        if start_date or end_date:
                            date_str = row.get('date', '')
                            if date_str:
                                try:
                                    entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                                    if start_date and entry_date < start_date:
                                        continue
                                    if end_date and entry_date > end_date:
                                        continue
                                except ValueError:
                                    logger.warning(f"Invalid date format in entry: {date_str}")
                                    continue
                        
                        # Convert numeric fields
                        try:
                            if row.get('actualMinutes'):
                                # Convert minutes to hours
                                row['actualHours'] = float(row['actualMinutes']) / 60.0
                            else:
                                row['actualHours'] = 0.0
                                
                            # Get hourly rate from taskHourlyPrice only
                            task_rate = row.get('taskHourlyPrice', '')
                            if task_rate:
                                row['hourlyRate'] = float(task_rate)
                            else:
                                row['hourlyRate'] = 0.0
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Failed to convert numeric fields for entry {row}: {e}")
                            row['actualHours'] = 0.0
                            row['hourlyRate'] = 0.0
                        
                        entries.append(row)
                        filtered_entries += 1
                logger.info("Successfully read raw hours with encoding: %s", encoding)
                break
            except UnicodeDecodeError:
                logger.debug("Failed to read with encoding %s, trying next", encoding)
                continue
            except Exception as e:
                logger.error("Failed to read raw hours: %s", str(e))
                raise
        
        if not entries:
            raise ValueError(f"Failed to read raw hours with any of the attempted encodings: {encodings}")
        
        logger.info(
            "Processed %d raw hour entries, %d entries after date filtering",
            total_entries,
            filtered_entries
        )
        return entries

    def transform_to_csv(self, entries: List[Dict[str, Any]], output_path: Path) -> None:
        """Transform entries to CSV format.

        Parameters
        ----------
        entries : List[Dict[str, Any]]
            List of time entries to transform
        output_path : Path
            Path to write the CSV file
        """
        if not entries:
            logger.warning("No entries to write to CSV")
            return
            
        # Get all possible field names from all entries
        fieldnames = sorted(set(
            field
            for entry in entries
            for field in entry.keys()
        ))
        
        with output_path.open('w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(entries)
            
        logger.info("Wrote %d entries to %s", len(entries), output_path)

    def _get_role(self, email: str) -> str:
        """Get role based on email address.
        
        Parameters
        ----------
        email : str
            Email address of the employee
            
        Returns
        -------
        str
            Role of the employee
        """
        email = email.lower()
        for role, emails in ROLE_EMAILS.items():
            if email in [e.lower() for e in emails]:
                return role
        return 'Engineer'

    def _write_role_summary(
        self,
        processed_entries: Dict[str, List[Dict[str, Any]]],
        result_file_path: Path,
        start_date: Optional[datetime.date],
        end_date: Optional[datetime.date]
    ) -> None:
        """Write a weekly summary of hours by role and task to CSV file.
        
        Parameters
        ----------
        processed_entries : Dict[str, List[Dict[str, Any]]]
            Dictionary of processed entries grouped by task
        result_file_path : Path
            Path to the result file, used to determine summary file path
        start_date : Optional[datetime.date]
            Start date used for filtering
        end_date : Optional[datetime.date]
            End date used for filtering
        """
        # Determine date range for columns
        if start_date and end_date:
            current_date = start_date
            end = end_date
        else:
            # Find min and max dates from entries
            all_dates = []
            for entries in processed_entries.values():
                for entry in entries:
                    date_str = entry.get('date', '')
                    if date_str:
                        try:
                            entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            all_dates.append(entry_date)
                        except ValueError:
                            continue
            if not all_dates:
                logger.warning("No valid dates found in entries")
                return
            current_date = min(all_dates)
            end = max(all_dates)
        
        # Generate week columns
        weeks = []
        while current_date <= end:
            week_start = current_date - datetime.timedelta(days=current_date.weekday())
            week_end = week_start + datetime.timedelta(days=6)
            weeks.append((week_start, week_end))
            current_date += datetime.timedelta(days=7)
        
        # Group entries by role and task
        role_task_data: Dict[str, Dict[str, Dict[str, float]]] = {}
        for task_name, entries in processed_entries.items():
            for entry in entries:
                # Try both email fields
                email = entry.get('employeeEmail') or entry.get('employeeEmailAddress', '')
                if not email:
                    logger.warning(f"No email found for entry: {entry}")
                    continue
                    
                role = self._get_role(email)
                logger.debug(f"Assigned role {role} to email {email}")
                
                if role not in role_task_data:
                    role_task_data[role] = {}
                if task_name not in role_task_data[role]:
                    role_task_data[role][task_name] = {}
                
                # Initialize hours for each week
                for week_start, week_end in weeks:
                    week_key = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
                    if week_key not in role_task_data[role][task_name]:
                        role_task_data[role][task_name][week_key] = 0.0
                
                # Add hours to appropriate week
                date_str = entry.get('date', '')
                if date_str:
                    try:
                        entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                        for week_start, week_end in weeks:
                            if week_start <= entry_date <= week_end:
                                week_key = f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}"
                                role_task_data[role][task_name][week_key] += float(entry.get('actualHours', 0))
                                break
                    except ValueError:
                        continue
        
        # Write to CSV
        role_file = result_file_path.with_stem(f"{result_file_path.stem}_roles")
        with role_file.open('w', newline='') as csvfile:
            fieldnames = ['Role', 'Task'] + [f"{start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}" 
                                           for start, end in weeks]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            # Write data for each role and task
            for role in ['Backoffice', 'Service Lead', 'Team Lead', 'Engineer']:
                if role in role_task_data:
                    for task_name, week_data in sorted(role_task_data[role].items()):
                        row = {'Role': role, 'Task': task_name}
                        # Convert float values to strings for CSV
                        row.update({k: str(v) for k, v in week_data.items()})
                        writer.writerow(row)
        
        logger.info("Wrote role-based summary to %s", role_file)

    def transform_to_utilization(
        self,
        customer_data_path: Path,
        result_file_path: Path,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
        raw_hours_path: Optional[Path] = None
    ) -> None:
        """Transform time entries to utilization metrics.

        Parameters
        ----------
        customer_data_path : Path
            Path to customer data CSV file
        result_file_path : Path
            Path to write the result file
        start_date : Optional[datetime.date]
            Start date for filtering hours (inclusive)
        end_date : Optional[datetime.date]
            End date for filtering hours (inclusive)
        raw_hours_path : Optional[Path]
            Path to raw hours CSV file. If not provided, hours will be fetched from AgileDay.
        """
        # Verify input files exist and are readable
        if not customer_data_path.is_file():
            raise ValueError(f"Customer data file not found: {customer_data_path}")
        if raw_hours_path and not raw_hours_path.is_file():
            raise ValueError(f"Raw hours file not found: {raw_hours_path}")

        try:
            # Read customer data
            customer_data = self._read_customer_data(customer_data_path)
            logger.info("Successfully read customer data from %s", customer_data_path)
            
            # Get hours either from file or AgileDay
            if raw_hours_path:
                logger.info("Reading hours from file: %s", raw_hours_path)
                entries = self._read_raw_hours(raw_hours_path, start_date, end_date)
            else:
                if not start_date or not end_date:
                    raise ValueError("Both start_date and end_date are required when fetching from AgileDay")
                logger.info("Fetching hours from AgileDay")
                entries = self._fetch_hours(start_date, end_date)
            
            if not entries:
                logger.warning("No time entries found for the specified period")
                # Write empty summary
                self._write_utilization_summary({}, result_file_path, None, None, start_date, end_date)
                return
            
            # Track first and last day of hours
            first_day = None
            last_day = None
            
            # Process hours
            processed_entries, projects_not_found = self._process_hours(customer_data, entries)
            
            # Find first and last day
            for entries in processed_entries.values():
                for entry in entries:
                    date_str = entry.get('date', '')
                    if date_str:
                        try:
                            entry_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                            if first_day is None or entry_date < first_day:
                                first_day = entry_date
                            if last_day is None or entry_date > last_day:
                                last_day = entry_date
                        except ValueError:
                            logger.warning(f"Invalid date format in entry: {date_str}")
            
            # Write utilization summary
            self._write_utilization_summary(processed_entries, result_file_path, first_day, last_day, start_date, end_date)
            
            # Write weekly summary
            self._write_weekly_summary(processed_entries, result_file_path, start_date, end_date)
            
            # Write role-based summary
            self._write_role_summary(processed_entries, result_file_path, start_date, end_date)
            
            # Write projects not found
            self._write_projects_not_found(projects_not_found, result_file_path)
            
            logger.info("Successfully wrote result file: %s", result_file_path)
            
        except Exception as e:
            logger.error("Failed to process data: %s", str(e))
            raise 