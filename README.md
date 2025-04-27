# TeirLink [new frontiers]

a Secure Mentor-Mentee Matching App
This project is a secure mentor-mentee matching platform, inspired by swipe-style interfaces (like Tinder) but designed for classified roles such as cybersecurity, intelligence, and defense.
Users can browse profiles and request mentorship based on clearance levels, roles, and expertise.

Features
Secure swipe-based matching system

Role and clearance-level display

Flask backend for serving pages and handling logic

MongoDB for storing user profiles and matches

Formal UI design for professional environments

Tech Stack
Backend: Flask (Python)

Database: MongoDB 

Frontend: HTML, CSS, JavaScript

Setup Instructions
1. Clone the repository
bash
Copy
Edit
git clone https://github.com/your-username/secure-mentor-match.git
cd secure-mentor-match
2. Set up a virtual environment
bash
Copy
Edit
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install dependencies
bash
Copy
Edit
pip install -r requirements.txt
4. Configure MongoDB
Make sure you have a MongoDB server running.
Create a .env file in the root directory and add:

ini
Copy
Edit
MONGO_URI=mongodb://localhost:27017/your-database-name
SECRET_KEY=your-secret-key
5. Run the application
bash
Copy
Edit
flask run
The app will be available at http://localhost:5000

Project Structure
rust
Copy
Edit
secure-mentor-match/
│
├── static/
│   ├── css/
│   ├── js/
│
├── templates/
│   ├── home.html
│   ├── match.html
│
├── app.py
├── models.py
├── requirements.txt
├── README.md
└── .env
Example Profile Fields
Name

Role (e.g., "Cybersecurity Analyst")

Clearance Level (e.g., "Top Secret", "Confidential")

Years of Experience

Skills / Expertise Areas

Future Improvements
Swipe animations (left/right) using JavaScript

Match notifications

Real-time messaging between matched users

Admin dashboard for approving mentors/mentees

Clearance verification integration

License
This project is licensed under the MIT License.

