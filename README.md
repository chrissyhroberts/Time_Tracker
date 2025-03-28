# Open Time Tracker


## Description

This project is a time-tracking application built using PyQt5 and pandas. It allows users to log their work activities, track time spent on tasks, and view daily logs and summary statistics.
I built this because I was frustrated with apps such as Toggl which have annoying paywalls and subscription models. 


All the data are saved to CSV files on your machine. There's no cloud, no syncs and no frills. 

<img width="442" alt="Screenshot 2025-03-28 at 11 34 38" src="https://github.com/user-attachments/assets/3df80bc1-2fc1-47a3-a21f-ad197502adc5" />

## Features

* Start and stop time tracking for selected tasks
* Auto-save time logs in CSV format
* Display of today's logs and summary statistics
* Task dropdown with editable input for new tasks
* Auto-refresh feature to update logs and task list
  
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



