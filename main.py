import os
import sys
import copy
import html
import re
import shutil
import sqlite3
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# ---------------------------------------------------------------------------
# WINDOWS --NOCONSOLE SAFE STREAMS INITIALIZATION
# ---------------------------------------------------------------------------
# In PyInstaller --noconsole / GUI mode, Windows leaves sys.stdout, sys.stderr,
# and sys.stdin as None. This causes uvicorn's ColourizedFormatter to crash with:
#   AttributeError: 'NoneType' object has no attribute 'isatty'
class SafeStream:
    """Safe stream proxy for GUI / --noconsole environments."""
    def __init__(self, log_filepath=None):
        self.log_filepath = log_filepath

    def write(self, s):
        if self.log_filepath and s:
            try:
                with open(self.log_filepath, "a", encoding="utf-8") as f:
                    f.write(s)
            except Exception:
                pass

    def flush(self):
        pass

    def isatty(self):
        return False


base_appdata_init = os.environ.get("APPDATA")
if base_appdata_init:
    init_appdata_dir = Path(base_appdata_init) / "ContractorApp"
else:
    init_appdata_dir = Path.home() / "AppData" / "Roaming" / "ContractorApp"
init_appdata_dir.mkdir(parents=True, exist_ok=True)
_app_log_path = init_appdata_dir / "app.log"

if sys.stdout is None or not hasattr(sys.stdout, "isatty"):
    sys.stdout = SafeStream(_app_log_path)
if sys.stderr is None or not hasattr(sys.stderr, "isatty"):
    sys.stderr = SafeStream(_app_log_path)
if sys.stdin is None:
    sys.stdin = SafeStream()

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, status, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# PATH AND DATA VAULT RESOLUTION (%APPDATA%\ContractorApp)
# ---------------------------------------------------------------------------
def get_appdata_dir() -> Path:
    r"""
    Returns the %APPDATA%\ContractorApp directory.
    Ensures user data persists across .exe updates and replacements.
    """
    base_appdata = os.environ.get("APPDATA")
    if base_appdata:
        app_dir = Path(base_appdata) / "ContractorApp"
    else:
        app_dir = Path.home() / "AppData" / "Roaming" / "ContractorApp"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


APPDATA_DIR = get_appdata_dir()
DB_PATH = APPDATA_DIR / "projects.db"
ATTACHMENTS_DIR = APPDATA_DIR / "attachments"
BACKUPS_DIR = APPDATA_DIR / "backups"

ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# Determine base directory for static assets and templates (PyInstaller bundle safe)
if getattr(sys, "frozen", False):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).resolve().parent

STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

CURRENT_DB_VERSION = 1


# ---------------------------------------------------------------------------
# DATABASE INITIALIZATION AND MIGRATIONS
# ---------------------------------------------------------------------------
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def backup_database():
    """
    ALWAYS executes a shutil.copy2 backup of the .db file to a backup folder
    before applying any schema alterations.
    """
    if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUPS_DIR / f"projects_backup_{timestamp}.db"
        shutil.copy2(DB_PATH, backup_file)


def ensure_schema_columns(cursor: sqlite3.Cursor):
    """
    Safely adds new columns to existing SQLite tables if not already present.
    """
    # Projects columns
    cursor.execute("PRAGMA table_info(Projects);")
    proj_cols = [row[1] for row in cursor.fetchall()]
    for col, col_def in [
        ("Project_Manager_Name", "TEXT DEFAULT ''"),
        ("Project_Manager_Email", "TEXT DEFAULT ''"),
        ("Contractor_Lead_Name", "TEXT DEFAULT ''"),
        ("Contractor_Lead_Phone", "TEXT DEFAULT ''"),
    ]:
        if col not in proj_cols:
            cursor.execute(f"ALTER TABLE Projects ADD COLUMN {col} {col_def};")

    # Phases columns
    cursor.execute("PRAGMA table_info(Phases);")
    phase_cols = [row[1] for row in cursor.fetchall()]
    if "Notes" not in phase_cols:
        cursor.execute("ALTER TABLE Phases ADD COLUMN Notes TEXT DEFAULT '';")

    # Steps columns
    cursor.execute("PRAGMA table_info(Steps);")
    step_cols = [row[1] for row in cursor.fetchall()]
    if "Details" not in step_cols:
        cursor.execute("ALTER TABLE Steps ADD COLUMN Details TEXT DEFAULT '';")
    if "Completed_By" not in step_cols:
        cursor.execute("ALTER TABLE Steps ADD COLUMN Completed_By TEXT DEFAULT '';")

    # Updates columns
    cursor.execute("PRAGMA table_info(Updates);")
    update_cols = [row[1] for row in cursor.fetchall()]
    if "User_ID" not in update_cols:
        cursor.execute("ALTER TABLE Updates ADD COLUMN User_ID INTEGER DEFAULT NULL;")
    if "Author_Name" not in update_cols:
        cursor.execute("ALTER TABLE Updates ADD COLUMN Author_Name TEXT DEFAULT '';")

    # Time_Logs columns
    cursor.execute("PRAGMA table_info(Time_Logs);")
    tl_cols = [row[1] for row in cursor.fetchall()]
    if "User_ID" not in tl_cols:
        cursor.execute("ALTER TABLE Time_Logs ADD COLUMN User_ID INTEGER DEFAULT NULL;")
    if "Author_Name" not in tl_cols:
        cursor.execute("ALTER TABLE Time_Logs ADD COLUMN Author_Name TEXT DEFAULT '';")

    # Users table
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS Users (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Email TEXT DEFAULT '',
            Role TEXT DEFAULT 'Technician',
            Is_Active BOOLEAN NOT NULL DEFAULT 1,
            Created_At TEXT NOT NULL
        );
        """
    )
    cursor.execute("SELECT COUNT(*) FROM Users;")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Users (Name, Email, Role, Is_Active, Created_At) VALUES (?, ?, ?, 1, ?);",
            ("Lead Technician", "field.lead@hitachienergy.com", "Field Lead", now_str),
        )


def run_migrations():
    """
    Checks App_Settings table for DB_Version and executes required migrations safely.
    """
    with sqlite3.connect(str(DB_PATH)) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        cursor = conn.cursor()

        # Check if App_Settings table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='App_Settings';"
        )
        has_settings = cursor.fetchone() is not None

        db_version = 0
        if has_settings:
            cursor.execute("SELECT DB_Version FROM App_Settings LIMIT 1;")
            row = cursor.fetchone()
            if row:
                db_version = row[0]

        if db_version < CURRENT_DB_VERSION:
            # Backup database before any schema alterations
            backup_database()

            # Execute migration / initial creation
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS App_Settings (
                    DB_Version INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS Projects (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Name TEXT NOT NULL,
                    Contractor_Name TEXT NOT NULL,
                    Status TEXT NOT NULL CHECK(Status IN ('Active', 'Blocked', 'Completed')),
                    Notes TEXT,
                    Project_Manager_Name TEXT DEFAULT '',
                    Project_Manager_Email TEXT DEFAULT '',
                    Contractor_Lead_Name TEXT DEFAULT '',
                    Contractor_Lead_Phone TEXT DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS Phases (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Project_ID INTEGER NOT NULL,
                    Phase_Name TEXT NOT NULL,
                    Notes TEXT DEFAULT '',
                    FOREIGN KEY (Project_ID) REFERENCES Projects(ID) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS Steps (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Phase_ID INTEGER NOT NULL,
                    Step_Name TEXT NOT NULL,
                    Details TEXT DEFAULT '',
                    Is_Completed BOOLEAN NOT NULL DEFAULT 0,
                    Reported_Flag BOOLEAN NOT NULL DEFAULT 0,
                    Completed_At TEXT,
                    FOREIGN KEY (Phase_ID) REFERENCES Phases(ID) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS Time_Logs (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Project_ID INTEGER NOT NULL,
                    Start_Time TEXT NOT NULL,
                    End_Time TEXT NOT NULL,
                    Hours_Logged REAL NOT NULL,
                    Reported_Flag BOOLEAN NOT NULL DEFAULT 0,
                    Description TEXT,
                    Created_At TEXT NOT NULL,
                    FOREIGN KEY (Project_ID) REFERENCES Projects(ID) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS Updates (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Project_ID INTEGER NOT NULL,
                    Note_Text TEXT NOT NULL,
                    Timestamp TEXT NOT NULL,
                    Reported_Flag BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (Project_ID) REFERENCES Projects(ID) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS Attachments (
                    ID INTEGER PRIMARY KEY AUTOINCREMENT,
                    Project_ID INTEGER NOT NULL,
                    File_Name TEXT NOT NULL,
                    Local_Path TEXT NOT NULL,
                    File_Size INTEGER NOT NULL DEFAULT 0,
                    Uploaded_At TEXT NOT NULL,
                    Reported_Flag BOOLEAN NOT NULL DEFAULT 0,
                    FOREIGN KEY (Project_ID) REFERENCES Projects(ID) ON DELETE CASCADE
                );
                """
            )

            # Update DB_Version
            cursor.execute("DELETE FROM App_Settings;")
            cursor.execute("INSERT INTO App_Settings (DB_Version) VALUES (?);", (CURRENT_DB_VERSION,))
            conn.commit()

            # Seed sample project if empty
            cursor.execute("SELECT COUNT(*) FROM Projects;")
            if cursor.fetchone()[0] == 0:
                seed_initial_data(cursor)
                conn.commit()

        # Ensure new schema columns exist in existing databases
        ensure_schema_columns(cursor)
        conn.commit()


