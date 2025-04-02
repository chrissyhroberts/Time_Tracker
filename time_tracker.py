# -*- coding: utf-8 -*-

import sys
import pandas as pd
import os
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QComboBox, QSizePolicy, QMessageBox
from PyQt5.QtCore import QTimer, Qt

ACTIVITIES_FILE = "activities.csv"
LOG_FILE = os.path.join(os.getcwd(), "./time_log.csv")
current_task = None
start_time = None

def load_activities():
    if os.path.exists(ACTIVITIES_FILE):
        df = pd.read_csv(ACTIVITIES_FILE)
        activities = df['Activities'].dropna().unique().tolist()
        return sorted(activities, key=str.casefold)
    return []

def save_activities(activities):
    activities = sorted(set(activities), key=str.casefold)
    df = pd.DataFrame(activities, columns=['Activities'])
    df.to_csv(ACTIVITIES_FILE, index=False)

def save_log(task, start, end):
    start_unix = start.timestamp()
    end_unix = end.timestamp()
    duration_seconds = int(end_unix - start_unix)
    duration = f"{duration_seconds // 3600:02}:{(duration_seconds % 3600) // 60:02}:{duration_seconds % 60:02}"
    new_entry = pd.DataFrame([[start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S'), duration, task]],
                              columns=["StartTime", "EndTime", "Duration", "Task"])
    if os.path.exists(LOG_FILE):
        df = pd.read_csv(LOG_FILE)
    else:
        df = pd.DataFrame(columns=["StartTime", "EndTime", "Duration", "Task"])
    df = pd.concat([df, new_entry], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)

def filter_today_logs():
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        return pd.DataFrame(columns=["StartTime", "EndTime", "Duration", "Task"])
    df = pd.read_csv(LOG_FILE)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    df = df[df['StartTime'].str.startswith(today)]
    if not df.empty:
        df['StartTime'] = pd.to_datetime(df['StartTime'], errors='coerce').dt.strftime('%H:%M')
        df['EndTime'] = pd.to_datetime(df['EndTime'], errors='coerce').dt.strftime('%H:%M')
        df = df[['StartTime', 'EndTime', "Duration", "Task"]]
    return df.tail(5)

class TimeTrackerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed_label)

    def update_elapsed_label(self):
        global start_time
        if current_task:
            try:
                edited_time_str = self.start_time_edit.toPlainText().strip()
                manual_time = datetime.datetime.strptime(edited_time_str, '%H:%M:%S').time()
                today = datetime.datetime.now().date()
                effective_start = datetime.datetime.combine(today, manual_time)
            except ValueError:
                effective_start = start_time or datetime.datetime.now()

            elapsed_seconds = int((datetime.datetime.now() - effective_start).total_seconds())
            if elapsed_seconds < 0:
                elapsed_seconds = 0
            formatted_time = f"{elapsed_seconds // 3600:02}:{(elapsed_seconds % 3600) // 60:02}:{elapsed_seconds % 60:02}"
            self.elapsed_time_label.setText(f"Elapsed Time: {formatted_time}")

    def initUI(self):
        self.setWindowTitle("Time Tracker")
        self.main_layout = QVBoxLayout()

        self.status_label = QLabel("No active task")
        self.main_layout.addWidget(self.status_label)

        self.task_dropdown = QComboBox()
        self.task_dropdown.setEditable(True)
        self.task_dropdown.addItem("")
        self.task_dropdown.addItems(load_activities())
        self.task_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.task_dropdown)

        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_task)
        self.main_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_task)
        self.main_layout.addWidget(self.stop_button)

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        self.main_layout.addWidget(self.refresh_button)

        self.start_time_label = QLabel("Start Time (HH:MM:SS):")
        self.main_layout.addWidget(self.start_time_label)

        self.start_time_edit = QTextEdit()
        self.start_time_edit.setFixedHeight(30)
        self.start_time_edit.setText("")
        self.start_time_edit.setStyleSheet("font-size: 14px; font-family: Menlo;")
        self.start_time_edit.textChanged.connect(lambda: self.timer.start(1000))  # Ensure timer is ticking
        self.start_time_edit.textChanged.connect(self.update_elapsed_label)
        self.main_layout.addWidget(self.start_time_edit)

        self.elapsed_time_label = QLabel("Elapsed Time: 00:00:00")
        self.elapsed_time_label.setStyleSheet("font-size: 20px;")
        self.main_layout.addWidget(self.elapsed_time_label)

        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-size: 10px; font-family: Menlo; text-align: left;")
        self.main_layout.addWidget(QLabel("Today's Logged Tasks"))
        self.main_layout.addWidget(self.log_display)

        self.summary_display = QTextEdit()
        self.summary_display.setReadOnly(True)
        self.summary_display.setStyleSheet("font-size: 10px; font-family: Menlo; text-align: left;")
        self.main_layout.addWidget(QLabel("Task Summary"))
        self.main_layout.addWidget(self.summary_display)

        self.setLayout(self.main_layout)
        self.update_log_display()

    def update_task_summary(self):
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            self.summary_display.setText("No log entries yet.")
            return
        df = pd.read_csv(LOG_FILE)
        if df.empty:
            self.summary_display.setText("No log entries yet.")
            return
        df['Duration'] = df['Duration'].apply(lambda x: sum(int(t) * 60 ** i for i, t in enumerate(reversed(x.split(':')))))
        task_durations = df.groupby('Task')['Duration'].sum()
        total_time = task_durations.sum()
        task_durations_hours = task_durations / 3600
        task_percentage = (task_durations / total_time) * 100
        summary_df = pd.DataFrame({
            "Task": task_durations_hours.index,
            "Total Hours": task_durations_hours.round(2),
            "Percent of Time": task_percentage.round(1)
        }).sort_values(by="Percent of Time", ascending=False)
        summary_df["Percent of Time"] = summary_df["Percent of Time"].astype(str) + "%"
        log_text = summary_df.to_string(index=False, justify='left')
        self.summary_display.setText(f"Task Summary\n{'-'*40}\n{log_text}")

    def refresh(self):
        self.task_dropdown.clear()
        self.task_dropdown.addItem("")
        self.task_dropdown.addItems(load_activities())
        self.update_log_display()

    def update_log_display(self):
        df = filter_today_logs()
        log_text = df.to_string(index=False) if not df.empty else "No log entries yet."
        self.log_display.setText(log_text)
        self.update_task_summary()

    def start_task(self):
        global current_task, start_time
        task = self.task_dropdown.currentText().strip()
        if not task:
            return
        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())
        current_task = task
        now = datetime.datetime.now()
        self.start_time_edit.setText(now.strftime('%H:%M:%S'))
        start_time = now
        self.status_label.setText(f"⏳ Timing started for {task}")
        self.timer.start(1000)
        self.update_log_display()

    def stop_task(self):
        global current_task, start_time
        if current_task:
            edited_time_str = self.start_time_edit.toPlainText().strip()
            try:
                manual_time = datetime.datetime.strptime(edited_time_str, '%H:%M:%S').time()
                today = datetime.datetime.now().date()
                start_time = datetime.datetime.combine(today, manual_time)
            except ValueError:
                QMessageBox.warning(self, "Invalid Time Format", "Please enter the start time in HH:MM:SS format.")
                return
            save_log(current_task, start_time, datetime.datetime.now())
            current_task = None
            start_time = None
            self.status_label.setText("✅ Timing stopped")
            self.timer.stop()
            self.update_log_display()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    tracker = TimeTrackerApp()
    tracker.show()
    sys.exit(app.exec_())
