from bson import ObjectId
from flask import Flask, render_template, request, flash, session, url_for
from werkzeug.utils import redirect
from flask_mail import Mail, Message
from pymongo import MongoClient 
import random
import secrets
from config import configurations
from datetime import datetime

app = Flask(__name__)
client = MongoClient('mongodb://localhost:27017/')
app.db = client.Microblog
app.secret_key = secrets.token_hex(16)
app.config['MAIL_SERVER'] = configurations['MAIL_SERVER']
app.config['MAIL_PORT'] = configurations['MAIL_PORT']
app.config['MAIL_USE_TLS'] = configurations['MAIL_USE_TLS']
app.config['MAIL_USE_SSL'] = configurations['MAIL_USE_SSL']
app.config['MAIL_USERNAME'] = configurations['MAIL_USERNAME']
app.config['MAIL_PASSWORD'] = configurations['MAIL_PASSWORD']
app.config['MAIL_DEFAULT_SENDER'] = configurations['MAIL_DEFAULT_SENDER']

mail = Mail(app)

def get_unique_username(user):
    flag = True
    for item in app.db.credentials.find({}):
        if user == item.get('username'):
            flag = False
            break
    return flag

def generate_otp():
    return random.randint(111111, 999999)

def send_email(email, subject, body, msg):
    message = Message(subject, recipients=[email], body=body)
    
    try:
        mail.send(message)
        print(f'{msg} has been sent successfully to {email}')
    except Exception as e:
        print(f'Error in sending email: {str(e)}')

def get_user_details(username):
    user_details = app.db.credentials.find_one({'username': username})
    return user_details

def get_user_email(username):
    user_details = app.db.credentials.find_one({'username': username})
    return user_details['email']

def notify_followers(username, title):
    followers = app.db.followers.find_one({username: {'$exists':True}})
    followee = get_user_details(username)
    if followers:
        for follower in followers[username]:
            follower_email = get_user_email(follower)
            subject = f"🚀 New Blog Alert: {followee['first_name'].capitalize()} {followee['last_name'].capitalize()} just Dropped a Must-Read Post!"
            body = f"""
            Hi There,

            🎉 Great news! {followee['first_name'].capitalize()} {followee['last_name'].capitalize()} just published a brand-new blog titled "{title}" and it is packed with insights you'll love.

            Don't miss out to read it now and join the conversation!

            stay tuned for more amazing updates,

            Microblog Team
            """
            send_email(follower_email, subject, body, msg='msg to follower')

def remove_delete_user(username):
    for i in app.db.followers.find({}):
        for k,v in i.items():
            if isinstance(v, list) and username in v:
                app.db.followers.update_one(
                    {k:{'$exists':True}},
                    {'$pull':{k:username}}
                )
    

@app.route('/')
def home():
    user = ''
    if 'username' in session:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details['first_name'].capitalize()} {user_details['last_name'].capitalize()}'
    entries = [
        (
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['author'],
            entry['_id']
        )for entry in app.db.entries.find({})
    ]
    return render_template('home.html', user= user, entries= entries[::-1])

@app.route('/login', methods = ['GET', 'POST'])
def login():
    print('reqeust.form', request.form)
    if request.method =='POST':
        print(request)
        username = request.form['username']
        password = request.form['password']
        for user in app.db.credentials.find({}):
            if username == user['username'] and password == user['password']:
                session['username'] = username
                return redirect('/')
    return render_template('login.html')

@app.route('/signup', methods = ['GET', 'POST'])
def signup():
    if request.method =='POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        if get_unique_username(username):
            session['username'] = username
        else:
            flash('Username already exist. Please choose different username,', 'error')
            return render_template('signup.html')
        email = request.form['email']
        otp = generate_otp()
        subject = 'Microbog - OTP Validation'
        body = f'Your OTP for Microblog Sign Up is: {otp}'
        send_email(email, subject, body, msg='OTP')
        session['otp'] = otp
        session['first_name'] = first_name
        session['last_name'] = last_name
        session['email'] = email
        session['password'] = request.form['password']
        return render_template('otp.html', email=email)
    return render_template('signup.html')

