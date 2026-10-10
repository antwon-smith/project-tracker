import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app, APPDATA_DIR, DB_PATH, run_migrations

client = TestClient(app)

def test_startup_and_migrations():
    run_migrations()
    assert DB_PATH.exists()
    assert DB_PATH.stat().st_size > 0

def test_serve_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "Hitachi Project Tracker" in response.text
    assert "Command Center" in response.text
    assert "tailwind.min.css" in response.text

def test_static_assets():
    res_css = client.get("/static/css/tailwind.min.css")
    assert res_css.status_code == 200
    res_custom = client.get("/static/css/custom.css")
    assert res_custom.status_code == 200
    res_js = client.get("/static/js/app.js")
    assert res_js.status_code == 200
    res_font = client.get("/static/fonts/Inter-Regular.woff2")
    assert res_font.status_code == 200

def test_system_info():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert "appdata_dir" in data
    assert "db_path" in data
    assert data["db_version"] == 1

def test_get_projects():
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert isinstance(projects, list)
    assert len(projects) > 0
    proj = projects[0]
    assert "Name" in proj
    assert "Contractor_Name" in proj
    assert "Status" in proj
    assert "Progress_Percentage" in proj

def test_create_and_manage_project():
    # 1. Create Project
    payload = {
        "Name": "HVDC Converter Test Rig",
        "Contractor_Name": "Hitachi Engineering",
        "Status": "Active",
        "Notes": "Testing converter firing angle valves",
    }
    res_create = client.post("/api/projects", json=payload)
    assert res_create.status_code == 201
    proj_id = res_create.json()["ID"]

    # 2. Get details
    res_details = client.get(f"/api/projects/{proj_id}")
    assert res_details.status_code == 200
    p_data = res_details.json()
    assert p_data["Name"] == "HVDC Converter Test Rig"
    assert "Project_Manager_Name" in p_data
    assert "Contractor_Lead_Name" in p_data
    assert len(p_data["Phases"]) >= 1
    phase_id = p_data["Phases"][0]["ID"]

    # Update Project with PM and Contractor Lead info
    res_update_proj = client.put(f"/api/projects/{proj_id}", json={
        "Project_Manager_Name": "Jane Doe",
        "Project_Manager_Email": "jane.doe@example.com",
        "Contractor_Lead_Name": "Bob Smith",
        "Contractor_Lead_Phone": "+1 (555) 123-4567",
    })
    assert res_update_proj.status_code == 200

    # Verify updated contacts in details
    res_details2 = client.get(f"/api/projects/{proj_id}")
    assert res_details2.json()["Project_Manager_Name"] == "Jane Doe"
    assert res_details2.json()["Project_Manager_Email"] == "jane.doe@example.com"
    assert res_details2.json()["Contractor_Lead_Name"] == "Bob Smith"
    assert res_details2.json()["Contractor_Lead_Phone"] == "+1 (555) 123-4567"

    # Update Phase Notes
    res_phase_notes = client.put(f"/api/phases/{phase_id}", json={
        "Phase_Name": p_data["Phases"][0]["Phase_Name"],
        "Notes": "Safety lockout completed and verified by site safety engineer.",
    })
    assert res_phase_notes.status_code == 200

    # 3. Add Step with Details
    res_step = client.post(f"/api/phases/{phase_id}/steps", json={
        "Step_Name": "Calibrate Rogowski Coils",
        "Details": "Inspect coil sensitivity at 60Hz and log output mV.",
    })
    assert res_step.status_code == 201
    step_id = res_step.json()["ID"]
    assert res_step.json()["Details"] == "Inspect coil sensitivity at 60Hz and log output mV."

    # Update Step Details via PUT
    res_step_update = client.put(f"/api/steps/{step_id}", json={
        "Step_Name": "Calibrate Rogowski Coils (Primary & Secondary)",
        "Details": "Updated calibration spec: 100mV/kA target.",
    })
    assert res_step_update.status_code == 200
    assert res_step_update.json()["Step_Name"] == "Calibrate Rogowski Coils (Primary & Secondary)"
    assert res_step_update.json()["Details"] == "Updated calibration spec: 100mV/kA target."

    # Verify phase notes and step details persisted
    res_details3 = client.get(f"/api/projects/{proj_id}")
    p3 = res_details3.json()
    assert p3["Phases"][0]["Notes"] == "Safety lockout completed and verified by site safety engineer."
    found_step = next(s for s in p3["Phases"][0]["Steps"] if s["ID"] == step_id)
    assert found_step["Details"] == "Updated calibration spec: 100mV/kA target."

    # 4. Rename Phase and verify its steps are preserved
    res_rename = client.put(f"/api/phases/{phase_id}", json={
        "Phase_Name": "Phase 1: Mobilization, Lockout & Rogowski Testing"
    })
    assert res_rename.status_code == 200
    assert res_rename.json()["Phase_Name"] == "Phase 1: Mobilization, Lockout & Rogowski Testing"

    # Verify project details shows new phase name and steps are still present
    res_details4 = client.get(f"/api/projects/{proj_id}")
    p4 = res_details4.json()
    assert p4["Phases"][0]["Phase_Name"] == "Phase 1: Mobilization, Lockout & Rogowski Testing"
    assert any(s["ID"] == step_id for s in p4["Phases"][0]["Steps"])

    # 4. Toggle Step
    res_toggle = client.patch(f"/api/steps/{step_id}", json={"Is_Completed": True})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["Is_Completed"] is True

    # 5. Add Field Update
    res_update = client.post(f"/api/projects/{proj_id}/updates", json={"Note_Text": "Rogowski coil calibration completed on Phase A."})
    assert res_update.status_code == 201

    # 6. Log Time
    res_time = client.post(f"/api/projects/{proj_id}/time-logs", json={
        "Start_Time": "08:00",
        "End_Time": "12:30",
        "Hours_Logged": 4.5,
        "Description": "Sensor calibration and fiber tests",
    })
    assert res_time.status_code == 201

    # 7. Upload Attachment
    dummy_content = b"Hitachi SCADA Telemetry Log File Content\nStatus: OK\n"
    files = {"file": ("scada_test.txt", dummy_content, "text/plain")}
    res_upload = client.post(f"/api/projects/{proj_id}/attachments", files=files)
    assert res_upload.status_code == 201
    att_id = res_upload.json()["ID"]

    # Download attachment
    res_download = client.get(f"/api/attachments/{att_id}/download")
    assert res_download.status_code == 200
    assert res_download.content == dummy_content

    # 8. Check End of Shift Summary
    res_summary = client.get("/api/end-of-shift/summary")
    assert res_summary.status_code == 200
    summary = res_summary.json()
    assert summary["has_unreported_items"] is True
    assert summary["total_hours"] >= 4.5
    assert any(s["ID"] == step_id for s in summary["steps"])
    assert any(a["ID"] == att_id for a in summary["attachments"])

    # Test End of Shift HTML email preview endpoint
    res_preview = client.get("/api/end-of-shift/preview")
    assert res_preview.status_code == 200
    assert "text/html" in res_preview.headers.get("content-type", "")
    assert "End of Shift Report" in res_preview.text
    assert "Hitachi Energy" in res_preview.text
    assert "IT/OT Operations" in res_preview.text
    assert "Calibri" in res_preview.text

    # Test filtering End of Shift Summary by specific project_id
    res_filtered_summary = client.get(f"/api/end-of-shift/summary?project_ids={proj_id}")
    assert res_filtered_summary.status_code == 200
    f_summary = res_filtered_summary.json()
    assert len(f_summary["projects_overview"]) == 1
    assert f_summary["projects_overview"][0]["ID"] == proj_id

    # Test filtering End of Shift Preview by specific project_id
    res_filtered_preview = client.get(f"/api/end-of-shift/preview?project_ids={proj_id}")
    assert res_filtered_preview.status_code == 200
    assert "HVDC Converter Test Rig" in res_filtered_preview.text
    assert "Jane Doe" in res_filtered_preview.text

    # Test End of Shift EML download
    import email
    res_eml = client.get(f"/api/end-of-shift/eml?project_ids={proj_id}")
    assert res_eml.status_code == 200
    assert "message/rfc822" in res_eml.headers.get("content-type", "")
    parsed_msg = email.message_from_bytes(res_eml.content)
    assert "Hitachi End of Shift Report" in parsed_msg["Subject"]
    assert "HVDC Converter Test Rig" in parsed_msg["Subject"]

    # Test End of Shift POST trigger endpoint with project_ids filter
    from unittest.mock import MagicMock, patch
    mock_outlook = MagicMock()
    mock_mail = MagicMock()
    mock_outlook.CreateItem.return_value = mock_mail

    with patch("win32com.client.Dispatch", return_value=mock_outlook):
        res_trigger = client.post("/api/end-of-shift", json={"project_ids": [proj_id]})
    assert res_trigger.status_code == 200
    trigger_data = res_trigger.json()
    assert trigger_data["success"] is True
    assert "Classic Outlook draft generated successfully" in trigger_data["message"]
    mock_mail.Display.assert_called_once_with(False)

    # Test Mark Reported endpoint
    res_mark = client.post("/api/end-of-shift/mark-reported", json={"project_ids": [proj_id]})
    assert res_mark.status_code == 200
    assert res_mark.json()["success"] is True

    # 9. Clean up created test project
    res_delete = client.delete(f"/api/projects/{proj_id}")
    assert res_delete.status_code == 200


