from flask import render_template, url_for, flash, redirect, request
from flask_wtf import form
import os
import uuid
from linkvine import app, db, bcrypt, mail
from linkvine.forms import RegistrationForm, LoginForm, SettingForm, RequestResetForm, ResetPasswordForm
from linkvine.models import User, Link, Files, AdminAppearance, Page
from flask_login import login_user, logout_user, current_user, login_required
from flask_mail import Message
import boto3


@app.route('/')
def home():
    return render_template('user/home.html')


@app.route('/user/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard_main():
    all_data = current_user.links
    visible_data = current_user.links.filter_by(visibility="shown")  # lazy = 'dynamic'
    user_img = current_user.files
    user_background_theme = current_user.pages

    # AWS S3 BUCKET
    s3 = boto3.resource('s3')
    s3_object_name = s3.Object('s3-linkvine', current_user.files[0].image_file)

    s3_object_key = s3_object_name.key

    return render_template('user/dashboard.html', all_data=all_data, page="dashboard", user_img=user_img,
                           visible_data=visible_data, user_background_theme=user_background_theme,
                           s3_object_key=s3_object_key)


@app.route('/user/dashboard/edit', methods=['GET', 'POST'])
def dashboard_edit_link():
    if request.method == "POST":
        data_obj = Link.query.get(request.form['id'])
        data_obj.title = request.form['title']
        data_obj.link = request.form['link']

        visibility = str(request.form.getlist('visibility'))

        if visibility == "['on']":
            data_obj.visibility = "shown"

        elif visibility == "[]":
            data_obj.visibility = "hidden"

        db.session.commit()

        return redirect(url_for('dashboard_main'))


@app.route('/user/dashboard/delete/<link_id>/', methods=['GET', 'POST'])
def dashboard_delete_link(link_id):
    data_obj = Link.query.get(link_id)
    db.session.delete(data_obj)

    db.session.commit()

    return redirect(url_for('dashboard_main'))


@app.route("/add_link", methods=['GET', 'POST'])
def dashboard_add_link():
    if form.request.method == "POST":
        title = request.form['title']
        link = request.form['link']

        link_obj = Link(title=title, link=link, user_id=current_user.id)
        db.session.add(link_obj)
        db.session.commit()

        return redirect(url_for('dashboard_main'))


@app.route('/<username>')
def profile(username):
    user_obj = User.query.filter_by(username=username).first()

    if not user_obj:
        return redirect(url_for('page_not_found'))

    user_name = user_obj.username
    user_links = user_obj.links.filter_by(visibility="shown")
    # user_img = user_obj.files
    user_background_theme = user_obj.pages

    # AWS S3 BUCKET
    s3 = boto3.resource('s3')
    s3_object_name = s3.Object('s3-linkvine', user_obj.files[0].image_file)

    s3_object_key = s3_object_name.key

    print(s3_object_key)

    return render_template('user/profile.html', user_links=user_links, user_name=user_name,
                           user_background_theme=user_background_theme, s3_object_key=s3_object_key)


@app.route('/user/appearance', methods=['GET', 'POST'])
@login_required
def appearance():
    visible_data = current_user.links.filter_by(visibility="shown")  # lazy = 'dynamic'
    user_img = current_user.files
    user_background_theme = current_user.pages
    background_colors = AdminAppearance.query.all()

    print(user_img)
    print(current_user.files[0].image_file)

    # AWS S3 BUCKET
    s3 = boto3.resource('s3')
    s3_object_name = s3.Object('s3-linkvine', current_user.files[0].image_file)

    s3_object_key = s3_object_name.key

    return render_template('user/appearance.html', page="appearance", visible_data=visible_data, user_img=user_img,
                           background_colors=background_colors, user_background_theme=user_background_theme,
                           s3_object_key=s3_object_key)


@app.route('/user/appearance/edit/background/<theme_name>', methods=["GET", "POST"])
@login_required
def appearance_edit_background(theme_name):
    if request.method == "POST":
        user_obj = current_user.pages.first()

        selected_theme = request.form[theme_name]
        user_obj.background_color = selected_theme

        db.session.commit()

        flash("Your background theme has been changed.", "success")

    return redirect(url_for('appearance'))


@app.route('/user/appearance/upload_img', methods=['GET', 'POST'])
def appearance_upload_img():
    # Allowed extensions
    extensions_type = ('png', 'jpg')

    # Random ID generator
    unique_file_name = str(uuid.uuid1()) + '.png'

    user_obj = User.query.filter_by(username=current_user.username).first()
    user_img = user_obj.files[0].image_file

    if request.method == 'POST':
        # Updates existing images
        if str(user_img) != "":
            # Validation no empty file
            if request.files['file-img'].filename == '':
                flash('Please upload an image.', 'danger')

            # Validation: only .png file
            elif not request.files['file-img'].filename.endswith(extensions_type):
                flash('Please upload .png files only.', 'danger')

            # Conditions met
            else:
                uploaded_file = unique_file_name
                current_user.files[0].image_file = uploaded_file
                uploaded_file = request.files['file-img']
                # uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_file_name))

                db.session.commit()

                # AWS S3 BUCKET
                s3 = boto3.client('s3')
                s3.upload_fileobj(uploaded_file, 's3-linkvine', unique_file_name)

                flash("Your profile image has been changed.", "success")

                return redirect(url_for('appearance'))

        # First time upload
        else:
            # Validation no empty file
            if request.files['file-img'].filename == '':
                flash('Please upload an image.', 'danger')

            # Validation: only .png file
            elif not request.files['file-img'].filename.endswith(extensions_type):
                flash('Please upload .png files only.', 'danger')

            # Conditions met
            else:
                uploaded_file = request.files['file-img']
                # uploaded_file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_file_name))

                db_file_saved = Files(image_file=unique_file_name, user_id=current_user.id)
                db.session.add(db_file_saved)
                db.session.commit()

                # AWS S3 BUCKET
                s3 = boto3.client('s3')
                s3.upload_fileobj(uploaded_file, 's3-linkvine', unique_file_name)

    return redirect(url_for('appearance'))


@app.route('/user/setting', methods=['GET', 'POST'])
@login_required
def setting():
    form = SettingForm()
    data_obj = User.query.get(current_user.id)

    if form.validate_on_submit():
        # Password unchanged
        if form.password.data == '':
            data_obj.password = current_user.password

        # Password changes
        else:
            data_obj.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')

        # Default changes
        data_obj.username = form.username.data
        data_obj.email = form.email.data
        data_obj.phone_number = form.phone_number.data

        flash("Your account has been updated.", "success")

        db.session.commit()

    return render_template('user/setting.html', form=form)


@app.route('/user/setting/delete/<user_id>', methods=['GET', 'POST'])
def setting_delete_account(user_id):
    data_obj = User.query.get(user_id)
    db.session.delete(data_obj)

    db.session.commit()

    flash("We're sad to see you go. Feel free to leave us a message any time! ", "info")

    return redirect(url_for('home'))


@app.route('/user/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and user.role == "admin" and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('admin_dashboard'))

        if user and user.role == "user" and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard_main'))
        else:
            flash("Login unsuccessful. Please check email and password.", "danger")

    return render_template('user/login.html', title="Login", form=form)


@app.route('/user/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/user/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            'utf-8')  # To make a string instead of byte

        user = User(username=form.username.data.lower(), email=form.email.data.lower(), password=hashed_password)
        db.session.add(user)
        db.session.commit()

        user_obj = User.query.filter_by(username=form.username.data).first()

        # Set default profile image when user is created
        user_img = Files(image_file="default.jpg", user_id=user_obj.id)

        # Set default page background theme when user is created
        user_background_theme = Page(background_color="theme-default", user_id=user_obj.id)

        db.session.add(user_img)
        db.session.add(user_background_theme)

        db.session.commit()

        flash('Your account has been created! You are now able to login', 'success')

        return redirect(url_for('login'))

    return render_template('user/register.html', title="Register", form=form)


@app.route('/user/404')
def page_not_found():
    return render_template('user/404.html')


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender="noreply@demo.com", recipients=[user.email])

    msg.body = f''' To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}

    If you did not make this request then simply ignore this email and no changes will be made.        
    '''

    mail.send(msg)


# Input email
@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RequestResetForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)

        flash("An email has been sent with instructions to reset your password in your spam inbox", "info")
        return redirect(url_for("login"))

    return render_template('user/reset_request.html', titile='Reset Password', form=form)


#  Reset password with token active
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    user = User.verify_reset_token(token)

    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))

    # Valid token
    form = ResetPasswordForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode(
            'utf-8')  # To make a string instead of byte

        user.password = hashed_password
        db.session.commit()

        flash("Your password has been updated. You are now able to login", "success")
        return redirect(url_for('login'))

    return render_template('user/reset_token.html', titile='Reset Password', form=form)
