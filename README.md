# Open Time Tracker

<img width="413" alt="Screenshot 2025-04-02 at 18 49 41" src="https://github.com/user-attachments/assets/ba3cac07-d4f2-4b3f-aedc-de556e109812" />

## Description

This project is a time-tracking application built using PyQt5 and pandas. It allows users to log their work activities, track time spent on tasks, and view daily logs and summary statistics.
I built this because I was frustrated with apps such as Toggl which have annoying paywalls and subscription models. 


All the data are saved to CSV files on your machine. There's no cloud, no syncs and no frills. 


## Features


V1.0.0
* Start and stop time tracking for selected tasks
* Auto-save time logs in CSV format
* Display of today's logs and summary statistics
* Task dropdown with editable input for new tasks
* Auto-refresh feature to update logs and task list

V1.1.0
* Added support for backdated log entries with date, start, and stop time inputs
*  Implemented elapsed time label that updates in real time
*  Enabled partial backdating via manual entry of start time before stopping task
*  Display and update of today's task log and task summary now more responsive
*  Added error handling for invalid datetime inputs
*  Improved UI layout with clearer labeling and font styling
*  Refactored duration and summary calculation logic for consistency

V1.1.1

* Auto-updating 'Stop Time' field every second using a QTimer.
* Manual override detection: if user edits the field, auto-update stops.
* Restart auto-update when a new task is started.
* Refresh now updates start date to today’s date.

## Installation

Ensure you have Python installed. Then, install the required dependencies:

`pip install -r requirements.txt`

Alternatively, install dependencies manually:

`pip install pandas PyQt5`

## Usage

To run the application, execute:

`python time_tracker.py`

On my mac, I used applescript to make an 'app' that runs the script. This allows me to put an icon in my dock. 


## Configuration

The application uses the following files:

`activities.csv` - Stores the list of activities/tasks. New tasks are automatically added by the system, or you can manually edit
`time_log.csv` - Stores the time tracking logs as below


|StartTime|EndTime|Duration|Task|
|---------|-------|--------|----|
|2025-03-27 14:47:40|2025-03-27 14:47:45|00:00:04|Exam Board|
|2025-03-27 14:47:48|2025-03-27 14:47:53|00:00:04|Research|
|2025-03-27 14:48:00|2025-03-27 14:48:08|00:00:07|Ethics|
|2025-03-27 14:49:51|2025-03-27 14:49:55|00:00:03|Exam Board|
|2025-03-27 14:49:56|2025-03-27 14:49:59|00:00:02|Research|


```
File Structure

project_root/
│── main.py
│── activities.csv  (auto-generated if missing)
│── time_log.csv  (auto-generated if missing)
│── requirements.txt
│── README.md
```
## License

This project is licensed under the MIT License. See the LICENSE file for details.



