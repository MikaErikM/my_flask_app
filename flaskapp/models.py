from flaskapp import db
from datetime import datetime

# Defining a model for users
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    posts = db.relationship('BlogPost', backref='author', lazy=True)
    def __repr__(self): return f"User('{self.name}', '{self.id}'')"

# Defining a model for blog posts
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    def __repr__(self): return f"BlogPost('{self.title}', '{self.date_posted}')"

class Day(db.Model):
    id = db.Column(db.Date, primary_key=True)
    views = db.Column(db.Integer)
    def __repr__(self): return f"Day('{self.id}', '{self.views}')"

class IpView(db.Model):
    ip = db.Column(db.String(20), primary_key=True)
    date_id = db.Column(db.Date, db.ForeignKey('day.id'), primary_key=True)
    def __repr__(self): return f"IpView('{self.ip}', '{self.date_id}')"

class UkData(db.Model):
    id = db.Column(db.String(9), primary_key=True)
    constituency_name = db.Column(db.Text, nullable=False)
    country = db.Column(db.String(8), nullable=False)
    region = db.Column(db.String(24), nullable=False)
    Turnout19 = db.Column(db.Float, nullable=False)
    ConVote19 = db.Column(db.Float, nullable=False)
    LabVote19 = db.Column(db.Float, nullable=False)
    LDVote19 = db.Column(db.Float) # Nullable, as not all parties contest all seats
    SNPVote19 = db.Column(db.Float)
    PCVote19 = db.Column(db.Float)
    UKIPVote19 = db.Column(db.Float)
    GreenVote19 = db.Column(db.Float)
    BrexitVote19 = db.Column(db.Float)
    TotalVote19 = db.Column(db.Float, nullable=False)
    c11PopulationDensity = db.Column(db.Float, nullable=False)
    c11Female = db.Column(db.Float, nullable=False)
    c11FulltimeStudent = db.Column(db.Float, nullable=False)
    c11Retired = db.Column(db.Float, nullable=False)
    c11HouseOwned = db.Column(db.Float, nullable=False)
    c11HouseholdMarried = db.Column(db.Float, nullable=False)
    def __repr__(self): return f"UkData('{self.constituency_name}')"