@app.route('/verify_otp', methods = ['POST'])
def verify_otp():
    user_otp = request.form.get('otp')
    saved_otp =session['otp']

    if user_otp and saved_otp and user_otp == str(saved_otp):
        username = session.get('username')
        password = session.get('password')
        email = session.get('email')
        first_name = session.get('first_name')
        last_name = session.get('last_name')
        app.db.credentials.insert_one(
            {
                'username': username,
                'password': password,
                'first_name': first_name,
                'last_name': last_name,
                'email': email,
            }
        )

        user = f'{first_name.capitalize()} {last_name.capitalize()}'
        subject = 'Welcome to Microblog!'
        body = f'Dear {user}, \n\tThank you for choosing Microblog! Your account has been created successfully. Dive into our platform and discover a world of possibilities. If you have any queries or suggestion, our team is there to help you out.\n\n Best Regards, \nMicroblog Team'
        send_email(email, subject, body, msg='onboarding mail')
        return redirect('/')
    else:
        return redirect('/signup')
    
@app.route('/logout')
def logout():
    if'username' in session:
        session.pop('username')

    return redirect('/')


@app.route('/about')
def about():
    user = ''
    if 'username' in session:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details['first_name'].capitalize()} {user_details['last_name'].capitalize()}'
    return render_template('about.html', user=user)

@app.route('/user_page', methods= ['GET', 'POST'])
def user_page():
    if 'username' not in session:
        return redirect('/')
    user = ''
    if 'username' in session:
        username = session['username']
        user_details = get_user_details(username)
        user = f'{user_details['first_name'].capitalize()} {user_details['last_name'].capitalize()}'
        if app.db.entries.find({}):
            entries = [
                (
                    entry['title'],
                    entry['content'],
                    entry['created_at'],
                    entry['author'],
                    entry['_id']
                )for entry in app.db.entries.find({}) if entry['username'] ==session['username']
            ]
    return render_template('user_page.html', user=user, entries=entries)

@app.route('/newblog', methods=['GET', 'POST'])
def newblog():
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    user = f'{user_details['first_name'].capitalize()} {user_details['last_name'].capitalize()}'
    if request.method == 'POST':
        blog_title = request.form.get('title')
        blog_content = request.form.get('content')
        formatted__datetime = datetime.now().strftime("%Y-%m-%d %H:%M")
        app.db.entries.insert_one({
            'username': username,
            'author': user,
            'title': blog_title,
            'content': blog_content,
            'created_at': formatted__datetime 
        })

        subject = '🚀 Your blog post is live!'
        body = f'Dear {user}, \n\tExciting news! Your new blog post, {blog_title}, is now live on Microblog!. 🎉 Thank you for sharing your insights! Your contribution make our community thrive. Looking forward to more from you!\n\n best regards, \nMicroblog Team.'
        email = get_user_email(username)
        send_email(email, subject, body, msg='New Blog')
        notify_followers(username, blog_title)
        return redirect('/user_page')

    return render_template('new_blog.html', user=user)

