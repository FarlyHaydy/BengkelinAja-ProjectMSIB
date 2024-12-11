from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'

UPLOAD_FOLDER = 'static/img/pembayaran'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

client = MongoClient("mongodb+srv://bengkelinaja:bengkelinaja@cluster0.0q1zz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client['bengkelinaja']

users_collection = db['users']
produk_collection = db['produk']
orders_collection = db['orders']
cart_collection = db['cart']


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
            session['role'] = user.get('role')  
            session['email'] = user.get('email', None)  
            session['alamat'] = user.get('alamat', None)  

            if user['role'] == 'admin':
                return redirect(url_for('index')) 
            else:
                return redirect(url_for('home')) 
        else:
            return 'Invalid credentials!' 
    return redirect(url_for('home'))  

@app.route('/admin/index')
def index():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login')) 
    return render_template('admin/index.html') 

@app.route('/produk')
def produk():
    if 'username' not in session:
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('login'))

    # Ambil parameter pencarian
    category = request.args.get('category', 'All')
    search = request.args.get('search', '').strip()

    # Buat query
    query = {}
    if category != 'All':
        query['category'] = category  # Filter kategori
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}  # Filter nama (case-insensitive)

    print(f"Query MongoDB: {query}")  # Debug query

    # Ambil data dari MongoDB
    produk_list = list(produk_collection.find(query))

    print(f"Produk ditemukan: {len(produk_list)}")  # Debug jumlah hasil

    # Balikkan data untuk AJAX atau render halaman penuh
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('admin/produk_list.html', produk_list=produk_list)
    
    return render_template(
        'user/produk.html',
        produk_list=produk_list,
        selected_category=category,
        search=search
    )

     
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    # Ambil data dari request
    data = request.get_json()
    product_id = data['product_id']
    product_name = data['product_name']
    product_price = data['product_price']
    product_image = data['product_image']
    quantity = data['quantity']

    cart_collection = db['cart']
    cart_collection.insert_one({
        'username': session['username'],
        'product_id': product_id,
        'product_name': product_name,
        'product_price': product_price,
        'product_image': product_image,
        'quantity': quantity,
        'alamat': session.get('alamat', ''),
        'email': session.get('email', '')
    })

    return jsonify({'status': 'success', 'message': 'Product added to cart'})

@app.route('/remove_cart_item/<product_id>', methods=['DELETE'])
def remove_cart_item(product_id):
    if 'username' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'}), 401

    cart_collection = db['cart']
    
    # Hapus item berdasarkan product_id dan username
    result = cart_collection.delete_one({
        '_id': ObjectId(product_id),
        'username': session['username']
    })
    
    if result.deleted_count > 0:
        return jsonify({'status': 'success', 'message': 'Item removed from cart'})
    else:
        return jsonify({'status': 'error', 'message': 'Item not found or not authorized to delete'}), 404


@app.route('/cart')
def cart():
    # Periksa apakah pengguna sudah login
    if 'username' not in session: 
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('login'))  

    # Ambil data cart dari MongoDB untuk pengguna saat ini
    cart_collection = db['cart']
    try:
        # Ambil item cart berdasarkan pengguna
        cart_items = list(cart_collection.find(
            {
                'username': session['username']
            }
        ))

        # Hitung total harga (pastikan field yang digunakan sudah ada di database)
        total_price = sum(
            float(item.get('product_price', 0)) * int(item.get('quantity', 1))
            for item in cart_items
        )

        # Konversi ke integer untuk memastikan total harga tanpa desimal
        total_price = int(total_price)

    except Exception as e:
        # Jika ada error, log pesan error dan berikan feedback ke pengguna
        print(f"Error fetching cart items: {e}")
        flash('Failed to fetch cart items. Please try again.', 'danger')
        return redirect(url_for('produk'))  

   
    return render_template(
        'user/cart.html',
        cart_items=cart_items,
        total_price=total_price
    )

