### file: README.md
### file: README.md

# RushCheck 🟢🔴

AI-Powered Campus Congestion Monitoring System
GITHUB LINK: https://github.com/NotKenpachi/195_Project.git

---

## 🔍 Project Overview

RushCheck is a full-stack web application that uses computer vision to analyze
crowd congestion in campus spaces. It provides real-time and historical insights
into how busy different locations are, helping students make informed decisions
about where to study, eat, or go.

Unlike traditional navigation tools, RushCheck analyzes **indoor and campus
spaces** using AI-based people detection from video feeds.

---

## 🚀 Features

- AI-powered people detection using YOLO
- Real-time congestion analysis
- Hierarchical location structure:
  - Main Locations (buildings)
  - Sub Locations (sections inside buildings)
- Animated progress bars and color-coded indicators
- Historical congestion lookup
- Admin dashboard for managing locations
- Google Maps directions for main locations
- Responsive UI with Tailwind CSS

---

## 🧠 Congestion Logic

Congestion is determined using percentage of capacity:

percent = (people_detected / capacity) \* 100

yaml
Copy code

| Level  | Percentage |
| ------ | ---------- |
| Low    | < 40%      |
| Medium | 40–60%     |
| High   | > 60%      |

This logic is applied consistently across:

- Sub-location checks
- Main-location aggregation
- UI indicators and progress bars

---

## 🗄️ Database Schema

The application uses **SQLite** with four tables:

### 1. `main_locations`

Stores buildings or large areas.

- id (PK)
- name
- capacity
- image
- address

### 2. `sub_locations`

Stores sections inside a main location.

- id (PK)
- main_location_id (FK → main_locations.id)
- name
- capacity
- image
- video

### 3. `status`

Stores congestion results for sub locations.

- id (PK → sub_locations.id)
- location_name
- average_people
- capacity
- percent
- level
- updated_at

### 4. `admin_users`

Stores admin login credentials.

- username (PK)
- password_hash

---

## 🧩 How Data Flows

1. Admin uploads video for a sub location
2. User clicks **Check**
3. Frontend sends request to `/api/analyze`
4. YOLO processes the video
5. Results are stored in the database
6. UI updates instantly
7. Results can be retrieved later via **Previous**

---

## 📁 Project Structure

rushcheck/
│
├── app.py # Flask backend and API
├── data.sqlite # SQLite database
├── utils/
│ └── detection.py # YOLO people detection logic
│
├── static/
│ ├── js/
│ │ └── script.js # Frontend interactivity
│ ├── uploads/
│ │ ├── images/ # Location images
│ │ └── videos/ # Analysis videos
│ └── css/
│ └── custom.css
│
├── templates/
│ ├── layout.html # Shared layout
│ ├── home.html # Landing page
│ ├── spaces.html # Main locations
│ ├── sub_locations.html # Sub location details
│ ├── admin_dashboard.html
│ └── admin_login.html
│
└── README.md

yaml
Copy code

---

## 🛠️ Setup Instructions

### 1️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
2️⃣ Install Dependencies
bash
Copy code
pip install flask flask-login opencv-python ultralytics werkzeug
3️⃣ Run the Application
bash
Copy code
python app.py
App will be available at:

cpp
Copy code
http://127.0.0.1:5000
🔐 Admin Login
Default credentials:

makefile
Copy code
Username: Admin195B
Password: admin1
(Admin password is hashed in the database.)

🗺️ Google Maps Integration
Main locations include a Map button that opens Google Maps directions using:

ruby
Copy code
https://www.google.com/maps/search/?api=1&query=<address>
This allows users to navigate to the building containing sub locations.

```

# RushCheck — Local Run

1. Ensure Python and pip are installed.
2. Place video files under `videos/` and thumbnails under `static/images/` matching keys in `LOCATIONS` in `app.py`.
3. Install dependencies:
   pip install -r requirements.txt
4. Run the server:
   python app.py
5. Visit http://127.0.0.1:5000/

Notes:

- First run of YOLO may download model weights.
- The app stores results in `data.sqlite` in the project root.

```

```

```
# RushCheck — Local Run

1. Ensure Python and pip are installed.
2. Place video files under `videos/` and thumbnails under `static/images/` matching keys in `LOCATIONS` in `app.py`.
3. Install dependencies:
   pip install -r requirements.txt
4. Run the server:
   python app.py
5. Visit http://127.0.0.1:5000/

Notes:
- First run of YOLO may download model weights.
- The app stores results in `data.sqlite` in the project root.
```
