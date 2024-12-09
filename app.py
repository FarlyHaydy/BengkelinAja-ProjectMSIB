from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from flask_mail import Mail, Message
import secrets
from datetime import datetime, timedelta
from twilio.rest import Client


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Inisialisasi MongoDB Client
client = MongoClient("mongodb+srv://bengkelinaja:bengkelinaja123@cluster0.0q1zz.mongodb.net/bengkelinaja?retryWrites=true&w=majority")
db = client['bengkelinaja']
users_collection = db['users']
produk_collection = db['produk']

# Konfigurasi Twilio
TWILIO_ACCOUNT_SID = 'your_twilio_account_sid'
TWILIO_AUTH_TOKEN = 'your_twilio_auth_token'
TWILIO_PHONE_NUMBER = 'your_twilio_phone_number'

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Konfigurasi Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'

mail = Mail(app)

@app.route('/', methods=['GET'])
def home():
    if 'username' in session:  
        if session['role'] == 'admin':  
            return redirect(url_for('index'))  
        return render_template('user/hompage.html') 
    return render_template('user/hompage.html') 

@app.route ('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_identifier = request.form['username']  # Bisa berupa username atau email
        password = request.form['password']
        
        # Cari user di MongoDB berdasarkan username ATAU email
        user = users_collection.find_one({
            "$or": [
                {"username": login_identifier}, 
                {"email": login_identifier}
            ],
            "password": password
        })
        
        if user:
            # Simpan informasi user di session
            session['username'] = user.get('username')
            session['role'] = user.get('role')
            session['email'] = user.get('email')
            session['alamat'] = user.get('alamat')

            if user['role'] == 'admin':
                return redirect(url_for('index'))  # Redirect ke halaman admin
            else:
                return redirect(url_for('home'))  # Redirect ke halaman user
        else:
            return 'Invalid credentials!'  # Error jika login gagal
    return redirect(url_for('home'))
 
@app.route('/index')
def index():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login')) 
    return render_template('admin/index.html') 

@app.route('/produk')
def produk():
    if 'username' not in session:  
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
     
@app.route('/add_to_checkout', methods=['POST'])
def add_to_checkout():
    data = request.get_json()
    product_id = data['product_id']
    product_name = data['product_name']
    product_price = data['product_price']
    product_image = data['product_image']
    quantity = int(data['quantity'])

    # Simpan informasi checkout di koleksi 'checkout' MongoDB
    checkout_collection = db['checkout']
    checkout_collection.insert_one({
        'username': session['username'],
        'email' : session['email'],
        'alamat' : session['alamat'],
        'product_id': product_id,
        'product_name': product_name,
        'product_price': product_price,
        'product_image': product_image,
        'quantity': quantity
    })

    return jsonify({'success': True}), 200

@app.route('/remove_from_checkout/<item_id>', methods=['POST'])
def remove_from_checkout(item_id):
    
    # Hapus item dari koleksi checkout
    checkout_collection = db['checkout']
    checkout_collection.delete_one({'_id': ObjectId(item_id)})

    return jsonify({'success': True}), 200


@app.route('/checkout')
def checkout():
    if 'username' not in session: 
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('login'))  

    # Ambil data checkout dari MongoDB untuk pengguna saat ini
    checkout_collection = db['checkout']
    checkout_items = list(checkout_collection.find(
        {'username': session['username'],
         'alamat' : session['alamat'],
         'email' : session['email']
         }))

   # Hitung total harga
    total_price = sum(float(item['product_price']) * item['quantity'] for item in checkout_items)

    # Convert total price to integer if needed
    total_price = int(total_price)  # Convert to integer if you want to remove decimal points

    return render_template('user/checkout.html', checkout_items=checkout_items, total_price=total_price)

@app.route('/check_order')
def check_order():
    if 'username' not in session:  
        flash('You must be logged in to access this page.', 'warning')
        
        return redirect(url_for('login'))  
    return render_template('user/check_order.html') 

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'username' not in session:
        flash('You must be logged in to access this page.', 'warning')
        
        return redirect(url_for('login'))  

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
        product_category = request.form['productCategory']  
        product_image = request.files['productImage']

        image_path = f"static/img/produk/{product_image.filename}"
        product_image.save(image_path)

        produk_collection.insert_one({
            'name': product_name,
            'description': product_description,
            'price': product_price,
            'category': product_category, 
            'image': image_path
        })

        flash("Produk berhasil ditambahkan!", 'success')
        return redirect(url_for('produk'))
    return render_template('admin/tambah_produk.html')