@app.route('/buy', methods=['POST'])
def buy():
    
    cart_collection = db['cart']
    cart_items = list(cart_collection.find({'username': session['username']}))

    if not cart_items:
        return jsonify({'status': 'error', 'message': 'No items in cart'}), 400

    try:
        for item in cart_items:
            orders_collection.insert_one({
                'username': session['username'],
                'product_id': item['product_id'],
                'product_name': item['product_name'],
                'product_price': item['product_price'],
                'product_image': item['product_image'],
                'quantity': item['quantity'],
                'alamat': item['alamat'],
                'email': item['email'],
                'status': 'pending',  
                'payment_proof': None  
            })

        cart_collection.delete_many({'username': session['username']})

        return jsonify({'status': 'success', 'message': 'Pembelian berhasil!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/buy_direct', methods=['POST'])
def buy_direct():
   
    data = request.get_json()
    product_id = data['product_id']
    product_name = data['product_name']
    product_price = data['product_price']
    product_image = data['product_image']
    quantity = data['quantity']


    orders_collection.insert_one({
        'username': session['username'],
        'product_id': product_id,
        'product_name': product_name,
        'product_price': product_price,
        'product_image': product_image,
        'quantity': quantity,
        'alamat': session.get('alamat', ''),
        'email': session.get('email', ''),
        'status': 'pending',  
        'payment_proof': None  
    })

    return jsonify({'status': 'success', 'message': 'Product added to orders'})

@app.route('/check_order')
def check_order():
    if 'username' not in session:  
        flash('You must be logged in to access this page.', 'warning')
        return redirect(url_for('login'))  

    orders_collection = db['orders']

    try:
        orders = list(orders_collection.find({'username': session['username']}))

        total_price = sum(
            float(item.get('product_price', 0)) * int(item.get('quantity', 1))
            for item in orders
        )

        total_bayar = 0
        for item in orders:
            if item.get('status') == 'completed':
                total_bayar += float(item.get('product_price', 0)) * int(item.get('quantity', 1))

        total_price = int(total_price)
        total_bayar = int(total_bayar)

    except Exception as e:
        print(f"Error fetching orders: {e}")
        flash('Gagal mengambil pesanan. Silakan coba lagi.', 'danger')
        return redirect(url_for('produk'))

    return render_template('user/check_order.html', cart_items=orders, total_price=total_price, total_bayar=total_bayar)


@app.route('/upload_payment', methods=['POST'])
def upload_payment():
    if request.method == 'POST':
        payment_proof = request.files['payment_proof']
        order_id = request.form.get('order_id')  

        if payment_proof:
            filename = secure_filename(payment_proof.filename)
            new_filename = f'bukti_bayar_{filename}'
            payment_path = os.path.join('static/img/pembayaran/', new_filename)

            payment_proof.save(payment_path)

            orders_collection.update_one(
                {'_id': ObjectId(order_id)},
                {'$set': {'payment_proof': payment_path, 'status': 'pending'}}  
            )

            flash('Bukti pembayaran berhasil diupload!', 'success')
            return redirect(url_for('check_order')) 

    return render_template('user/check_order.html')

@app.route('/admin/payment_verification', methods=['GET'])
def payment_verification():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    orders = list(orders_collection.find({'status': 'pending'}))
    return render_template('admin/payment_verification.html', orders=orders)

@app.route('/approve_payment/<order_id>', methods=['POST'])
def approve_payment(order_id):
    orders_collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': 'completed'}}  
    )
    flash('Pembayaran disetujui!', 'success')
    return redirect(url_for('payment_verification'))

@app.route('/reject_payment/<order_id>', methods=['POST'])
def reject_payment(order_id):
    orders_collection.update_one(
        {'_id': ObjectId(order_id)},
        {'$set': {'status': 'canceled'}}  
    )
    flash('Pembayaran ditolak!', 'danger')
    return redirect(url_for('payment_verification'))

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

        
        if new_username != user['username'] and users_collection.find_one({"username": new_username}):
            return 'Username already taken, please choose another one!'

        
        users_collection.update_one(
            {"_id": user['_id']},
            {"$set": {
                "username": new_username,
                "email": new_email,
                "alamat": new_alamat
            }}
        )

        session['username'] = new_username
        
        return redirect(url_for('profile'))  

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

        filename = secure_filename(product_image.filename)
        new_filename = f'produk_{filename}'
        image_path = f"static/img/produk/{new_filename}"
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
    return render_template('admin/index.html')

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
            filename = secure_filename(product_image.filename)
            new_filename1 = f'produk_{filename}'
            image_path = f"static/img/produk/{new_filename1}"
            product_image.save(image_path)
            update_data['image'] = image_path

        produk_collection.update_one({'_id': ObjectId(product_id)}, {'$set': update_data})

        flash("Produk berhasil diperbarui!", 'success')
        return redirect(url_for('produk'))

    produk = produk_collection.find_one({'_id': ObjectId(product_id)})
    return render_template('admin/update_produk.html', produk=produk)

@app.route('/payment', methods=['GET', 'POST'])
def paymentview():
    return render_template('/user/payment.html')
        
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

            session['username'] = username
            session['role'] = role
            session['email'] = email
            session['alamat'] = alamat
            
            return redirect(url_for('home'))  
    
    return render_template('user/register.html', error=error)

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)