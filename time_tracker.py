# -*- coding: utf-8 -*-

import datetime
import os
import shutil
import sys
import uuid
from pathlib import Path

import pandas as pd
from PyQt5.QtCore import QDate, QTime, QTimer, QUrl, Qt
from PyQt5.QtGui import QBrush, QColor, QDesktopServices, QPainter, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QScrollArea,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "OpenTimeTracker"


def get_user_data_dir():
    """Return a writable per-user directory for application data."""
    if sys.platform == "darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    elif os.name == "nt":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    data_dir = base_dir / APP_NAME
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def bundled_resource_path(filename):
    """Locate a read-only file bundled by PyInstaller or stored beside the source."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / filename
    return Path(__file__).resolve().parent / filename


def legacy_data_directories():
    """Locations used by older source/AppleScript versions of the app."""
    candidates = [Path.cwd()]

    if not getattr(sys, "frozen", False):
        candidates.append(Path(__file__).resolve().parent)
    else:
        executable = Path(sys.executable).resolve()
        candidates.append(executable.parent)

        # A macOS bundle runs from App.app/Contents/MacOS/. Also check the
        # directory containing the .app in case old CSVs were stored there.
        if sys.platform == "darwin":
            for parent in executable.parents:
                if parent.suffix == ".app":
                    candidates.append(parent.parent)
                    break

    return list(dict.fromkeys(path.resolve() for path in candidates if path.exists()))


def migrate_legacy_file(filename, destination):
    """Copy an existing legacy CSV into the new data directory on first run."""
    if destination.exists():
        return

    for directory in legacy_data_directories():
        source = directory / filename
        if source.exists() and source.is_file() and source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
            return


def initialise_user_data():
    """Create/migrate writable CSV files without modifying bundled resources."""
    migrate_legacy_file("activities.csv", ACTIVITIES_FILE)
    migrate_legacy_file("time_log.csv", LOG_FILE)

    if not ACTIVITIES_FILE.exists():
        default_activities = bundled_resource_path("activities.csv")
        if default_activities.exists():
            shutil.copy2(default_activities, ACTIVITIES_FILE)
        else:
            pd.DataFrame(columns=["Activities"]).to_csv(ACTIVITIES_FILE, index=False)


def backup_data_file(path):
    """Create a timestamped backup before editing persistent CSV data."""
    path = Path(path)
    if not path.exists():
        return None

    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destination = backup_dir / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, destination)
    return destination


DATA_DIR = get_user_data_dir()
ACTIVITIES_FILE = DATA_DIR / "activities.csv"
LOG_FILE = DATA_DIR / "time_log.csv"
initialise_user_data()

current_task = None
start_time = None


def load_activities():
    """Return configured dropdown activities."""
    if ACTIVITIES_FILE.exists() and ACTIVITIES_FILE.stat().st_size > 0:
        df = pd.read_csv(ACTIVITIES_FILE)
        if "Activities" in df.columns:
            activities = [str(x).strip() for x in df["Activities"].dropna().tolist()]
            activities = [x for x in activities if x]
            return sorted(set(activities), key=str.casefold)
    return []


def save_activities(activities):
    """Persist a clean, de-duplicated activity list."""
    cleaned = [str(x).strip() for x in activities if str(x).strip()]
    cleaned = sorted(set(cleaned), key=str.casefold)
    pd.DataFrame(cleaned, columns=["Activities"]).to_csv(ACTIVITIES_FILE, index=False)


def load_log():
    """Load the time log, returning an empty log with the expected schema if absent."""
    columns = ["EntryID", "StartTime", "EndTime", "Duration", "Task"]
    if not LOG_FILE.exists() or LOG_FILE.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    df = pd.read_csv(LOG_FILE)
    needs_migration = "EntryID" not in df.columns
    if "EntryID" not in df.columns:
        df.insert(0, "EntryID", "")
    missing_ids = df["EntryID"].isna() | (df["EntryID"].astype(str).str.strip() == "")
    needs_migration = needs_migration or bool(missing_ids.any())
    if needs_migration:
        backup_data_file(LOG_FILE)
        df.loc[missing_ids, "EntryID"] = [str(uuid.uuid4()) for _ in range(int(missing_ids.sum()))]
        df.to_csv(LOG_FILE, index=False)
    for column in columns:
        if column not in df.columns:
            df[column] = pd.NA
    return df[columns]


def all_activity_names():
    """Return activity names found either in the dropdown list or historical logs."""
    names = set(load_activities())
    df = load_log()
    if not df.empty:
        names.update(str(x).strip() for x in df["Task"].dropna().tolist() if str(x).strip())
    return sorted(names, key=str.casefold)


def add_activity(activity):
    """Add an activity to the configured dropdown list."""
    activity = activity.strip()
    if not activity:
        return False
    activities = load_activities()
    if activity not in activities:
        activities.append(activity)
        save_activities(activities)
        return True
    return False


def remove_activity_from_list(activity):
    """Remove an activity from the dropdown without altering historical logs."""
    activities = load_activities()
    updated = [x for x in activities if x != activity]
    if updated == activities:
        return False
    backup_data_file(ACTIVITIES_FILE)
    save_activities(updated)
    return True


def rename_activity_everywhere(old_name, new_name):
    """Rename an activity in both configuration and all matching historical log rows."""
    old_name = old_name.strip()
    new_name = new_name.strip()
    if not old_name or not new_name:
        raise ValueError("Both the old and new activity names are required.")
    if old_name == new_name:
        return 0

    activities = load_activities()
    if old_name in activities:
        backup_data_file(ACTIVITIES_FILE)
        renamed = [new_name if x == old_name else x for x in activities]
        save_activities(renamed)
    elif new_name not in activities:
        # A historical-only task should become available in the dropdown after renaming.
        activities.append(new_name)
        save_activities(activities)

    df = load_log()
    changed_rows = 0
    if not df.empty:
        mask = df["Task"].astype(str) == old_name
        changed_rows = int(mask.sum())
        if changed_rows:
            backup_data_file(LOG_FILE)
            df.loc[mask, "Task"] = new_name
            df.to_csv(LOG_FILE, index=False)

    return changed_rows


def save_log(task, start, end):
    """Append one time-log row."""
    task = task.strip()
    add_activity(task)

    duration_seconds = max(0, int((end - start).total_seconds()))
    duration = (
        f"{duration_seconds // 3600:02}:"
        f"{(duration_seconds % 3600) // 60:02}:"
        f"{duration_seconds % 60:02}"
    )
    new_entry = pd.DataFrame(
        [[str(uuid.uuid4()), start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), duration, task]],
        columns=["EntryID", "StartTime", "EndTime", "Duration", "Task"],
    )
    df = load_log()
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)


def duration_to_hms(seconds):
    seconds = max(0, int(seconds))
    return (
        f"{seconds // 3600:02}:"
        f"{(seconds % 3600) // 60:02}:"
        f"{seconds % 60:02}"
    )


def duration_to_seconds(value):
    """Convert HH:MM:SS-like values to seconds, returning zero for malformed values."""
    try:
        parts = [int(part) for part in str(value).split(":")]
        if len(parts) != 3:
            return 0
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds
    except (TypeError, ValueError):
        return 0


def filter_today_logs():
    """Return the five most recent log entries that started today."""
    df = load_log()
    if df.empty:
        return df

    df = df[df["StartTime"].notna()].copy()
    today = datetime.date.today()
    parsed_start = pd.to_datetime(df["StartTime"], errors="coerce")
    df = df[parsed_start.dt.date == today].copy()

    if not df.empty:
        df["StartTime"] = pd.to_datetime(df["StartTime"], errors="coerce").dt.strftime("%H:%M")
        df["EndTime"] = pd.to_datetime(df["EndTime"], errors="coerce").dt.strftime("%H:%M")
        df = df[["StartTime", "EndTime", "Duration", "Task"]]
    return df.tail(5)


def summarise_log(start_date=None, end_date=None):
    """Summarise logged hours by task for an inclusive date range.

    Dates are applied to the date on which each log entry starts. A missing
    start or end bound leaves that side of the interval open.
    """
    if start_date and end_date and end_date < start_date:
        raise ValueError("End date must be on or after the start date.")

    df = load_log()
    if df.empty:
        return pd.DataFrame(columns=["Task", "Total Hours", "Percent of Time"]), 0

    parsed_start = pd.to_datetime(df["StartTime"], errors="coerce")
    df = df[parsed_start.notna()].copy()
    parsed_start = pd.to_datetime(df["StartTime"], errors="coerce")

    if start_date:
        mask = parsed_start.dt.date >= start_date
        df = df[mask].copy()
        parsed_start = pd.to_datetime(df["StartTime"], errors="coerce")
    if end_date:
        mask = parsed_start.dt.date <= end_date
        df = df[mask].copy()

    if df.empty:
        return pd.DataFrame(columns=["Task", "Total Hours", "Percent of Time"]), 0

    df["DurationSeconds"] = df["Duration"].apply(duration_to_seconds)
    task_durations = df.groupby("Task", dropna=False)["DurationSeconds"].sum()
    task_durations = task_durations[task_durations > 0]
    if task_durations.empty:
        return pd.DataFrame(columns=["Task", "Total Hours", "Percent of Time"]), 0

    total_time = int(task_durations.sum())
    summary_df = pd.DataFrame(
        {
            "Task": task_durations.index.astype(str),
            "Total Hours": (task_durations / 3600).round(2),
            "Percent of Time": ((task_durations / total_time) * 100).round(1),
        }
    ).sort_values(by="Percent of Time", ascending=False)
    return summary_df, total_time


def week_start_for(date_value):
    """Return the Monday for the week containing date_value."""
    return date_value - datetime.timedelta(days=date_value.weekday())


def logs_overlapping_range(start_dt, end_dt):
    """Return log rows whose time interval overlaps [start_dt, end_dt)."""
    df = load_log()
    if df.empty:
        return df

    starts = pd.to_datetime(df["StartTime"], errors="coerce")
    ends = pd.to_datetime(df["EndTime"], errors="coerce")
    mask = starts.notna() & ends.notna() & (starts < end_dt) & (ends > start_dt)
    out = df.loc[mask].copy()
    if out.empty:
        return out

    out["_start"] = pd.to_datetime(out["StartTime"], errors="coerce")
    out["_end"] = pd.to_datetime(out["EndTime"], errors="coerce")
    return out


class CalendarEntryDialog(QDialog):
    """Edit one exact log row, identified by its stable EntryID."""

    def __init__(self, row, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Calendar Entry")
        start = pd.to_datetime(row["StartTime"]).to_pydatetime()
        end = pd.to_datetime(row["EndTime"]).to_pydatetime()
        self.task_edit = QComboBox()
        self.task_edit.addItems(all_activity_names())
        self.task_edit.setCurrentText(str(row.get("Task", "")))
        self.start_date = QDateEdit(QDate(start.year, start.month, start.day))
        self.end_date = QDateEdit(QDate(end.year, end.month, end.day))
        self.start_time = QTimeEdit(QTime(start.hour, start.minute, start.second))
        self.end_time = QTimeEdit(QTime(end.hour, end.minute, end.second))
        for control in (self.start_date, self.end_date):
            control.setCalendarPopup(True)
            control.setDisplayFormat("yyyy-MM-dd")
        for control in (self.start_time, self.end_time):
            control.setDisplayFormat("HH:mm:ss")

        form = QFormLayout()
        form.addRow("Task", self.task_edit)
        form.addRow("Start date", self.start_date)
        form.addRow("Start time", self.start_time)
        form.addRow("End date", self.end_date)
        form.addRow("End time", self.end_time)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def values(self):
        sd, ed = self.start_date.date(), self.end_date.date()
        st, et = self.start_time.time(), self.end_time.time()
        start = datetime.datetime(sd.year(), sd.month(), sd.day(), st.hour(), st.minute(), st.second())
        end = datetime.datetime(ed.year(), ed.month(), ed.day(), et.hour(), et.minute(), et.second())
        return self.task_edit.currentText().strip(), start, end

    def validate_and_accept(self):
        task, start, end = self.values()
        if not task:
            QMessageBox.warning(self, "Invalid Entry", "Task cannot be empty.")
        elif end <= start:
            QMessageBox.warning(self, "Invalid Times", "End time must be after start time.")
        else:
            self.accept()


class WeekDayCanvas(QWidget):
    """One 24-hour day column used by the retrospective week calendar."""

    MINUTES_PER_DAY = 24 * 60
    PIXELS_PER_HOUR = 44
    SNAP_MINUTES = 15

    def __init__(self, owner, date_value):
        super().__init__(owner)
        self.owner = owner
        self.date_value = date_value
        self.drag_start_minute = None
        self.drag_current_minute = None
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.PIXELS_PER_HOUR * 24)
        self.setMouseTracking(True)

    def minute_from_y(self, y):
        minute = int(round((y / self.height()) * self.MINUTES_PER_DAY))
        minute = max(0, min(self.MINUTES_PER_DAY, minute))
        snap = self.SNAP_MINUTES
        return int(round(minute / snap) * snap)

    def y_from_minute(self, minute):
        return (minute / self.MINUTES_PER_DAY) * self.height()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(250, 250, 250))

        # Hour grid.
        for hour in range(25):
            y = int(self.y_from_minute(hour * 60))
            pen = QPen(QColor(205, 205, 205) if hour % 6 else QColor(165, 165, 165))
            pen.setWidth(1)
            painter.setPen(pen)
            painter.drawLine(0, y, self.width(), y)

        # Existing logs. Overnight entries are clipped to the visible day.
        day_start = datetime.datetime.combine(self.date_value, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)
        df = logs_overlapping_range(day_start, day_end)
        if not df.empty:
            palette = [
                QColor(198, 220, 245),
                QColor(211, 233, 210),
                QColor(245, 221, 190),
                QColor(229, 210, 238),
                QColor(241, 205, 213),
                QColor(206, 228, 229),
            ]
            for _, row in df.iterrows():
                start = max(row["_start"].to_pydatetime(), day_start)
                end = min(row["_end"].to_pydatetime(), day_end)
                start_minute = (start - day_start).total_seconds() / 60
                end_minute = (end - day_start).total_seconds() / 60
                top = self.y_from_minute(start_minute)
                bottom = self.y_from_minute(end_minute)
                height = max(4, bottom - top)

                task = str(row.get("Task", ""))
                colour = palette[abs(hash(task)) % len(palette)]
                rect = self.rect()
                x = 3
                w = max(10, self.width() - 6)
                painter.fillRect(int(x), int(top), int(w), int(height), QBrush(colour))
                selected = str(row.get("EntryID", "")) == str(self.owner.selected_entry_id or "")
                painter.setPen(QPen(QColor(220, 95, 25) if selected else QColor(95, 95, 95), 3 if selected else 1))
                painter.drawRect(int(x), int(top), int(w), int(height))

                if height >= 18:
                    label = f"{start.strftime('%H:%M')} {task}"
                    painter.setPen(QPen(QColor(35, 35, 35)))
                    painter.drawText(int(x + 4), int(top + 14), label[:22])

        # Active drag selection.
        if self.drag_start_minute is not None and self.drag_current_minute is not None:
            a, b = sorted((self.drag_start_minute, self.drag_current_minute))
            if a != b:
                top = self.y_from_minute(a)
                bottom = self.y_from_minute(b)
                painter.fillRect(
                    2,
                    int(top),
                    self.width() - 4,
                    max(3, int(bottom - top)),
                    QBrush(QColor(90, 140, 210, 80)),
                )
                painter.setPen(QPen(QColor(70, 110, 175), 2))
                painter.drawRect(2, int(top), self.width() - 5, max(3, int(bottom - top)))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            row = self.entry_at(event.y())
            if row is not None:
                self.owner.select_entry(row)
                self.update()
                return
            minute = self.minute_from_y(event.y())
            self.drag_start_minute = minute
            self.drag_current_minute = minute
            self.update()

    def mouseMoveEvent(self, event):
        if self.drag_start_minute is not None:
            self.drag_current_minute = self.minute_from_y(event.y())
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self.drag_start_minute is None:
            return

        self.drag_current_minute = self.minute_from_y(event.y())
        start_minute, end_minute = sorted((self.drag_start_minute, self.drag_current_minute))
        self.drag_start_minute = None
        self.drag_current_minute = None
        self.update()

        if end_minute - start_minute < self.SNAP_MINUTES:
            return

        # Treat an end exactly at 24:00 as next-day midnight.
        day_start = datetime.datetime.combine(self.date_value, datetime.time.min)
        start_dt = day_start + datetime.timedelta(minutes=start_minute)
        end_dt = day_start + datetime.timedelta(minutes=end_minute)
        self.owner.create_calendar_entry(start_dt, end_dt)

    def entry_at(self, y):
        day_start = datetime.datetime.combine(self.date_value, datetime.time.min)
        day_end = day_start + datetime.timedelta(days=1)
        df = logs_overlapping_range(day_start, day_end)
        for _, row in df.iterrows():
            start = max(row["_start"].to_pydatetime(), day_start)
            end = min(row["_end"].to_pydatetime(), day_end)
            top = self.y_from_minute((start - day_start).total_seconds() / 60)
            bottom = self.y_from_minute((end - day_start).total_seconds() / 60)
            if top <= y <= max(top + 4, bottom):
                return row.to_dict()
        return None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            row = self.entry_at(event.y())
            if row is not None:
                self.owner.select_entry(row)
                self.owner.edit_selected_entry()


class WeekCalendarPanel(QFrame):
    """Monday-Sunday 24-hour visual calendar with drag-to-create entry."""

    def __init__(self, tracker):
        super().__init__(tracker)
        self.tracker = tracker
        self.current_week_start = week_start_for(datetime.date.today())
        self.selected_entry = None
        self.selected_entry_id = None
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(820)

        outer = QVBoxLayout(self)

        nav = QHBoxLayout()
        self.prev_button = QPushButton("‹")
        self.prev_button.setToolTip("Previous week")
        self.prev_button.clicked.connect(lambda: self.shift_week(-7))
        nav.addWidget(self.prev_button)

        self.today_button = QPushButton("Today")
        self.today_button.clicked.connect(self.go_today)
        nav.addWidget(self.today_button)

        self.week_label = QLabel()
        self.week_label.setAlignment(Qt.AlignCenter)
        self.week_label.setStyleSheet("font-weight: 600;")
        nav.addWidget(self.week_label, 1)

        self.next_button = QPushButton("›")
        self.next_button.setToolTip("Next week")
        self.next_button.clicked.connect(lambda: self.shift_week(7))
        nav.addWidget(self.next_button)
        self.edit_button = QPushButton("Edit")
        self.edit_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_selected_entry)
        nav.addWidget(self.edit_button)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_entry)
        nav.addWidget(self.delete_button)
        outer.addLayout(nav)

        hint = QLabel("Drag over any blank time to add a retrospective entry. Times snap to 15 minutes.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        outer.addWidget(hint)

        self.header_widget = QWidget()
        self.header_grid = QGridLayout(self.header_widget)
        self.header_grid.setContentsMargins(4, 4, 4, 0)
        self.header_grid.setHorizontalSpacing(2)
        self.header_grid.setVerticalSpacing(0)
        outer.addWidget(self.header_widget)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.calendar_widget = QWidget()
        self.grid = QGridLayout(self.calendar_widget)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setHorizontalSpacing(2)
        self.grid.setVerticalSpacing(0)
        self.grid.setColumnStretch(0, 0)
        for column in range(1, 8):
            self.grid.setColumnStretch(column, 1)
        self.scroll.setWidget(self.calendar_widget)
        outer.addWidget(self.scroll, 1)

        self.day_canvases = []
        self.rebuild_week()
        QTimer.singleShot(0, self.scroll_to_current_time)

    def shift_week(self, days):
        self.current_week_start += datetime.timedelta(days=days)
        self.rebuild_week()

    def go_today(self):
        self.current_week_start = week_start_for(datetime.date.today())
        self.rebuild_week()
        QTimer.singleShot(0, self.scroll_to_current_time)

    def rebuild_week(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        while self.header_grid.count():
            item = self.header_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        end = self.current_week_start + datetime.timedelta(days=6)
        self.week_label.setText(
            f"{self.current_week_start.strftime('%d %b %Y')} – {end.strftime('%d %b %Y')}"
        )

        self.header_grid.addWidget(QLabel("Time"), 0, 0)
        self.header_grid.setColumnMinimumWidth(0, 52)

        self.day_canvases = []
        for day_index in range(7):
            date_value = self.current_week_start + datetime.timedelta(days=day_index)
            header = QLabel(date_value.strftime("%a\n%d %b"))
            header.setAlignment(Qt.AlignCenter)
            if date_value == datetime.date.today():
                header.setStyleSheet("font-weight: 700;")
            self.header_grid.addWidget(header, 0, day_index + 1)
            self.header_grid.setColumnStretch(day_index + 1, 1)

            canvas = WeekDayCanvas(self, date_value)
            self.day_canvases.append(canvas)
            self.grid.addWidget(canvas, 0, day_index + 1)

        # Time labels in a matching 24-hour column.
        time_column = QWidget()
        time_column.setFixedWidth(52)
        time_column.setFixedHeight(WeekDayCanvas.PIXELS_PER_HOUR * 24)
        time_layout = QVBoxLayout(time_column)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(0)
        for hour in range(24):
            label = QLabel(f"{hour:02}:00")
            label.setAlignment(Qt.AlignTop | Qt.AlignRight)
            label.setFixedHeight(WeekDayCanvas.PIXELS_PER_HOUR)
            label.setStyleSheet("font-size: 10px; color: #666; padding-right: 4px;")
            time_layout.addWidget(label)
        self.grid.addWidget(time_column, 0, 0)
        self.header_widget.setMinimumHeight(42)
        self.header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.calendar_widget.setMinimumWidth(0)

    def select_entry(self, row):
        self.selected_entry = row
        self.selected_entry_id = str(row.get("EntryID", ""))
        self.edit_button.setEnabled(True)
        self.delete_button.setEnabled(True)
        self.refresh()

    def edit_selected_entry(self):
        row = self.selected_entry
        if not row:
            return
        try:
            dialog = CalendarEntryDialog(row, self)
            if dialog.exec_() != QDialog.Accepted:
                return
            task, start, end = dialog.values()
            df = load_log()
            matches = df["EntryID"].astype(str) == str(row.get("EntryID", ""))
            if not matches.any():
                raise ValueError("The selected entry no longer exists.")
            backup_data_file(LOG_FILE)
            df.loc[matches, "Task"] = task
            df.loc[matches, "StartTime"] = start.strftime("%Y-%m-%d %H:%M:%S")
            df.loc[matches, "EndTime"] = end.strftime("%Y-%m-%d %H:%M:%S")
            df.loc[matches, "Duration"] = duration_to_hms(int((end - start).total_seconds()))
            df.to_csv(LOG_FILE, index=False)
            add_activity(task)
            self.tracker.refresh_task_dropdown()
            self.tracker.update_log_display()
        except Exception as exc:
            QMessageBox.critical(self, "Calendar Error", f"Could not edit the entry:\n\n{exc}")

    def delete_selected_entry(self):
        row = self.selected_entry
        if not row:
            return
        if QMessageBox.question(self, "Delete Calendar Entry", f"Delete '{row.get('Task', '')}'?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        try:
            df = load_log()
            matches = df["EntryID"].astype(str) == str(row.get("EntryID", ""))
            if not matches.any():
                raise ValueError("The selected entry no longer exists.")
            backup_data_file(LOG_FILE)
            df = df.loc[~matches].copy()
            df.to_csv(LOG_FILE, index=False)
            self.selected_entry = None
            self.selected_entry_id = None
            self.edit_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.tracker.update_log_display()
        except Exception as exc:
            QMessageBox.critical(self, "Calendar Error", f"Could not delete the entry:\n\n{exc}")

    def refresh(self):
        for canvas in self.day_canvases:
            canvas.update()

    def scroll_to_current_time(self):
        # Keep nights fully available but initially position near the current hour
        # when viewing the current week.
        if week_start_for(datetime.date.today()) != self.current_week_start:
            return
        now = datetime.datetime.now()
        target_hour = max(0, now.hour - 2)
        y = target_hour * WeekDayCanvas.PIXELS_PER_HOUR
        self.scroll.verticalScrollBar().setValue(y)

    def create_calendar_entry(self, start_dt, end_dt):
        activities = all_activity_names()
        if not activities:
            QMessageBox.warning(
                self,
                "No Activities",
                "Add at least one activity before creating a calendar entry.",
            )
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add Calendar Entry")
        layout = QVBoxLayout(dialog)

        period = QLabel(
            f"{start_dt.strftime('%a %d %b %Y, %H:%M')} – "
            f"{end_dt.strftime('%a %d %b %Y, %H:%M')}"
        )
        period.setWordWrap(True)
        layout.addWidget(period)

        layout.addWidget(QLabel("Activity"))
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(activities)
        layout.addWidget(combo)

        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)

        if dialog.exec_() != QDialog.Accepted:
            return

        task = combo.currentText().strip()
        if not task:
            QMessageBox.warning(self, "Missing Activity", "Choose or enter an activity.")
            return

        try:
            save_log(task, start_dt, end_dt)
            self.tracker.refresh_task_dropdown()
            self.tracker.update_log_display()
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Calendar Error", f"Could not save the entry:\n\n{exc}")


class ActivityManagerDialog(QDialog):
    """Manage configured activity names and retrospective historical renames."""

    def __init__(self, tracker):
        super().__init__(tracker)
        self.tracker = tracker
        self.setWindowTitle("Manage Activities")
        self.resize(520, 420)

        layout = QVBoxLayout(self)
        explanation = QLabel(
            "Rename updates the dropdown and every matching historical log entry. "
            "Removing only hides an activity from the dropdown and leaves historical logs intact."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)

        self.activity_list = QListWidget()
        self.activity_list.currentTextChanged.connect(self.populate_name_field)
        layout.addWidget(self.activity_list)

        layout.addWidget(QLabel("Activity name"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter a new name or select an activity above")
        layout.addWidget(self.name_edit)

        first_row = QHBoxLayout()
        self.add_button = QPushButton("Add to dropdown")
        self.add_button.clicked.connect(self.add_selected_name)
        first_row.addWidget(self.add_button)

        self.rename_button = QPushButton("Rename everywhere")
        self.rename_button.clicked.connect(self.rename_selected_activity)
        first_row.addWidget(self.rename_button)
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        self.remove_button = QPushButton("Remove from dropdown")
        self.remove_button.clicked.connect(self.remove_selected_activity)
        second_row.addWidget(self.remove_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.accept)
        second_row.addWidget(self.close_button)
        layout.addLayout(second_row)

        self.refresh_list()

    def refresh_list(self, select_name=None):
        self.activity_list.clear()
        names = all_activity_names()
        self.activity_list.addItems(names)
        if select_name in names:
            items = self.activity_list.findItems(select_name, Qt.MatchExactly)
            if items:
                self.activity_list.setCurrentItem(items[0])

    def populate_name_field(self, name):
        if name:
            self.name_edit.setText(name)

    def add_selected_name(self):
        try:
            name = self.name_edit.text().strip()
            if not name:
                QMessageBox.warning(self, "Missing Activity", "Enter an activity name first.")
                return
            added = add_activity(name)
            self.tracker.activity_data_changed()
            self.refresh_list(select_name=name)
            if not added:
                QMessageBox.information(self, "Already Present", f"'{name}' is already in the dropdown list.")
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Activity Error",
                f"Could not add the activity:\n\n{exc}",
            )

    def rename_selected_activity(self):
        try:
            selected = self.activity_list.currentItem()
            if not selected:
                QMessageBox.warning(self, "No Selection", "Select the activity you want to rename.")
                return

            old_name = selected.text().strip()
            new_name = self.name_edit.text().strip()
            if not new_name:
                QMessageBox.warning(self, "Missing Name", "Enter the new activity name.")
                return
            if old_name == new_name:
                return

            if new_name in all_activity_names():
                answer = QMessageBox.question(
                    self,
                    "Merge Activities?",
                    f"'{new_name}' already exists. Rename '{old_name}' to '{new_name}' and merge their historical totals?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if answer != QMessageBox.Yes:
                    return

            changed_rows = rename_activity_everywhere(old_name, new_name)
            self.tracker.activity_data_changed(old_name=old_name, new_name=new_name)
            self.refresh_list(select_name=new_name)
            QMessageBox.information(
                self,
                "Activity Renamed",
                f"Renamed '{old_name}' to '{new_name}'.\nHistorical rows updated: {changed_rows}\nBackups are stored in the data folder's backups directory.",
            )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Activity Error",
                f"Could not rename the activity:\n\n{exc}",
            )

    def remove_selected_activity(self):
        try:
            selected = self.activity_list.currentItem()
            if not selected:
                QMessageBox.warning(self, "No Selection", "Select an activity first.")
                return

            name = selected.text().strip()
            removed = remove_activity_from_list(name)
            self.tracker.activity_data_changed()
            self.refresh_list(select_name=name)
            if removed:
                QMessageBox.information(
                    self,
                    "Removed from Dropdown",
                    f"'{name}' was removed from the dropdown. Historical log entries were not changed.",
                )
            else:
                QMessageBox.information(
                    self,
                    "Historical Activity",
                    f"'{name}' is not currently in the dropdown list; its historical log entries remain available for summaries and renaming.",
                )
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Activity Error",
                f"Could not remove the activity:\n\n{exc}",
            )


class TimeTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.stop_time_autoupdate = True
        self.initUI()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed_label)

        self.stop_time_timer = QTimer(self)
        self.stop_time_timer.timeout.connect(self.update_stop_time_edit)
        self.stop_time_timer.start(1000)

    def update_elapsed_label(self):
        global start_time
        if current_task:
            try:
                date_str = self.start_date_edit.text().strip()
                time_str = self.start_time_edit.text().strip()
                combined_dt = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
            except ValueError:
                combined_dt = start_time or datetime.datetime.now()

            elapsed_seconds = max(0, int((datetime.datetime.now() - combined_dt).total_seconds()))
            formatted_time = (
                f"{elapsed_seconds // 3600:02}:"
                f"{(elapsed_seconds % 3600) // 60:02}:"
                f"{elapsed_seconds % 60:02}"
            )
            self.elapsed_time_label.setText(f"Elapsed Time: {formatted_time}")

    def update_stop_time_edit(self):
        if self.stop_time_autoupdate:
            self.stop_time_edit.setText(datetime.datetime.now().strftime("%H:%M:%S"))

    def disable_stop_time_autoupdate(self):
        self.stop_time_autoupdate = False

    def initUI(self):
        self.resize(390, 850)
        self.setWindowTitle("Open Time Tracker")
        self.root_layout = QHBoxLayout(self)
        self.main_panel = QWidget()
        self.main_layout = QVBoxLayout(self.main_panel)
        self.root_layout.addWidget(self.main_panel)

        self.calendar_panel = WeekCalendarPanel(self)
        self.calendar_panel.setVisible(False)
        self.root_layout.addWidget(self.calendar_panel, 1)

        self.elapsed_time_label = QLabel("Elapsed Time: 00:00:00")
        self.elapsed_time_label.setStyleSheet("font-size: 20px;")
        self.main_layout.addWidget(self.elapsed_time_label)

        self.status_label = QLabel("No active task")
        self.main_layout.addWidget(self.status_label)

        self.task_dropdown = QComboBox()
        self.task_dropdown.setEditable(True)
        self.task_dropdown.addItem("")
        self.task_dropdown.addItems(load_activities())
        self.task_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.task_dropdown)

        button_row = QHBoxLayout()
        self.start_button = QPushButton("🟢 Start")
        self.start_button.clicked.connect(self.start_task)
        button_row.addWidget(self.start_button)

        self.stop_button = QPushButton("🔴 Stop")
        self.stop_button.clicked.connect(self.stop_task)
        button_row.addWidget(self.stop_button)
        self.main_layout.addLayout(button_row)

        self.start_date_label = QLabel("Start Date (YYYY-MM-DD):")
        self.main_layout.addWidget(self.start_date_label)

        self.start_date_edit = QLineEdit()
        self.start_date_edit.setFixedHeight(30)
        self.start_date_edit.setText(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.start_date_edit.setStyleSheet("font-size: 14px; font-family: Menlo;")
        self.start_date_edit.textChanged.connect(lambda: self.timer.start(1000))
        self.start_date_edit.textChanged.connect(self.update_elapsed_label)
        self.main_layout.addWidget(self.start_date_edit)

        time_row = QHBoxLayout()
        start_time_col = QVBoxLayout()
        self.start_time_label = QLabel("Start Time")
        start_time_col.addWidget(self.start_time_label)

        self.start_time_edit = QLineEdit()
        self.start_time_edit.setFixedHeight(30)
        self.start_time_edit.setText("")
        self.start_time_edit.setStyleSheet("font-size: 14px; font-family: Menlo;")
        self.start_time_edit.textChanged.connect(lambda: self.timer.start(1000))
        self.start_time_edit.textChanged.connect(self.update_elapsed_label)
        start_time_col.addWidget(self.start_time_edit)

        stop_time_col = QVBoxLayout()
        self.stop_time_label = QLabel("Stop Time")
        stop_time_col.addWidget(self.stop_time_label)

        self.stop_time_edit = QLineEdit()
        self.stop_time_edit.setFixedHeight(30)
        self.stop_time_edit.setText("")
        self.stop_time_edit.setStyleSheet("font-size: 14px; font-family: Menlo;")
        self.stop_time_edit.textEdited.connect(self.disable_stop_time_autoupdate)
        stop_time_col.addWidget(self.stop_time_edit)

        time_row.addLayout(start_time_col)
        time_row.addLayout(stop_time_col)
        self.main_layout.addLayout(time_row)

        self.save_backdated_button = QPushButton("🔙🕰 Save Backdated Log")
        self.save_backdated_button.clicked.connect(self.save_backdated_log)
        self.main_layout.addWidget(self.save_backdated_button)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-size: 10px; font-family: Menlo; text-align: left;")
        self.main_layout.addWidget(QLabel("Today's Logged Tasks"))
        self.main_layout.addWidget(self.log_display)

        summary_header = QHBoxLayout()
        summary_header.addWidget(QLabel("Task Summary"))
        summary_header.addStretch()
        self.main_layout.addLayout(summary_header)

        summary_filter_row = QHBoxLayout()
        self.summary_start_enabled = QCheckBox("From")
        self.summary_start_enabled.toggled.connect(self.on_summary_filter_changed)
        summary_filter_row.addWidget(self.summary_start_enabled)

        self.summary_start_date = QDateEdit()
        self.summary_start_date.setCalendarPopup(True)
        self.summary_start_date.setDisplayFormat("yyyy-MM-dd")
        self.summary_start_date.setDate(QDate.currentDate().addMonths(-1))
        self.summary_start_date.setEnabled(False)
        self.summary_start_date.dateChanged.connect(self.update_task_summary)
        summary_filter_row.addWidget(self.summary_start_date)

        self.summary_end_enabled = QCheckBox("To")
        self.summary_end_enabled.toggled.connect(self.on_summary_filter_changed)
        summary_filter_row.addWidget(self.summary_end_enabled)

        self.summary_end_date = QDateEdit()
        self.summary_end_date.setCalendarPopup(True)
        self.summary_end_date.setDisplayFormat("yyyy-MM-dd")
        self.summary_end_date.setDate(QDate.currentDate())
        self.summary_end_date.setEnabled(False)
        self.summary_end_date.dateChanged.connect(self.update_task_summary)
        summary_filter_row.addWidget(self.summary_end_date)
        self.main_layout.addLayout(summary_filter_row)

        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setStyleSheet("font-size: 10px; font-family: Menlo; text-align: left;")
        self.main_layout.addWidget(self.summary_display)

        utility_row = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        utility_row.addWidget(self.refresh_button)

        self.manage_activities_button = QPushButton("Manage Activities")
        self.manage_activities_button.clicked.connect(self.open_activity_manager)
        utility_row.addWidget(self.manage_activities_button)

        self.calendar_button = QPushButton("Show Calendar")
        self.calendar_button.clicked.connect(self.toggle_calendar)
        utility_row.addWidget(self.calendar_button)
        self.main_layout.addLayout(utility_row)

        self.open_data_folder_button = QPushButton("Open Data Folder")
        self.open_data_folder_button.clicked.connect(self.open_data_folder)
        self.main_layout.addWidget(self.open_data_folder_button)

        self.update_log_display()

    def on_summary_filter_changed(self):
        self.summary_start_date.setEnabled(self.summary_start_enabled.isChecked())
        self.summary_end_date.setEnabled(self.summary_end_enabled.isChecked())
        self.update_task_summary()

    def selected_summary_dates(self):
        start_date = None
        end_date = None
        if self.summary_start_enabled.isChecked():
            qdate = self.summary_start_date.date()
            start_date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        if self.summary_end_enabled.isChecked():
            qdate = self.summary_end_date.date()
            end_date = datetime.date(qdate.year(), qdate.month(), qdate.day())
        return start_date, end_date

    def update_task_summary(self):
        start_date, end_date = self.selected_summary_dates()
        try:
            summary_df, total_time = summarise_log(start_date, end_date)
        except ValueError as exc:
            self.summary_display.setText(str(exc))
            return

        if summary_df.empty:
            self.summary_display.setText(self.summary_period_label() + "\n\nNo log entries in this period.")
            return

        display_df = summary_df.copy()
        display_df["Percent of Time"] = display_df["Percent of Time"].astype(str) + "%"
        log_text = display_df.to_string(index=False, justify="left")
        total_hours = total_time / 3600
        self.summary_display.setText(
            f"{self.summary_period_label()}\n"
            f"Total logged: {total_hours:.2f} hours\n"
            f"{'-' * 52}\n{log_text}"
        )

    def summary_period_label(self):
        start_date, end_date = self.selected_summary_dates()
        if start_date and end_date:
            return f"Task Summary: {start_date.isoformat()} to {end_date.isoformat()}"
        if start_date:
            return f"Task Summary: since {start_date.isoformat()}"
        if end_date:
            return f"Task Summary: through {end_date.isoformat()}"
        return "Task Summary: all time"

    def refresh_task_dropdown(self, preserve_text=True):
        current_text = self.task_dropdown.currentText().strip() if preserve_text else ""
        self.task_dropdown.blockSignals(True)
        self.task_dropdown.clear()
        self.task_dropdown.addItem("")
        self.task_dropdown.addItems(load_activities())
        if current_text:
            self.task_dropdown.setCurrentText(current_text)
        self.task_dropdown.blockSignals(False)

    def activity_data_changed(self, old_name=None, new_name=None):
        global current_task
        if old_name and new_name and current_task == old_name:
            current_task = new_name
            self.status_label.setText(f"⏳ Active Task - {new_name}")
        self.refresh_task_dropdown()
        self.update_log_display()

    def refresh(self):
        self.refresh_task_dropdown()
        self.start_date_edit.setText(datetime.datetime.now().strftime("%Y-%m-%d"))
        self.update_log_display()

    def update_log_display(self):
        df = filter_today_logs()
        log_text = df.to_string(index=False) if not df.empty else "No log entries yet."
        self.log_display.setText(log_text)
        self.update_task_summary()
        if hasattr(self, "calendar_panel"):
            self.calendar_panel.refresh()

    def toggle_calendar(self):
        visible = not self.calendar_panel.isVisible()
        self.calendar_panel.setVisible(visible)
        self.calendar_button.setText("Hide Calendar" if visible else "Show Calendar")
        if visible:
            self.calendar_panel.refresh()
            self.resize(max(self.width(), 1240), max(self.height(), 900))
            QTimer.singleShot(0, self.calendar_panel.scroll_to_current_time)
        else:
            self.resize(430, self.height())

    def open_data_folder(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(DATA_DIR)))
        if not opened:
            QMessageBox.warning(self, "Unable to Open Folder", f"Data folder:\n{DATA_DIR}")

    def open_activity_manager(self):
        dialog = ActivityManagerDialog(self)
        dialog.exec_()
        self.activity_data_changed()

    def start_task(self):
        global current_task, start_time
        task = self.task_dropdown.currentText().strip()
        if not task:
            return

        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())

        add_activity(task)
        self.refresh_task_dropdown()
        self.task_dropdown.setCurrentText(task)

        current_task = task
        now = datetime.datetime.now()
        self.stop_time_autoupdate = True
        self.start_time_edit.setText(now.strftime("%H:%M:%S"))
        self.start_date_edit.setText(now.strftime("%Y-%m-%d"))
        start_time = now
        self.status_label.setText(f"⏳ Active Task - {task}")
        self.timer.start(1000)
        self.update_log_display()

    def stop_task(self):
        global current_task, start_time
        if current_task:
            edited_time_str = self.start_time_edit.text().strip()
            edited_date_str = self.start_date_edit.text().strip()
            try:
                combined_start = datetime.datetime.strptime(
                    f"{edited_date_str} {edited_time_str}", "%Y-%m-%d %H:%M:%S"
                )
            except ValueError:
                QMessageBox.warning(self, "Invalid Format", "Use YYYY-MM-DD for date and HH:MM:SS for time.")
                return

            save_log(current_task, combined_start, datetime.datetime.now())
            current_task = None
            start_time = None
            self.status_label.setText("✅ Timing stopped")
            self.timer.stop()
            self.refresh_task_dropdown()
            self.update_log_display()

    def save_backdated_log(self):
        task = self.task_dropdown.currentText().strip()
        start_date = self.start_date_edit.text().strip()
        start_time_str = self.start_time_edit.text().strip()
        stop_time_str = self.stop_time_edit.text().strip()

        if not task:
            QMessageBox.warning(self, "Missing Task", "Please enter or select a task.")
            return

        try:
            start_dt = datetime.datetime.strptime(f"{start_date} {start_time_str}", "%Y-%m-%d %H:%M:%S")
            stop_dt = datetime.datetime.strptime(f"{start_date} {stop_time_str}", "%Y-%m-%d %H:%M:%S")
            if stop_dt <= start_dt:
                QMessageBox.warning(self, "Invalid Times", "Stop time must be after start time.")
                return
        except ValueError:
            QMessageBox.warning(self, "Invalid Format", "Start and Stop time must be in HH:MM:SS format.")
            return

        save_log(task, start_dt, stop_dt)
        self.refresh_task_dropdown()
        self.task_dropdown.setCurrentText(task)
        self.status_label.setText("📌 Backdated log saved")
        self.update_log_display()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    tracker = TimeTrackerApp()
    tracker.show()
    sys.exit(app.exec_())
