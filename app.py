import os
import shutil
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, session, request
from flask_bcrypt import Bcrypt
from flask_mail import Message, Mail
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, IMAGES, configure_uploads, patch_request_class

# Run from all devices command line
# flask run -h YOUR_IP_ADDRESS -p 5000

app = Flask(__name__)
app.config['SECRET_KEY'] = '123412341234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_COMMIT_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['MAIL_SERVER'] = 'smtp.mail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'meetomove@mail.com'
app.config['MAIL_PASSWORD'] = 'meetomovepsw'
app.config['UPLOADED_PHOTOS_DEST'] = os.getcwd() + '/static/img/users'

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mailobject = Mail(app)


def send_mail(to, subject, template, **kwargs):
    msg = Message(subject,
                  recipients=[to],
                  sender=app.config['MAIL_USERNAME'])
    msg.html = render_template(template + '.html', **kwargs)
    mailobject.send(msg)


photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app)


from model import User, Review, FavouriteSport, Town, Sport, Event, SportClubDetails, DetailsForm, CreateEvent, \
    CreateEvenSportClub, JoinedEvent, CreateReview, UploadForm
from model import SearchEvent, SignInForm, SignUpForm


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
def index():
    search_event_form = SearchEvent()
    towns = Town.query.all()
    sports = Sport.query.all()
    if search_event_form.is_submitted():
        session['town_id'] = search_event_form.town.data
        session['sport_id'] = search_event_form.sport.data
        return redirect("events")
    return render_template('index.html', search_event_form=search_event_form, towns=towns, sports=sports)


@app.route('/signin', methods=['GET', 'POST'])
def signin():
    sign_in_form = SignInForm()
    if sign_in_form.validate_on_submit():
        user_info = User.query.filter(User.email == sign_in_form.email.data).first()
        if user_info and bcrypt.check_password_hash(user_info.password, sign_in_form.password.data):
            session['user_id'] = user_info.id
            session['user_name'] = user_info.name
            session['user_surname'] = user_info.surname
            session['user_email'] = user_info.email
            session['user_role'] = user_info.role_id
            if user_info.profile_pic is None:
                session['user_pic'] = "img/users/null.png"
            else:
                session['user_pic'] = "img/users/" + str(session['user_id']) + "/" + user_info.profile_pic
            if not sign_in_form.remember.data:
                session['clear'] = True
            return redirect(url_for('index'))
        else:
            return render_template('signin_error.html')

    return render_template('signin.html', sign_in_form=sign_in_form)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    sign_up_form = SignUpForm()
    if sign_up_form.validate_on_submit():
        email = sign_up_form.email.data
        found = User.query.filter(User.email == email).all()
        if len(found) > 0:
            return render_template('signup_error.html')

        password = bcrypt.generate_password_hash(sign_up_form.password.data).encode('utf-8')
        new_user = User(email=email,
                        password=password,
                        name=sign_up_form.name.data,
                        surname=sign_up_form.surname.data,
                        role_id=2)
        db.session.add(new_user)
        db.session.commit()

        send_mail(email, 'Welcome to meeTOmove!', 'mail',
                  name=sign_up_form.name.data, username=email, password=sign_up_form.password.data)

        return redirect(url_for('index'))
    return render_template('signup.html', sign_up_form=sign_up_form)


@app.route('/signup_sportclubs', methods=['GET', 'POST'])
def signup_sportclubs():
    sign_up_form = SignUpForm()
    if sign_up_form.validate_on_submit():
        email = sign_up_form.email.data
        found = User.query.filter(User.email == email).all()
        if len(found) > 0:
            return render_template('signup_error.html')

        password = bcrypt.generate_password_hash(sign_up_form.password.data).encode('utf-8')
        new_user = User(email=email,
                        password=password,
                        name=sign_up_form.name.data,
                        role_id=3)
        db.session.add(new_user)
        db.session.commit()

        send_mail(email, 'Welcome to meeTOmove!', 'mail',
                  name=sign_up_form.name.data, username=email, password=sign_up_form.password.data)

        return redirect(url_for('index'))
    return render_template('signup_sportclubs.html', sign_up_form=sign_up_form)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/handle_sports_form', methods=['GET', 'POST'])
