from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'

client = MongoClient("mongodb+srv://bengkelinaja:bengkelinaja@cluster0.0q1zz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client['bengkelinaja']

users_collection = db['users']
produk_collection = db['produk']


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
    return redirect(url_for('home'))  

@app.route('/index')
def index():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login')) 
    return render_template('admin/index.html') 

@app.route('/produk')
def produk():
    if 'username' not in session:  # Periksa apakah pengguna sudah login
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('login'))

    # Ambil parameter kategori dan pencarian
    category = request.args.get('category', 'All')  # Default ke 'All'
    search = request.args.get('search', '').strip()  # Default ke string kosong jika tidak ada pencarian

    # Query MongoDB
    query = {}
    if category != 'All':  # Filter kategori
        query['category'] = category
    if search:  # Filter pencarian berdasarkan nama
        query['name'] = {'$regex': search, '$options': 'i'}  # Regex hanya untuk kolom nama (case-insensitive)

    produk_list = list(produk_collection.find(query))

    # Render template dengan produk yang difilter
    return render_template(
        'user/produk.html',
        produk_list=produk_list,
        selected_category=category,
        search=search
    )
     

@app.route('/checkout')
def checkout():
    if 'username' not in session:  # Jika pengguna belum login
        flash('You must be logged in to access this page.', 'warning')
     
        return redirect(url_for('login'))  # Arahkan ke halaman login
    return render_template('user/checkout.html')
 
@app.route('/check_order')
def check_order():
    if 'username' not in session:  # Jika pengguna belum login
        flash('You must be logged in to access this page.', 'warning')
        
        return redirect(url_for('login'))  # Arahkan ke halaman login
    return render_template('user/check_order.html') 

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('You must be logged in to access this page.', 'warning')
        
        return redirect(url_for('login'))  # Jika pengguna belum login, arahkan ke halaman login

    # Ambil data pengguna dari session
    user = users_collection.find_one({"username": session['username']})

    if request.method == 'POST':
        new_username = request.form['username']
        new_email = request.form['email']
        new_alamat = request.form['alamat']

        # Cek apakah username sudah ada
        if new_username != user['username'] and users_collection.find_one({"username": new_username}):
            return 'Username already taken, please choose another one!'

        # Perbarui data di MongoDB
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {
                "username": new_username,
                "email": new_email,
                "alamat": new_alamat
            }}
        )

        # Perbarui session dengan username baru
        session['username'] = new_username
        
        return redirect(url_for('profile'))  # Redirect ke halaman profile setelah berhasil update

    return render_template('user/profile.html', user=user)


@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    print("Session after logout:", session) 
    if 'username' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('home'))

@app.route('/tambah_produk', methods=['GET', 'POST'])
def tambah_produk():
    if request.method == 'POST':
        product_name = request.form['productName']
        product_description = request.form['productDescription']
        product_price = request.form['productPrice']
        product_category = request.form['productCategory']  # Ambil kategori dari form
        product_image = request.files['productImage']

        # Menyimpan gambar (optional, pastikan ada folder 'static/img/products')
        image_path = f"static/img/produk/{product_image.filename}"
        product_image.save(image_path)

        # Menyimpan data produk ke MongoDB
        produk_collection.insert_one({
            'name': product_name,
            'description': product_description,
            'price': product_price,
            'category': product_category,  # Tambahkan kategori ke MongoDB
            'image': image_path
        })

        flash("Produk berhasil ditambahkan!", 'success')
        return redirect(url_for('produk'))
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
