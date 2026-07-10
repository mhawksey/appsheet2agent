"""
AppSheet API Client Library with Automatic OAuth User Delegation (RunAsUserEmail).

This client is designed for use in A2A agents where AppSheet API calls must be executed
on behalf of the authenticated user. Built with standard library urllib for zero-dependency portability.

AI ASSISTANT GUIDE:
-------------------
To use this client in your agent:
1. Instantiate AppSheet(app_id, access_key, appsheet_region, user_email).
2. The client automatically injects 'RunAsUserEmail': user_email into the Properties dict
   for all API actions (Add, Delete, Edit, Find, Action).
"""

import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Union, Any, Optional

class AppSheet:
    """
    AppSheet API Client for Python with automatic RunAsUserEmail support.
    """

    def __init__(
        self,
        app_id: Optional[str] = None,
        access_key: Optional[str] = None,
        appsheet_region: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        """
        Initialize the AppSheet API client.

        Args:
            app_id (str, optional): AppSheet App ID. Defaults to APPSHEET_APP_ID env var.
            access_key (str, optional): AppSheet Application Access Key. Defaults to APPSHEET_ACCESS_KEY env var.
            appsheet_region (str, optional): Region domain (e.g. www.appsheet.com, eu.appsheet.com). 
                                            Defaults to APPSHEET_REGION env var or 'www.appsheet.com'.
            user_email (str, optional): User email extracted from OAuth token for RunAsUserEmail injection.
        """
        self.app_id = app_id or os.environ.get("APPSHEET_APP_ID", "")
        self.access_key = access_key or os.environ.get("APPSHEET_ACCESS_KEY", "")
        self.appsheet_region = (
            appsheet_region 
            or os.environ.get("APPSHEET_REGION", "www.appsheet.com")
        ).strip()
        self.user_email = user_email

        if not self.app_id or not self.access_key:
            raise ValueError("APPSHEET_APP_ID and APPSHEET_ACCESS_KEY must be provided or set in environment variables.")

        # Construct region-aware base URL
        self.base_url = f"https://{self.appsheet_region}/api/v2/apps/{self.app_id}/tables"

    def set_user_email(self, user_email: str) -> None:
        """Dynamically set or update the user email for RunAsUserEmail property."""
        self.user_email = user_email

    def _prepare_request(
        self, 
        table_name: str, 
        action: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None
    ) -> Dict:
        """
        Construct the request headers, payload, and URL for AppSheet API.
        Automatically merges RunAsUserEmail if user_email is present.
        """
        merged_properties = properties.copy() if properties else {}

        # Automatically inject RunAsUserEmail from OAuth user identity if not explicitly overridden
        if self.user_email and "RunAsUserEmail" not in merged_properties:
            merged_properties["RunAsUserEmail"] = self.user_email

        return {
            "url": f"{self.base_url}/{table_name}/Action",
            "headers": {
                'ApplicationAccessKey': self.access_key,
                'Content-Type': 'application/json'
            },
            "json": {
                "Action": action,
                "Rows": rows,
                "Properties": merged_properties
            }
        }

    def _execute_request(self, request_params: Dict) -> Dict:
        """Execute the HTTP POST request to AppSheet API."""
        try:
            payload_bytes = json.dumps(request_params['json']).encode('utf-8')
            req = urllib.request.Request(
                url=request_params['url'],
                data=payload_bytes,
                headers=request_params['headers'],
                method='POST'
            )
            with urllib.request.urlopen(req) as response:
                body = response.read().decode('utf-8')
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            error_text = e.read().decode('utf-8', errors='replace') if hasattr(e, 'read') else str(e)
            return {"error": f"HTTP {e.code}: {e.reason}", "details": error_text}
        except Exception as e:
            return {"error": str(e), "details": "No response text"}

    def add(
        self, 
        table_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        """Add records to an AppSheet table."""
        params = self._prepare_request(table_name, "Add", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def delete(
        self, 
        table_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        """Delete records from an AppSheet table."""
        params = self._prepare_request(table_name, "Delete", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def edit(
        self, 
        table_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        """Update existing records in an AppSheet table."""
        params = self._prepare_request(table_name, "Edit", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def find(
        self, 
        table_name: str, 
        rows: Optional[List[Dict]] = None, 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        """Read records from an AppSheet table."""
        rows_to_send = rows if rows is not None else []
        params = self._prepare_request(table_name, "Find", rows_to_send, properties)
        return params if defer_execution else self._execute_request(params)

    def action(
        self, 
        table_name: str, 
        action_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        """Invoke a custom AppSheet action on a table."""
        params = self._prepare_request(table_name, action_name, rows, properties)
        return params if defer_execution else self._execute_request(params)

    @staticmethod
    def fetch_all(request_params_list: List[Dict], max_workers: int = 5) -> List[Dict]:
        """Executes multiple deferred requests in parallel."""
        def _worker(params):
            try:
                payload_bytes = json.dumps(params['json']).encode('utf-8')
                req = urllib.request.Request(
                    url=params['url'],
                    data=payload_bytes,
                    headers=params['headers'],
                    method='POST'
                )
                with urllib.request.urlopen(req) as response:
                    body = response.read().decode('utf-8')
                    return json.loads(body) if body else {}
            except Exception as e:
                return {"error": str(e)}

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(_worker, request_params_list))