@app.route('/delete_produk/<product_id>', methods=['POST'])
def delete_produk(product_id):
    if 'username' not in session or session['role'] != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    produk_collection.delete_one({'_id': ObjectId(product_id)})
    return jsonify({'success': True}), 200

@app.route('/update_produk/<product_id>', methods=['GET', 'POST'])
def update_produk(product_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        product_name = request.form['productName']
        product_description = request.form['productDescription']
        product_price = request.form['productPrice']
        product_category = request.form['productCategory']  
        product_image = request.files['productImage'] if 'productImage' in request.files else None

        update_data = {
            'name': product_name,
            'description': product_description,
            'price': product_price,
            'category': product_category
        }

        if product_image:
            image_path = f"static/img/produk/{product_image.filename}"
            product_image.save(image_path)
            update_data['image'] = image_path

        produk_collection.update_one({'_id': ObjectId(product_id)}, {'$set': update_data})

        flash("Produk berhasil diperbarui!", 'success')
        return redirect(url_for('produk'))

    # Jika GET, ambil data produk untuk ditampilkan di form
    produk = produk_collection.find_one({'_id': ObjectId(product_id)})
    return render_template('admin/update_produk.html', produk=produk)
        
@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        alamat = request.form['alamat']

        # Periksa apakah username atau email sudah digunakan
        if users_collection.find_one({"username": username}):
            error = 'Username already taken, please choose another one!'
        elif users_collection.find_one({"email": email}):
            error = 'Email already registered!'
        elif users_collection.find_one({"phone": phone}):
            error = 'Phone number already registered!'
        else:
            role = 'user'
            users_collection.insert_one({
                'username': username,
                'password': password,
                'email': email,
                'phone': phone,  # Tambahkan nomor ponsel
                'alamat': alamat,
                'role': role
            })

            # Simpan data ke session
            session['username'] = username
            session['role'] = role
            session['email'] = email
            session['phone'] = phone
            session['alamat'] = alamat
            
            return redirect(url_for('home'))  # Redirect ke halaman utama setelah berhasil registrasi

    return render_template('user/register.html', error=error)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        identifier = request.form['identifier']  # Input email atau nomor telepon
        user = users_collection.find_one({
            "$or": [
                {"email": identifier},
                {"phone": identifier}
            ]
        })

        if user:
            reset_token = secrets.token_urlsafe(32)
            expiry_time = datetime.utcnow() + timedelta(hours=1)

            # Simpan token ke database
            db['password_reset_tokens'].insert_one({
                'user_id': user['_id'],
                'token': reset_token,
                'expiry': expiry_time
            })

            reset_link = f"http://localhost:5000/reset_password?token={reset_token}"

            if "@" in identifier:  # Kirim email
                try:
                    msg = Message(
                        "Reset Password Request",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[identifier]
                    )
                    msg.body = f"Hello {user['username']},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this message."
                    mail.send(msg)
                    flash('Email pemulihan telah dikirim!', 'success')
                except Exception as e:
                    flash(f"Gagal mengirim email: {e}", 'danger')
            else:  # Kirim WhatsApp
                try:
                    twilio_client.messages.create(
                        from_=TWILIO_PHONE_NUMBER,
                        to=f'whatsapp:{identifier}',
                        body=f"Hello {user['username']},\n\nClick the link below to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this message."
                    )
                    flash('Pesan pemulihan telah dikirim via WhatsApp!', 'success')
                except Exception as e:
                    flash(f"Gagal mengirim pesan WhatsApp: {e}", 'danger')
        else:
            flash('User tidak ditemukan!', 'warning')

    return render_template('user/forgot_password.html')

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    token = request.args.get('token')
    token_entry = db['password_reset_tokens'].find_one({'token': token})

    if not token_entry or token_entry['expiry'] < datetime.utcnow():
        flash('Token tidak valid atau telah kadaluarsa!', 'danger')
        return redirect(url_for('forgot_password'))

    if request.method == 'POST':
        new_password = request.form['password']
        user_id = token_entry['user_id']

        # Perbarui kata sandi
        users_collection.update_one({'_id': ObjectId(user_id)}, {'$set': {'password': new_password}})
        db['password_reset_tokens'].delete_one({'_id': token_entry['_id']})

        flash('Kata sandi berhasil diubah!', 'success')
        return redirect(url_for('login'))

    return render_template('user/reset_password.html')


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
