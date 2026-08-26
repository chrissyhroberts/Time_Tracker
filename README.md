# Open Time Tracker

<img width="413" alt="Screenshot 2025-04-02 at 18 49 41" src="https://github.com/user-attachments/assets/ba3cac07-d4f2-4b3f-aedc-de556e109812" />

## Description

Open Time Tracker is a small PyQt5/pandas desktop application for logging work activities, tracking time spent on tasks, and viewing daily logs and summary statistics.

It is deliberately local-first: the application writes CSV files on your machine. There is no cloud account, sync service, subscription, or external database.

## Features

### V1.0.0

- Start and stop time tracking for selected tasks
- Auto-save time logs in CSV format
- Display today's logs and summary statistics
- Editable task dropdown
- Refresh task list and logs

### V1.1.0

- Backdated log entries with date, start, and stop time inputs
- Real-time elapsed time display
- Partial backdating by manually editing the start time before stopping a task
- Improved daily log and task summary display
- Datetime validation and error handling
- UI/layout improvements

### V1.1.1

- Auto-updating Stop Time field
- Manual override detection for Stop Time
- Restart Stop Time auto-update when a new task starts
- Refresh resets the start date to today's date

### V1.2.0 packaging

- Native Apple Silicon macOS build
- Windows x64 build
- Python is bundled inside each desktop build; users do not need to install Python
- GitHub Actions automatically builds both platforms
- Version tags such as `v1.2.0` automatically publish both binaries to a GitHub Release
- Application data now live in a writable per-user data directory instead of depending on the launch working directory

### V1.3.0 data management and summaries

- **Open Data Folder** button opens the per-user CSV storage directory in Finder/Explorer
- **Manage Activities** window for adding and removing dropdown activities
- Retrospective activity renaming updates both the configured activity list and all matching historical `time_log.csv` rows
- Historical renames create timestamped backups in `OpenTimeTracker/backups/` before changing CSV data
- Removing an activity from the dropdown does not delete or alter historical time records
- Summary date filters support all-time, since a selected date, through a selected date, or an inclusive start/end date range
- Summary display now shows total logged hours for the selected period

## Downloading the desktop app

GitHub Actions produces two packages:

- `OpenTimeTracker-macOS-arm64.zip` — native Apple Silicon macOS application
- `OpenTimeTracker.exe` — Windows x64 executable

Every push to `main`, every pull request to `main`, and every manually triggered workflow builds both versions. Builds are available under the corresponding workflow run's **Artifacts** section.

Pushing a tag beginning with `v`, for example:

```bash
git tag v1.3.0
git push origin v1.3.0
```

also creates a GitHub Release containing the macOS and Windows builds.

### macOS signing note

The CI build is ad-hoc signed by PyInstaller so that the Apple Silicon bundle is internally valid, but it is not Developer ID signed or notarized. macOS may therefore show a Gatekeeper warning for a downloaded release. A fully notarized public distribution can be added later by storing an Apple Developer signing certificate/notarization credentials as GitHub Actions secrets.

The Windows executable is likewise not Authenticode-signed, so Windows SmartScreen may warn on a newly downloaded build.

## Runtime versions

The reproducible build currently pins:

- Python 3.14.7
- pandas 3.0.5
- PyQt5 5.15.11
- Qt 5.15.19
- PyInstaller 6.22.2

The macOS workflow runs on a GitHub-hosted Apple Silicon runner and verifies that both Python and the generated application are `arm64`.

## Data files

The packaged application stores writable data separately from the application bundle:

### macOS

```text
~/Library/Application Support/OpenTimeTracker/
├── activities.csv
├── time_log.csv
└── backups/
```

### Windows

```text
%APPDATA%\OpenTimeTracker\
├── activities.csv
├── time_log.csv
└── backups\
```

On first run, the application attempts to migrate `activities.csv` and `time_log.csv` from locations used by older source/AppleScript launches. If no activities file exists, the bundled `activities.csv` is copied into the user data directory as a starting list.

`time_log.csv` has the following structure:

| StartTime | EndTime | Duration | Task |
|---|---|---|---|
| 2025-03-27 14:47:40 | 2025-03-27 14:47:45 | 00:00:04 | Exam Board |
| 2025-03-27 14:47:48 | 2025-03-27 14:47:53 | 00:00:04 | Research |

Use **Open Data Folder** in the application to open this directory directly. The **Manage Activities** dialog can rename an activity retrospectively; exact matches in the `Task` column are changed and existing categories can be merged. Before a retrospective rename, the affected CSV files are copied into the `backups` directory.

## Running from source

Python 3.14.7 is the pinned development/runtime version.

```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# .venv\Scripts\activate        # Windows
python -m pip install -r requirements.txt
python time_tracker.py
```

## Building locally

Install the build dependencies:

```bash
python -m pip install -r requirements-build.txt
```

### Apple Silicon macOS

Run this from an arm64 Python environment:

```bash
python -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name OpenTimeTracker \
  --add-data "activities.csv:." \
  time_tracker.py
```

The application will be written to `dist/OpenTimeTracker.app`.

### Windows x64

```powershell
python -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name OpenTimeTracker `
  --add-data "activities.csv:." `
  time_tracker.py
```

The executable will be written to `dist/OpenTimeTracker.exe`.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── build.yml
├── .python-version
├── activities.csv
├── requirements.txt
├── requirements-build.txt
├── time_tracker.py
└── README.md
```

## License

This project is licensed under the MIT License.