def test_user_management_and_attribution():
    # 1. Get users (should have seeded default user)
    res_users = client.get("/api/users")
    assert res_users.status_code == 200
    users = res_users.json()
    assert len(users) >= 1

    # 2. Create a new team member
    user_payload = {
        "Name": "Alex Rivers",
        "Email": "alex.rivers@hitachienergy.com",
        "Role": "Lead Systems Engineer",
    }
    res_create = client.post("/api/users", json=user_payload)
    assert res_create.status_code == 201
    created_user = res_create.json()
    u_id = created_user["ID"]
    assert created_user["Name"] == "Alex Rivers"
    assert created_user["Email"] == "alex.rivers@hitachienergy.com"

    # 3. Test End of Shift preview with user attribution
    res_preview = client.get(f"/api/end-of-shift/preview?user_id={u_id}")
    assert res_preview.status_code == 200
    assert "Alex Rivers" in res_preview.text
    assert "alex.rivers@hitachienergy.com" in res_preview.text
    assert "Report Prepared By:" in res_preview.text

    # 4. Delete / deactivate the user
    res_del = client.delete(f"/api/users/{u_id}")
    assert res_del.status_code == 200

    # 5. Verify user is no longer listed in active users
    res_after = client.get("/api/users")
    active_ids = [u["ID"] for u in res_after.json()]
    assert u_id not in active_ids
