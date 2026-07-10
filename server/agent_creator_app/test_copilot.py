from app.antigravity_copilot import AntigravityCopilotEngine

def test_copilot_inspection_form_generation():
    tables = {
        "Inspections": {
            "schema": {
                "columns": {
                    "InspectionID": {"type": "string", "required": True},
                    "Facility ID": {"type": "string", "required": True},
                    "Inspection Point ID": {"type": "string", "required": True},
                    "Comments": {"type": "string", "required": False},
                    "Status": {"type": "string", "required": False}
                }
            }
        },
        "Facilities": {
            "schema": {
                "columns": {
                    "Facility ID": {"type": "string", "required": True},
                    "Facility Name": {"type": "string", "required": True}
                }
            }
        }
    }

    engine = AntigravityCopilotEngine(parsed_tables=tables)
    result = engine.process_request(
        user_prompt="Can I submit an inspection?",
        user_email="martin.hawksey@devoteam.com",
        app_id="40c823df-3005-4dea-9d32-2197837ce3e7"
    )

    assert result["matched_table"] == "Inspections"
    assert result["matched_action"] == "Add"
    assert "Inspections" in result["response_text"]
    assert len(result["a2ui_commands"]) == 2
    assert "add_inspections" in result["generated_tool_code"]
    assert "@tool" in result["generated_tool_code"]

    print("✅ Antigravity Copilot Inspection Form Test Passed Successfully!")

if __name__ == "__main__":
    test_copilot_inspection_form_generation()
