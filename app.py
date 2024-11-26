from flask import Flask, render_template

app = Flask(__name__)

@app.route('/', methods=['GET'], endpoint='home')
def home():
    return render_template('user/hompage.html')

@app.route('/login')
def login():
    return render_template('user/login.html') 

@app.route('/register', endpoint = 'registrasi')
def register():
    return render_template('user/register.html') 

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


if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)