def seed_initial_data(cursor: sqlite3.Cursor):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        """
        INSERT INTO Projects (Name, Contractor_Name, Status, Notes)
        VALUES (?, ?, ?, ?);
        """,
        (
            "HVDC Converter Station - Control Automation",
            "Hitachi Energy Integration Team",
            "Active",
            "Mission-critical commissioning phase for primary converter control cabinets and fiber telemetry.",
        ),
    )
    project_id = cursor.lastrowid

    # Add Phases
    cursor.execute("INSERT INTO Phases (Project_ID, Phase_Name) VALUES (?, ?);", (project_id, "Phase 1: Pre-Commissioning & Safety Lockout"))
    p1_id = cursor.lastrowid
    cursor.execute("INSERT INTO Phases (Project_ID, Phase_Name) VALUES (?, ?);", (project_id, "Phase 2: Valve Base Electronics (VBE) Testing"))
    p2_id = cursor.lastrowid
    cursor.execute("INSERT INTO Phases (Project_ID, Phase_Name) VALUES (?, ?);", (project_id, "Phase 3: SCADA & RTU Telemetry Validation"))
    p3_id = cursor.lastrowid

    # Add Steps
    steps_p1 = [
        ("Verify LOTO (Lockout/Tagout) on 400kV bus isolators", 1, 1),
        ("Calibrate optical temperature sensors on thyristor stacks", 1, 1),
        ("Perform continuity test on grounding switch interlocks", 0, 0),
    ]
    for s_name, is_comp, rep in steps_p1:
        cursor.execute(
            "INSERT INTO Steps (Phase_ID, Step_Name, Is_Completed, Reported_Flag, Completed_At) VALUES (?, ?, ?, ?, ?);",
            (p1_id, s_name, is_comp, rep, now_str if is_comp else None),
        )

    steps_p2 = [
        ("Inject test pulses into VBE firing pulse transmitter units", 0, 0),
        ("Verify gate unit power supply redundancy", 0, 0),
        ("Conduct de-energized protection trip loop check", 0, 0),
    ]
    for s_name, is_comp, rep in steps_p2:
        cursor.execute(
            "INSERT INTO Steps (Phase_ID, Step_Name, Is_Completed, Reported_Flag, Completed_At) VALUES (?, ?, ?, ?, ?);",
            (p2_id, s_name, is_comp, rep, None),
        )

    steps_p3 = [
        ("Configure DNP3 communication channel to Regional Control Center", 0, 0),
        ("Execute live alarm acknowledgment test from Master HMI", 0, 0),
    ]
    for s_name, is_comp, rep in steps_p3:
        cursor.execute(
            "INSERT INTO Steps (Phase_ID, Step_Name, Is_Completed, Reported_Flag, Completed_At) VALUES (?, ?, ?, ?, ?);",
            (p3_id, s_name, is_comp, rep, None),
        )

    # Add initial update
    cursor.execute(
        """
        INSERT INTO Updates (Project_ID, Note_Text, Timestamp, Reported_Flag)
        VALUES (?, ?, ?, ?);
        """,
        (
            project_id,
            "Initial setup completed. Pre-commissioning safety checks underway with site engineering staff.",
            now_str,
            1,
        ),
    )


# ---------------------------------------------------------------------------
# FASTAPI APP CREATION & LIFECYCLE
# ---------------------------------------------------------------------------
app = FastAPI(title="Hitachi Project Tracker", version="1.0.0")

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def startup_event():
    run_migrations()


# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------
class ProjectCreate(BaseModel):
    Name: str
    Contractor_Name: str
    Status: str = "Active"
    Notes: Optional[str] = ""
    Project_Manager_Name: Optional[str] = ""
    Project_Manager_Email: Optional[str] = ""
    Contractor_Lead_Name: Optional[str] = ""
    Contractor_Lead_Phone: Optional[str] = ""


class ProjectUpdate(BaseModel):
    Name: Optional[str] = None
    Contractor_Name: Optional[str] = None
    Status: Optional[str] = None
    Notes: Optional[str] = None
    Project_Manager_Name: Optional[str] = None
    Project_Manager_Email: Optional[str] = None
    Contractor_Lead_Name: Optional[str] = None
    Contractor_Lead_Phone: Optional[str] = None


class PhaseCreate(BaseModel):
    Phase_Name: str
    Notes: Optional[str] = ""


class PhaseUpdate(BaseModel):
    Phase_Name: Optional[str] = None
    Notes: Optional[str] = None


class StepCreate(BaseModel):
    Step_Name: str
    Details: Optional[str] = ""


class StepUpdate(BaseModel):
    Step_Name: Optional[str] = None
    Details: Optional[str] = None


class UserCreate(BaseModel):
    Name: str
    Email: Optional[str] = ""
    Role: Optional[str] = "Technician"


class StepToggle(BaseModel):
    Is_Completed: bool
    Completed_By: Optional[str] = ""


class UpdateCreate(BaseModel):
    Note_Text: str
    User_ID: Optional[int] = None
    Author_Name: Optional[str] = ""


class TimeLogCreate(BaseModel):
    Start_Time: str
    End_Time: str
    Hours_Logged: float
    Description: Optional[str] = ""
    User_ID: Optional[int] = None
    Author_Name: Optional[str] = ""


# ---------------------------------------------------------------------------
# FRONTEND ROOT ROUTE
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_file))


@app.get("/api/system/info")
def get_system_info():
    """Returns local vault and storage paths for debugging/status display."""
    return {
        "appdata_dir": str(APPDATA_DIR),
        "db_path": str(DB_PATH),
        "attachments_dir": str(ATTACHMENTS_DIR),
        "backups_dir": str(BACKUPS_DIR),
        "db_version": CURRENT_DB_VERSION,
        "is_frozen": getattr(sys, "frozen", False),
    }


