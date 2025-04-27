from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

# MongoDB setup - using MongoDB Atlas
def get_database():
    try:
        # Connection timeout set to 5000 milliseconds (5 seconds)
        client = MongoClient(
            'mongodb+srv://ajanimjohnson9:supertf123@m-tree.ecfxwa9.mongodb.net/mentree?retryWrites=true&w=majority',
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            retryWrites=True
        )
        
        # Test the connection
        client.admin.command('ping')
        print("Successfully connected to MongoDB Atlas!")
        return client.mentree
    except Exception as e:
        print(f"Error connecting to MongoDB Atlas: {e}")
        print("Attempting to connect to local MongoDB...")
        try:
            # Fallback to local MongoDB
            client = MongoClient('mongodb://localhost:27017/', 
                               serverSelectionTimeoutMS=5000)
            client.admin.command('ping')
            print("Connected to local MongoDB")
            return client.mentree
        except Exception as local_error:
            print(f"Error connecting to local MongoDB: {local_error}")
            print("Please ensure either MongoDB Atlas or local MongoDB is accessible")
            exit(1)

# Initialize database and collections
db = get_database()
users = db.users
matches_collection = db.matches
preferences = db.preferences
messages = db.messages

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.clearance_level = user_data.get('clearance_level', 'basic')
        self.role = user_data.get('role', 'mentee')  # 'mentee' or 'mentor'
        self.bio = user_data.get('bio', '')
        self.expertise = user_data.get('expertise', [])
        self.interests = user_data.get('interests', [])

@login_manager.user_loader
def load_user(user_id):
    user_data = users.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.context_processor
def utility_processor():
    return {
        'now': datetime.utcnow()
    }

@app.route("/")
def index():
    return render_template("index.html")

# Initialize rate limiter
limiter = Limiter(
    get_remote_address,  # Pass the key function directly
    app=app,  # Attach the app
    default_limits=["200 per day", "50 per hour"],  # Set default rate limits
    storage_uri="memory://"  # Use in-memory storage for rate limiting
)

@app.route("/login", methods=['GET', 'POST'])
@limiter.limit("5 per minute")  # Prevent brute force
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = users.find_one({'username': username})
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('index'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        clearance_level = request.form.get('clearance_level', 'basic')
        
        if users.find_one({'username': username}):
            flash('Username already exists')
            return redirect(url_for('register'))
        
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'clearance_level': clearance_level
        }
        users.insert_one(user_data)
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update user profile
        users.update_one(
            {'_id': ObjectId(current_user.id)},
            {'$set': {
                'bio': request.form.get('bio'),
                'expertise': request.form.getlist('expertise'),
                'interests': request.form.getlist('interests'),
                'role': request.form.get('role'),
                'linkedin': request.form.get('linkedin'),
                'github': request.form.get('github')
            }}
        )
        flash('Profile updated successfully!')
        return redirect(url_for('profile'))
    
    user_data = users.find_one({'_id': ObjectId(current_user.id)})
    return render_template('profile.html', user=user_data)