def handle_sports_form():
    if FavouriteSport.query.filter(FavouriteSport.user_id == session['user_id']).delete() > 0:
        FavouriteSport.query.filter(FavouriteSport.user_id == session['user_id']).delete()
        db.session.commit()
    for temp in request.form.getlist('sports_checkbox'):
        new_fav_sport = FavouriteSport(user_id=session['user_id'], sport_id=temp)
        db.session.add(new_fav_sport)
        db.session.commit()
    return redirect(url_for("myaccount"))


@app.route('/players')
def players():
    users = User.query.filter(User.role_id != 3).order_by(User.surname.asc()).all()
    reviews = Review.query.all()
    favourite_sports = FavouriteSport.query.all()

    return render_template('players.html', users=users, reviews=reviews, favourite_sports=favourite_sports)


@app.route('/player/<int:id>')
def player(id):
    users = User.query.all()
    player = User.query.filter(User.id == id).first()
    favourite_sports = FavouriteSport.query.filter(FavouriteSport.user_id == id).all()
    reviews = Review.query.filter(Review.reviewed_id == id).order_by(Review.date_added.desc()).all()

    if len(favourite_sports) == 0:
        favourite_sports = None

    skills = 0
    sportsmanship = 0
    willingness = 0
    reliability = 0
    punctuality = 0

    if len(reviews) > 0:
        for review in reviews:
            skills = skills + review.skills
            sportsmanship = sportsmanship + review.sportsmanship
            willingness = willingness + review.willingness
            reliability = reliability + review.reliability
            punctuality = punctuality + review.punctuality
        skills = skills / len(reviews)
        sportsmanship = sportsmanship / len(reviews)
        willingness = willingness / len(reviews)
        reliability = reliability / len(reviews)
        punctuality = punctuality / len(reviews)
        player_score = (skills + sportsmanship + willingness + reliability + punctuality) / 5

        return render_template('player.html', player=player, player_score=player_score, skills=skills,
                               sportsmanship=sportsmanship, willingness=willingness,
                               reliability=reliability, punctuality=punctuality,
                               favourite_sports=favourite_sports, users=users, reviews_received=reviews)
    else:
        return render_template('player.html', player=player, player_score="n.a.", skills="n.a.",
                               sportsmanship="n.a.", willingness="n.a.",
                               reliability="n.a.", punctuality="n.a.",
                               favourite_sports=favourite_sports, users=users, reviews_received=None)


@app.route('/sportclub/<int:id>')
def sportclub(id):
    sportclub = User.query.filter(User.id == id).first()
    details = SportClubDetails.query.filter(SportClubDetails.id == id).all()
    practicable_sports = FavouriteSport.query.filter(FavouriteSport.user_id == id).all()
    events_created = Event.query.filter(Event.creator_id == id).all()

    if len(practicable_sports) == 0:
        practicable_sports = None

    return render_template('sportclub.html', sportclub=sportclub, details=details,
                           practicable_sports=practicable_sports, events_created=events_created)


@app.route('/sportclubs')
def sportclubs():
    sport_clubs = User.query.filter(User.role_id == 3).order_by(User.name.asc()).all()
    details = SportClubDetails.query.all()
    practicable_sports = FavouriteSport.query.all()

    return render_template('sportclubs.html', sport_clubs=sport_clubs, details=details,
                           practicable_sports=practicable_sports)


