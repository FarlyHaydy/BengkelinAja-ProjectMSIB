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

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
       
        return 'Email pemulihan telah dikirim!'
    
    return render_template('forgot_password.html') 

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)
