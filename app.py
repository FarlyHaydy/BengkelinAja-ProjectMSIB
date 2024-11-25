from flask import Flask, render_template, request, redirect, url_for, session
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient("mongodb+srv://bengkelinaja:bengkelinaja@cluster0.0q1zz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client['bengkelinaja']

users_collection = db['users']


@app.route('/', methods=['GET'])
def home():
    if 'username' in session:  
        if session['role'] == 'admin':  
            return redirect(url_for('index'))  
        return render_template('user/hompage.html') 
    return render_template('user/hompage.html') 

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Cari user di MongoDB
        user = users_collection.find_one({"username": username, "password": password})
        
        if user:
            session['username'] = username
            session['role'] = user['role']
            
            if user['role'] == 'admin':
                return redirect(url_for('index')) 
            else:
                return redirect(url_for('home')) 
        else:
            return 'Invalid credentials!' 
    
    return render_template('user/login.html')  

@app.route('/logout')
def user_logout(): 
    session.pop('username', None)  
    session.pop('role', None)  
    return redirect(url_for('home'))  


@app.route('/index')
def index():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login')) 
    return render_template('admin/index.html') 

@app.route('/produk')
def produk():
    return render_template('user/produk.html') 

@app.route('/checkout')
def checkout():
    return render_template('user/checkout.html')
 
@app.route('/check_order')
def check_order():
    return render_template('user/check_order.html') 

@app.route('/profile')
def profile():
    return render_template('user/profile.html') 

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    print("Session after logout:", session) 
    return redirect(url_for('home'))

@app.route('/tambah_produk', methods=['GET', 'POST'])
def tambah_produk():
    return render_template('admin/tambah_produk.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None 
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        alamat = request.form['alamat']
        
        
        if users_collection.find_one({"username": username}):
            error = 'Username already taken, please choose another one!'
        else:
            role = 'user' 
            users_collection.insert_one({
                'username': username,
                'password': password,
                'email': email,
                'alamat': alamat,
                'role': role
            })
            return redirect(url_for('home'))  
    
    return render_template('user/register.html', error=error)




@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
       
        return 'Email pemulihan telah dikirim!'
    
    return render_template('forgot_password.html') 

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
