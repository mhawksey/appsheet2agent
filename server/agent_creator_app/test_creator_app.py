import os
from app.openapi_parser import AppSheetOpenAPIParser
from app.ard_generator import ARDGenerator

def test_openapi_parser():
    sample_spec_path = "/Users/mhawksey/Documents/Antigravity Agents/Docs/openapi.json"
    if not os.path.exists(sample_spec_path):
        print(f"Skipping test, sample file not found at {sample_spec_path}")
        return

    parser = AppSheetOpenAPIParser.from_file(sample_spec_path)
    tables = parser.get_tables()
    app_id = parser.get_app_id()

    assert app_id == "40c823df-3005-4dea-9d32-2197837ce3e7"
    assert "Facilities" in tables
    assert "Staff" in tables
    assert "Inspections" in tables

    print(f"✅ Parser Test Passed! Extracted {len(tables)} tables ({', '.join(tables.keys())}) for App ID '{app_id}'.")

def test_ard_generator():
    tables = {
        "Facilities": {"actions": [{"action": "Find"}, {"action": "Add"}]},
        "Staff": {"actions": [{"action": "Find"}]}
    }

    gen = ARDGenerator(
        agent_id="test-agent",
        display_name="Facility Inspections Agent",
        description="Test description",
        appsheet_app_id="40c823df-3005-4dea-9d32-2197837ce3e7",
        service_url="https://test-agent-service.a.run.app",
        tables=tables,
        capabilities=[{"table": "Staff", "action": "Find"}]
    )

    ard_spec = gen.generate_ard_spec()
    payload = gen.generate_gemini_enterprise_admin_payload()

    assert ard_spec["ardVersion"] == "1.0"
    assert ard_spec["transport"]["endpoint"] == "https://test-agent-service.a.run.app/a2a"
    assert len(ard_spec["capabilities"]) == 1
    assert payload["name"] == "test-agent"
    assert payload["url"] == "https://test-agent-service.a.run.app"
    assert len(payload["skills"]) == 1
    assert payload["skills"][0]["id"] == "staff"
    assert payload["skills"][0]["tags"] == ["staff"]

    print("✅ ARD Generator Test Passed! Validated ARD spec and Gemini Enterprise payload structure.")

def test_specialist_fallback():
    from app.specialist_agent import SpecialistAgentArchitect
    
    tables = {
        "Users": {},
        "Plans": {},
        "Tasks": {}
    }
    
    specialist = SpecialistAgentArchitect(parsed_tables=tables)
    
    # Simulating the user dialog
    res = specialist._run_rule_based_simulator(
        creator_prompt="I would like to list users and tasks",
        user_email="martin.hawksey@devoteam.com",
        app_id="f173ba32-3f56-4167-b2b6-6d5213896fa8",
        active_capabilities=[]
    )
    
    caps = res.get("capabilities", [])
    print(f"Detected capabilities: {caps}")
    assert len(caps) == 2, "Failed to extract multiple capabilities!"
    assert any(c["table"] == "Users" and c["action"] == "Find" for c in caps), "Missing Users capability!"
    assert any(c["table"] == "Tasks" and c["action"] == "Find" for c in caps), "Missing Tasks capability!"
    print("✅ Fallback Specialist Simulator Test Passed!")

if __name__ == "__main__":
    test_openapi_parser()
    test_ard_generator()
    test_specialist_fallback()
    print("🎉 All Agent Creator Web App tests passed!")
