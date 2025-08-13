# Alarm-Clock
**A simple and customizable **Python-based alarm clock** with a web interface and audio notifications. This project allows you to set alarms, manage reminders, and get notified with sound at the scheduled time**


---

## 📖 About
This project is designed to create a **fully functional alarm clock** using Python.  
It is ideal for learning Python web development, threading, time management, and audio playback. The alarm clock supports multiple alarms and provides notifications in real-time.

---

## 🚀 Features
- ⏱ Set multiple alarms with time and optional AM/PM format  
- 🔔 Audio notification when alarm goes off  
- 🗂 Manage alarms (add, view, delete) via a simple interface  
- 🌐 Optional web interface to set and manage alarms  
- 💾 Persistent storage of alarms (via JSON or local files)  

---

## 🛠 Tech Stack
- **Language:** Python 3  
- **Libraries:** `datetime`, `time`, `threading`, `pygame`, `http.server`, `json`, `os`, `urllib`  
- **Audio Playback:** `pygame.mixer`  

---

## 📂 Project Structure
python-alarm-clock/
├── alarm.py # Main Python script for the alarm clock
├── alarms.json # Optional: stores saved alarms
├── assets/ # Audio files or icons
├── README.md # Project documentation

yaml
Copy
Edit

---

## ⚙️ Installation & Setup
1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/python-alarm-clock.git
   cd python-alarm-clock
**2. Install dependencies**
bash
Copy
Edit
pip install pygame


**3. Run the alarm clock**
bash
Copy
Edit
python alarm.py
**Follow the on-screen instructions to set alarms or open the web interface (if enabled).**

**📌 Usage**
Set alarms with specific hours and minutes (AM/PM supported).

The alarm will play a sound at the scheduled time.

Multiple alarms can run simultaneously.

Customize audio notifications by replacing the default sound file.

**🤝 Contributing**
Contributions are welcome!
Feel free to submit issues or pull requests for bug fixes, new features, or improvements.

**📜 License**
This project is licensed under the MIT License.
Use, modify, and share freely.

**📬 Contact**
Author: ISHIKA

LinkedIn:www.linkedin.com/in/ishika-goyal-6a1180309

⭐ If you like this project, don’t forget to star the repository!.
