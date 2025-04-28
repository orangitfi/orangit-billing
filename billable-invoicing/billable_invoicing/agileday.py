"""AgileDay API client for fetching time entries."""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

class AgileDayClient:
    """Client for interacting with the AgileDay API."""
    
    def __init__(self):
        """Initialize the AgileDay API client using token from environment variable."""
        self.api_url = "https://sevendos.agileday.io/api/v1"
        self.api_key = os.getenv("AGILEDAY_TOKEN")
        if not self.api_key:
            raise ValueError("AGILEDAY_TOKEN environment variable is not set")
        
        # Remove any whitespace from token
        self.api_key = self.api_key.strip()
        
        # Store masked version of token for logging
        self.masked_token = f"{self.api_key[:4]}...{self.api_key[-4:]}" if len(self.api_key) > 8 else "***"
        logger.debug("Using API token: %s", self.masked_token)
        
        # Initialize session with headers
        self.session = requests.Session()
        auth_header = f"Bearer {self.api_key}"
        logger.debug("Authorization header format: %s", auth_header.replace(self.api_key, self.masked_token))
        
        self.session.headers.update({
            "Authorization": auth_header,
            "Accept": "application/json",
            "User-Agent": "billable_invoicing/0.1.0"
        })
        
        # Cache for project data
        self._project_cache: Dict[str, Dict[str, Any]] = {}
    
    def _mask_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Mask sensitive information in headers for logging."""
        return {
            k: v.replace(self.api_key, self.masked_token) if k == 'Authorization' else v
            for k, v in headers.items()
        }
    
    def get_time_entries(
        self,
        start_date: datetime,
        end_date: datetime,
        status: str = "Submitted"
    ) -> List[Dict[str, Any]]:
        """
        Fetch time entries from AgileDay.
        
        Parameters
        ----------
        start_date : datetime
            Start date for time entries
        end_date : datetime
            End date for time entries
        status : str, optional
            Status of entries to fetch, defaults to "Submitted"
            
        Returns
        -------
        List[Dict[str, Any]]
            List of time entries matching the criteria
        """
        url = f'{self.api_url}/time_reporting'
        params = {
            'startDate': start_date.strftime('%Y-%m-%d'),
            'endDate': end_date.strftime('%Y-%m-%d'),
            'status': status
        }
        
        logger.info(
            "Fetching time entries between %s and %s with status %s",
            start_date.date(),
            end_date.date(),
            status
        )
        logger.debug("Making GET request to %s with params %s", url, params)
        logger.debug("Request headers: %s", self._mask_headers(dict(self.session.headers)))
        
        try:
            response = self.session.get(url, params=params)
            if response.status_code == 404:
                logger.error(
                    "API endpoint not found. Response: %s",
                    response.text
                )
            elif response.status_code == 401:
                logger.error(
                    "Authentication failed. Please check your AGILEDAY_TOKEN. Response: %s",
                    response.text
                )
            response.raise_for_status()
            
            entries = response.json()
            logger.debug("Retrieved %d time entries", len(entries))
            
            return entries
        except requests.exceptions.RequestException as e:
            logger.error(
                "API request failed: %s\nResponse: %s\nRequest URL: %s\nRequest Headers: %s",
                str(e),
                e.response.text if hasattr(e, 'response') and e.response else 'No response',
                url,
                self._mask_headers(dict(self.session.headers))
            )
            raise
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch project details from AgileDay, with caching.
        
        Parameters
        ----------
        project_id : str
            ID of the project to fetch
            
        Returns
        -------
        Dict[str, Any]
            Project details
        """
        if project_id not in self._project_cache:
            url = f'{self.api_url}/project/id/{project_id}'
            logger.debug("Fetching project details from %s", url)
            
            response = self.session.get(url)
            response.raise_for_status()
            self._project_cache[project_id] = response.json()
        
        return self._project_cache[project_id] 