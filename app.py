from flask import Flask, render_template, url_for, redirect, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, RadioField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from email.message import EmailMessage
import ssl
import smtplib


# kiterjesztések
app = Flask(__name__,template_folder='templates')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# adatbázis kapcsolat
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdatabase.db'
app.config['SECRET_KEY'] = 'secretkey'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##################################################################################################################

# adatbázis táblák

# a felhasználók adatbázisának létrehozása (felhasználó tábla)
class User(db.Model, UserMixin):
   id = db.Column(db.Integer, primary_key=True)
   username = db.Column(db.String(20), nullable=False, unique=True)
   password = db.Column(db.String(60), nullable=False)

# IP címhez kötött válasz adatbázis táblája
class Answer(db.Model):
    Qid = db.Column(db.Integer, primary_key=True)
    IP = db.Column(db.String(60), nullable=False)
    answer = db.Column(db.String(50), nullable=False)

# radiobutton értékének elmentése adatbázisba(tábla), anonim vagy nem anonim szavazás és a szavazás kérdése
class Anonim(db.Model):
    Tid = db.Column(db.Integer, primary_key=True)
    question_title = db.Column(db.String(50))
    radio_value = db.Column(db.String(10))

# email címek táblája
class Email(db.Model):
    Eid = db.Column(db.Integer, primary_key=True)
    emails_data = db.Column(db.String(100))

##################################################################################################################

# FlaskForm

# FlaskForm createpoll.html oldal
class QuestionForm(FlaskForm):
    question = StringField(validators=[InputRequired(), Length(
        min=4, max=50)], render_kw={"placeholder": "Kérdés..."})
    anonymous = RadioField('Anonim szavazás', choices=[('Igen','Anonim'),('Nem','Nem Anonim')])
    submit = SubmitField("Szavazás elkészítése")

# FlaskForm sendmail.html oldal
class EmailForm(FlaskForm):
    emails = StringField(validators=[InputRequired(), Length(
        min=1, max=100)], render_kw={"placeholder": "Emailcímek"})
    submit_email = SubmitField('Szavazás kiküldése')

# FlaskForm register.html oldal
class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Felhasználónév"})
    password = PasswordField(validators=[InputRequired(), Length(
       min=4, max=20)], render_kw={"placeholder": "Jelszó"})
    submit = SubmitField("Regisztráció")

    # felhasználónév adatbázisból való lekérdezés
    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()

        # ha létezik, felhasználónév hiba üzenete
        if existing_user_username:
            raise ValidationError(
               "Ez a felhasználónév már létezik. Kérlek válassz másikat."
            )

# FlaskForm login.html oldal
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Felhasználónév"})
    password = PasswordField(validators=[InputRequired(), Length(
       min=4, max=20)], render_kw={"placeholder": "Jelszó"})
    submit = SubmitField("Belépés")

# FlaskForm pollpage.html oldal
class AnswerForm(FlaskForm):
    answer_field = SelectField(choices=[("Igen","Igen"), ("Nem","Nem")])
    submit_answer = SubmitField('Szavazás leadása')

##################################################################################################################

#route

# főoldal  
@app.route('/')
def home():
    
    return render_template("home.html")

# bejelentkezési oldal
@app.route('/login', methods=['GET', 'POST'])
def login():
    
    form = LoginForm()

    # le ellenőrzi, hogy a felhasználó létezik e az adatbázisban vagy sem, a gomb lenyomása után
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        # ha benne van, létezik ilyen felhasználó
        if user:
            # tikosított jelszó ellenőrzése, hogy a beírt jelszó a bejelentekésnél egyezik e az adatbázisbelivel
            if bcrypt.check_password_hash(user.password, form.password.data):
                # ha egyezik, akkor belépteti
                login_user(user)
                return redirect(url_for('login_succes'))
        # ha nem létezik
        else:
            wrong_user = "Rossz felhasználónevet, vagy jelszót adott meg!"
            return render_template("login.html", form=form, wrong_user=wrong_user)
    return render_template("login.html", form=form)

# sikeres belépés oldal
@app.route('/loginsucces', methods=['GET', 'POST'])
def login_succes():
    
    return render_template("loginsucces.html")

# regisztrációs oldal
@app.route('/register', methods=['GET', 'POST'])
def register():
    
    form = RegisterForm()

    # a jelszó titkosítása (hash) Bcrypt-tel és az adatbázisba helyezése
    # lekérdezés esetén a tikosított jelszót adja vissza
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template("register.html", form=form)

# kijelentkezés
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    
    logout_user
    return redirect(url_for('home'))

