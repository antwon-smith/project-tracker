# Hitachi Project Tracker | Offline Command Center Single Page Application (SPA)

A completely offline, zero-install, portable Project Management Single Page Application (SPA) built for field contractors, electrical engineers, and project leads.

---

## 1. Key Architectural Highlights

- **100% Offline & Zero-Install**: No external CDNs, no internet dependencies. All CSS (Tailwind), Typography (Inter woff2 fonts), and Icons (Heroicons inline SVGs) are hosted and served directly from the local filesystem.
- **Persistent Data Vault**: All SQLite database records (`projects.db`), uploaded files, and automatic backups are stored in the Windows `%APPDATA%\ContractorApp\` directory. Replacing or upgrading the `.exe` will **never wipe user data**.
- **Automated Schema Migrations & Backups**: On startup, the application verifies the `App_Settings` table for `DB_Version`. Before applying any schema update, it automatically creates a timestamped `shutil.copy2` backup of the database in `%APPDATA%\ContractorApp\backups\`.
- **Desktop Outlook Integration**: Generates professional, HTML-formatted End-of-Shift reports via native Windows COM (`win32com.client`), automatically attaches all newly uploaded files, and leaves the draft open on screen for review before marking records as reported.

---

## 2. Directory Structure

```text
Hitachi Project Tracker/
│
├── main.py                     # FastAPI backend, SQLite models, migrations, Outlook COM integration, static file server
├── requirements.txt            # Python dependencies (FastAPI, uvicorn, pywin32, multipart, pyinstaller)
├── build.py                    # One-click PyInstaller build script
├── test_app.py                 # Pytest test suite covering all APIs and storage
│
├── templates/
│   └── index.html              # Dark-mode Command Center SPA HTML with embedded Heroicons
│
├── static/
│   ├── css/
│   │   ├── tailwind.min.css    # Complete compiled offline Tailwind CSS
│   │   └── custom.css          # Inter @font-face rules, custom scrollbars, animations
│   ├── js/
│   │   └── app.js              # Vanilla JS controller (Hitlist, dynamic tabs, accordion, drag-and-drop, Outlook)
│   └── fonts/
│       ├── Inter-Regular.woff2 # Offline Inter font files
│       ├── Inter-Medium.woff2
│       ├── Inter-SemiBold.woff2
│       └── Inter-Bold.woff2
│
└── dist/
    └── HitachiProjectTracker.exe # Standalone zero-install Windows binary
```

---

## 3. Database Schema

Stored in `%APPDATA%\ContractorApp\projects.db`:

1. **`App_Settings`**: `DB_Version (INTEGER)`
2. **`Projects`**: `ID (PK)`, `Name`, `Contractor_Name`, `Status (Active, Blocked, Completed)`, `Notes`
3. **`Phases`**: `ID (PK)`, `Project_ID (FK)`, `Phase_Name`
4. **`Steps`**: `ID (PK)`, `Phase_ID (FK)`, `Step_Name`, `Is_Completed (BOOLEAN)`, `Reported_Flag (BOOLEAN)`, `Completed_At`
5. **`Time_Logs`**: `ID (PK)`, `Project_ID (FK)`, `Start_Time`, `End_Time`, `Hours_Logged (REAL)`, `Reported_Flag (BOOLEAN)`, `Description`, `Created_At`
6. **`Updates`**: `ID (PK)`, `Project_ID (FK)`, `Note_Text`, `Timestamp`, `Reported_Flag (BOOLEAN)`
7. **`Attachments`**: `ID (PK)`, `Project_ID (FK)`, `File_Name`, `Local_Path`, `File_Size`, `Uploaded_At`, `Reported_Flag (BOOLEAN)`

---

## 4. How to Run Locally

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the Application
```bash
python main.py
```
*The application starts at `http://127.0.0.1:8000` and automatically opens your default web browser.*

---

## 5. How to Package into a Standalone Executable

### Option A: Using the Automated Build Script
```bash
python build.py
```

### Option B: Direct PyInstaller CLI Command
```bash
python -m PyInstaller --noconsole --onefile --add-data "static;static" --add-data "templates;templates" --name "HitachiProjectTracker" main.py
```

The resulting `dist/HitachiProjectTracker.exe` is completely portable and can be placed anywhere (e.g. Desktop, USB drive).
