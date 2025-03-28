# Time_Tracker


## Description

This project is a time-tracking application built using PyQt5 and pandas. It allows users to log their work activities, track time spent on tasks, and view daily logs and summary statistics.

## Installation

Ensure you have Python installed. Then, install the required dependencies:

`pip install -r requirements.txt`

Alternatively, install dependencies manually:

`pip install pandas PyQt5`

## Usage

To run the application, execute:

`time_tracker.py`

## Features

* Start and stop time tracking for selected tasks

* Auto-save time logs in CSV format

* Display of today's logs and summary statistics

* Task dropdown with editable input for new tasks

* Auto-refresh feature to update logs and task list

## Configuration

The application uses the following files:

`activities.csv` - Stores the list of activities/tasks.

`time_log.csv` - Stores the time tracking logs.

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