# szavazás elkészítésének oldala
@app.route('/createpoll', methods =["GET", "POST"])
@login_required
def createpoll():
    voted_ip = Answer.query.order_by(Answer.IP).all()
    if voted_ip:
        flash('Már leadta a szavazatát')
        return redirect(url_for('result'))
    
    # új szavazás esetén a táblák törlése
    db.session.query(Answer).delete()
    db.session.commit()
    db.session.query(Anonim).delete()
    db.session.commit()
    db.session.query(Email).delete()
    db.session.commit()
    form = QuestionForm()
    # radiobutton értékének és a szavazás kérdésének elmentése adatbázisba
    if form.validate_on_submit():
        new_anonim = Anonim(radio_value=form.anonymous.data, question_title=form.question.data)
        db.session.add(new_anonim)
        db.session.commit()
        return redirect(url_for('sendmail'))
    return render_template("createpoll.html", form=form)

# meghívó kiküldés oldal
@app.route('/emailsend', methods=["GET", "POST"])
@login_required
def sendmail():
    form = EmailForm()
    if form.validate_on_submit():

        # meghívó kiküldése mailben
        new_emails = Email(emails_data=form.emails.data)
        db.session.add(new_emails)
        db.session.commit()

        email_values = Email.query.all()
        for email in email_values:
            emails = email.emails_data
        email_list = emails.split(', ')

        email_sender = 'flask.poll@gmail.com'
        email_password = 'hfnttlwztwpzfvjv'
        email_receiver = email_list
        subject = 'Szavazás meghívó'
        body = """
        Ön meghívást kapott egy online szavazásra.
        A linkre kattintva le tudja adni a szavazatát http://127.0.0.1:5000/pollpage.
        """
        em = EmailMessage()
        em['From'] = email_sender
        em['To'] = email_receiver
        em['Subject'] = subject
        em.set_content(body)

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
            smtp.login(email_sender, email_password)
            smtp.sendmail(email_sender, email_receiver, em.as_string())

        return redirect(url_for('polling'))
    return render_template("sendmail.html", form=form)

# szavazás oldala
@app.route('/pollpage', methods =["GET", "POST"])
def polling():
    voted_ip = Answer.query.order_by(Answer.IP).all()
    if voted_ip:
        flash('Már leadta a szavazatát')
        return redirect(url_for('result'))

    form = AnswerForm()

    # szavazás kérdése adatbázisból változóba mentése
    question_titles = Anonim.query.all()
    for question in question_titles:
        title = question.question_title

    if form.validate_on_submit():

        # a radio button értékének lekérdezése, hogy a szavazás anonim, vagy nem anonim
        radio_values = Anonim.query.all()
        for anonim in radio_values:
           crypt = anonim.radio_value

        # ha már valaki szavazott, akkor nem tud újra
        voted_ip = Answer.query.order_by(Answer.IP).all()
        if voted_ip:
            flash('Már leadta a szavazatát')
            return redirect(url_for('result'))
        # ha még nem zavazott:
        else:
            # ha a radio button értéke "Nem", vagyis a szavazás nem anonim,
            # akkor a szavazó IP címe titkosítás nélkül mentődik el az adatbázisba a szavazatával együtt
            if crypt == "Nem":
                if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                    ip_addr = request.environ['REMOTE_ADDR']
                else: # proxy használata esetén
                    ip_addr = request.environ['HTTP_X_FORWARDED_FOR']  
                new_answer = Answer(IP=ip_addr, answer=form.answer_field.data)
                db.session.add(new_answer)
                db.session.commit()
            # ha a radio button értéke "Igen", vagyis a szavazás anonim,
            # akkor a szavazó IP címe titkosítva mentődik el az adatbázisba a szavazatával együtt
            elif crypt == "Igen":
                if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                    ip_addr = request.environ['REMOTE_ADDR']
                else: # proxy használata esetén
                    ip_addr = request.environ['HTTP_X_FORWARDED_FOR']   
                hashed_IP = bcrypt.generate_password_hash(ip_addr)
                new_answer = Answer(IP=hashed_IP, answer=form.answer_field.data)
                db.session.add(new_answer)
                db.session.commit()

        return redirect(url_for('result'))
    return render_template("pollpage.html", form=form, title=title)

# szavazatok száma, szavazás eredménye oldal
@app.route('/resultpage', methods =["GET", "POST"])
def result():

    # szavazás kérdésének lekérdezése
    question_titles = Anonim.query.all()
    for question in question_titles:
        title = question.question_title

    # szavazatok kiírása
    Result_Igen = Answer.query.filter_by(answer="Igen").count()
    Result_Nem = Answer.query.filter_by(answer="Nem").count()
    return render_template("result.html", Result_Igen=Result_Igen, Result_Nem=Result_Nem, title=title)

if __name__=='__main__':
   app.run(debug=True)

##################################################################################################################
# terminálon keresztül történő adatbázis lekérdezés táblák szerint:

# sqlite3 userdatabase.db
# select * from user; - felhasználó tábla
# select * from anonim; - szavazás fajtája (Anonim, vagy nem anonim) és a szavazás kérdése
# select * from answer; - a szavazó IP címe(titkosított vagy nem titkosított) és válasza
# .exit

##################################################################################################################
# adatbázis létrehozása terminálon keresztül:

# python3    
# from app import db
# db.create_all()
# exit()