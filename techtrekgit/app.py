import hashlib
import re
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from datetime import datetime
import os

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'techtrek.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mysecretkey'
UPLOAD_FOLDER = 'static/images'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# bcrypt=Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    mobile = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_picture = db.Column(db.String(100), nullable=True)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def is_strong_password(password):
    return (
        len(password) >= 8 and
        re.search(r'[A-Z]', password) and
        re.search(r'[a-z]', password) and
        re.search(r'\d', password) and
        re.search(r'[!@#$%^&*]', password)
    )

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # if fields are empty
        if not all([name, email, mobile, password, confirm_password]):
            flash("⚠ All fields are required!", "warning")
            return redirect(url_for('register'))

        # if passwords match
        if password != confirm_password:
            flash("❌ Passwords do not match!", "danger")
            return redirect(url_for('register'))

        if not is_strong_password(password):
            flash("⚠ Password must be at least 8 characters, include an uppercase, lowercase, number, and special character (!@#$%^&*).", "warning")
            return redirect(url_for('register'))

        # if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("📧 Email already registered. Please login!", "warning")
            return redirect(url_for('login'))

        # Hash password and save user
        hashed_password = generate_password_hash(password)
        new_user = User(name=name, email=email, mobile=mobile, password=hashed_password)

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("✅ Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error: {e}")
            flash("❌ An error occurred. Please try again.", "danger")
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("✅ Login successful!", "success")
            return redirect(url_for('profile'))
        else:
            flash("❌ Invalid email or password. Try again!", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("✅ Logged out successfully!", "info")
    return redirect(url_for('login'))

@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        mobile = request.form.get('mobile')

        if not all([name, email, mobile]):
            flash("⚠ All fields are required!", "warning")
            return redirect(url_for('profile'))

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                current_user.profile_picture = filename
                db.session.commit()

        current_user.name = name
        current_user.email = email
        current_user.mobile = mobile
        db.session.commit()

        flash("✅ Profile updated successfully!", "success")

    return render_template("profile.html", user=current_user)

@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                current_user.profile_picture = filename
                db.session.commit()

        current_user.name = name
        current_user.email = email
        current_user.mobile = mobile
        current_user.profile_picture = current_user.profile_picture
        db.session.commit()

        flash("✅ Profile updated successfully!", "success")
        return redirect(url_for('profile'))

    return render_template("edit_profile.html", user=current_user)

class Course(db.Model):
    __tablename__ = "courses"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    instructor = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, nullable=False)
    rating_count = db.Column(db.Integer, nullable=False)
    featured = db.Column(db.Boolean, default=False)
    image_url = db.Column(db.String(500), nullable=False)

    def __init__(self, title, instructor, price, rating, rating_count, featured=False, image_url="/api/placeholder/280/160"):
        self.title = title
        self.instructor = instructor
        self.price = price
        self.rating = rating
        self.rating_count = rating_count
        self.featured = featured
        self.image_url = image_url

class Testimonial(db.Model):
    __tablename__ = "testimonials"
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_title = db.Column(db.String(200), nullable=False)
    image_url = db.Column(db.String(500), nullable=False)

    def __init__(self, content, student_name, student_title, image_url="/api/placeholder/80/80"):
        self.content = content
        self.student_name = student_name
        self.student_title = student_title
        self.image_url = image_url

@app.route("/")
def index():
    featured_courses = Course.query.filter_by(featured=True).limit(3).all()
    testimonials = Testimonial.query.limit(3).all()
    return render_template("index.html", featured_courses=featured_courses, testimonials=testimonials)

