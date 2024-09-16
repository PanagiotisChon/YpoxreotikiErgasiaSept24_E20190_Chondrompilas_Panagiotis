from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
import os
from datetime import datetime

# Flask App Initialization
app = Flask(__name__)
app.secret_key = 'a_random_key'

SERVER_HOST = os.environ.get('SERVER_HOST', 'localhost')
SERVER_PORT = int(os.environ.get('SERVER_PORT', 5000))
MONGO_DATABASE = os.environ.get('MONGO_DATABASE', 'DigiMeet')
MONGO_HOST = os.environ.get('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.environ.get('MONGO_PORT', 27017))

# MongoDB Client Initialization
client = MongoClient(MONGO_HOST, MONGO_PORT)
db = client[MONGO_DATABASE]
users_collection = db["users"]
events_collection = db["events"]



# Route για την εγγραφή χρηστών
@app.route('/register', methods=['GET', 'POST'])
def register():
    # Αν η μέθοδος του αιτήματος είναι POST (δηλαδή, αν η φόρμα έχει υποβληθεί)
    if request.method == 'POST':
        # Λήψη των δεδομένων από τη φόρμα
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        if name and surname and email and username and password:
            if users_collection.find_one({"email": email}):
                flash('Email already exists!', 'danger')
            elif users_collection.find_one({"username": username}):
                flash('Username already exists!', 'danger')
            else:
                user = {
                    'name': name,
                    'surname': surname,
                    'email': email,
                    'username': username,
                    'password': password,  
                    'role': 'user'
                }
                # Εισαγωγή του χρήστη στη συλλογή της βάσης δεδομένων
                users_collection.insert_one(user)
                flash('User registered successfully!', 'success')
                return redirect(url_for('login'))
        else:
            flash('All fields are required!', 'danger')
    
    return render_template('register.html')



# Route για το login χρηστών
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Λήψη του username και password από τη φόρμα login
        username = request.form['username']
        password = request.form['password']

        # Αναζήτηση του χρήστη στη συλλογή των χρηστών (users_collection) με βάση το username
        user = users_collection.find_one({"username": username})

        if not user:
            flash('Username not found', 'danger')
        elif user['password'] != password:
            flash('Incorrect password', 'danger')
        else:
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Logged in successfully!', 'success')
            return redirect(url_for('home'))

    return render_template('login.html')


# Route για την προβολή της αρχικής σελίδας μετά τήν σύνδεση
@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        role = session.get('role')
        return render_template('home.html', username=username, role=role)
    else:
        flash('Please login to perform this action.', 'danger')
        return redirect(url_for('login'))
    


# Route για το logout χρηστών
@app.route('/logout')
def logout():
     # Έλεγχος αν ο χρήστης είναι συνδεδεμένος   
    if 'username' not in session:
        flash('Please login to perform this action.', 'danger')
        return redirect(url_for('login'))
    
    # Αφαίρεση του 'username' και του role από το session αν υπάρχει
    session.pop('username', None)
    session.pop('role', None)
    flash('You have been logged out.', 'success')

    return redirect(url_for('login'))



# Route για την προσθήκη εκδήλωσης (διαθέσιμο για όλους τους χρήστες)
@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'username' not in session:
        flash('Please login to create an event.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Λήψη δεδομένων από τη φόρμα
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']
        event_type = request.form['event_type']

        # Έλεγχος αν υπάρχει ήδη εκδήλωση με τον ίδιο τίτλο
        existing_event = events_collection.find_one({'title': title})
        if existing_event:
            flash('An event with this title already exists. Please choose a different title.', 'danger')
            return render_template('add_event.html', title=title, description=description, date=date, time=time, location=location, event_type=event_type)

        # Επαλήθευση ημερομηνίας και ώρας
        event_datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        # Αν η ημερομηνία και η ώρα είναι στο παρελθόν, εμφάνιση μηνύματος λάθους
        if event_datetime < datetime.now():
            flash('Event date and time must be in the future.', 'danger')
            return render_template('add_event.html', title=title, description=description, date=date, time=time, location=location, event_type=event_type)

        # Δημιουργία του αντικειμένου εκδήλωσης
        event = {
            'title': title,
            'description': description,
            'date': date,
            'time': time,
            'location': location,
            'event_type': event_type,
            'creator': session['username'],  # Καταγραφή του δημιουργού της εκδήλωσης
            'participants': []  # Αρχικοποίηση του πίνακα συμμετοχών
        }
        events_collection.insert_one(event)
        flash('Event added successfully!', 'success')
        return redirect(url_for('my_events'))

    return render_template('add_event.html')



# Route για την εμφάνιση εκδηλώσεων που έχει δημιουργήσει ο χρήστης
@app.route('/my_events')
def my_events():
    if 'username' not in session:
        flash('Please login to view your events.', 'danger')
        return redirect(url_for('login'))
    
    username = session['username']  # Λήψη του username από το session
    now = datetime.now().strftime('%Y-%m-%d')
    events = list(events_collection.find({
        'date': {'$gte': now},  # Εύρεση εκδηλώσεων με ημερομηνία μεγαλύτερη ή ίση από την τρέχουσα
        'creator': username  # Εύρεση εκδηλώσεων που δημιουργήθηκαν από τον συνδεδεμένο χρήστη
    }).sort([('date', 1), ('time', 1)]))
    
    # Έλεγχος αν δεν υπάρχουν εκδηλώσεις για τον χρήστη
    if len(events) == 0:
        flash('You have not created any event yet.', 'info')

    return render_template('my_events.html', events=events)



# Route για την προβολή των εκδηλώσεων στις οποίες συμμετέχει ο χρήστης
@app.route('/my_participations')
def my_participations():
    if 'username' not in session:
        flash('Please login to view your participations.', 'danger')
        return redirect(url_for('login'))

    username = session['username']
    now = datetime.now().strftime('%Y-%m-%d')
    events = list(events_collection.find({
        'participants': {'$elemMatch': {'username': username}},  # Αναζήτηση σε εκδηλώσεις όπου υπάρχει συμμετοχή του χρήστη
        'date': {'$gte': now}
    }).sort([('date', 1), ('time', 1)]))

    if len(events) == 0:
        flash('You are not participating in any upcoming events.', 'info')

    return render_template('my_participations.html', events=events)



# Route για την αφαίρεση της συμμετοχής από μια εκδήλωση
@app.route('/remove_participation/<event_title>', methods=['POST'])
def remove_participation(event_title):
    if 'username' not in session:
        flash('Please login to remove your participation.', 'danger')
        return redirect(url_for('login'))

    username = session['username']
    event = events_collection.find_one({"title": event_title})

    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('my_participations'))

    # Λήψη της λίστας συμμετοχών της εκδήλωσης
    event_participants = event.get('participants', [])
    updated = False

    # Δημιουργία νέας λίστας συμμετεχόντων χωρίς τον τρέχοντα χρήστη
    new_participants = [participant for participant in event_participants if participant['username'] != username]
    
    # Έλεγχος αν υπήρξε αλλαγή στη λίστα συμμετοχών
    if len(new_participants) < len(event_participants):
        # Αν υπάρχει αλλαγή (δηλαδή, ο χρήστης συμμετείχε και αφαιρέθηκε), ενημέρωση της βάσης δεδομένων
        events_collection.update_one(
            {"title": event_title},
            {"$set": {"participants": new_participants}}
        )
        flash('Your participation has been removed.', 'success')
    else:
        flash('You are not participating in this event.', 'warning')

    return redirect(url_for('my_participations'))
    


# Route για την προβολή όλων των εκδηλώσεων
@app.route('/all_events')
def all_events():
    if 'username' not in session:
        flash('Please login to view all events.', 'danger')
        return redirect(url_for('login'))
    
    now = datetime.now().strftime('%Y-%m-%d')
    events = list(events_collection.find({
        'date': {'$gte': now}
    }).sort([('date', 1), ('time', 1)]))
    
    if len(events) == 0:
        flash('No Events found.', 'info')

    return render_template('all_events.html', events=events)



# Route για την αναζήτηση εκδηλώσεων
@app.route('/search_events', methods=['GET', 'POST'])
def search_events():
    if 'username' not in session:
        flash('Please login to search for events.', 'danger')
        return redirect(url_for('login'))

    # Αν η μέθοδος είναι POST, σημαίνει ότι ο χρήστης υποβάλει τα κριτήρια αναζήτησης
    if request.method == 'POST':
        # Λήψη των τιμών που υποβλήθηκαν από τη φόρμα
        title = request.form.get('title').strip()
        event_type = request.form.get('event_type').strip()
        location = request.form.get('location').strip()

        # Έλεγχος αν όλα τα πεδία είναι κενά
        if not title and not event_type and not location:
            flash('Please enter at least one search criteria.', 'warning')
            return render_template('search_events.html')

        # Δημιουργία ενός κενού ερωτήματος για την αναζήτηση στη βάση δεδομένων
        query = {}
        now = datetime.now().strftime('%Y-%m-%d')
        query['date'] = {'$gte': now}  # Αναζήτηση μόνο για μελλοντικές εκδηλώσεις

        # Προσθήκη των κριτηρίων αναζήτησης στο ερώτημα αν είναι συμπληρωμένα
        if title:
            query['title'] = {'$regex': f'^{title}$', '$options': 'i'}
        if event_type:
            query['event_type'] = {'$regex': f'^{event_type}$', '$options': 'i'}
        if location:
            query['location'] = {'$regex': f'^{location}$', '$options': 'i'}

        # Αναζήτηση για εκδηλώσεις με τον τίτλο που δόθηκε
        if title:
            title_results = list(events_collection.find({'title': query['title']}))
            if not title_results:
                flash('No events found matching your criteria.', 'warning')
                return render_template('search_events.html')

        # Αναζήτηση για εκδηλώσεις με τον τύπο εκδήλωσης που δόθηκε
        if event_type:
            event_type_results = list(events_collection.find({'event_type': query['event_type']}))
            if not event_type_results:
                flash('No events found matching your criteria.', 'warning')
                return render_template('search_events.html')

        # Αναζήτηση για εκδηλώσεις με την τοποθεσία που δόθηκε
        if location:
            location_results = list(events_collection.find({'location': query['location']}))
            if not location_results:
                flash('No events found matching your criteria.', 'warning')
                return render_template('search_events.html')

        # Τελική αναζήτηση με συνδυασμό των πεδίων
        final_results = list(events_collection.find(query).sort([('date', 1), ('time', 1)]))

        if not final_results:
            flash('No events found matching your criteria.', 'warning')
            return render_template('search_events.html')
        
        # Εμφάνιση των αποτελεσμάτων αναζήτησης στη σελίδα `search_results.html`
        return render_template('search_results.html', events=final_results)

    return render_template('search_events.html')



# Route για την αναλυτική προβολή ενός event και δήλωση συμμετοχής σε αυτό
@app.route('/view_event/<event_title>', methods=['GET', 'POST'])
def view_event(event_title):
    if 'username' not in session:
        flash('Please login to view event details.', 'danger')
        return redirect(url_for('login'))

    event = events_collection.find_one({"title": event_title})

    if not event:
        flash('Event not found.', 'danger')
        return redirect(url_for('all_events'))

    # Αν η μέθοδος του αιτήματος είναι POST, σημαίνει ότι ο χρήστης υποβάλει δεδομένα για την κατάσταση συμμετοχής
    if request.method == 'POST':
        # Λήψη της νέας κατάστασης συμμετοχής από τη φόρμα
        participation = request.form.get('participation')
        username = session['username']

        # Λήψη της λίστας των συμμετοχών από την εκδήλωση
        event_participants = event.get('participants', [])
        updated = False

        # Ενημέρωση ή προσθήκη συμμετοχής
        for participant in event_participants:
            if participant['username'] == username:
                # Αν ο χρήστης είναι ήδη συμμετοχών, ενημέρωση της κατάστασης συμμετοχής
                participant['ans'] = participation
                updated = True
                break

        if not updated:
            # Αν ο χρήστης δεν είναι ήδη στη λίστα συμμετοχών, προσθήκη του με την κατάσταση συμμετοχής (yes or not sure)
            event_participants.append({'username': username, 'ans': participation})

        # Ενημέρωση της εκδήλωσης στη βάση δεδομένων με τις νέες συμμετοχές
        events_collection.update_one(
            {"title": event_title},
            {"$set": {"participants": event_participants}}
        )

        flash('Your participation status has been updated.', 'success')
        return redirect(url_for('view_event', event_title=event_title))

    return render_template('view_event.html', event=event)



# Route για την διαχείρηση (edit/delete) των εκδηλώσεων που ο χρήστης έχει δημιουργήσει 
@app.route('/manage_my_events')
def manage_my_events():
    if 'username' not in session:
        flash('Please login to manage your events.', 'danger')
        return redirect(url_for('login'))
    
    now = datetime.now().strftime('%Y-%m-%d')
    username = session['username']
    events = list(events_collection.find({
        'date': {'$gte': now},
        'creator': username}).sort([('date', 1), ('time', 1)]))
    
    if len(events) == 0:
        flash('No Events found.', 'info')

    return render_template('manage_my_events.html', events=events)



# Route για την ενημέρωση των εκδηλώσεων του χρήστη
@app.route('/edit_event', methods=['GET', 'POST'])
def edit_event():
    if 'username' not in session:
        flash('Please login to edit your event.', 'danger')
        return redirect(url_for('login'))

    # Αν η μέθοδος αιτήματος είναι POST, σημαίνει ότι ο χρήστης στέλνει δεδομένα για επεξεργασία
    if request.method == 'POST':
        password = request.form['password']
        old_title = request.form['old_title']  # Παλιός τίτλος της εκδήλωσης
        new_title = request.form['title']       # Νέος τίτλος της εκδήλωσης
        user = users_collection.find_one({'username': session['username']})

        # Έλεγχος αν ο χρήστης υπάρχει και αν η παλιά του κωδικός είναι σωστή
        if not user or user['password'] != password:
            flash('Incorrect password. Please try again.', 'danger')
            return render_template('edit_event.html', event={
                'title': old_title, 
                'description': request.form['description'],
                'date': request.form['date'],
                'time': request.form['time'],
                'location': request.form['location'],
                'event_type': request.form['event_type']
            })

        # Εύρεση της εκδήλωσης με βάση τον παλιό τίτλο και τον δημιουργό
        event = events_collection.find_one({'title': old_title, 'creator': session['username']})
        if not event:
            flash('Event not found or you are not authorized to edit this event.', 'danger')
            return redirect(url_for('manage_my_events'))

        # Λήψη των νέων δεδομένων για την εκδήλωση
        description = request.form['description']
        date = request.form['date']
        time = request.form['time']
        location = request.form['location']
        event_type = request.form['event_type']

        # Έλεγχος αν η νέα ημερομηνία/ώρα είναι στο παρελθόν
        event_datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        if event_datetime < datetime.now():
            flash('Event date and time must be in the future.', 'danger')
            return render_template('edit_event.html', event={
                'title': new_title,
                'description': description,
                'date': date,
                'time': time,
                'location': location,
                'event_type': event_type
            })

        # Έλεγχος αν υπάρχει ήδη εκδήλωση με τον νέο τίτλο
        if old_title != new_title and events_collection.find_one({'title': new_title}):
            flash('An event with this new title already exists.<br>Please choose a different title.', 'danger')
            return render_template('edit_event.html', event={
                'title': old_title,
                'description': description,
                'date': date,
                'time': time,
                'location': location,
                'event_type': event_type
            })

        # Ενημέρωση της εκδήλωσης στη βάση δεδομένων
        events_collection.update_one(
            {'title': old_title, 'creator': session['username']},
            {'$set': {
                'title': new_title,
                'description': description,
                'date': date,
                'time': time,
                'location': location,
                'event_type': event_type
            }}
        )
        flash('Event updated successfully!', 'success')
        return redirect(url_for('my_events'))

    # Αν η μέθοδος αιτήματος είναι GET, εμφανίζεται η φόρμα επεξεργασίας με τα τρέχοντα δεδομένα της εκδήλωσης
    title = request.args.get('title')
    if not title:
        flash('No event title provided.', 'danger')
        return redirect(url_for('manage_my_events'))

    event = events_collection.find_one({'title': title, 'creator': session['username']})
    if not event:
        flash('Event not found or you are not authorized to edit this event.', 'danger')
        return redirect(url_for('manage_my_events'))

    return render_template('edit_event.html', event=event)



# Route για την διαγραφή των εκδηλώσεων
@app.route('/delete_event', methods=['POST'])
def delete_event():
    if 'username' not in session:
        flash('Please login to delete your event.', 'danger')
        return redirect(url_for('login'))

    password = request.form['password']
    title = request.form['title']
    user = users_collection.find_one({'username': session['username']})

    # Έλεγχος αν ο κωδικός του χρήστη είναι σωστός
    if user['password'] != password:
        flash('Incorrect password. Please try again.', 'danger')
        return redirect(url_for('manage_my_events'))

    event = events_collection.find_one({'title': title, 'creator': session['username']})
    if not event:
        flash('Event not found or you are not authorized to delete this event.', 'danger')
        return redirect(url_for('manage_my_events'))

    # Διαγραφή της εκδήλωσης από τη βάση δεδομένων
    events_collection.delete_one({'title': title, 'creator': session['username']})
    flash(f'Event "{title}" deleted successfully!', 'success')
    
    return redirect(url_for('manage_my_events'))



# Route για την προβολή των users από τον admin
@app.route('/list_users')
def list_users():
    # Έλεγχος αν ο χρήστης είναι συνδεδεμένος και έχει τον ρόλο 'admin'
    if 'username' not in session or session['role'] != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('login'))
    
    # Αν ο χρήστης είναι admin, ανακτά τη λίστα με όλους τους χρήστες που έχουν ρόλο 'user'
    users = list(users_collection.find({'role': 'user'}))
    if len(users) == 0:
        flash('No Users found.', 'info')
    return render_template('list_users.html', users=users)



