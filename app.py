from flask import Flask, render_template, url_for, redirect, request, make_response, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from email.message import EmailMessage
from datetime import datetime
import ssl
import smtplib
import pandas as pd
import os.path
import os
import uuid

app = Flask(__name__,template_folder='templates', static_url_path='/static')
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///userdatabase.db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://nckeojgzjrjqom:7d1b48baac42ff55e02fff7378ead30be562e8b92c018ec4a680b458f5f81839@ec2-54-208-11-146.compute-1.amazonaws.com:5432/dd7a3urjq479o8'
app.config['SECRET_KEY'] = 'secretkeysecretum22'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

##################################################################################################################

# adatbázis tábla

# a felhasználók adatbázisa (felhasználó tábla)
class User(db.Model, UserMixin):
   id = db.Column(db.Integer, primary_key=True)
   username = db.Column(db.String(20), nullable=False, unique=True)
   password = db.Column(db.String(60), nullable=False)

# utoljára bejelentkezett felhasználó tábla
class LastLoggedInUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    last_logged_in_user_name = db.Column(db.String(20), nullable=False)
    date = db.Column(db.String(50), nullable=False)

##################################################################################################################

# FlaskForm

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

        # ha létezik, felhasználónév vagy jelszó hiba üzenete
        if existing_user_username:
            raise ValidationError(
               "Ez a felhasználónév vagy jelszó már létezik. Kérlek válassz másikat."
            )

# FlaskForm login.html oldal
class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(
        min=4, max=20)], render_kw={"placeholder": "Felhasználónév"})
    password = PasswordField(validators=[InputRequired(), Length(
       min=4, max=20)], render_kw={"placeholder": "Jelszó"})
    submit = SubmitField("Belépés")

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
    print("\a")
    return render_template("login.html", form=form)

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

# kijelentkezés oldal
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    login_required
    logout_user
    return redirect(url_for('home'))


# sikeres belépés oldal
@app.route('/loginsucces', methods=['GET', 'POST'])
def login_succes():

    login_required

    # log készítése, hogy melyik felhasználó mikor lépett be és adatbázis táblába mentése
    user_name = current_user.username
    logged_in_date = datetime.now()

    last_user = LastLoggedInUser(last_logged_in_user_name=user_name, date=logged_in_date)
    db.session.add(last_user)
    db.session.commit()

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name

    # csv fájl készítése, ha még a felhasználónak nincs csv fájlja a szavazatairól
    if not os.path.exists(f'./users_polls_csv/user_{current_user_name}_polls.csv'):
        flash("Még nem hozott létre szavazást")
        flash("Készítse el az első szavazását")
        structure = {
            "Qid": ["0"],
            "question": ["0"],
            "participants": ["0"],
            "crypt": ["0"],
            "option_1": ["0"],
            "vote_result_counter_1": ["0"],
            "option_2": ["0"],
            "vote_result_counter_2": ["0"],
            "option_3": ["0"],
            "vote_result_counter_3": ["0"]
        }
        pd.DataFrame(structure).set_index("Qid").to_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')

    return render_template("loginsucces.html")

# a felhasználó oldala
@app.route('/userpage')
def user_page():

    login_required

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name
    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv').set_index("Qid")


    return render_template("user.html", polls = polls_df)

# elkészített szavazások oldala
@app.route('/polls/<Qid>')
def polls(Qid):

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name

    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv').set_index("Qid")
    
    question = polls_df.loc[int(Qid)]

    return render_template("pollpage.html", question=question)