def add_sample_data():
    if Course.query.count() == 0:
        sample_courses = [
            Course("Complete Python Bootcamp", "John Smith", 49.99, 4.5, 1250, True),
            Course("React.js Advanced Concepts", "Sarah Johnson", 59.99, 5.0, 850, True),
            Course("Full-Stack Web Development", "Mike Wilson", 69.99, 4.0, 2000, True)
        ]
        for course in sample_courses:
            db.session.add(course)

    if Testimonial.query.count() == 0:
        sample_testimonials = [
            Testimonial(
                "The Python Bootcamp was exactly what I needed to transition into a career in data science. The instructor's teaching style made complex concepts easy to understand.",
                "Abc",
                "Data Scientist at Tech Corp"
            ),
            Testimonial(
                "I went from knowing nothing about web development to building full-stack applications. The step-by-step approach and project-based learning was incredible.",
                "Emily Rodriguez",
                "Frontend Developer"
            ),
            Testimonial(
                "The React.js course helped me level up my development skills. The advanced concepts section was particularly helpful for my current role.",
                "David Chen",
                "Senior Web Developer"
            )
        ]
        for testimonial in sample_testimonials:
            db.session.add(testimonial)

    db.session.commit()


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/blog", methods=["GET", "POST"])
def blog():
    return render_template("blog.html")

@app.route("/careers", methods=["GET", "POST"])
def careers():
    return render_template("careers.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")

@app.route("/accessibility")
def accessibility():
    return render_template("accessibility.html")

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plan_type = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    # date_added = db.Column(db.DateTime, default=datetime.utcnow)
    user_session = db.Column(db.String(100), nullable=False)


@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/cart')
@login_required
def cart():
    if 'user_session' not in session:
        session['user_session'] = str(datetime.utcnow().timestamp())
    
    cart_items = CartItem.query.filter_by(user_session=session['user_session']).all()
    subtotal = sum(item.price for item in cart_items)
    tax = subtotal * 0.1  # 10% tax
    total = subtotal + tax
    
    return render_template('cart.html', 
                         cart_items=cart_items,
                         subtotal=subtotal,
                         tax=tax,
                         total=total)

@app.route('/add-to-cart', methods=['POST'])
def add_to_cart():
    if 'user_session' not in session:
        session['user_session'] = str(datetime.utcnow().timestamp())
    
    plan_type = request.form.get('plan_type')
    price = float(request.form.get('plan_price'))

    existing_item = CartItem.query.filter_by(
        user_session=session['user_session'],
        plan_type=plan_type
    ).first()
    
    if existing_item:
        flash('This plan is already in your cart')
    else:
        cart_item = CartItem(
            plan_type=plan_type,
            price=price,
            user_session=session['user_session']
        )
        db.session.add(cart_item)
        db.session.commit()
        flash('Plan added to cart successfully')
    
    return redirect(url_for('cart'))

@app.route('/remove-from-cart', methods=['POST'])
def remove_from_cart():
    item_id = request.form.get('item_id')
    cart_item = CartItem.query.get_or_404(item_id)
    
    if cart_item.user_session == session.get('user_session'):
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart')
    
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['POST'])
def checkout():
    flash('Checkout functionality will be implemented soon')
    return redirect(url_for('cart'))

@app.route('/python')
def python_course():
    return render_template('python.html')

@app.route('/react')
def react_course():
    return render_template('react.html')

@app.route('/webdev')
def webdev_course():
    return render_template('webdev.html')

@app.route('/cpp')
def cpp_course():
    return render_template('cpp.html')
@app.route('/js')
def js_course():
    return render_template('js.html')

class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired(), Length(min=2, max=200)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            new_message = ContactMessage(
                name=form.name.data,
                email=form.email.data,
                subject=form.subject.data,
                message=form.message.data
            )

            db.session.add(new_message)
            db.session.commit()

            flash('Thank you! Your message has been sent successfully.', 'success')

            return redirect(url_for('contact'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while sending your message. Please try again.', 'danger')
            print(f"Database error: {str(e)}")

    return render_template('contact.html', form=form)

# @app.route('/teach')
# def teach():
#     return render_template('teach.html')

@app.route('/sql')
def sql_course():
    return render_template('sql.html')

@app.route('/ai')
def ai_course():
    return render_template('ai.html')

@app.route('/datascience')
def datascience_course():
    return render_template('datascience.html')

if __name__ == '__main__':
    with app.app_context():
        # db.drop_all()
        db.create_all()
        add_sample_data()
    app.run(debug=True)