# Route για την διαγραφή των users
@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if 'username' not in session or session['role'] != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('home'))

    # Διαγραφή των events που έχει δημιουργήσει ο χρήστης
    events_collection.delete_many({'creator': username})

    # Αφαίρεση του χρήστη από τα participants όλων των events
    events_collection.update_many(
        {},  # Ενημέρωση όλων των events στη βάση δεδομένων
        {'$pull': {'participants': {'username': username}}}  # Αφαίρεση του χρήστη από τη λίστα participants
    )

    # Διαγραφή του χρήστη από τη βάση δεδομένων
    result = users_collection.delete_one({'username': username})
    
    if result.deleted_count > 0:
        flash(f'User {username} has been deleted along with their events and participations.', 'success')
    else:
        flash('User not found.', 'danger')
    
    return redirect(url_for('list_users'))



# Route για την διαγραφή οποιουδήποτε event απο τον admin
@app.route('/delete_event_admin/<title>', methods=['POST'])
def delete_event_admin(title):
    if 'username' not in session or session.get('role') != 'admin':
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('home'))
    
    result = events_collection.delete_one({'title': title})
    
    if result.deleted_count > 0:
        flash(f'Event {title} has been deleted.', 'success')
    else:
        flash('Event not found.', 'danger')
    
    return redirect(url_for('all_events'))

    

# Δημιουργία του admin αν δεν υπάρχει
def create_admin():
    admin_user = users_collection.find_one({'username': 'admin'})
    if not admin_user:
        admin_user = {
            'name': 'Admin',
            'surname': 'Admin surname',
            'email': 'admin@gmail.com',
            'username': 'admin',
            'password': 'admin321',
            'role': 'admin'
        }
        users_collection.insert_one(admin_user)


# Run the Flask App
if __name__ == '__main__':
    create_admin()   # Δημιουργία του χρήστη admin κατά την εκκίνηση της εφαρμογής
    app.run(debug=True, host=SERVER_HOST, port=SERVER_PORT)