@app.route("/matches")
@login_required
def view_matches():
    pipeline = [
        {
            '$match': {
                '$or': [
                    {'mentee_id': ObjectId(current_user.id)},
                    {'mentor_id': ObjectId(current_user.id)}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentor_id',
                'foreignField': '_id',
                'as': 'mentor'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentee_id',
                'foreignField': '_id',
                'as': 'mentee'
            }
        },
        {
            '$unwind': '$mentor'
        },
        {
            '$unwind': '$mentee'
        },
        {
            '$addFields': {
                'other_user': {
                    '$cond': {
                        'if': {'$eq': ['$mentee_id', ObjectId(current_user.id)]},
                        'then': '$mentor',
                        'else': '$mentee'
                    }
                }
            }
        },
        {
            '$sort': {'matched_at': -1}
        }
    ]
    
    try:
        matches = list(matches_collection.aggregate(pipeline))
        
        # Process matches
        for match in matches:
            # Convert ObjectIds to strings
            match['_id'] = str(match['_id'])
            match['mentor_id'] = str(match['mentor_id'])
            match['mentee_id'] = str(match['mentee_id'])
            match['mentor']['_id'] = str(match['mentor']['_id'])
            match['mentee']['_id'] = str(match['mentee']['_id'])
            match['other_user']['_id'] = str(match['other_user']['_id'])
            
            # Get last message
            last_message = messages.find_one(
                {'match_id': ObjectId(match['_id'])},
                sort=[('created_at', -1)]
            )
            match['last_message'] = last_message['content'] if last_message else None

            # Ensure status exists
            if 'status' not in match:
                match['status'] = 'pending'

        return render_template('matches.html', matches=matches)
    except Exception as e:
        print(f"Error in view_matches: {str(e)}")
        return render_template('matches.html', matches=[])

@app.route("/discover")
@login_required
def discover():
    try:
        current_user_id = current_user.id
        
        # Create mock users with phone numbers and one guaranteed match
        mock_users = []
        for i in range(1, 10):
            mock_user = {
                '_id': ObjectId(),
                'username': f'Mock{i}',
                'clearance_level': 'basic',
                'bio': f'Expert with {random.randint(2, 15)} years of experience.',
                'expertise': random.sample(['Python', 'JavaScript', 'Cybersecurity', 'Data Science', 'AI', 'Cloud Computing', 'DevOps'], k=3),
                'interests': random.sample(['Hiking', 'Reading', 'Gaming', 'Traveling', 'Photography'], k=2),
                'phone': f'+1 (555) {random.randint(100,999)}-{random.randint(1000,9999)}',
                # Make Mock3 always match with the user
                'guaranteed_match': (i == 3)
            }
            mock_users.append(mock_user)
        
        # Shuffle but keep guaranteed match in first few cards
        non_guaranteed = [u for u in mock_users if not u.get('guaranteed_match')]
        guaranteed = [u for u in mock_users if u.get('guaranteed_match')]
        random.shuffle(non_guaranteed)
        
        # Put guaranteed match in the first 3 cards
        insert_position = random.randint(0, min(2, len(non_guaranteed)))
        non_guaranteed.insert(insert_position, guaranteed[0])
        
        return render_template('discover.html', potential_matches=non_guaranteed)
        
    except Exception as e:
        print(f"Error in discover: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route("/like/<user_id>", methods=['POST'])
@login_required
def like_user(user_id):
    try:
        # Use current_user instead of session
        current_user_id = current_user.id
        
        # Convert string IDs to ObjectId
        target_user_id = ObjectId(user_id)
        current_user_id = ObjectId(current_user_id)
        
        # Add the like to the current user's likes
        users.update_one(
            {'_id': current_user_id},
            {'$addToSet': {'likes': target_user_id}}
        )
        
        # Check if it's a match (if the other user has already liked current user)
        target_user = users.find_one({
            '_id': target_user_id,
            'likes': current_user_id
        })
        
        if target_user:
            # It's a match! Add to both users' matches
            users.update_one(
                {'_id': current_user_id},
                {'$addToSet': {'matches': target_user_id}}
            )
            users.update_one(
                {'_id': target_user_id},
                {'$addToSet': {'matches': current_user_id}}
            )
            return jsonify({'status': 'matched'})
        
        return jsonify({'status': 'liked'})
        
    except Exception as e:
        print(f"Error in like_user: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/pass/<user_id>", methods=['POST'])
@login_required
def pass_user(user_id):
    try:
        # Use current_user instead of session
        current_user_id = current_user.id
        
        # Convert string IDs to ObjectId
        target_user_id = ObjectId(user_id)
        current_user_id = ObjectId(current_user_id)
        
        # Add the user to passes
        users.update_one(
            {'_id': current_user_id},
            {'$addToSet': {'passes': target_user_id}}
        )
        
        return jsonify({'status': 'passed'})
        
    except Exception as e:
        print(f"Error in pass_user: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route("/dashboard")
@login_required
def dashboard():
    pipeline = [
        {
            '$match': {
                '$or': [
                    {'mentee_id': ObjectId(current_user.id)},
                    {'mentor_id': ObjectId(current_user.id)}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentor_id',
                'foreignField': '_id',
                'as': 'mentor'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentee_id',
                'foreignField': '_id',
                'as': 'mentee'
            }
        },
        {
            '$unwind': {
                'path': '$mentor',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$unwind': {
                'path': '$mentee',
                'preserveNullAndEmptyArrays': True
            }
        },
        {
            '$addFields': {
                'other_user': {
                    '$cond': {
                        'if': {'$eq': ['$mentee_id', ObjectId(current_user.id)]},
                        'then': '$mentor',
                        'else': '$mentee'
                    }
                }
            }
        }
    ]
    
    try:
        matches = list(matches_collection.aggregate(pipeline))
        
        # Process matches safely
        for match in matches:
            # Convert ObjectIds to strings
            match['_id'] = str(match['_id'])
            match['mentee_id'] = str(match['mentee_id'])
            match['mentor_id'] = str(match['mentor_id'])
            
            if 'mentor' in match and match['mentor']:
                match['mentor']['_id'] = str(match['mentor']['_id'])
            if 'mentee' in match and match['mentee']:
                match['mentee']['_id'] = str(match['mentee']['_id'])
            if 'other_user' in match and match['other_user']:
                match['other_user']['_id'] = str(match['other_user']['_id'])

            # Get last message
            try:
                last_message = messages.find_one(
                    {'match_id': ObjectId(match['_id'])},
                    sort=[('created_at', -1)]
                )
                match['last_message'] = last_message['content'] if last_message else None
            except Exception as e:
                print(f"Error fetching last message: {str(e)}")
                match['last_message'] = None

            # Ensure required fields exist
            if 'status' not in match:
                match['status'] = 'pending'
            if 'matched_at' not in match:
                match['matched_at'] = match.get('created_at', datetime.utcnow())

        return render_template('dashboard.html',
                             matches=matches,
                             current_user=current_user)
    except Exception as e:
        print(f"Error in dashboard: {str(e)}")
        return render_template('dashboard.html',
                             matches=[],
                             current_user=current_user)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        # Logic to handle password reset (e.g., send reset email)
        flash('If an account with that email exists, a password reset link has been sent.', 'info')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route("/mentee")
@login_required
def mentee_view():
    # Get all mentees except current user
    other_mentees = list(users.find({
        'role': 'mentee',
        '_id': {'$ne': ObjectId(current_user.id)}
    }))
    return render_template('mentee.html', mentees=other_mentees)

@app.route("/mentor")
@login_required
def mentor_view():
    # Get all mentors
    all_mentors = list(users.find({'role': 'mentor'}))
    # Mark some as premium randomly for demo
    for mentor in all_mentors:
        mentor['is_premium'] = random.choice([True, False])
    return render_template('mentor.html', mentors=all_mentors)

@app.route("/api/messages/<match_id>")
@login_required
def get_messages(match_id):
    # Verify user is part of the match
    match = matches_collection.find_one({
        '_id': ObjectId(match_id),
        'status': 'matched',
        '$or': [
            {'mentee_id': ObjectId(current_user.id)},
            {'mentor_id': ObjectId(current_user.id)}
        ]
    })
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    # Get all messages for this match
    all_messages = list(messages.find({
        'match_id': ObjectId(match_id)
    }).sort('created_at', 1))
    # If no messages and it's a mock user (starts with 'Mock'), create initial messages
    if not all_messages and (
        str(match['mentor_id']).startswith('Mock') or 
        str(match['mentee_id']).startswith('Mock')
    ):
        mock_user_id = match['mentor_id'] if str(match['mentor_id']).startswith('Mock') else match['mentee_id']
        mock_messages = [
            {
                'match_id': ObjectId(match_id),
                'sender_id': mock_user_id,
                'content': "Hi! Thanks for connecting! I'm excited to start our mentorship journey.",
                'created_at': match['matched_at']
            },
            {
                'match_id': ObjectId(match_id),
                'sender_id': mock_user_id,
                'content': "What areas would you like to focus on in our mentorship?",
                'created_at': match['matched_at'] + timedelta(minutes=1)
            }
        ]
        messages.insert_many(mock_messages)
        all_messages = mock_messages
    return jsonify([{
        '_id': str(msg['_id']),
        'sender_id': str(msg['sender_id']),
        'content': msg['content'],
        'created_at': msg['created_at'].isoformat()
    } for msg in all_messages])

@app.route("/api/messages/send", methods=['POST'])
@login_required
def send_message():
    data = request.json
    match_id = data.get('match_id')
    # Verify the match exists and user is part of it
    match = matches_collection.find_one({
        '_id': ObjectId(match_id),
        'status': 'matched',
        '$or': [
            {'mentee_id': ObjectId(current_user.id)},
            {'mentor_id': ObjectId(current_user.id)}
        ]
    })
    if not match:
        return jsonify({'error': 'Match not found'}), 404
    message = {
        'match_id': ObjectId(match_id),
        'sender_id': ObjectId(current_user.id),
        'content': data['content'],
        'created_at': datetime.utcnow()
    }
    messages.insert_one(message)
    return jsonify({'status': 'success'})

@app.route("/api/matches/<match_id>/delete", methods=['DELETE'])
@login_required
def delete_match(match_id):
    match = matches_collection.find_one({'_id': ObjectId(match_id)})
    # Only allow deletion of pending or passed matches
    if not match:
        return jsonify({'status': 'error', 'message': 'Match not found'}), 404
    if match['status'] == 'matched':
        return jsonify({'status': 'error', 'message': 'Cannot delete active matches'}), 403
    # Verify the current user is part of the match
    if str(match['mentee_id']) != str(current_user.id) and str(match['mentor_id']) != str(current_user.id):
        return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
    # Delete the match
    matches_collection.delete_one({'_id': ObjectId(match_id)})
    return jsonify({'status': 'success'})

@app.route("/chat/<match_id>")
@login_required
def chat(match_id):
    # Get match details with aggregation to include user data
    pipeline = [
        {
            '$match': {
                '_id': ObjectId(match_id),
                'status': 'matched',
                '$or': [
                    {'mentee_id': ObjectId(current_user.id)},
                    {'mentor_id': ObjectId(current_user.id)}
                ]
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentor_id',
                'foreignField': '_id',
                'as': 'mentor'
            }
        },
        {
            '$lookup': {
                'from': 'users',
                'localField': 'mentee_id',
                'foreignField': '_id',
                'as': 'mentee'
            }
        },
        {
            '$unwind': {
                'path': '$mentor',
                'preserveNullAndEmptyArrays': True  # Change true to True
            }
        },
        {
            '$unwind': {
                'path': '$mentee',
                'preserveNullAndEmptyArrays': True  # Change true to True
            }
        }
    ]
    match = list(matches_collection.aggregate(pipeline))
    if not match:
        flash('Match not found or not active')
        return redirect(url_for('dashboard'))
    match = match[0]  # Get first result
    # Determine other user
    if str(match['mentee_id']) == str(current_user.id):
        other_user = match['mentor']
        role_label = "Mentor"
    else:
        other_user = match['mentee']
        role_label = "Mentee"
    # Get chat messages
    chat_messages = list(messages.find({
        'match_id': ObjectId(match_id)
    }).sort('created_at', 1))
    # Convert ObjectIds to strings
    for msg in chat_messages:
        msg['_id'] = str(msg['_id'])
        msg['sender_id'] = str(msg['sender_id'])
    return render_template('chat.html',
                         match=match,
                         other_user=other_user,
                         role_label=role_label,
                         messages=chat_messages,
                         current_user_id=str(current_user.id))

# Add this function after your routes
def update_existing_matches():
    current_time = datetime.utcnow()
    try:
        # Update matches without matched_at or status
        matches_collection.update_many(
            {
                '$or': [
                    {'matched_at': None},
                    {'matched_at': {'$exists': False}},
                    {'status': {'$exists': False}}
                ]
            },
            {
                '$set': {
                    'matched_at': current_time,
                    'updated_at': current_time,
                    'status': 'pending'
                }
            }
        )
        print("Updated existing matches")
    except Exception as e:
        print(f"Error updating existing matches: {str(e)}")

@app.after_request
def add_security_headers(response):
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'"
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

if __name__ == "__main__":
    update_existing_matches()  # Update existing records
    app.run(debug=True)