# szavazás elkészítésének és meghívük kiküldésének oldala
@app.route('/createpoll', methods = ['GET', 'POST'])
def createpoll():

    login_required

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name
    
    # szavazás és eredmény csv fájl olvasása
    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv').set_index("Qid")
    if request.method == "GET":
        # oldal betöltése
        return render_template("createpoll.html")
    elif request.method == "POST":
        # a szavazás létrehozása után az input tagek értkékeinek csv fájlba mentése
        question = request.form["question"]
        option1 = request.form["option1"]
        option2 = request.form["option2"]
        option3 = request.form["option3"]
        crypt = request.form["anonim"]
        emails = request.form["emails"]
        email_list = []
        email_list = emails.split(', ')
        email_list_len = len(email_list)

        # új szavazás csv fájlban sor létrehozása, elmentve a szavazás adatait
        polls_df.loc[max(polls_df.index.values) + 1] = [question, email_list_len, crypt, option1, 0, option2, 0,  option3, 0]
        polls_df.to_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')
        
        # az utoljára létrehozott szavazás csv fájl ID lekérése és a kiküldendő linkbe illesztése
        polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')
        Qid = (polls_df["Qid"].size)-1

        crypt = (polls_df.at[Qid, 'crypt'])

        if crypt == "Anonim":
            # meghívó email küldés
            email_sender = 'poll.flask@gmail.com'
            email_password = 'fdqcecowahspvoul'
            email_receiver = email_list
            subject = request.form["subject"]
            mail_body = request.form["body"]
            body = f"""{mail_body}
                http://127.0.0.1:5000/polls/{Qid}.
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

            # csv fájl létrehozása minden elkészített szavazáshoz, melyekben a válaszadók adatai mentődnek:
            # a szavazó IP címe(szavazás fajtájától függően titkosítva, vagy titkosítás nélkül)
            # a szavazó válaszának száma
            if not os.path.exists(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv'):
                structure = {
                    "Pid": ["0"],
                    "voted_question": ["0"],
                    "voter_name": ["0"],
                    "IP_ADDRESS": ["0"],
                    "voted_option": ["0"],
                }
                pd.DataFrame(structure).set_index("Pid").to_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv')

            return render_template("pollsent.html")
        
        elif crypt == "Nem Anonim":
            # meghívó email küldés
            email_sender = 'poll.flask@gmail.com'
            email_password = 'fdqcecowahspvoul'
            email_receiver = email_list
            subject = request.form["subject"]
            mail_body = request.form["body"]
            body = f"""{mail_body}
                http://127.0.0.1:5000/votername.
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
            # csv fájl létrehozása minden elkészített szavazáshoz, melyekben a válaszadók adatai mentődnek:
            # a szavazó IP címe(szavazás fajtájától függően titkosítva, vagy titkosítás nélkül)
            # a szavazó válaszának száma
            if not os.path.exists(f'./participants_vote_by{current_user_name}/participants_vote__poll_{Qid}.csv'):
                structure = {
                    "Pid": ["0"],
                    "voted_question": ["0"],
                    "voter_name": ["0"],
                    "IP_ADDRESS": ["0"],
                    "voted_option": ["0"],
                }
                pd.DataFrame(structure).set_index("Pid").to_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv')
                
            return render_template("pollsent.html")

@app.route('/votername', methods=["GET", "POST"])
def getvotername():

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name

    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')
    Qid = (polls_df["Qid"].size)-1

    question = polls_df.iloc[int(Qid), polls_df.columns.get_loc("question")]
    participants_df = pd.read_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv').set_index("Pid")

    if request.method == "GET":
        return render_template("votername.html")
    elif request.method == "POST":
        voter_name = request.form["votername"]
        participants_df.loc[max(participants_df.index.values) + 1] = [question, voter_name, 0, 0]
        participants_df.to_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv')
        return redirect(url_for('polls', Qid=Qid))

