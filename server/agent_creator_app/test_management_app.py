from app.management_client import ManagementAppClient

def test_management_app_client():
    client = ManagementAppClient(user_email="alice@company.com")
    assert client.client.app_id == "c61d70ac-1a98-4c36-b735-593f6eeb60b3"
    assert client.client.access_key == "V2-32Uho-ogHZw-PhFb5-PxefX-pBAis-cJsES-BeiUA-u9IAw"

    # Test deferred request parameters for saving an agent with Base64 Data URI file upload
    openapi_sample = '{"openapi": "3.0.4", "info": {"title": "Test App"}}'
    req = client.client.add(
        table_name="Agents",
        rows=[{
            "app_id": "test-app-456",
            "appsheet_key": "test-key-789",
            "owner": "alice@company.com",
            "openapi_json": "data:application/json;base64,eyJvcGVuYXBpIjogIjMuMC40In0=",
            "status": "Draft"
        }],
        defer_execution=True
    )

    assert req["url"] == "https://www.appsheet.com/api/v2/apps/c61d70ac-1a98-4c36-b735-593f6eeb60b3/tables/Agents/Action"
    assert req["json"]["Action"] == "Add"
    assert req["json"]["Properties"]["RunAsUserEmail"] == "alice@company.com"
    assert req["json"]["Rows"][0]["app_id"] == "test-app-456"

    print("✅ Management App Client Integration Test Passed successfully!")

if __name__ == "__main__":
    test_management_app_client()