@app.route('/myaccount', methods=['GET', 'POST'])
def myaccount():
    if session.get('user_id'):
        sports = Sport.query.all()

        favourite_sports = FavouriteSport.query.filter(FavouriteSport.user_id == session['user_id']).all()
        if len(favourite_sports) == 0:
            favourite_sports = None

        if session.get('user_role') != 3:
            skills = 0
            sportsmanship = 0
            willingness = 0
            reliability = 0
            punctuality = 0
            reviews = Review.query.filter(Review.reviewed_id == session['user_id']).all()
            if len(reviews) > 0:
                for review in reviews:
                    skills = skills + review.skills
                    sportsmanship = sportsmanship + review.sportsmanship
                    willingness = willingness + review.willingness
                    reliability = reliability + review.reliability
                    punctuality = punctuality + review.punctuality
                skills = skills / len(reviews)
                sportsmanship = sportsmanship / len(reviews)
                willingness = willingness / len(reviews)
                reliability = reliability / len(reviews)
                punctuality = punctuality / len(reviews)
                player_score = (skills + sportsmanship + willingness + reliability + punctuality) / 5

                return render_template('myaccount.html', player_score=player_score, skills=skills,
                                       sportsmanship=sportsmanship, willingness=willingness,
                                       reliability=reliability, punctuality=punctuality,
                                       favourite_sports=favourite_sports, sports=sports)
            else:
                return render_template('myaccount.html', player_score="n.a.", skills="n.a.",
                                       sportsmanship="n.a.", willingness="n.a.",
                                       reliability="n.a.", punctuality="n.a.",
                                       favourite_sports=favourite_sports, sports=sports)
        else:
            details = SportClubDetails.query.filter(SportClubDetails.id == session['user_id']).all()
            towns = Town.query.all()
            details_form = DetailsForm()

            if details_form.is_submitted():
                if SportClubDetails.query.filter(SportClubDetails.id == session['user_id']).delete() > 0:
                    SportClubDetails.query.filter(SportClubDetails.id == session['user_id']).delete()
                    db.session.commit()

                id = session.get('user_id')
                town_id = details_form.town.data
                address = details_form.address.data
                zip_code = details_form.zip_code.data

                new_details = SportClubDetails(id=id, town_id=town_id, address=address, zip=zip_code)
                db.session.add(new_details)
                db.session.commit()
                return redirect(url_for("myaccount"))

            return render_template('myaccount.html', details=details, details_form=details_form,
                                   favourite_sports=favourite_sports, sports=sports, towns=towns)
    else:
        return redirect(url_for('signin'))


@app.route('/reviews')
def reviews():
    if session.get('user_id'):
        users = User.query.all()
        reviews_made = Review.query.filter(Review.reviewer_id == session['user_id']).order_by(Review.date_added.desc()).all()
        reviews_received = Review.query.filter(Review.reviewed_id == session['user_id']).order_by(Review.date_added.desc()).all()
        return render_template('reviews.html', users=users, reviews_made=reviews_made, reviews_received=reviews_received)
    else:
        return redirect(url_for('signin'))


@app.route('/myevents')
def myevents():
    if session.get('user_id'):
        users = User.query.all()
        events_created = Event.query.filter(Event.creator_id == session['user_id']).order_by(Event.date_start.asc()).all()
        events_created_desc = Event.query.filter(Event.creator_id == session['user_id']).order_by(
            Event.date_start.desc()).all()
        events = Event.query.order_by(Event.date_start.asc()).all()
        events_desc = Event.query.order_by(Event.date_start.desc()).all()
        joined_events = JoinedEvent.query.all()
        return render_template('myevents.html', users=users,
                               events_created=events_created, events_created_desc=events_created_desc,
                               events=events, events_desc=events_desc,
                               joined_events=joined_events, now=datetime.now())
    else:
        return redirect(url_for('signin'))


@app.route('/messages')
def messages():
    if session.get('user_id'):
        return render_template('messages.html')
    else:
        return redirect(url_for('signin'))


