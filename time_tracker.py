import sys  # Required for handling system-related functions, such as application exit
import pandas as pd
import os
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit  # Importing necessary PyQt widgets for GUI
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QPixmap
import matplotlib.pyplot as plt
from io import BytesIO  # QTimer is used to update elapsed time dynamically every second, Qt provides alignment options  # QTimer is used to update elapsed time dynamically every second

ACTIVITIES_FILE = "activities.csv"  # File storing activity list
LOG_FILE = os.path.join(os.getcwd(), "time_log.csv")  # File where tracked time is logged
current_task = None
start_time = None

def load_activities():  # Loads the list of activities from CSV file
    if os.path.exists(ACTIVITIES_FILE):
        df = pd.read_csv(ACTIVITIES_FILE)
        return df['Activities'].tolist()
    return ["Example Task"]

def save_log(task, start, end):  # Saves task start and stop times into log file
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

def filter_today_logs():  # Filters log entries to show only today’s activities and formats columns
    if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
        return pd.DataFrame(columns=["StartTime", "EndTime", "Duration", "Task"])
    
    df = pd.read_csv(LOG_FILE)
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    df = df[df['StartTime'].str.startswith(today)]  # Filter today's logs
    
    if not df.empty:
        df['StartTime'] = pd.to_datetime(df['StartTime'], errors='coerce').dt.strftime('%H:%M')  # Convert to HH:MM
        df['EndTime'] = pd.to_datetime(df['EndTime'], errors='coerce').dt.strftime('%H:%M')  # Convert to HH:MM
        df = df[['StartTime', 'EndTime', 'Duration', 'Task']]  # Ensure correct column order
    
    return df.tail(5)  # Show last 5 entries from today

class TimeTrackerApp(QWidget):  # Main GUI application class for time tracking
    def update_elapsed_label(self):
        if start_time:
            elapsed_seconds = int((datetime.datetime.now() - start_time).total_seconds())
            formatted_time = f"{elapsed_seconds // 3600:02}:{(elapsed_seconds % 3600) // 60:02}:{elapsed_seconds % 60:02}"
            self.elapsed_time_label.setText(f"Elapsed Time: {formatted_time}")  # Main GUI application class for time tracking
    def __init__(self):
        super().__init__()
        self.initUI()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_elapsed_label)

    def initUI(self):  # Initializes the GUI layout and elements
        self.setWindowTitle("Time Tracker")
        self.main_layout = QHBoxLayout()
        
        self.button_layout = QHBoxLayout()  # Adjusted button layout for better placement  # Smaller button layout under timing status  # Layout for top buttons
        self.left_layout = QVBoxLayout()  # Main vertical layout for buttons and labels
        self.status_label = QLabel("No active task")
        self.left_layout.addWidget(self.status_label)
        self.left_layout.addLayout(self.button_layout)  # Buttons placed just below status label
        self.elapsed_time_label = QLabel("Elapsed Time: 00:00:00")
        self.left_layout.addWidget(self.elapsed_time_label)
        
        self.buttons = []
        self.load_activity_buttons()
        
        self.stop_button = QPushButton("⏹")  # Stop button as an icon
        self.stop_button.setFixedSize(50, 50)  # Reduce button size  # Stop button as an icon
        self.stop_button.clicked.connect(self.stop_task)
        self.button_layout.addWidget(self.stop_button, alignment=Qt.AlignLeft)  # Align stop button left  # Center stop button  # Align stop button to the left
        
        self.refresh_button = QPushButton("🔄")  # Refresh button as an icon
        self.refresh_button.setFixedSize(50, 50)  # Reduce button size  # Refresh button as an icon
        self.refresh_button.clicked.connect(self.refresh)
        self.button_layout.addWidget(self.refresh_button, alignment=Qt.AlignCenter)  # Align refresh button right  # Center refresh button  # Align refresh button to the right
        
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.pie_chart_label = QLabel()
        self.right_layout = QVBoxLayout()
        self.pie_chart_container = QHBoxLayout()
        self.pie_chart_container.addWidget(self.pie_chart_label, alignment=Qt.AlignRight)  # Move further right
        self.right_layout.addLayout(self.pie_chart_container)  # Move pie chart to the left
        self.main_layout.addLayout(self.right_layout)  # Move pie chart to the right of the preview
        self.update_pie_chart()
        self.log_display.setStyleSheet("font-size: 10px; font-family: monospace;")
        self.update_log_display()
        
        self.main_layout.addLayout(self.button_layout)  # Add button layout below status message  # Add top layout first
        self.main_layout.addLayout(self.left_layout, stretch=1)  # Then add left layout
        self.right_layout.addWidget(self.log_display)  # Move preview to the right
        self.setLayout(self.main_layout)

    def load_activity_buttons(self):  # Dynamically loads buttons based on available activities
        for btn in self.buttons:
            btn.setParent(None)
        self.buttons.clear()
        for task in load_activities():
            btn = QPushButton(task)
            btn.clicked.connect(lambda checked, t=task: self.start_task(t))
            task_layout = QHBoxLayout()
            task_layout.addWidget(btn)
            self.left_layout.addLayout(task_layout)
            self.buttons.append(btn)
    
    def start_task(self, task):  # Starts a task, stopping any currently running task
        global current_task, start_time
        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())
        current_task = task
        start_time = datetime.datetime.now()
        self.status_label.setText(f"⏳ Timing started for {task}")
        self.elapsed_time_label.setText("Elapsed Time: 00:00:00")
        self.timer.start(1000)  # Update elapsed time every second
        self.update_log_display()

    def stop_task(self):  # Stops the current task and logs its duration
        global current_task, start_time
        if current_task:
            save_log(current_task, start_time, datetime.datetime.now())
            current_task = None
            start_time = None
            self.status_label.setText("✅ Timing stopped")
            self.elapsed_time_label.setText("Elapsed Time: 00:00:00")
            self.timer.stop()
            self.update_log_display()
        else:
            self.status_label.setText("⚠️ No active task to stop")

    def update_log_display(self):
        self.update_pie_chart()  # Refreshes the log display to show recent tasks
        df = filter_today_logs()  # Ensure only today's logs are displayed
        log_text = df.to_string(index=False) if not df.empty else "No log entries yet."
        self.log_display.setText(log_text)
    
    def update_pie_chart(self):
        df = pd.read_csv(LOG_FILE)  # Use full dataset to calculate time spent per task
        df = filter_today_logs()
        if not df.empty:
            df['Duration'] = df['Duration'].apply(lambda x: sum(int(t) * 60 ** i for i, t in enumerate(reversed(x.split(':')))))
            task_durations = df.groupby('Task')['Duration'].sum()
            plt.figure(figsize=(3, 3))
            wedges, texts, autotexts = plt.pie(task_durations,labels=task_durations.index,autopct='%1.1f%%', pctdistance=0.5,labeldistance=0.35 )            
            
            plt.axis('equal')
            buf = BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())
            self.pie_chart_label.setPixmap(pixmap)

    def refresh(self):  # Reloads activity buttons and updates log display
        self.load_activity_buttons()
        self.update_log_display()

if __name__ == '__main__':  # Runs the PyQt application when executed directly
    app = QApplication(sys.argv)
    tracker = TimeTrackerApp()
    tracker.show()
    sys.exit(app.exec_())