# ---------------------------------------------------------------------------
# PROJECTS API
# ---------------------------------------------------------------------------
@app.get("/api/projects")
def get_projects():
    """
    Returns list of all projects with dynamic step completion stats.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT p.ID, p.Name, p.Contractor_Name, p.Status, p.Notes,
                p.Project_Manager_Name, p.Project_Manager_Email, p.Contractor_Lead_Name, p.Contractor_Lead_Phone,
                COUNT(s.ID) as Total_Steps,
                COALESCE(SUM(CASE WHEN s.Is_Completed = 1 THEN 1 ELSE 0 END), 0) as Completed_Steps
            FROM Projects p
            LEFT JOIN Phases ph ON ph.Project_ID = p.ID
            LEFT JOIN Steps s ON s.Phase_ID = ph.ID
            GROUP BY p.ID
            ORDER BY p.ID DESC;
            """
        )
        rows = cursor.fetchall()
        projects = []
        for row in rows:
            total = row["Total_Steps"]
            completed = row["Completed_Steps"]
            percentage = round((completed / total * 100), 1) if total > 0 else 0
            projects.append({
                "ID": row["ID"],
                "Name": row["Name"],
                "Contractor_Name": row["Contractor_Name"],
                "Status": row["Status"],
                "Notes": row["Notes"] or "",
                "Project_Manager_Name": row["Project_Manager_Name"] or "",
                "Project_Manager_Email": row["Project_Manager_Email"] or "",
                "Contractor_Lead_Name": row["Contractor_Lead_Name"] or "",
                "Contractor_Lead_Phone": row["Contractor_Lead_Phone"] or "",
                "Total_Steps": total,
                "Completed_Steps": completed,
                "Progress_Percentage": percentage,
            })
        return projects


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate):
    valid_statuses = ("Active", "Blocked", "Completed")
    if payload.Status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Projects (Name, Contractor_Name, Status, Notes, Project_Manager_Name, Project_Manager_Email, Contractor_Lead_Name, Contractor_Lead_Phone)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                payload.Name.strip(),
                payload.Contractor_Name.strip(),
                payload.Status,
                payload.Notes or "",
                (payload.Project_Manager_Name or "").strip(),
                (payload.Project_Manager_Email or "").strip(),
                (payload.Contractor_Lead_Name or "").strip(),
                (payload.Contractor_Lead_Phone or "").strip(),
            ),
        )
        new_id = cursor.lastrowid
        # Create an initial default Phase for convenience
        cursor.execute("INSERT INTO Phases (Project_ID, Phase_Name, Notes) VALUES (?, ?, ?);", (new_id, "Phase 1: Mobilization & Planning", ""))
        conn.commit()

        return {"ID": new_id, "message": "Project created successfully"}