@app.route('/events', methods=['GET', 'POST'])
def events():
    users = User.query.all()
    towns = Town.query.all()
    sports = Sport.query.all()
    participating_players = JoinedEvent.query.all()

    events_asc = Event.query.order_by(Event.date_start.asc()).all()
    if session.get('town_id') and session.get('sport_id'):
        if session['sport_id'] == "all":
            events_asc = Event.query.filter(Event.town_id == session['town_id']).order_by(Event.date_start.asc()).all()
        else:
            events_asc = Event.query.filter(Event.town_id == session['town_id'], Event.sport_id == session['sport_id']).order_by(Event.date_start.asc()).all()

    events_desc = Event.query.order_by(Event.date_start.desc()).all()
    if session.get('town_id') and session.get('sport_id'):
        if session['sport_id'] == "all":
            events_desc = Event.query.filter(Event.town_id == session['town_id']).order_by(Event.date_start.desc()).all()
        else:
            events_desc = Event.query.filter(Event.town_id == session['town_id'], Event.sport_id == session['sport_id']).order_by(Event.date_start.desc()).all()

    filter_event_form = SearchEvent()
    if filter_event_form.is_submitted():
        session['town_id'] = filter_event_form.town.data
        session['sport_id'] = filter_event_form.sport.data
        return redirect("events")

    now = datetime.now()

    return render_template('events.html', filter_event_form=filter_event_form, users=users, towns=towns, sports=sports,
                           events_asc=events_asc, events_desc=events_desc, now=now,
                           participating_players=participating_players)


@app.route('/event/<int:id>')
def event(id):
    event = Event.query.filter(Event.id == id).first()
    users = User.query.all()
    found_players_number = JoinedEvent.query.filter(JoinedEvent.event_id == id).count() - 1
    participating_players = JoinedEvent.query.filter(JoinedEvent.event_id == id).all()
    reviews = Review.query.all()

    now = datetime.now()

    return render_template('event.html', id=id, event=event, users=users, reviews=reviews, now=now,
                           found_players_number=found_players_number, participating_players=participating_players)


@app.route('/edit_event/<int:id>', methods=['GET', 'POST'])
def edit_event(id):
    event_selected = Event.query.filter(Event.id == id).first()
    found_players_number = JoinedEvent.query.filter(JoinedEvent.event_id == id).count() - 1
    if found_players_number == 0:
        found_players_number = 1
    session['sport_selected'] = event_selected.sport_id

    create_event_form = CreateEvent()
    if create_event_form.is_submitted():
        Event.query.filter(Event.id == id).delete()
        db.session.commit()

        if create_event_form.sport_club.data == "other":
            event = Event(id=id,
                          town_id=create_event_form.town.data,
                          sport_id=create_event_form.sport.data,
                          place=create_event_form.place.data,
                          date_start=create_event_form.date_start.data,
                          date_end=create_event_form.date_end.data,
                          wanted_players_number=create_event_form.wanted_players_number.data,
                          creator_id=session['user_id'])
            db.session.add(event)
            db.session.commit()
        else:
            event = Event(id=id,
                          town_id=create_event_form.town.data,
                          sport_id=create_event_form.sport.data,
                          sport_club_id=create_event_form.sport_club.data,
                          date_start=create_event_form.date_start.data,
                          date_end=create_event_form.date_end.data,
                          wanted_players_number=create_event_form.wanted_players_number.data,
                          creator_id=session['user_id'])
            db.session.add(event)
            db.session.commit()

        return redirect(url_for('event', id=id))

    towns = Town.query.all()
    sports = Sport.query.all()
    sportclubs = User.query.filter(User.role_id == 3).all()
    details = SportClubDetails.query.all()
    practicable_sports = FavouriteSport.query.all()

    return render_template('edit_event.html', create_event_form=create_event_form, towns=towns, sports=sports,
                           sportclubs=sportclubs, details=details, practicable_sports=practicable_sports,
                           event_selected=event_selected, found_players_number=found_players_number)


