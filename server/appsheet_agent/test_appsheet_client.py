from appsheet_client import AppSheet

def test_run_as_user_email_injection():
    client = AppSheet(
        app_id="test-app-123",
        access_key="test-key-abc",
        appsheet_region="eu.appsheet.com",
        user_email="alice@example.com"
    )

    # Test URL formatting with region
    assert client.base_url == "https://eu.appsheet.com/api/v2/apps/test-app-123/tables"

    # Test deferred find request parameters
    req = client.find("Tasks", defer_execution=True)
    assert req["url"] == "https://eu.appsheet.com/api/v2/apps/test-app-123/tables/Tasks/Action"
    assert req["headers"]["ApplicationAccessKey"] == "test-key-abc"
    assert req["json"]["Action"] == "Find"
    assert req["json"]["Properties"]["RunAsUserEmail"] == "alice@example.com"

    # Test deferred add request parameters
    req_add = client.add("Tasks", rows=[{"Title": "Test Task"}], defer_execution=True)
    assert req_add["json"]["Action"] == "Add"
    assert req_add["json"]["Properties"]["RunAsUserEmail"] == "alice@example.com"
    assert req_add["json"]["Rows"] == [{"Title": "Test Task"}]

if __name__ == "__main__":
    test_run_as_user_email_injection()
    print("✅ All unit tests passed successfully!")
