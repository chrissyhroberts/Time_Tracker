# -*- coding: utf-8 -*-

import sys
import pandas as pd
import os
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QTextEdit, QComboBox, QSizePolicy, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
import matplotlib.pyplot as plt
from io import BytesIO

ACTIVITIES_FILE = "activities.csv"
LOG_FILE = os.path.join(os.getcwd(), "./time_log.csv")
current_task = None
start_time = None

def load_activities():
    """ Load and return a sorted list of activities from CSV file. """
    if os.path.exists(ACTIVITIES_FILE):
        df = pd.read_csv(ACTIVITIES_FILE)
        activities = df['Activities'].dropna().unique().tolist()
        return sorted(activities, key=str.casefold)  # Case-insensitive sorting
    return []

def save_activities(activities):
    """ Save activities to CSV file in sorted order (preserving original case). """
    activities = sorted(set(activities), key=str.casefold)  # Remove duplicates case-insensitively
    df = pd.DataFrame(activities, columns=['Activities'])
    df.to_csv(ACTIVITIES_FILE, index=False)

def save_log(task, start, end):
    """ Save time tracking log entry. """
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
    """ Retrieve logs for the current day. """
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
    def update_elapsed_label(self):
        """ Update elapsed time label dynamically. """
        if start_time:
            elapsed_seconds = int((datetime.datetime.now() - start_time).total_seconds())
            formatted_time = f"{elapsed_seconds // 3600:02}:{(elapsed_seconds % 3600) // 60:02}:{elapsed_seconds % 60:02}"
            self.elapsed_time_label.setText(f"Elapsed Time: {formatted_time}")
    
    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed_label)

    def initUI(self):
        """ Initialize UI components. """
        self.setWindowTitle("Time Tracker")
        self.main_layout = QVBoxLayout()
        
        # Status Label
        self.status_label = QLabel("No active task")
        self.main_layout.addWidget(self.status_label)
        
        # Drop-down for selecting or entering an activity (starts blank)
        self.task_dropdown = QComboBox()
        self.task_dropdown.setEditable(True)  # Allows user to type a new task
        self.task_dropdown.addItem("")  # Start with blank selection
        self.task_dropdown.addItems(load_activities())  # Load activities sorted
        self.task_dropdown.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.main_layout.addWidget(self.task_dropdown)

        # Start Button
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.start_task)
        self.main_layout.addWidget(self.start_button)

        # Stop Button
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_task)
        self.main_layout.addWidget(self.stop_button)

        # Refresh Button
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        self.main_layout.addWidget(self.refresh_button)

        # Elapsed Time Label
        self.elapsed_time_label = QLabel("Elapsed Time: 00:00:00")
        self.main_layout.addWidget(self.elapsed_time_label)

        # Log Display
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setStyleSheet("font-size: 8px; font-family: Menlo; text-align: left;")

        self.main_layout.addWidget(self.log_display)

        # Pie Chart Display
        self.pie_chart_label = QLabel()
        self.main_layout.addWidget(self.pie_chart_label)

        self.setLayout(self.main_layout)
        self.update_log_display()

    def update_pie_chart(self):
        """ Generate and update pie chart for task distribution with smaller font. """
        df = filter_today_logs()
        if not df.empty:
            df['Duration'] = df['Duration'].apply(lambda x: sum(int(t) * 60 ** i for i, t in enumerate(reversed(x.split(':')))))
            task_durations = df.groupby('Task')['Duration'].sum()
            
            plt.figure(figsize=(3, 3))
            
            wedges, texts, autotexts = plt.pie(
                task_durations, labels=task_durations.index, autopct='%1.1f%%', 
                pctdistance=0.6, labeldistance=0.4, textprops={'fontsize': 6}  # 👈 Smaller font
            )
            
            # Reduce the font size of labels and percentages
            for text in texts:
                text.set_fontsize(6)  # 👈 Smaller label font
            for autotext in autotexts:
                autotext.set_fontsize(6)  # 👈 Smaller percentage font
            
            plt.axis('equal')  # Keep the pie chart circular
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100)
            plt.close()
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            self.pie_chart_label.setPixmap(pixmap)
        
        
    def refresh(self):
        """ Refresh the drop-down list and update logs. """
        self.task_dropdown.clear()
        self.task_dropdown.addItem("")  # Keep initial blank selection
        self.task_dropdown.addItems(load_activities())
        self.update_log_display()

    def update_log_display(self):
        """ Update log display with today's logs. """
        df = filter_today_logs()
        log_text = df.to_string(index=False) if not df.empty else "No log entries yet."
        self.log_display.setText(log_text)
        self.update_pie_chart()  # Ensure pie chart updates

    def show_warning(self, message):
        """ Display a warning message box. """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setText(message)
        msg.setWindowTitle("Warning")
        msg.exec_()

    def start_task(self):
        """ Start timing a selected or newly entered task. """
        global current_task, start_time
        task = self.task_dropdown.currentText().strip()

        if not task:
            self.show_warning("Please enter a valid task before starting.")
            return

        current_activities = load_activities()
        lower_case_activities = {activity.lower(): activity for activity in current_activities}

        if task.lower() in lower_case_activities:
            task = lower_case_activities[task.lower()]
        else:
            current_activities.append(task)
            save_activities(current_activities)
            self.refresh()

        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())

        current_task = task
        start_time = datetime.datetime.now()
        self.status_label.setText(f"⏳ Timing started for {task}")
        self.timer.start(1000)
        self.update_log_display()

    def stop_task(self):
        """ Stop current task and log time. """
        global current_task, start_time
        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())
            current_task = None
            start_time = None
            self.status_label.setText("✅ Timing stopped")
            self.timer.stop()
            self.update_log_display()
        else:
            self.show_warning("No active task to stop.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    tracker = TimeTrackerApp()
    tracker.show()
    sys.exit(app.exec_())