@app.route('/edit_event_sportclub/<int:id>', methods=['GET', 'POST'])
def edit_event_sportclub(id):
    event_selected = Event.query.filter(Event.id == id).first()
    found_players_number = JoinedEvent.query.filter(JoinedEvent.event_id == id).count() - 1
    if found_players_number == 0:
        found_players_number = 1

    details = SportClubDetails.query.all()
    practicable_sports = FavouriteSport.query.all()

    create_event_sportclub_form = CreateEvenSportClub()
    if create_event_sportclub_form.is_submitted():
        Event.query.filter(Event.id == id).delete()
        db.session.commit()

        event = Event(id=id,
                      town_id=event_selected.town_id,
                      sport_id=create_event_sportclub_form.sport.data,
                      sport_club_id=session['user_id'],
                      date_start=create_event_sportclub_form.date_start.data,
                      date_end=create_event_sportclub_form.date_end.data,
                      wanted_players_number=create_event_sportclub_form.wanted_players_number.data,
                      creator_id=session['user_id'])
        db.session.add(event)
        db.session.commit()

        return redirect(url_for('event', id=id))

    return render_template('edit_event_sportclub.html', create_event_sportclub_form=create_event_sportclub_form,
                           details=details, practicable_sports=practicable_sports,
                           event_selected=event_selected, found_players_number=found_players_number)


@app.route('/handle_join/<int:event_id>')
def handle_join(event_id):
    je = JoinedEvent(user_id=session['user_id'], event_id=event_id)
    db.session.add(je)
    db.session.commit()

    return redirect(url_for('event', id=event_id))


@app.route('/handle_disjoin/<int:event_id>')
def handle_disjoin(event_id):
    JoinedEvent.query.filter(JoinedEvent.user_id == session['user_id'], JoinedEvent.event_id == event_id).delete()
    db.session.commit()

    return redirect(url_for('event', id=event_id))


@app.route('/handle_delete_event/<int:event_id>')
def handle_delete_event(event_id):
    Event.query.filter(Event.id == event_id).delete()
    db.session.commit()
    JoinedEvent.query.filter(JoinedEvent.event_id == event_id).delete()
    db.session.commit()

    return redirect(url_for('events'))


@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    create_event_form = CreateEvent()
    if create_event_form.is_submitted():
        if create_event_form.sport_club.data == "other":
            event = Event(town_id=create_event_form.town.data,
                          sport_id=create_event_form.sport.data,
                          place=create_event_form.place.data,
                          date_start=create_event_form.date_start.data,
                          date_end=create_event_form.date_end.data,
                          wanted_players_number=create_event_form.wanted_players_number.data,
                          creator_id=session['user_id'])
            db.session.add(event)
            db.session.commit()
        else:
            event = Event(town_id=create_event_form.town.data,
                          sport_id=create_event_form.sport.data,
                          sport_club_id=create_event_form.sport_club.data,
                          date_start=create_event_form.date_start.data,
                          date_end=create_event_form.date_end.data,
                          wanted_players_number=create_event_form.wanted_players_number.data,
                          creator_id=session['user_id'])
            db.session.add(event)
            db.session.commit()

        last_event = Event.query.filter(Event.creator_id == session['user_id']).order_by(Event.date_added.desc()).first()
        je = JoinedEvent(user_id=session['user_id'], event_id=last_event.id)
        db.session.add(je)
        db.session.commit()

        return redirect("events")

    towns = Town.query.all()
    sports = Sport.query.all()
    sportclubs = User.query.filter(User.role_id == 3).all()
    details = SportClubDetails.query.all()
    practicable_sports = FavouriteSport.query.all()

    return render_template('create_event.html', create_event_form=create_event_form, towns=towns, sports=sports,
                           sportclubs=sportclubs, details=details, practicable_sports=practicable_sports)


