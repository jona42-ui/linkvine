from linkvine import db, login_manager, app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone_number = db.Column(db.String(120), default="", nullable=True)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=True, default="user")

    # Foreign Keys
    links = db.relationship('Link', backref='links', lazy='dynamic')
    files = db.relationship('Files', backref='files', lazy=True)  # lazy=true so that can apply filter_by to ORM
    pages = db.relationship('Page', backref='pages', lazy='dynamic')

    def get_reset_token(self, expires_sec=1800):  # 30 minutes
        s = Serializer(app.config['SECRET_KEY'], expires_sec)
        return s.dumps({'user_id': self.id}).decode('utf-8')

    @staticmethod  # Basically to ignore self, this is a static function
    def verify_reset_token(token):
        s = Serializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token)['user_id']
        except:
            return None

        # If valid, returns user with Id
        return User.query.get(user_id)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"


class Files(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_file = db.Column(db.String(200), default='default.jpg', nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class Link(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    link = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    background_color = db.Column(db.String(1000), nullable=True)
    visibility = db.Column(db.String(10), nullable=False, default='shown')
    priority = db.Column(db.String(10), nullable=False, default='no')
    archive = db.Column(db.Boolean, default=False, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"User('{self.user_id}', '{self.title}', '{self.link}')"


class Page(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    background_color = db.Column(db.String(1000), nullable=False, default='theme-default')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class AdminAppearance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    background_color = db.Column(db.String(1000), nullable=True)
    background_image = db.Column(db.String(1000), nullable=True)