# szavazás lebonyolításának oldala
@app.route('/polling/<Qid>/<option>', methods=["GET", "POST"])
def polling(Qid, option):
    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name

    # csv fájlok olvasása
    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv').set_index("Qid")
    participants_df = pd.read_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv').set_index("Pid")

    crypt = (polls_df.at[int(Qid), 'crypt'])

    #cookie használata, hogy a szavazó csak egyszer szavazhasson
    if request.cookies.get(f'polling_{current_user_name}_{Qid}_cookie') is None:

        # szavat leadása után a választott szavazat értékének növelése egyel a csv fájlban
        polls_df.at[int(Qid), "vote_result_counter_"+str(option)] += 1
        polls_df.to_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')

        voted_question = (polls_df.at[int(Qid), 'question'])

        # titkosítás
        if crypt == "Nem Anonim":
            # ha a szavazás "Nem Anonim", akkor a szavazó IP címe mentődik el a csv fájlban a választott szavazatának számával
            if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                ip_addr = request.environ['REMOTE_ADDR']
            else: # proxy használata esetén
                ip_addr = request.environ['HTTP_X_FORWARDED_FOR']
            participants_df.at[max(participants_df.index.values), "IP_ADDRESS"] = ip_addr
            participants_df.at[max(participants_df.index.values), "voted_option"] = option
        elif crypt == "Anonim":
            # ha a szavazás "Anonim", akkor a szavazó IP címe titkosítva mentődik el a csv fájlban a választott szavazatának számával
            if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
                ip_addr = request.environ['REMOTE_ADDR']
            else: # proxy használata esetén
                ip_addr = request.environ['HTTP_X_FORWARDED_FOR']   
            hashed_ip_addr = bcrypt.generate_password_hash(ip_addr)
            participants_df.loc[max(participants_df.index.values) + 1] = [voted_question, 0, hashed_ip_addr, option]
        participants_df.to_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv')
        
        #cookie beállítása
        flash("Leadta szavazatát, köszönjük!")
        response = make_response(redirect(url_for('polls', Qid=Qid)))
        response.set_cookie(f'polling_{current_user_name}_{Qid}_cookie', str(option))
        return response

    else:
        flash("Már egyszer szavazott, nem tud mégegyszer szavazni")
        return redirect(url_for('polls', Qid=Qid))
        

# szavazások eredményéneinek oldala
@app.route('/results/<Qid>')
def results(Qid):

    last_user_name = LastLoggedInUser.query.all()
    for username in last_user_name:
        current_user_name = username.last_logged_in_user_name

    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')
    question = polls_df.loc[int(Qid)]

    # Google Chart data
    polls_df = pd.read_csv(f'./users_polls_csv/user_{current_user_name}_polls.csv')
    option_1 = polls_df.at[int(Qid), 'option_1']
    option_2 = polls_df.at[int(Qid), 'option_2']
    option_3 = polls_df.at[int(Qid), 'option_3']
    option_1 = str(option_1)
    option_2 = str(option_2)
    option_3 = str(option_3)
    result_1 = polls_df.at[int(Qid), 'vote_result_counter_1']
    result_2 = polls_df.at[int(Qid), 'vote_result_counter_2']
    result_3 = polls_df.at[int(Qid), 'vote_result_counter_3']
    result_1 = int(result_1)
    result_2 = int(result_2)
    result_3 = int(result_3)
    option = []
    result = []
    option.append(option_1)
    option.append(option_2)
    option.append(option_3)
    result.append(result_1)
    result.append(result_2)
    result.append(result_3)

    values = [
        ["Válaszlehetőség", "Szavazatok száma"],
        [option_1, result_1],
        [option_2, result_2],
        [option_3, result_3]
        ]
    
    crypt = (polls_df.at[int(Qid), 'crypt'])
    participants_df = pd.read_csv(f'./participants_vote_csv/participants_vote_{current_user_name}_poll_{Qid}.csv').set_index("Pid")

    if crypt == "Nem Anonim":
        voter_name = participants_df["voter_name"].to_list()
        del voter_name[0]
        voted_option = participants_df["voted_option"].to_list()
        del voted_option[0]
        data = zip(voter_name, voted_option)
        return render_template("result.html", question=question, row_data=values, data=data)

    elif crypt == "Anonim":
        return render_template("result.html", question=question, row_data=values)
    
if __name__=='__main__':
   app.run(debug=True)