"""
AppSheet API Client Library with Automatic OAuth User Delegation (RunAsUserEmail).
Built with standard library urllib for zero-dependency portability.
"""

import json
import os
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Union, Any, Optional

class AppSheet:
    def __init__(
        self,
        app_id: Optional[str] = None,
        access_key: Optional[str] = None,
        appsheet_region: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        self.app_id = app_id or os.environ.get("APPSHEET_APP_ID", "")
        self.access_key = access_key or os.environ.get("APPSHEET_ACCESS_KEY", "")
        self.appsheet_region = (
            appsheet_region 
            or os.environ.get("APPSHEET_REGION", "www.appsheet.com")
        ).strip()
        self.user_email = user_email

        if not self.app_id or not self.access_key:
            raise ValueError("APPSHEET_APP_ID and APPSHEET_ACCESS_KEY must be provided or set in environment variables.")

        self.base_url = f"https://{self.appsheet_region}/api/v2/apps/{self.app_id}/tables"

    def set_user_email(self, user_email: str) -> None:
        self.user_email = user_email

    def _prepare_request(
        self, 
        table_name: str, 
        action: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None
    ) -> Dict:
        merged_properties = properties.copy() if properties else {}

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
        params = self._prepare_request(table_name, "Add", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def delete(
        self, 
        table_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        params = self._prepare_request(table_name, "Delete", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def edit(
        self, 
        table_name: str, 
        rows: List[Dict], 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
        params = self._prepare_request(table_name, "Edit", rows, properties)
        return params if defer_execution else self._execute_request(params)

    def find(
        self, 
        table_name: str, 
        rows: Optional[List[Dict]] = None, 
        properties: Optional[Dict] = None, 
        defer_execution: bool = False
    ) -> Union[Dict, Any]:
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
        params = self._prepare_request(table_name, action_name, rows, properties)
        return params if defer_execution else self._execute_request(params)