@app.route('/create_event_sportclub', methods=['GET', 'POST'])
def create_event_sportclub():
    details = SportClubDetails.query.all()
    practicable_sports = FavouriteSport.query.all()

    create_event_sportclub_form = CreateEvenSportClub()
    if create_event_sportclub_form.is_submitted():
        town_id = 0
        for detail in details:
            if detail.id == session['user_id']:
                town_id = detail.town_id

        event = Event(town_id=town_id,
                      sport_id=create_event_sportclub_form.sport.data,
                      sport_club_id=session['user_id'],
                      date_start=create_event_sportclub_form.date_start.data,
                      date_end=create_event_sportclub_form.date_end.data,
                      wanted_players_number=create_event_sportclub_form.wanted_players_number.data,
                      creator_id=session['user_id'])
        db.session.add(event)
        db.session.commit()

        last_event = Event.query.filter(Event.creator_id == session['user_id']).order_by(Event.date_added.desc()).first()
        je = JoinedEvent(user_id=session['user_id'], event_id=last_event.id)
        db.session.add(je)
        db.session.commit()

        return redirect("events")

    return render_template('create_event_sportclub.html', create_event_sportclub_form=create_event_sportclub_form,
                           details=details, practicable_sports=practicable_sports)


@app.route('/handle_sport_clubs/<sport_id>')
def handle_sport_clubs(sport_id):
    if sport_id != "other":
        session['sport_selected'] = int(sport_id)
    else:
        session['sport_selected'] = sport_id

    return redirect(url_for('create_event'))


@app.route('/create_review/<int:event_id>', methods=['GET', 'POST'])
def create_review(event_id):
    event_selected = Event.query.filter(Event.id == event_id).first()
    create_review_form = CreateReview()
    if create_review_form.is_submitted():
        review = Review(reviewed_id=create_review_form.reviewed_id.data,
                        reviewer_id=session['user_id'],
                        event_id=event_selected.id,
                        skills=create_review_form.skills.data,
                        sportsmanship=create_review_form.sportsmanship.data,
                        willingness=create_review_form.willingness.data,
                        reliability=create_review_form.reliability.data,
                        punctuality=create_review_form.punctuality.data,
                        notes=create_review_form.notes.data,
                        date_added=datetime.now())
        db.session.add(review)
        db.session.commit()

        return redirect(url_for('event', id=event_selected.id))

    joined_events = JoinedEvent.query.filter(JoinedEvent.event_id == event_id).all()
    reviews = Review.query.filter(Review.event_id == event_id).all()

    return render_template('create_review.html', event_selected=event_selected,
                           create_review_form=create_review_form,
                           joined_events=joined_events, reviews=reviews,
                           now=datetime.now())


@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if session.get('user_id'):
        user_info = User.query.filter(User.id == session['user_id']).first()
        if not os.path.exists('static/img/users/' + str(session.get('user_id'))):
            os.makedirs('static/img/users/' + str(session.get('user_id')))
        file_url = os.listdir('static/img/users/' + str(session.get('user_id')))
        file_url = [str(session.get('user_id')) + '/' + file for file in file_url]
        upload_form = UploadForm()
        if upload_form.validate_on_submit():
            shutil.rmtree('static/img/users/' + str(session.get('user_id')))
            filename = photos.save(upload_form.file.data,
                                   name=str(session.get('user_id')) + '.jpg',
                                   folder=str(session.get('user_id')))
            file_url.append(filename)

            user_info.profile_pic = str(session.get('user_id')) + '.jpg'
            db.session.commit()
            session['user_pic'] = 'img/users/' + str(session['user_id']) + '/' + str(session['user_id']) + '.jpg'

            return redirect(url_for('myaccount'))

        return render_template('upload.html', upload_form=upload_form, filelist=file_url, user_info=user_info)
    else:
        return redirect(url_for('signin'))


@app.before_first_request
def setup():
    db.create_all()
    db.session.commit()


@app.before_request
def make_session_permanent():
    if session.get('clear'):
        if session['clear']:
            session.permanent = False
    else:
        session.permanent = True


if __name__ == '__main__':
    app.run()