@app.get("/api/projects/{project_id}")
def get_project_details(project_id: int):
    """
    Returns comprehensive project details including Phases, Steps, Updates, Attachments, and Time Logs.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Project details
        cursor.execute("SELECT * FROM Projects WHERE ID = ?;", (project_id,))
        p = cursor.fetchone()
        if not p:
            raise HTTPException(status_code=404, detail="Project not found")

        # Phases and Steps
        cursor.execute("SELECT * FROM Phases WHERE Project_ID = ? ORDER BY ID ASC;", (project_id,))
        phases_rows = cursor.fetchall()

        phases = []
        total_steps = 0
        completed_steps = 0

        for ph in phases_rows:
            cursor.execute(
                "SELECT * FROM Steps WHERE Phase_ID = ? ORDER BY ID ASC;",
                (ph["ID"],),
            )
            step_rows = cursor.fetchall()
            steps = []
            for s in step_rows:
                is_comp = bool(s["Is_Completed"])
                total_steps += 1
                if is_comp:
                    completed_steps += 1
                steps.append({
                    "ID": s["ID"],
                    "Phase_ID": s["Phase_ID"],
                    "Step_Name": s["Step_Name"],
                    "Details": s["Details"] or "",
                    "Is_Completed": is_comp,
                    "Reported_Flag": bool(s["Reported_Flag"]),
                    "Completed_At": s["Completed_At"],
                    "Completed_By": s["Completed_By"] if "Completed_By" in s.keys() and s["Completed_By"] else "",
                })

            phases.append({
                "ID": ph["ID"],
                "Project_ID": ph["Project_ID"],
                "Phase_Name": ph["Phase_Name"],
                "Notes": ph["Notes"] or "",
                "Steps": steps,
            })

        # Updates
        cursor.execute("SELECT * FROM Updates WHERE Project_ID = ? ORDER BY ID DESC;", (project_id,))
        updates = [
            {
                "ID": u["ID"],
                "Project_ID": u["Project_ID"],
                "Note_Text": u["Note_Text"],
                "Timestamp": u["Timestamp"],
                "Reported_Flag": bool(u["Reported_Flag"]),
                "User_ID": u["User_ID"] if "User_ID" in u.keys() else None,
                "Author_Name": u["Author_Name"] if "Author_Name" in u.keys() and u["Author_Name"] else "",
            }
            for u in cursor.fetchall()
        ]

        # Attachments
        cursor.execute("SELECT * FROM Attachments WHERE Project_ID = ? ORDER BY ID DESC;", (project_id,))
        attachments = [
            {
                "ID": a["ID"],
                "Project_ID": a["Project_ID"],
                "File_Name": a["File_Name"],
                "Local_Path": a["Local_Path"],
                "File_Size": a["File_Size"],
                "Uploaded_At": a["Uploaded_At"],
                "Reported_Flag": bool(a["Reported_Flag"]),
            }
            for a in cursor.fetchall()
        ]

        # Time Logs
        cursor.execute("SELECT * FROM Time_Logs WHERE Project_ID = ? ORDER BY ID DESC;", (project_id,))
        time_logs = [
            {
                "ID": t["ID"],
                "Project_ID": t["Project_ID"],
                "Start_Time": t["Start_Time"],
                "End_Time": t["End_Time"],
                "Hours_Logged": t["Hours_Logged"],
                "Reported_Flag": bool(t["Reported_Flag"]),
                "Description": t["Description"] or "",
                "Created_At": t["Created_At"],
                "User_ID": t["User_ID"] if "User_ID" in t.keys() else None,
                "Author_Name": t["Author_Name"] if "Author_Name" in t.keys() and t["Author_Name"] else "",
            }
            for t in cursor.fetchall()
        ]

        progress_percentage = round((completed_steps / total_steps * 100), 1) if total_steps > 0 else 0
        total_hours = round(sum(tl["Hours_Logged"] for tl in time_logs), 2)

        return {
            "ID": p["ID"],
            "Name": p["Name"],
            "Contractor_Name": p["Contractor_Name"],
            "Status": p["Status"],
            "Notes": p["Notes"] or "",
            "Project_Manager_Name": p["Project_Manager_Name"] or "",
            "Project_Manager_Email": p["Project_Manager_Email"] or "",
            "Contractor_Lead_Name": p["Contractor_Lead_Name"] or "",
            "Contractor_Lead_Phone": p["Contractor_Lead_Phone"] or "",
            "Total_Steps": total_steps,
            "Completed_Steps": completed_steps,
            "Progress_Percentage": progress_percentage,
            "Total_Hours_Logged": total_hours,
            "Phases": phases,
            "Updates": updates,
            "Attachments": attachments,
            "Time_Logs": time_logs,
        }


@app.put("/api/projects/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Projects WHERE ID = ?;", (project_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Project not found")

        new_name = payload.Name if payload.Name is not None else existing["Name"]
        new_contractor = payload.Contractor_Name if payload.Contractor_Name is not None else existing["Contractor_Name"]
        new_status = payload.Status if payload.Status is not None else existing["Status"]
        new_notes = payload.Notes if payload.Notes is not None else existing["Notes"]
        new_pm_name = payload.Project_Manager_Name if payload.Project_Manager_Name is not None else existing["Project_Manager_Name"]
        new_pm_email = payload.Project_Manager_Email if payload.Project_Manager_Email is not None else existing["Project_Manager_Email"]
        new_lead_name = payload.Contractor_Lead_Name if payload.Contractor_Lead_Name is not None else existing["Contractor_Lead_Name"]
        new_lead_phone = payload.Contractor_Lead_Phone if payload.Contractor_Lead_Phone is not None else existing["Contractor_Lead_Phone"]

        cursor.execute(
            """
            UPDATE Projects
            SET Name = ?, Contractor_Name = ?, Status = ?, Notes = ?,
                Project_Manager_Name = ?, Project_Manager_Email = ?, Contractor_Lead_Name = ?, Contractor_Lead_Phone = ?
            WHERE ID = ?;
            """,
            (new_name, new_contractor, new_status, new_notes, new_pm_name, new_pm_email, new_lead_name, new_lead_phone, project_id),
        )
        conn.commit()
        return {"message": "Project updated successfully"}


@app.delete("/api/projects/{project_id}")
def delete_project(project_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Projects WHERE ID = ?;", (project_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Project not found")
        conn.commit()
        return {"message": "Project deleted successfully"}


# ---------------------------------------------------------------------------
# PHASES & STEPS API
# ---------------------------------------------------------------------------
@app.post("/api/projects/{project_id}/phases", status_code=status.HTTP_201_CREATED)
def add_phase(project_id: int, payload: PhaseCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Projects WHERE ID = ?;", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        cursor.execute(
            "INSERT INTO Phases (Project_ID, Phase_Name, Notes) VALUES (?, ?, ?);",
            (project_id, payload.Phase_Name.strip(), (payload.Notes or "").strip()),
        )
        new_phase_id = cursor.lastrowid
        conn.commit()
        return {"ID": new_phase_id, "Phase_Name": payload.Phase_Name.strip(), "Notes": payload.Notes or ""}


@app.put("/api/phases/{phase_id}")
def update_phase(phase_id: int, payload: PhaseUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Phases WHERE ID = ?;", (phase_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Phase not found")

        new_name = payload.Phase_Name.strip() if payload.Phase_Name is not None else existing["Phase_Name"]
        new_notes = payload.Notes.strip() if payload.Notes is not None else (existing["Notes"] or "")

        cursor.execute(
            "UPDATE Phases SET Phase_Name = ?, Notes = ? WHERE ID = ?;",
            (new_name, new_notes, phase_id),
        )
        conn.commit()
        return {"message": "Phase updated successfully", "ID": phase_id, "Phase_Name": new_name, "Notes": new_notes}


@app.delete("/api/phases/{phase_id}")
def delete_phase(phase_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Phases WHERE ID = ?;", (phase_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Phase not found")
        conn.commit()
        return {"message": "Phase deleted successfully"}


@app.post("/api/phases/{phase_id}/steps", status_code=status.HTTP_201_CREATED)
def add_step(phase_id: int, payload: StepCreate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Phases WHERE ID = ?;", (phase_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Phase not found")

        cursor.execute(
            """
            INSERT INTO Steps (Phase_ID, Step_Name, Details, Is_Completed, Reported_Flag, Completed_At)
            VALUES (?, ?, ?, 0, 0, NULL);
            """,
            (phase_id, payload.Step_Name.strip(), (payload.Details or "").strip()),
        )
        new_step_id = cursor.lastrowid
        conn.commit()
        return {
            "ID": new_step_id,
            "Phase_ID": phase_id,
            "Step_Name": payload.Step_Name.strip(),
            "Details": (payload.Details or "").strip(),
            "Is_Completed": False,
        }


@app.put("/api/steps/{step_id}")
def update_step(step_id: int, payload: StepUpdate):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Steps WHERE ID = ?;", (step_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Step not found")

        new_name = payload.Step_Name.strip() if payload.Step_Name is not None else existing["Step_Name"]
        new_details = payload.Details.strip() if payload.Details is not None else (existing["Details"] or "")

        cursor.execute(
            "UPDATE Steps SET Step_Name = ?, Details = ? WHERE ID = ?;",
            (new_name, new_details, step_id),
        )
        conn.commit()
        return {
            "message": "Step updated successfully",
            "ID": step_id,
            "Step_Name": new_name,
            "Details": new_details,
        }


@app.patch("/api/steps/{step_id}")
def toggle_step(step_id: int, payload: StepToggle):
    """
    Instantly updates step completion status. If completed, records completed_at and keeps reported_flag = 0
    until the End of Shift report is generated.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if payload.Is_Completed else None
    completed_by = payload.Completed_By.strip() if (payload.Is_Completed and payload.Completed_By) else ""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # When toggling to complete, reported_flag is reset to 0 so it gets included in the next shift report
        cursor.execute(
            """
            UPDATE Steps
            SET Is_Completed = ?,
                Completed_At = ?,
                Completed_By = ?,
                Reported_Flag = CASE WHEN ? = 1 THEN 0 ELSE Reported_Flag END
            WHERE ID = ?;
            """,
            (1 if payload.Is_Completed else 0, now_str, completed_by, 1 if payload.Is_Completed else 0, step_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Step not found")
        conn.commit()
        return {"ID": step_id, "Is_Completed": payload.Is_Completed, "Completed_At": now_str, "Completed_By": completed_by}


@app.delete("/api/steps/{step_id}")
def delete_step(step_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Steps WHERE ID = ?;", (step_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Step not found")
        conn.commit()
        return {"message": "Step deleted successfully"}


# ---------------------------------------------------------------------------
# UPDATES API
# ---------------------------------------------------------------------------
@app.post("/api/projects/{project_id}/updates", status_code=status.HTTP_201_CREATED)
def add_update(project_id: int, payload: UpdateCreate):
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Projects WHERE ID = ?;", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        author_name = payload.Author_Name.strip() if payload.Author_Name else ""
        cursor.execute(
            """
            INSERT INTO Updates (Project_ID, Note_Text, Timestamp, Reported_Flag, User_ID, Author_Name)
            VALUES (?, ?, ?, 0, ?, ?);
            """,
            (project_id, payload.Note_Text.strip(), timestamp_str, payload.User_ID, author_name),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return {
            "ID": new_id,
            "Project_ID": project_id,
            "Note_Text": payload.Note_Text.strip(),
            "Timestamp": timestamp_str,
            "Reported_Flag": False,
            "User_ID": payload.User_ID,
            "Author_Name": author_name,
        }


@app.delete("/api/updates/{update_id}")
def delete_update(update_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Updates WHERE ID = ?;", (update_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Update not found")
        conn.commit()
        return {"message": "Update deleted successfully"}


# ---------------------------------------------------------------------------
# ATTACHMENTS API
# ---------------------------------------------------------------------------
@app.post("/api/projects/{project_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(project_id: int, file: UploadFile = File(...)):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Projects WHERE ID = ?;", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

    # Sanitize file name and create unique path to avoid collisions
    timestamp_prefix = datetime.now().strftime("%Y%m%d_%H%M%S_")
    safe_name = Path(file.filename).name.replace(" ", "_")
    stored_filename = f"{timestamp_prefix}{safe_name}"
    target_path = ATTACHMENTS_DIR / stored_filename

    # Save file contents to %APPDATA%\ContractorApp\attachments
    size = 0
    with open(target_path, "wb") as buffer:
        while content := await file.read(1024 * 1024):  # 1MB chunks
            buffer.write(content)
            size += len(content)

    upload_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Save metadata in SQLite
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO Attachments (Project_ID, File_Name, Local_Path, File_Size, Uploaded_At, Reported_Flag)
            VALUES (?, ?, ?, ?, ?, 0);
            """,
            (project_id, file.filename, str(target_path), size, upload_timestamp),
        )
        new_id = cursor.lastrowid
        conn.commit()

        return {
            "ID": new_id,
            "Project_ID": project_id,
            "File_Name": file.filename,
            "Local_Path": str(target_path),
            "File_Size": size,
            "Uploaded_At": upload_timestamp,
            "Reported_Flag": False,
        }


@app.get("/api/attachments/{attachment_id}/open")
def open_attachment_locally(attachment_id: int):
    """
    Opens file locally using Windows default associated program.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Local_Path FROM Attachments WHERE ID = ?;", (attachment_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found")

        local_path = Path(row["Local_Path"])
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="Attachment file not found on disk")

        try:
            os.startfile(str(local_path))
            return {"message": "File opened in default viewer"}
        except Exception as e:
            return FileResponse(str(local_path), filename=local_path.name)


@app.get("/api/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Attachments WHERE ID = ?;", (attachment_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found")

        local_path = Path(row["Local_Path"])
        if not local_path.exists():
            raise HTTPException(status_code=404, detail="Attachment file not found on disk")

        return FileResponse(str(local_path), filename=row["File_Name"])


@app.delete("/api/attachments/{attachment_id}")
def delete_attachment(attachment_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT Local_Path FROM Attachments WHERE ID = ?;", (attachment_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Attachment not found")

        local_path = Path(row["Local_Path"])
        cursor.execute("DELETE FROM Attachments WHERE ID = ?;", (attachment_id,))
        conn.commit()

        if local_path.exists():
            try:
                local_path.unlink()
            except Exception:
                pass

        return {"message": "Attachment deleted successfully"}


# ---------------------------------------------------------------------------
# TIME LOGGING API
# ---------------------------------------------------------------------------
@app.post("/api/projects/{project_id}/time-logs", status_code=status.HTTP_201_CREATED)
def add_time_log(project_id: int, payload: TimeLogCreate):
    created_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID FROM Projects WHERE ID = ?;", (project_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Project not found")

        author_name = payload.Author_Name.strip() if payload.Author_Name else ""
        cursor.execute(
            """
            INSERT INTO Time_Logs (Project_ID, Start_Time, End_Time, Hours_Logged, Reported_Flag, Description, Created_At, User_ID, Author_Name)
            VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?);
            """,
            (
                project_id,
                payload.Start_Time.strip(),
                payload.End_Time.strip(),
                round(float(payload.Hours_Logged), 2),
                payload.Description.strip() if payload.Description else "",
                created_at_str,
                payload.User_ID,
                author_name,
            ),
        )
        new_id = cursor.lastrowid
        conn.commit()

        return {
            "ID": new_id,
            "Project_ID": project_id,
            "Start_Time": payload.Start_Time,
            "End_Time": payload.End_Time,
            "Hours_Logged": payload.Hours_Logged,
            "Description": payload.Description,
            "Reported_Flag": False,
            "Created_At": created_at_str,
            "User_ID": payload.User_ID,
            "Author_Name": author_name,
        }


@app.delete("/api/time-logs/{time_log_id}")
def delete_time_log(time_log_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Time_Logs WHERE ID = ?;", (time_log_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Time log not found")
        conn.commit()
        return {"message": "Time log deleted successfully"}


# ---------------------------------------------------------------------------
# USERS API
# ---------------------------------------------------------------------------
@app.get("/api/users")
def get_users():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ID, Name, Email, Role, Is_Active, Created_At FROM Users WHERE Is_Active = 1 ORDER BY Name ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate):
    name = payload.Name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="User name cannot be empty")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (Name, Email, Role, Is_Active, Created_At) VALUES (?, ?, ?, 1, ?);",
            (name, payload.Email.strip() if payload.Email else "", payload.Role.strip() if payload.Role else "Technician", now_str),
        )
        new_id = cursor.lastrowid
        conn.commit()
        return {
            "ID": new_id,
            "Name": name,
            "Email": payload.Email.strip() if payload.Email else "",
            "Role": payload.Role.strip() if payload.Role else "Technician",
            "Is_Active": 1,
            "Created_At": now_str,
        }


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users WHERE Is_Active = 1;")
        count = cursor.fetchone()[0]
        if count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last remaining active team member")

        cursor.execute("UPDATE Users SET Is_Active = 0 WHERE ID = ?;", (user_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="User not found")
        conn.commit()
        return {"message": "User deactivated successfully"}


# ---------------------------------------------------------------------------
# END OF SHIFT REPORT & OUTLOOK INTEGRATION
# ---------------------------------------------------------------------------
@app.get("/api/end-of-shift/summary")
def get_unreported_summary(project_ids: Optional[str] = None):
    """
    Gathers completed steps, time logs, updates, and attachments where Reported_Flag == 0.
    If project_ids is provided (e.g. "1,2"), filters strictly to those selected project IDs.
    """
    parsed_ids = None
    if project_ids:
        parsed_ids = [int(x.strip()) for x in str(project_ids).split(",") if x.strip().isdigit()]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Unreported completed steps
        steps_query = """
            SELECT s.ID, s.Step_Name, s.Details, s.Completed_At, s.Completed_By, ph.Phase_Name, p.Name as Project_Name, p.ID as Project_ID
            FROM Steps s
            JOIN Phases ph ON ph.ID = s.Phase_ID
            JOIN Projects p ON p.ID = ph.Project_ID
            WHERE s.Is_Completed = 1 AND s.Reported_Flag = 0
        """
        params_steps = []
        if parsed_ids:
            steps_query += f" AND p.ID IN ({','.join(['?']*len(parsed_ids))})"
            params_steps = list(parsed_ids)
        steps_query += " ORDER BY p.Name, ph.Phase_Name, s.ID;"
        cursor.execute(steps_query, params_steps)
        steps = [dict(row) for row in cursor.fetchall()]

        # Unreported Time Logs
        time_query = """
            SELECT t.ID, t.Start_Time, t.End_Time, t.Hours_Logged, t.Description, t.User_ID, t.Author_Name, p.Name as Project_Name, p.ID as Project_ID
            FROM Time_Logs t
            JOIN Projects p ON p.ID = t.Project_ID
            WHERE t.Reported_Flag = 0
        """
        params_time = []
        if parsed_ids:
            time_query += f" AND p.ID IN ({','.join(['?']*len(parsed_ids))})"
            params_time = list(parsed_ids)
        time_query += " ORDER BY t.ID DESC;"
        cursor.execute(time_query, params_time)
        time_logs = [dict(row) for row in cursor.fetchall()]
        total_hours = round(sum(tl["Hours_Logged"] for tl in time_logs), 2)

        # Unreported Updates
        updates_query = """
            SELECT u.ID, u.Note_Text, u.Timestamp, u.User_ID, u.Author_Name, p.Name as Project_Name, p.ID as Project_ID
            FROM Updates u
            JOIN Projects p ON p.ID = u.Project_ID
            WHERE u.Reported_Flag = 0
        """
        params_updates = []
        if parsed_ids:
            updates_query += f" AND p.ID IN ({','.join(['?']*len(parsed_ids))})"
            params_updates = list(parsed_ids)
        updates_query += " ORDER BY u.ID DESC;"
        cursor.execute(updates_query, params_updates)
        updates = [dict(row) for row in cursor.fetchall()]

        # Unreported Attachments
        att_query = """
            SELECT a.ID, a.File_Name, a.Local_Path, a.File_Size, a.Uploaded_At, p.Name as Project_Name, p.ID as Project_ID
            FROM Attachments a
            JOIN Projects p ON p.ID = a.Project_ID
            WHERE a.Reported_Flag = 0
        """
        params_att = []
        if parsed_ids:
            att_query += f" AND p.ID IN ({','.join(['?']*len(parsed_ids))})"
            params_att = list(parsed_ids)
        att_query += " ORDER BY a.ID DESC;"
        cursor.execute(att_query, params_att)
        attachments = [dict(row) for row in cursor.fetchall()]

        # Active projects overall status overview
        proj_query = """
            SELECT p.ID, p.Name, p.Contractor_Name, p.Status,
                p.Project_Manager_Name, p.Project_Manager_Email,
                p.Contractor_Lead_Name, p.Contractor_Lead_Phone,
                p.Notes as Project_Notes,
                COUNT(s.ID) as Total_Steps,
                COALESCE(SUM(CASE WHEN s.Is_Completed = 1 THEN 1 ELSE 0 END), 0) as Completed_Steps
            FROM Projects p
            LEFT JOIN Phases ph ON ph.Project_ID = p.ID
            LEFT JOIN Steps s ON s.Phase_ID = ph.ID
        """
        params_proj = []
        if parsed_ids:
            proj_query += f" WHERE p.ID IN ({','.join(['?']*len(parsed_ids))})"
            params_proj = list(parsed_ids)
        proj_query += " GROUP BY p.ID;"
        cursor.execute(proj_query, params_proj)

        projects_overview = []
        for p in cursor.fetchall():
            tot = p["Total_Steps"]
            comp = p["Completed_Steps"]
            pct = round((comp / tot * 100), 1) if tot > 0 else 0
            projects_overview.append({
                "ID": p["ID"],
                "Name": p["Name"],
                "Contractor_Name": p["Contractor_Name"],
                "Status": p["Status"],
                "Project_Manager_Name": p["Project_Manager_Name"] or "",
                "Project_Manager_Email": p["Project_Manager_Email"] or "",
                "Contractor_Lead_Name": p["Contractor_Lead_Name"] or "",
                "Contractor_Lead_Phone": p["Contractor_Lead_Phone"] or "",
                "Project_Notes": p["Project_Notes"] or "",
                "Progress_Percentage": pct,
                "Completed_Steps": comp,
                "Total_Steps": tot,
            })

        return {
            "steps": steps,
            "time_logs": time_logs,
            "total_hours": total_hours,
            "updates": updates,
            "attachments": attachments,
            "projects_overview": projects_overview,
            "has_unreported_items": bool(steps or time_logs or updates or attachments),
        }


def generate_outlook_email_html(summary_data: Dict[str, Any], shift_date_str: str, user_id: Optional[int] = None) -> str:
    """
    Constructs a bulletproof, 1999-style HTML table email template for Microsoft Outlook.
    Uses pure inline styles, standard table structures, and Calibri typography to guarantee
    flawless rendering under Microsoft Word's MSO email rendering engine.
    """
    user_info = None
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("SELECT ID, Name, Email, Role FROM Users WHERE ID = ?;", (user_id,))
            user_info = cursor.fetchone()
        if not user_info:
            cursor.execute("SELECT ID, Name, Email, Role FROM Users WHERE Is_Active = 1 ORDER BY ID ASC LIMIT 1;")
            user_info = cursor.fetchone()

    author_name = html.escape(str(user_info["Name"])) if user_info else "Lead Technician"
    author_email = html.escape(str(user_info["Email"])) if user_info and user_info["Email"] else ""
    author_role = html.escape(str(user_info["Role"])) if user_info and user_info["Role"] else "Technician"
    steps = summary_data.get("steps", [])
    time_logs = summary_data.get("time_logs", [])
    total_hours = summary_data.get("total_hours", 0)
    updates = summary_data.get("updates", [])
    attachments = summary_data.get("attachments", [])
    projects_overview = summary_data.get("projects_overview", [])

    # Project status & contacts cards
    project_cards_html = ""
    for p in projects_overview:
        p_name = html.escape(str(p.get("Name", "Unnamed Project")))
        p_contractor = html.escape(str(p.get("Contractor_Name", "Hitachi Field Team")))
        p_status = p.get("Status", "Active")
        status_bg = "#10b981" if p_status == "Active" else ("#f59e0b" if p_status == "Blocked" else "#64748b")
        pct = p.get("Progress_Percentage", 0)
        completed_steps = p.get("Completed_Steps", 0)
        total_steps = p.get("Total_Steps", 0)
        pm_name = html.escape(str(p.get("Project_Manager_Name", "") or "").strip())
        pm_email = html.escape(str(p.get("Project_Manager_Email", "") or "").strip())
        lead_name = html.escape(str(p.get("Contractor_Lead_Name", "") or "").strip())
        lead_phone = html.escape(str(p.get("Contractor_Lead_Phone", "") or "").strip())

        contacts_html = ""
        if pm_name or pm_email or lead_name or lead_phone:
            contact_parts = []
            if pm_name or pm_email:
                mail_str = f' &lt;<a href="mailto:{pm_email}" style="color: #4f46e5; text-decoration: underline;">{pm_email}</a>&gt;' if pm_email else ""
                contact_parts.append(f'<strong style="color: #475569;">Project Manager:</strong> {pm_name}{mail_str}')
            if lead_name or lead_phone:
                phone_str = f' &lt;<a href="tel:{lead_phone}" style="color: #0284c7; text-decoration: underline;">{lead_phone}</a>&gt;' if lead_phone else ""
                contact_parts.append(f'<strong style="color: #475569;">Contractor Lead:</strong> {lead_name}{phone_str}')
            contacts_html = f"""
            <tr>
              <td colspan="2" style="padding: 8px 12px; background-color: #f8fafc; font-size: 12px; color: #334155; border-top: 1px dashed #cbd5e1; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                {" &bull;&nbsp;&nbsp;".join(contact_parts)}
              </td>
            </tr>
            """

        pct_val = int(round(min(max(pct, 0), 100)))
        pct_remain = 100 - pct_val

        progress_bar_cells = ""
        if pct_val > 0:
            progress_bar_cells += f'<td width="{pct_val}%" style="background-color: #4f46e5; height: 8px;"></td>'
        if pct_remain > 0:
            progress_bar_cells += f'<td width="{pct_remain}%" style="background-color: #e2e8f0; height: 8px;"></td>'

        project_cards_html += f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; margin-bottom: 12px; background-color: #ffffff; border-collapse: collapse; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr style="background-color: #f8fafc;">
            <td style="padding: 10px 12px; font-weight: bold; font-size: 14px; color: #0f172a;">
              {p_name}
              <div style="font-size: 12px; font-weight: normal; color: #64748b; margin-top: 2px;">Contractor: {p_contractor}</div>
            </td>
            <td align="right" valign="top" style="padding: 10px 12px;">
              <span style="background-color: {status_bg}; color: #ffffff; padding: 3px 8px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                {p_status}
              </span>
            </td>
          </tr>
          <tr>
            <td colspan="2" style="padding: 10px 12px;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td style="font-size: 12px; font-weight: bold; color: #334155; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                    Completion Progress: <strong style="color: #4f46e5;">{pct}%</strong> ({completed_steps}/{total_steps} steps)
                  </td>
                </tr>
                <tr>
                  <td style="padding-top: 5px;">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #e2e8f0; height: 8px;">
                      <tr>
                        {progress_bar_cells}
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          {contacts_html}
        </table>
        """

    # Steps completed list (Tasks completed today)
    if steps:
        step_rows = []
        for s in steps:
            s_name = html.escape(str(s.get("Step_Name", "")))
            s_proj = html.escape(str(s.get("Project_Name", "")))
            s_phase = html.escape(str(s.get("Phase_Name", "")))
            s_details = html.escape(str(s.get("Details", "") or "")).strip()
            s_completed_by = html.escape(str(s.get("Completed_By", "") or "")).strip()
            by_str = f' &bull; Completed by: <strong>{s_completed_by}</strong>' if s_completed_by else ""
            details_html = (
                f'<div style="margin-top: 3px; font-size: 12px; color: #64748b; font-style: italic; padding-left: 8px; border-left: 2px solid #cbd5e1;">'
                f'Details: {s_details}</div>'
                if s_details
                else ""
            )
            step_rows.append(f"""
            <tr style="border-bottom: 1px solid #f1f5f9;">
              <td width="24" valign="top" style="padding: 8px 6px 8px 12px; font-size: 14px; color: #10b981; font-weight: bold;">
                &#10003;
              </td>
              <td valign="top" style="padding: 8px 12px 8px 0; font-size: 13px; color: #1e293b; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                <strong>{s_name}</strong>
                <div style="font-size: 11px; color: #64748b; margin-top: 2px;">
                  Project: <strong>{s_proj}</strong> &bull; Phase: {s_phase}{by_str}
                </div>
                {details_html}
              </td>
            </tr>
            """)
        steps_list_html = f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; border-collapse: collapse; background-color: #ffffff; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          {"".join(step_rows)}
        </table>
        """
    else:
        steps_list_html = """
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr>
            <td style="padding: 14px; font-size: 13px; color: #64748b; font-style: italic; text-align: center;">
              No specific steps marked complete during this shift period.
            </td>
          </tr>
        </table>
        """

    # Time logs table
    if time_logs:
        t_rows = []
        for t in time_logs:
            t_proj = html.escape(str(t.get("Project_Name", "")))
            t_start = html.escape(str(t.get("Start_Time", "")))
            t_end = html.escape(str(t.get("End_Time", "")))
            t_hours = t.get("Hours_Logged", 0)
            t_desc = html.escape(str(t.get("Description", "") or "General shift activities"))
            t_author = html.escape(str(t.get("Author_Name", "") or "")).strip()
            t_author_badge = f' <span style="color: #64748b; font-size: 11px;">({t_author})</span>' if t_author else ""
            t_rows.append(f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
              <td style="padding: 8px 10px; font-size: 12px; color: #0f172a; font-weight: bold;">{t_proj}</td>
              <td style="padding: 8px 10px; font-size: 12px; color: #475569;">{t_start} &ndash; {t_end}</td>
              <td style="padding: 8px 10px; font-size: 12px; color: #4f46e5; font-weight: bold;">{t_hours}h</td>
              <td style="padding: 8px 10px; font-size: 12px; color: #334155;">{t_desc}{t_author_badge}</td>
            </tr>
            """)
        time_table_html = f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; border-collapse: collapse; background-color: #ffffff; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr style="background-color: #f1f5f9; border-bottom: 2px solid #cbd5e1;">
            <th align="left" style="padding: 8px 10px; font-size: 12px; color: #475569;">Project</th>
            <th align="left" style="padding: 8px 10px; font-size: 12px; color: #475569;">Window</th>
            <th align="left" style="padding: 8px 10px; font-size: 12px; color: #475569;">Hours</th>
            <th align="left" style="padding: 8px 10px; font-size: 12px; color: #475569;">Activity Description</th>
          </tr>
          {"".join(t_rows)}
        </table>
        """
    else:
        time_table_html = """
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr>
            <td style="padding: 14px; font-size: 13px; color: #64748b; font-style: italic; text-align: center;">
              No shift hours recorded for this period.
            </td>
          </tr>
        </table>
        """

    # Field updates / Shift notes callouts
    if updates:
        u_boxes = []
        for u in updates:
            u_proj = html.escape(str(u.get("Project_Name", "")))
            u_time = html.escape(str(u.get("Timestamp", "")))
            u_text = html.escape(str(u.get("Note_Text", "")))
            u_author = html.escape(str(u.get("Author_Name", "") or "")).strip()
            u_author_badge = f' &bull; Logged by: <strong>{u_author}</strong>' if u_author else ""
            u_boxes.append(f"""
            <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #fffbeb; border-left: 4px solid #f59e0b; border-top: 1px solid #fef3c7; border-right: 1px solid #fef3c7; border-bottom: 1px solid #fef3c7; margin-bottom: 8px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
              <tr>
                <td style="padding: 10px 14px;">
                  <div style="font-size: 11px; font-weight: bold; color: #b45309; margin-bottom: 4px;">
                    {u_proj} &bull; {u_time}{u_author_badge}
                  </div>
                  <div style="font-size: 13px; color: #78350f; line-height: 1.45;">
                    {u_text}
                  </div>
                </td>
              </tr>
            </table>
            """)
        updates_callouts_html = "".join(u_boxes)
    else:
        updates_callouts_html = """
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr>
            <td style="padding: 14px; font-size: 13px; color: #64748b; font-style: italic; text-align: center;">
              No field notes posted during this shift.
            </td>
          </tr>
        </table>
        """

    # Attachments list
    if attachments:
        a_items = []
        for a in attachments:
            a_proj = html.escape(str(a.get("Project_Name", "")))
            a_file = html.escape(str(a.get("File_Name", "")))
            a_size_kb = round(a.get("File_Size", 0) / 1024, 1)
            a_items.append(f"""
            <li style="margin-bottom: 5px; font-size: 13px; color: #334155; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
              <strong>[{a_proj}]</strong> {a_file} <span style="color: #64748b;">({a_size_kb} KB)</span>
            </li>
            """)
        attachments_list_html = f"""
        <ul style="margin: 0; padding-left: 20px;">
          {"".join(a_items)}
        </ul>
        """
    else:
        attachments_list_html = """
        <div style="font-size: 13px; color: #64748b; font-style: italic; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          No files attached to this report.
        </div>
        """

    # Dynamic header title based on project selection
    if len(projects_overview) == 1:
        p0 = projects_overview[0]
        header_title = f"End of Shift Report &bull; {p0['Name']}"
        pm_sub = ""
        if p0.get("Project_Manager_Name"):
            pm_sub = f" &bull; PM: {p0['Project_Manager_Name']}"
            if p0.get("Project_Manager_Email"):
                pm_sub += f" &lt;{p0['Project_Manager_Email']}&gt;"
        header_subtitle = f"{shift_date_str}{pm_sub}"
    elif len(projects_overview) > 1:
        header_title = f"End of Shift Report &bull; Consolidated ({len(projects_overview)} Projects)"
        header_subtitle = f"{shift_date_str}"
    else:
        header_title = "End of Shift Report"
        header_subtitle = f"{shift_date_str}"

    if not projects_overview:
        project_cards_html = """
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="border: 1px solid #cbd5e1; background-color: #f8fafc; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          <tr>
            <td style="padding: 14px; font-size: 13px; color: #64748b; font-style: italic; text-align: center;">
              No projects were selected for this report.
            </td>
          </tr>
        </table>
        """

    # Assemble complete email document
    html_email = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Hitachi End of Shift Report</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f1f5f9; font-family: Calibri, 'Segoe UI', Arial, sans-serif; color: #1e293b; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f1f5f9; table-layout: fixed;">
    <tr>
      <td align="center" style="padding: 24px 12px;">
        <table border="0" cellpadding="0" cellspacing="0" width="640" style="width: 100%; max-width: 640px; background-color: #ffffff; border: 1px solid #cbd5e1; border-collapse: collapse; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
          
          <!-- BRAND HEADER -->
          <tr>
            <td style="background-color: #0f172a; padding: 22px 24px; border-bottom: 4px solid #4f46e5;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td valign="middle">
                    <div style="font-size: 11px; font-weight: bold; color: #818cf8; text-transform: uppercase; letter-spacing: 1px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">Hitachi Energy &bull; IT/OT Operations</div>
                    <div style="font-size: 20px; font-weight: bold; color: #ffffff; margin-top: 3px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{header_title}</div>
                    <div style="font-size: 12px; color: #cbd5e1; margin-top: 5px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                      Report Prepared By: <strong style="color: #ffffff;">{author_name}</strong> {f'({author_role})' if author_role else ''}{f' &bull; <a href=\"mailto:{author_email}\" style=\"color: #a5b4fc; text-decoration: none;\">{author_email}</a>' if author_email else ''}
                    </div>
                  </td>
                  <td align="right" valign="top">
                    <div style="font-size: 12px; color: #94a3b8; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{header_subtitle}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- KPI SUMMARY GRID (4 EQUAL COLUMNS) -->
          <tr>
            <td style="padding: 16px 24px; background-color: #f8fafc; border-bottom: 1px solid #e2e8f0;">
              <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                  <td align="center" width="25%" style="padding: 8px; border-right: 1px solid #e2e8f0;">
                    <div style="font-size: 22px; font-weight: bold; color: #0f172a; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{total_hours}<span style="font-size: 13px; font-weight: normal; color: #64748b;">h</span></div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold; margin-top: 2px;">Hours Logged</div>
                  </td>
                  <td align="center" width="25%" style="padding: 8px; border-right: 1px solid #e2e8f0;">
                    <div style="font-size: 22px; font-weight: bold; color: #10b981; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{len(steps)}</div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold; margin-top: 2px;">Tasks Done</div>
                  </td>
                  <td align="center" width="25%" style="padding: 8px; border-right: 1px solid #e2e8f0;">
                    <div style="font-size: 22px; font-weight: bold; color: #4f46e5; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{len(updates)}</div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold; margin-top: 2px;">Shift Notes</div>
                  </td>
                  <td align="center" width="25%" style="padding: 8px;">
                    <div style="font-size: 22px; font-weight: bold; color: #0284c7; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">{len(attachments)}</div>
                    <div style="font-size: 11px; color: #64748b; text-transform: uppercase; font-weight: bold; margin-top: 2px;">Attachments</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- SECTION 1: PROJECT HEALTH & CONTACTS -->
          <tr>
            <td style="padding: 20px 24px 10px 24px;">
              <div style="font-size: 14px; font-weight: bold; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                1. Project Status &amp; Progress
              </div>
              {project_cards_html}
            </td>
          </tr>

          <!-- SECTION 2: TASKS COMPLETED TODAY -->
          <tr>
            <td style="padding: 10px 24px;">
              <div style="font-size: 14px; font-weight: bold; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                2. Tasks Completed Today
              </div>
              {steps_list_html}
            </td>
          </tr>

          <!-- SECTION 3: TIME LOGS -->
          <tr>
            <td style="padding: 16px 24px 10px 24px;">
              <div style="font-size: 14px; font-weight: bold; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                3. Shift Time Tracking
              </div>
              {time_table_html}
            </td>
          </tr>

          <!-- SECTION 4: SHIFT NOTES / FIELD UPDATES -->
          <tr>
            <td style="padding: 16px 24px 10px 24px;">
              <div style="font-size: 14px; font-weight: bold; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                4. Field Notes &amp; Observations
              </div>
              {updates_callouts_html}
            </td>
          </tr>

          <!-- SECTION 5: ATTACHMENTS -->
          <tr>
            <td style="padding: 16px 24px 20px 24px;">
              <div style="font-size: 14px; font-weight: bold; color: #0f172a; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin-bottom: 12px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
                5. Attached Documentation
              </div>
              {attachments_list_html}
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="background-color: #f8fafc; border-top: 1px solid #e2e8f0; padding: 14px 24px; text-align: center; color: #94a3b8; font-size: 11px; font-family: Calibri, 'Segoe UI', Arial, sans-serif;">
              Report Prepared by {author_name} &bull; Generated by Hitachi Project Tracker Command Center
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""
    return html_email


class EndOfShiftRequest(BaseModel):
    project_ids: Optional[List[int]] = None
    user_id: Optional[int] = None


@app.get("/api/end-of-shift/preview", response_class=HTMLResponse)
def preview_end_of_shift_email(project_ids: Optional[str] = None, user_id: Optional[int] = None):
    """
    Renders the exact End of Shift HTML email in the browser for remote layout testing.
    If project_ids is provided (e.g. ?project_ids=1,2), includes only those selected projects.
    """
    summary = get_unreported_summary(project_ids=project_ids)
    shift_date_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    html_content = generate_outlook_email_html(summary, shift_date_str, user_id=user_id)
    return HTMLResponse(content=html_content)


@app.post("/api/end-of-shift")
def trigger_end_of_shift_report(payload: Optional[EndOfShiftRequest] = None):
    """
    Generates the End of Shift report for selected project(s) and launches
    a new draft directly in Microsoft Outlook desktop client via COM.
    Leaves the draft open on screen for contractor review before sending.
    Upon successful draft creation, marks included records as Reported_Flag = 1.
    """
    p_ids_str = None
    u_id = None
    if payload:
        if payload.project_ids:
            p_ids_str = ",".join(str(i) for i in payload.project_ids)
        u_id = payload.user_id

    summary = get_unreported_summary(project_ids=p_ids_str)
    steps = summary["steps"]
    time_logs = summary["time_logs"]
    updates = summary["updates"]
    attachments = summary["attachments"]

    shift_date_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    html_body = generate_outlook_email_html(summary, shift_date_str, user_id=u_id)

    # Initialize COM and dispatch Outlook
    outlook_launched = False
    error_message = None

    try:
        import win32com.client
        import pythoncom

        pythoncom.CoInitialize()
        try:
            outlook = win32com.client.Dispatch("Outlook.Application")
            # Create mail item (0 = olMailItem)
            mail = outlook.CreateItem(0)

            # Determine subject based on single vs multi project
            projects = summary.get("projects_overview", [])
            if len(projects) > 1:
                mail.Subject = f"Hitachi End of Shift Report - Consolidated ({len(projects)} Projects) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            elif len(projects) == 1:
                proj_name = projects[0].get("Name", "Project")
                mail.Subject = f"Hitachi End of Shift Report: {proj_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            else:
                mail.Subject = f"Hitachi End of Shift Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            mail.HTMLBody = html_body

            # Attach unreported files directly to the draft
            for att in attachments:
                local_file_path = att.get("Local_Path")
                if local_file_path and os.path.exists(local_file_path):
                    mail.Attachments.Add(os.path.abspath(local_file_path))

            # Display the draft on the screen for review (does NOT auto-send, leaves draft open)
            mail.Display(False)
            try:
                inspector = mail.GetInspector
                inspector.Activate()
                wscript = win32com.client.Dispatch("WScript.Shell")
                wscript.AppActivate(mail.Subject)
            except Exception:
                pass
            outlook_launched = True
        finally:
            pythoncom.CoUninitialize()

    except Exception as ex:
        outlook_launched = False
        error_message = str(ex)

    if not outlook_launched:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to launch Outlook draft via COM: {error_message}. Ensure Microsoft Outlook desktop application is installed.",
        )

    # If Outlook draft generation succeeded, update all queried records to Reported_Flag = 1
    with get_db_connection() as conn:
        cursor = conn.cursor()

        if steps:
            step_ids = [s["ID"] for s in steps]
            cursor.execute(
                f"UPDATE Steps SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(step_ids))});",
                step_ids,
            )

        if time_logs:
            time_ids = [t["ID"] for t in time_logs]
            cursor.execute(
                f"UPDATE Time_Logs SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(time_ids))});",
                time_ids,
            )

        if updates:
            update_ids = [u["ID"] for u in updates]
            cursor.execute(
                f"UPDATE Updates SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(update_ids))});",
                update_ids,
            )

        if attachments:
            att_ids = [a["ID"] for a in attachments]
            cursor.execute(
                f"UPDATE Attachments SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(att_ids))});",
                att_ids,
            )

        conn.commit()

    return {
        "success": True,
        "message": "Classic Outlook draft generated successfully and displayed on screen for your review.",
        "reported_counts": {
            "steps": len(steps),
            "time_logs": len(time_logs),
            "hours": summary["total_hours"],
            "updates": len(updates),
            "attachments": len(attachments),
            "projects": len(summary["projects_overview"]),
        },
    }


@app.post("/api/end-of-shift/mark-reported")
def mark_end_of_shift_reported(payload: Optional[EndOfShiftRequest] = None):
    """
    Marks all currently unreported steps, time logs, updates, and attachments
    as Reported_Flag = 1 for the selected projects.
    Used when a contractor copies the formatted email or downloads the draft file.
    """
    p_ids_str = None
    if payload and payload.project_ids:
        p_ids_str = ",".join(str(i) for i in payload.project_ids)

    summary = get_unreported_summary(project_ids=p_ids_str)
    steps = summary["steps"]
    time_logs = summary["time_logs"]
    updates = summary["updates"]
    attachments = summary["attachments"]

    with get_db_connection() as conn:
        cursor = conn.cursor()

        if steps:
            step_ids = [s["ID"] for s in steps]
            cursor.execute(
                f"UPDATE Steps SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(step_ids))});",
                step_ids,
            )

        if time_logs:
            time_ids = [t["ID"] for t in time_logs]
            cursor.execute(
                f"UPDATE Time_Logs SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(time_ids))});",
                time_ids,
            )

        if updates:
            update_ids = [u["ID"] for u in updates]
            cursor.execute(
                f"UPDATE Updates SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(update_ids))});",
                update_ids,
            )

        if attachments:
            att_ids = [a["ID"] for a in attachments]
            cursor.execute(
                f"UPDATE Attachments SET Reported_Flag = 1 WHERE ID IN ({','.join(['?']*len(att_ids))});",
                att_ids,
            )

        conn.commit()

    return {
        "success": True,
        "message": "Records marked as reported.",
        "reported_counts": {
            "steps": len(steps),
            "time_logs": len(time_logs),
            "hours": summary["total_hours"],
            "updates": len(updates),
            "attachments": len(attachments),
            "projects": len(summary["projects_overview"]),
        },
    }


@app.get("/api/end-of-shift/eml")
def download_end_of_shift_eml(project_ids: Optional[str] = None, user_id: Optional[int] = None):
    """
    Generates and downloads an RFC822 .eml draft file with complete HTML body and attachments.
    Can be opened directly or dragged into New Outlook's Drafts folder.
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    summary = get_unreported_summary(project_ids=project_ids)
    shift_date_str = datetime.now().strftime("%B %d, %Y - %I:%M %p")
    html_body = generate_outlook_email_html(summary, shift_date_str, user_id=user_id)

    projects = summary.get("projects_overview", [])
    if len(projects) > 1:
        subject = f"Hitachi End of Shift Report - Consolidated ({len(projects)} Projects) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    elif len(projects) == 1:
        proj_name = projects[0].get("Name", "Project")
        subject = f"Hitachi End of Shift Report: {proj_name} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    else:
        subject = f"Hitachi End of Shift Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["X-Unsent"] = "1"

    alt_part = MIMEMultipart("alternative")
    alt_part.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt_part)

    for att in summary.get("attachments", []):
        local_path = att.get("Local_Path")
        if local_path and os.path.exists(local_path):
            try:
                with open(local_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f'attachment; filename="{att.get("File_Name")}"')
                    msg.attach(part)
            except Exception:
                pass

    clean_sub = re.sub(r'[^a-zA-Z0-9_\- ]', '', subject).replace(' ', '_')
    filename = f"{clean_sub[:60]}.eml"
    return Response(
        content=msg.as_bytes(),
        media_type="message/rfc822",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# APPLICATION ENTRYPOINT FOR PYINSTALLER & LOCAL RUNS
# ---------------------------------------------------------------------------
def open_browser():
    webbrowser.open("http://127.0.0.1:8000")


if __name__ == "__main__":
    import uvicorn

    # Launch browser automatically after 1.2s when run directly or packaged
    threading.Timer(1.2, open_browser).start()

    # Configure uvicorn logging safely for --noconsole without color tty checks
    safe_log_config = copy.deepcopy(uvicorn.config.LOGGING_CONFIG)
    for fmt_name in ("default", "access"):
        if fmt_name in safe_log_config.get("formatters", {}):
            safe_log_config["formatters"][fmt_name]["use_colors"] = False

    # Run Uvicorn server on localhost:8000
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
        log_level="info",
        log_config=safe_log_config,
    )
