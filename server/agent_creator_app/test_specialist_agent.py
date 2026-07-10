from app.specialist_agent import SpecialistAgentArchitect

def test_specialist_2phase_workflow():
    tables = {
        "Facilities": {"schema": {"columns": {"Facility ID": {"type": "string"}, "Facility Name": {"type": "string"}}}},
        "Inspections": {"schema": {"columns": {"InspectionID": {"type": "string"}, "Comments": {"type": "string"}}}},
        "Staff": {"schema": {"columns": {"Staff ID": {"type": "string"}}}},
        "Inspection Points": {"schema": {"columns": {"Point ID": {"type": "string"}}}}
    }

    specialist = SpecialistAgentArchitect(parsed_tables=tables)

    # Turn 1: Conversational Requirement Gathering (Phase 1)
    turn1 = specialist.process_creator_dialogue(
        creator_prompt="I would like users to record inspections and query facilities",
        user_email="martin.hawksey@devoteam.com",
        app_id="40c823df-3005-4dea-9d32-2197837ce3e7"
    )

    assert turn1["is_plan_proposal"] is False
    assert len(turn1["capabilities"]) >= 2
    assert "Record Inspections" in turn1["response_text"] or "Add Inspections" in turn1["response_text"]
    assert "Facilities" in turn1["response_text"]

    # Turn 2: User Says "I am ready" (Phase 2 - Agent Implementation Plan Proposal)
    turn2 = specialist.process_creator_dialogue(
        creator_prompt="I am ready",
        user_email="martin.hawksey@devoteam.com",
        app_id="40c823df-3005-4dea-9d32-2197837ce3e7",
        active_capabilities=turn1["capabilities"]
    )

    assert turn2["is_plan_proposal"] is True
    assert "Proposed Agent Implementation Plan" in turn2["response_text"]
    assert len(turn2["a2ui_commands"]) >= 2  # A2UI card commands for both Inspections and Facilities
    assert "add_inspections" in turn2["generated_tool_code"]
    assert "find_facilities" in turn2["generated_tool_code"]

    print("✅ 2-Phase Specialist Agent Workflow Unit Test Passed Successfully!")

if __name__ == "__main__":
    test_specialist_2phase_workflow()