@app.route('/view/<string:entry_id>', methods = ['GET'])
def view(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    if request.method == 'GET':
        entry = app.db.entries.find_one({'_id':ObjectId(entry_id)})
        return render_template('view.html', entry=entry, user=user_details)
    
@app.route('/update_blog/<string:entry_id>', methods=['GET', 'POST'])
def upadate_blog(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    if request.method =='GET':
        entry = app.db.entries.find_one({'_id':ObjectId(entry_id)})
        return render_template('update_blog.html', entry=entry, user=user_details)
    elif request.method =='POST':
        updated_title = request.form.get('updated_title')
        update_content = request.form.get('updated_content')
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

        result = app.db.entries.update_one(
            {'_id': ObjectId(entry_id)},
            {'$set': {'title': updated_title, 'content': update_content, 'created_at': updated_at}}
        )

        if result.modified_count >0:
            print('Blog Entry updated successfully...')

        return redirect('/user_page')
    

@app.route('/delete_blog/<string:entry_id>', methods=['GET', 'POST'])
def delete_blog(entry_id):
    if 'username' not in session:
        return redirect('/')
    username = session['username']
    user_details = get_user_details(username)
    if request.method =='GET':
        entry = app.db.entries.find_one({'_id':ObjectId(entry_id)})
        return render_template('delete_blog.html', entry=entry, user=user_details)
    elif request.method == 'POST':
        result = app.db.entries.delete_one(
            {'_id':ObjectId(entry_id)}
        )

        print('Blog entry deleted successfully...')

        return redirect('/user_page')
    

@app.route('/user_profile/<string:username>')
def user_profile(username):
    if 'username' not in session:
        return redirect('/')
    session_username = session['username']
    profile_user = get_user_details(username)
    profile_user = f'{profile_user['first_name'].capitalize()} {profile_user['last_name'].capitalize()}'
    contribution = [
        (
            entry['author'],
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['_id']
        )
        for entry in app.db.entries.find({}) if entry['username'] == username
    ]
    
    is_own_profile = True if session_username == username else False
    email = get_user_email(username)
    follower = app.db.followers.find_one({username:{'$exists': True}})
    if follower:
        follower_count = len(follower[username])
        is_following = True if session_username in follower[username] else False
    else:
        follower_count = 0
        is_following = False

    return render_template('profile.html', is_own_profile=is_own_profile, contribution= contribution, username = username,  email=email, user= profile_user, follower_count=follower_count, is_following=is_following)
        
@app.route('/profile')
def profile():
    if 'username' not in session:
        return redirect('/')
    session_username = get_user_details(session['username'])
    session_user = f'{session_username['first_name'].capitalize()} {session_username['last_name'].capitalize()}'
    contribution = [
        (
            entry['author'],
            entry['title'],
            entry['content'],
            entry['created_at'],
            entry['_id']
        )
        for entry in app.db.entries.find({}) if entry['username'] == session['username']
    ]

    email = get_user_email(session['username'])
    follower = app.db.followers.find_one({session['username']:{'$exists': True}})
    if follower:
        follower_count = len(follower[session['username']])
    else:
        follower_count = 0

    return render_template('profile.html',is_own_profile= True, follower_count= follower_count, contribution= contribution, username = session['username'],  email=email, user= session_user)


@app.route('/follow/<string:username>', methods= ['POST'])
def follow(username):
    if 'username' not in session:
        return redirect('/')
    current_user = session['username']
    if not app.db.followers.find_one({username:{'$exists': True}}):
        app.db.followers.insert_one({username:[current_user]})
    else:
        app.db.followers.update_one(
            {username: {'$exists': True}},
            {'$push': {username:current_user}}


        )
    return redirect(url_for('user_profile', username=username))

@app.route('/unfollow/<string:username>', methods= ['POST'])
def unfollow(username):
    if 'username' not in session:
        return redirect('/')
    current_user = session['username']
    app.db.followers.update_one(
            {username: {'$exists': True}},
            {'$pull': {username:current_user}}
        )
    
    return redirect(url_for('user_profile', username=username))

@app.route('/delete_account', methods =['GET','POST'])
def delete_account():
    if 'username' not in session:
        return redirect('/')
    
    profile_user = get_user_details(session['username'])
    profile_user = f'{profile_user['first_name'].capitalize()} {profile_user['last_name'].capitalize()}'
    if request.method == 'POST':
        delete_option = request.form.get('delete_option')
        if delete_option == 'account_only':
            app.db.credentials.delete_one({'username': session['username']})
            remove_delete_user(session['username'])
            return redirect('/logout')
        elif delete_option == 'all_data':
            app.db.credentials.delete_one({'username': session['username']})
            app.db.entries.delete_many({'username': session['username']})
            remove_delete_user(session['username'])
            return redirect('/logout')
    return  render_template('delete_user.html')
    






    




if __name__ == '__main__':
    app.run(port=3000, debug=True)
