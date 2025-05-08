"""Transform time entries data to CSV format."""

import csv
import datetime
import logging
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DECEMBER = 12

class WorkdayTransformer:
    """Transform time entries and customer data to Workday invoice format."""

    def __init__(self):
        """Initialize the transformer."""
        self.company_code = "263"
        self.reply_email = "laskutus@barona.fi"
        self.source_system = "Orangit"
        self.dimensions = {
            'cost_center': '1999',
            'business_line': 'IT',
            'area': '10091',
            'service': 'KON'
        }

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
        return f"{value:.2f}"  # No need to replace, period is Python's default

    def _read_customer_data(self, customer_data_path: Path) -> Dict[str, Dict[str, Any]]:
        """Read customer data from CSV file and filter for active projects.

        Parameters
        ----------
        customer_data_path : Path
            Path to customer data CSV file

        Returns
        -------
        Dict[str, Dict[str, Any]]
            Dictionary of active customer data keyed by AgileDay project ID
        """
        customer_data: Dict[str, Dict[str, Any]] = {}
        with customer_data_path.open('r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            # Log the available fields from CSV
            logger.info("Customer CSV fields: %s", reader.fieldnames)
            for row in reader:
                # Only process active customers
                if row.get('Active', '').lower() != 'yes':
                    continue
                
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
        
        logger.info("Loaded %d active customer records", len(customer_data))
        return customer_data

    def _read_raw_hours(self, raw_hours_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        """Read raw hours from CSV file and group by project ID.

        Parameters
        ----------
        raw_hours_path : Path
            Path to raw hours CSV file

        Returns
        -------
        Dict[str, List[Dict[str, Any]]]
            Dictionary of hour entries grouped by project ID
        """
        hours_by_project: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        total_entries = 0
        
        with raw_hours_path.open('r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                total_entries += 1
                project_id = row.get('projectId')
                if project_id:
                    # Convert numeric fields
                    try:
                        if row.get('actualMinutes'):
                            # Convert minutes to hours
                            row['actualHours'] = float(row['actualMinutes']) / 60.0
                        else:
                            row['actualHours'] = 0.0
                            
                        # Get hourly rate (prefer task rate over opening rate)
                        task_rate = row.get('taskHourlyPrice', '')
                        opening_rate = row.get('openingHourlyPrice', '')
                        if task_rate:
                            row['hourlyRate'] = float(task_rate)
                        elif opening_rate:
                            row['hourlyRate'] = float(opening_rate)
                        else:
                            row['hourlyRate'] = 0.0
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to convert numeric fields for entry {row}: {e}")
                        row['actualHours'] = 0.0
                        row['hourlyRate'] = 0.0
                    
                    hours_by_project[project_id].append(row)
        
        logger.info(
            "Processed %d raw hour entries across %d projects",
            total_entries,
            len(hours_by_project)
        )
        return hours_by_project

    def _process_customer_hours(
        self,
        customer_data: Dict[str, Dict[str, Any]],
        hours_by_project: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """Process hours for active customers.

        Parameters
        ----------
        customer_data : Dict[str, Dict[str, Any]]
            Dictionary of active customer data
        hours_by_project : Dict[str, List[Dict[str, Any]]]
            Dictionary of hour entries by project

        Returns
        -------
        List[Dict[str, Any]]
            List of processed entries ready for transformation
        """
        processed_entries: List[Dict[str, Any]] = []
        projects_without_hours: List[str] = []
        
        # Process each active customer project
        for project_id, customer_info in customer_data.items():
            project_hours = hours_by_project.get(project_id, [])
            
            if not project_hours:
                projects_without_hours.append(
                    f"Project: {customer_info.get('projectName', 'Unknown')} "
                    f"(ID: {project_id})"
                )
                continue
            
            # Filter hours based on included_hours setting
            included_hours = customer_info.get('included_hours', '').strip()
            filtered_hours = []
            logger.debug(
                "Processing hours for project - Client: %s, Service: %s (ID: %s), included_hours: %s, total entries: %d",
                customer_info.get('Client', 'Unknown'),
                customer_info.get('Service name', 'Unknown Service'),
                project_id,
                included_hours,
                len(project_hours)
            )
            
            for entry in project_hours:
                if entry.get('billable') == 'True':  # Only process billable hours
                    # If included_hours is 'All', include all billable hours
                    # If included_hours is 'Orangit', only include hours from Orangit Oy
                    if included_hours.lower() == 'all':
                        filtered_hours.append(entry)
                    elif included_hours.lower() == 'orangit':
                        employee_company = entry.get('employeeCompany', '')
                        logger.debug(
                            "Checking employee company: '%s' for entry with project task: %s",
                            employee_company,
                            entry.get('projectTask', '')
                        )
                        # Case-insensitive comparison for company name
                        if employee_company.lower() == 'orangit oy'.lower():
                            filtered_hours.append(entry)
                    else:
                        logger.warning(
                            "Unknown included_hours value '%s' for project - Client: %s, Service: %s (ID: %s)",
                            included_hours,
                            customer_info.get('Client', 'Unknown'),
                            customer_info.get('Service name', 'Unknown Service'),
                            project_id
                        )
            
            logger.debug(
                "After filtering - Client: %s, Service: %s (ID: %s), included_hours: %s, filtered entries: %d",
                customer_info.get('Client', 'Unknown'),
                customer_info.get('Service name', 'Unknown Service'),
                project_id,
                included_hours,
                len(filtered_hours)
            )
            
            if not filtered_hours:
                logger.warning(
                    "No matching hours after filtering - Client: %s, Service: %s (ID: %s), included_hours: %s",
                    customer_info.get('Client', 'Unknown'),
                    customer_info.get('Service name', 'Unknown Service'),
                    project_id,
                    included_hours
                )
                continue
            
            # Group filtered hours by task
            hours_by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            for entry in filtered_hours:
                task_name = entry.get('projectTask', '')
                hours_by_task[task_name].append(entry)
            
            # Process each task
            for task_name, task_entries in hours_by_task.items():
                if task_entries:
                    try:
                        total_hours = sum(float(entry.get('actualHours', 0)) for entry in task_entries)
                        hourly_rate = float(task_entries[0].get('hourlyRate', 0))
                        
                        processed_entry = {
                            'projectId': project_id,
                            'projectName': task_entries[0].get('projectName', ''),
                            'projectTask': task_name,
                            'actualHours': total_hours,
                            'hourlyRate': hourly_rate,
                            'customer_info': customer_info
                        }
                        processed_entries.append(processed_entry)
                    except (ValueError, TypeError) as e:
                        logger.warning(
                            f"Failed to process task {task_name} for project {project_id}: {e}"
                        )
        
        # Log warnings for projects without hours
        if projects_without_hours:
            logger.warning(
                "No hours found for %d active projects:\n%s",
                len(projects_without_hours),
                "\n".join(projects_without_hours)
            )
        
        return processed_entries

    def _write_invoicing_summary(
        self,
        entries_by_customer: Dict[str, List[Dict[str, Any]]],
        result_file_path: Path,
        total_amount: float,
        total_hours: float,
        total_invoices: int,
        total_lines: int,
        first_day: Optional[datetime.date],
        last_day: Optional[datetime.date]
    ) -> None:
        """Write a summary of invoicing data.
        
        Parameters
        ----------
        entries_by_customer : Dict[str, List[Dict[str, Any]]]
            Dictionary of entries grouped by customer ID
        result_file_path : Path
            Path to the result file, used to determine summary file path
        total_amount : float
            Total amount across all invoices
        total_hours : float
            Total hours across all invoices
        total_invoices : int
            Total number of invoices
        total_lines : int
            Total number of invoice lines
        first_day : Optional[datetime.date]
            First day of hours
        last_day : Optional[datetime.date]
            Last day of hours
        """
        summary_file = result_file_path.with_stem(f"{result_file_path.stem}_summary")
        
        try:
            with open(summary_file, 'w', encoding='utf-8', newline='') as f:
                # Write customer details
                for customer_id, entries in entries_by_customer.items():
                    if not entries:
                        continue
                        
                    customer_info = entries[0]['customer_info']
                    client_name = customer_info.get('Client', 'Unknown')
                    
                    # Write customer/client header
                    f.write(f"Customer: {client_name}\n")
                    f.write("-" * 80 + "\n")
                    
                    # Group entries by service and task
                    service_task_entries: Dict[tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
                    for entry in entries:
                        service = entry['customer_info'].get('Service name', 'Unknown Service')
                        task = entry['projectTask']
                        service_task_entries[(service, task)].append(entry)
                    
                    # Calculate and write totals for each service/task combination
                    customer_total = 0.0
                    customer_lines = 0
                    for (service, task), task_entries in service_task_entries.items():
                        total_hours = sum(entry['actualHours'] for entry in task_entries)
                        # All entries in a task group should have the same rate
                        hour_rate = task_entries[0]['hourlyRate']
                        amount = total_hours * hour_rate
                        customer_total += amount
                        customer_lines += 1
                        
                        f.write(f"Service: {service}\n")
                        f.write(f"Task: {task}\n")
                        f.write(f"Hours: {self._format_decimal(total_hours)}\n")
                        f.write(f"Rate: {self._format_decimal(hour_rate)}\n")
                        f.write(f"Amount: {self._format_decimal(amount)}\n")
                        f.write("\n")
                    
                    # Write customer total and line count
                    f.write(f"Total for {client_name}: {self._format_decimal(customer_total)} ({customer_lines} lines)\n")
                    f.write("=" * 80 + "\n\n")
                
                # Write overall summary at the end
                f.write("\nOVERALL SUMMARY\n")
                f.write("=" * 80 + "\n")
                f.write(f"Total number of invoices: {total_invoices}\n")
                f.write(f"Total number of invoice lines: {total_lines}\n")
                f.write(f"Total amount across all invoices: {self._format_decimal(total_amount)}\n")
                if first_day and last_day:
                    f.write(f"First day of hours: {first_day.strftime('%Y-%m-%d')}\n")
                    f.write(f"Last day of hours: {last_day.strftime('%Y-%m-%d')}\n")
                f.write("=" * 80 + "\n")
                    
            logger.info("Wrote invoicing summary to %s", summary_file)
            logger.info(
                "Summary totals - Invoices: %d, Lines: %d, Amount: %.2f",
                total_invoices, total_lines, total_amount
            )
            if first_day and last_day:
                logger.info(
                    "Hours period - First day: %s, Last day: %s",
                    first_day.strftime('%Y-%m-%d'),
                    last_day.strftime('%Y-%m-%d')
                )
        except Exception as e:
            logger.error("Failed to write invoicing summary: %s", str(e))
            raise

    def _check_missing_orangit_projects(
        self,
        hours_by_project: Dict[str, List[Dict[str, Any]]],
        processed_entries: List[Dict[str, Any]],
        result_file_path: Path
    ) -> None:
        """Check for OrangIT Oy projects that are not included in the final result.
        
        Parameters
        ----------
        hours_by_project : Dict[str, List[Dict[str, Any]]]
            Dictionary of hour entries grouped by project ID
        processed_entries : List[Dict[str, Any]]
            List of processed entries that made it to the final result
        result_file_path : Path
            Path to the result file, used to determine the output path for missing projects
        """
        # Get set of project IDs that made it to the final result
        included_project_ids = {entry['projectId'] for entry in processed_entries}
        
        # Track missing projects
        missing_projects: List[Dict[str, Any]] = []
        
        # Check each project in raw hours
        for project_id, entries in hours_by_project.items():
            # Skip if project is already included
            if project_id in included_project_ids:
                continue
                
            # Check if any entries are from OrangIT Oy
            orangit_entries: List[Dict[str, Any]] = [
                entry for entry in entries
                if entry.get('employeeCompany', '').lower() == 'orangit oy'.lower()
                and entry.get('billable') == 'True'
            ]
            
            if orangit_entries:
                # Calculate total hours for this project
                total_hours = sum(float(entry.get('actualHours', 0)) for entry in orangit_entries)
                
                # Get project details from the first entry
                first_entry = orangit_entries[0]
                missing_projects.append({
                    'customerName': first_entry.get('customerName', 'Unknown'),
                    'projectName': first_entry.get('projectName', 'Unknown'),
                    'projectId': project_id,
                    'totalHours': total_hours
                })
                
                # Log warning
                logger.warning(
                    "OrangIT Oy project not included in result - Customer: %s, Project: %s (ID: %s), Total Hours: %.2f",
                    first_entry.get('customerName', 'Unknown'),
                    first_entry.get('projectName', 'Unknown'),
                    project_id,
                    total_hours
                )
        
        # Write missing projects to CSV if any found
        if missing_projects:
            missing_file = result_file_path.with_stem(f"{result_file_path.stem}_projects_not_included")
            with missing_file.open('w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=['customerName', 'projectName', 'projectId', 'totalHours'])
                writer.writeheader()
                for project in sorted(missing_projects, key=lambda x: (x['customerName'], x['projectName'])):
                    writer.writerow(project)
            logger.info("Wrote %d missing OrangIT Oy projects to %s", len(missing_projects), missing_file)

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
            Path to customer data CSV file (primary source)
        raw_hours_path : Path
            Path to raw hours CSV file
        rates_file_path : Path
            Path to rates CSV file with internal hour rates
        result_file_path : Path
            Path to write the result file
        """
        # Verify input files exist and are readable
        if not customer_data_path.is_file():
            raise ValueError(f"Customer data file not found: {customer_data_path}")
        if not raw_hours_path.is_file():
            raise ValueError(f"Raw hours file not found: {raw_hours_path}")
        if not rates_file_path.is_file():
            raise ValueError(f"Rates file not found: {rates_file_path}")

        try:
            # Load internal rates first
            internal_rates = self._load_internal_rates(rates_file_path)
            logger.info("Successfully loaded internal rates from %s", rates_file_path)
            
            # Read active customer data (primary source)
            customer_data = self._read_customer_data(customer_data_path)
            logger.info("Successfully read customer data from %s", customer_data_path)
            
            # Read and group raw hours
            hours_by_project = self._read_raw_hours(raw_hours_path)
            logger.info("Successfully read raw hours from %s", raw_hours_path)
            
            # Process hours for active customers
            processed_entries = []
            projects_without_hours = []
            
            # Track first and last day of hours
            first_day = None
            last_day = None
            
            # Process each active customer project
            for project_id, customer_info in customer_data.items():
                project_hours = hours_by_project.get(project_id, [])
                
                if not project_hours:
                    projects_without_hours.append(
                        f"Project: {customer_info.get('projectName', 'Unknown')} "
                        f"(ID: {project_id})"
                    )
                    continue
                
                # Filter hours based on included_hours setting
                included_hours = customer_info.get('included_hours', '').strip()
                filtered_hours = []
                logger.debug(
                    "Processing hours for project - Client: %s, Service: %s (ID: %s), included_hours: %s, total entries: %d",
                    customer_info.get('Client', 'Unknown'),
                    customer_info.get('Service name', 'Unknown Service'),
                    project_id,
                    included_hours,
                    len(project_hours)
                )
                
                for entry in project_hours:
                    if entry.get('billable') == 'True':  # Only process billable hours
                        # Track first and last day
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
                        
                        # If included_hours is 'All', include all billable hours
                        # If included_hours is 'Orangit', only include hours from Orangit Oy
                        if included_hours.lower() == 'all':
                            filtered_hours.append(entry)
                        elif included_hours.lower() == 'orangit':
                            employee_company = entry.get('employeeCompany', '')
                            logger.debug(
                                "Checking employee company: '%s' for entry with project task: %s",
                                employee_company,
                                entry.get('projectTask', '')
                            )
                            # Case-insensitive comparison for company name
                            if employee_company.lower() == 'orangit oy'.lower():
                                filtered_hours.append(entry)
                        else:
                            logger.warning(
                                "Unknown included_hours value '%s' for project - Client: %s, Service: %s (ID: %s)",
                                included_hours,
                                customer_info.get('Client', 'Unknown'),
                                customer_info.get('Service name', 'Unknown Service'),
                                project_id
                            )
                
                logger.debug(
                    "After filtering - Client: %s, Service: %s (ID: %s), included_hours: %s, filtered entries: %d",
                    customer_info.get('Client', 'Unknown'),
                    customer_info.get('Service name', 'Unknown Service'),
                    project_id,
                    included_hours,
                    len(filtered_hours)
                )
                
                if not filtered_hours:
                    logger.warning(
                        "No matching hours after filtering - Client: %s, Service: %s (ID: %s), included_hours: %s",
                        customer_info.get('Client', 'Unknown'),
                        customer_info.get('Service name', 'Unknown Service'),
                        project_id,
                        included_hours
                    )
                    continue
                
                # Group filtered hours by task
                hours_by_task: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
                for entry in filtered_hours:
                    task_name = entry.get('projectTask', '')
                    hours_by_task[task_name].append(entry)
                
                # Process each task
                for task_name, task_entries in hours_by_task.items():
                    if task_entries:
                        try:
                            total_hours = sum(float(entry.get('actualHours', 0)) for entry in task_entries)
                            # Get hourly rate using the new rate logic
                            hourly_rate = self._get_hour_rate(task_entries[0], project_id, customer_info, internal_rates)
                            
                            processed_entry = {
                                'projectId': project_id,
                                'projectName': task_entries[0].get('projectName', ''),
                                'projectTask': task_name,
                                'actualHours': total_hours,
                                'hourlyRate': hourly_rate,
                                'customer_info': customer_info,
                                'date': task_entries[0].get('date', '')  # Add date to processed entry
                            }
                            processed_entries.append(processed_entry)
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Failed to process task {task_name} for project {project_id}: {e}"
                            )
            
            logger.info("Processed %d billable entries for active customers", len(processed_entries))
            
            # Check for missing OrangIT Oy projects
            self._check_missing_orangit_projects(hours_by_project, processed_entries, result_file_path)
            
            # Calculate period dates
            today = datetime.date.today()
            # Calculate previous month
            if today.month == 1:
                period_start = datetime.date(today.year - 1, 12, 1)
                period_end = datetime.date(today.year, 1, 1) - datetime.timedelta(days=1)
            else:
                period_start = datetime.date(today.year, today.month - 1, 1)
                period_end = datetime.date(today.year, today.month, 1) - datetime.timedelta(days=1)

            # Ensure output directory exists
            result_file_path = Path(result_file_path).resolve()
            result_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Group entries by group invoice key (Group invoice or customer ID)
            groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
            group_to_customer_info: Dict[str, Dict[str, Any]] = {}
            for entry in processed_entries:
                customer_info = entry['customer_info']
                group_invoice = customer_info.get('Group invoice') or customer_info.get('Invoice Info A2 Ext Id', '')
                if group_invoice:
                    groups[group_invoice].append(entry)
                    # Always use the customer_info from the first entry in the group
                    if group_invoice not in group_to_customer_info:
                        group_to_customer_info[group_invoice] = customer_info

            # Generate output file
            temp_file = result_file_path.with_suffix('.tmp')
            try:
                # Initialize file content as a list of lines
                file_content = []
                total_amount = 0.0
                total_hours = 0.0
                header_count = 0
                detail_count = 0

                # Add the constant header lines
                file_content = [
                    "Invoice transfer into Workday;;;Company code:;263;;;Invoicing total;;;;;;;;;;;;;",
                    f"Title information/Row information;;;Reply-to-email:;{self.reply_email};;;0.00;;;;;;;;;;;;;",
                    "Row type H= Title;ConnectID;Invoice A2 ID;Account A2 ID;Free text;Accounting date[YYYY-MM-DD];Invoicing date[YYYY-MM-DD];Our reference;Customer reference;Period Start date [YYYY-MM-DD];Period End date [YYYY-MM-DD];Contract number;PO number;Appendix 1;Appendix 2;Appendix 3;Appendix 4;;;Source System;",
                    "Row type R= Row;ConnectID;Grouping info (Memo);Sales Item;Description;Quantity;Unit of measure;Unit price;Dim 1: Cost center;Dim 2: Business line (Function);Dim 3: Area;Dim 4: Service;Dim 5: Project;Dim 7: Counter company;Dim 8: Work type;Dim 10: Official;Dim 11: Employee;Dim 13: Company;Tax_Applicability;Tax_Code;"
                ]

                # Process each group (invoice)
                for group_key, entries in groups.items():
                    connect_id = str(uuid.uuid4())
                    customer_info = group_to_customer_info[group_key]
                    
                    # Collect non-zero rows first
                    invoice_rows = []
                    invoice_total = 0.0
                    
                    # Process each entry (already grouped by project and task)
                    for entry in entries:
                        task_hours = entry['actualHours']
                        hourly_rate = entry['hourlyRate']
                        task_amount = task_hours * hourly_rate
                        
                        # Skip rows with zero amount
                        if task_amount == 0:
                            logger.debug(
                                "Skipping zero amount row - Project: %s, Task: %s, Hours: %.2f, Rate: %.2f",
                                entry['projectName'],
                                entry['projectTask'],
                                task_hours,
                                hourly_rate
                            )
                            continue
                            
                        total_amount += task_amount
                        total_hours += task_hours
                        detail_count += 1
                        invoice_total += task_amount

                        logger.info(
                            "Project: %s, Task: %s, Hours: %.2f, Rate: %.2f, Amount: %.2f",
                            entry['projectName'],
                            entry['projectTask'],
                            task_hours,
                            hourly_rate,
                            task_amount
                        )

                        description = (
                            f"{entry['projectName']} - "
                            f"{customer_info.get('Billable Description', '')} - "
                            f"{entry['projectTask']}"
                        )
                        detail_row = [
                            "R", connect_id, entry['projectName'],
                            customer_info.get('Sales Item hours', ''),
                            description, self._format_decimal(task_hours), "",
                            self._format_decimal(hourly_rate),
                            self.dimensions['cost_center'],
                            self.dimensions['business_line'],
                            self.dimensions['area'],
                            self.dimensions['service'],
                            "", "", "", "", "", "",
                            customer_info.get('Tax_Applicability', ''),
                            customer_info.get('Tax_Code', ''),
                            ""
                        ]
                        invoice_rows.append(";".join(detail_row))

                    # Only write invoice if it has non-zero rows
                    if invoice_rows:
                        header_count += 1
                        # Add header row (always use customer_info fields, not group key)
                        header_row = [
                            "H", connect_id, customer_info.get('Invoice Info A2 Ext Id', ''),
                            customer_info.get('Account A2 Ext ID', ''), "",
                            datetime.date(today.year, today.month, 1).strftime("%Y-%m-%d"),  # Accounting date: 1st of current month
                            today.strftime("%Y-%m-%d"),
                            customer_info.get('Our Reference', ''),
                            customer_info.get('CUSTOMER_REFERENCE', ''),
                            period_start.strftime("%Y-%m-%d"),  # Period Start: 1st of previous month
                            period_end.strftime("%Y-%m-%d"),    # Period End: last day of previous month
                            customer_info.get('Contract number', ''),
                            "", "", "", "", "", "", "",
                            self.source_system, ""
                        ]
                        file_content.append(";".join(header_row))
                        
                        # Add all non-zero rows
                        file_content.extend(invoice_rows)
                    else:
                        logger.info(
                            "Skipping invoice for group %s - no non-zero amount rows",
                            group_key
                        )

                # Log summary before writing file
                logger.info(f"\nSummary:")
                logger.info(f"Number of invoices (H rows): {header_count}")
                logger.info(f"Number of invoice rows (R rows): {detail_count}")
                logger.info(f"Total hours: {total_hours:.2f}")
                logger.info(f"Total amount: {total_amount:.2f}")
                if first_day and last_day:
                    logger.info(f"Hours period - First day: {first_day.strftime('%Y-%m-%d')}, Last day: {last_day.strftime('%Y-%m-%d')}")

                # Now that we have the total, update the second line
                file_content[1] = f"Title information/Row information;;;Reply-to-email:;{self.reply_email};;;{self._format_decimal(total_amount)};;;;;;;;;;;;;"

                # Write all content to file
                with open(temp_file, mode='w', encoding='cp1252', errors='replace', newline='') as f:
                    f.write("\n".join(file_content))

                # Write the invoicing summary with the same totals
                self._write_invoicing_summary(groups, result_file_path, total_amount, total_hours, header_count, detail_count, first_day, last_day)

                # Rename temp file to final file
                temp_file.replace(result_file_path)
                logger.info(f"\nSuccessfully wrote result file: {result_file_path}")

            except Exception as e:
                logger.error("Failed to write result file: %s", str(e))
                if temp_file.exists():
                    temp_file.unlink()
                raise
        except Exception as e:
            logger.error("Failed to process data: %s", str(e))
            raise

    def _load_internal_rates(self, rates_file_path: Path) -> Dict[tuple[str, str], float]:
        """Load internal rates from CSV file.
        
        Parameters
        ----------
        rates_file_path : Path
            Path to rates CSV file containing project ID, task name, and rate
            
        Returns
        -------
        Dict[tuple[str, str], float]
            Dictionary mapping (project_id, task_name) to hourly rate
        """
        internal_rates: Dict[tuple[str, str], float] = {}
        
        with rates_file_path.open('r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if len(row) >= 3:  # Ensure we have all required columns
                    try:
                        project_id = row[0].strip()
                        task_name = row[1].strip()
                        rate = float(row[2].strip())
                        internal_rates[(project_id, task_name)] = rate
                        logger.debug(
                            "Loaded internal rate %.2f for project %s, task %s",
                            rate, project_id, task_name
                        )
                    except (ValueError, IndexError) as e:
                        logger.warning(
                            "Failed to parse rate from row %s: %s",
                            row, str(e)
                        )
                        
        logger.info("Loaded %d internal rates", len(internal_rates))
        return internal_rates

    def _get_hour_rate(
        self,
        entry: Dict[str, Any],
        project_id: str,
        customer_info: Dict[str, Any],
        internal_rates: Dict[tuple[str, str], float]
    ) -> float:
        """Get the appropriate hour rate based on customer settings.
        
        Parameters
        ----------
        entry : Dict[str, Any]
            Time entry data
        project_id : str
            Project ID
        customer_info : Dict[str, Any]
            Customer information
        internal_rates : Dict[tuple[str, str], float]
            Dictionary of internal rates by project ID and task
            
        Returns
        -------
        float
            Hour rate to use
        """
        hour_rates_type = customer_info.get('hour_rates', '').lower().strip()
        task_name = entry.get('projectTask', '')
        client_name = customer_info.get('Client', 'Unknown')
        service_name = customer_info.get('Service name', 'Unknown Service')
        
        if hour_rates_type == 'internal':
            # Try to get rate from internal rates
            rate = internal_rates.get((project_id, task_name))
            if rate is not None:
                return rate
            
            # If not found, log warning and write to missing_from_rates.txt
            warning_msg = (
                f"Internal rate not found - Client: {client_name}, "
                f"Service: {service_name}, Task: {task_name}, "
                f"Project ID: {project_id}"
            )
            logger.warning(warning_msg)
            
            # Write to missing_from_rates.txt
            try:
                with open('missing_from_rates.txt', 'a') as f:
                    f.write(f"{warning_msg}\n")
            except Exception as e:
                logger.error(f"Failed to write to missing_from_rates.txt: {e}")
        
        # Use AgileDay rate from taskHourlyPrice
        task_rate = entry.get('taskHourlyPrice', '')
        try:
            if task_rate and task_rate != '':
                return float(task_rate)
            else:
                warning_msg = (
                    f"No hourly rate found - Client: {client_name}, "
                    f"Service: {service_name}, Task: {task_name}, "
                    f"Project ID: {project_id}"
                )
                logger.warning(warning_msg)
                
                # Write to missing_from_rates.txt if it's an internal rate case
                if hour_rates_type == 'internal':
                    try:
                        with open('missing_from_rates.txt', 'a') as f:
                            f.write(f"{warning_msg}\n")
                    except Exception as e:
                        logger.error(f"Failed to write to missing_from_rates.txt: {e}")
                return 0.0
        except (ValueError, TypeError) as e:
            warning_msg = (
                f"Invalid hourly rate - Client: {client_name}, "
                f"Service: {service_name}, Task: {task_name}, "
                f"Project ID: {project_id}, Error: {e}"
            )
            logger.warning(warning_msg)
            
            # Write to missing_from_rates.txt if it's an internal rate case
            if hour_rates_type == 'internal':
                try:
                    with open('missing_from_rates.txt', 'a') as f:
                        f.write(f"{warning_msg}\n")
                except Exception as e:
                    logger.error(f"Failed to write to missing_from_rates.txt: {e}")
            return 0.0
