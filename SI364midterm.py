###############################
####### SETUP (OVERALL) #######
###############################

## Import statements
import os
import requests
import json
from flask import Flask, render_template, session, redirect, url_for, flash, request
from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, IntegerField, SubmitField, RadioField, ValidationError
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import Required, Length, NumberRange # Here, too
from flask_sqlalchemy import SQLAlchemy
import hashlib
import datetime

m = hashlib.md5()


## App setup code
app = Flask(__name__)
app.debug = True
app.use_reloader = True

## All app.config values
## app.config keys taken from previous assignments to avoid setup errors
app.config['SECRET_KEY'] = 'myN4m3isM4ll0CcnduW1lLn3VeRKn0w'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/SI364Midterm"
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

## Statements for db setup (and manager setup if using Manager)
db = SQLAlchemy(app)

## Yes I know this should be stored somewhere else but it needs to be graded.
marvelPublicKey = '70c51b464cb7732b54c1f5fb9b6b24eb'
marvelPrivateKey = '83b7b064e4f3b6251dc8cbe7a40ff9467bc301c8'

######################################
######## HELPER FXNS (If any) ########
######################################

def addComics(comicTitles, heroID):
    for c in comicTitles:
        print(c[0])
        newComic = Comic.query.filter_by(title = c[0]).first()
        if not newComic:
            newComic = Comic(title = c[0], imageUrl = c[1], heroID = heroID)
            db.session.add(newComic)
            db.session.commit()
            print('{}  - {} added'.format(c[0], c[1]))



def getOrCreateHero(heroName, numComics):
    '''
    gets Hero from table
    if not already present, requests data for Hero with heroName
    Makes calls to add comics to table either way, in case of increased quantity.
    '''
    global m
    heroQ = Hero.query.filter_by(name = heroName).first()
    inTable = True
    requestSuccess = True
    if not heroQ:
        inTable = False
        try:
            ts = str(datetime.datetime.now().timestamp())
            combo = ts + marvelPrivateKey + marvelPublicKey
            m.update(combo.encode('utf-8'))
            baseURL = 'https://gateway.marvel.com/v1/public/characters'
            params =  {'name': heroName, 'apikey': marvelPublicKey, 'hash': m.hexdigest(), 'ts': ts }
            resp = requests.get(baseURL, params = params)
            heroDict = json.loads(resp.text)
            print(heroDict)
            heroDict = heroDict['data']['results'][0]
            heroName = heroDict['name']
            marvelID = heroDict['id']
            heroImg = heroDict['thumbnail']['path'] + '.' + heroDict['thumbnail']['extension']
            comicTitles = []
            if numComics > 0:
                comicTitles = [(c['name'], c['resourceURI']) for c in heroDict['comics']['items']][:numComics]
            heroQ = Hero(name = heroName, marvelID = marvelID, imageUrl = heroImg)
            db.session.add(heroQ)
            db.session.commit()
            addComics(comicTitles, heroQ.id)
        except:
            print("EXCEPT TRIGGERED")
            requestSuccess = False   
    
    return inTable, requestSuccess, heroQ


##################
##### MODELS #####
##################

class Name(db.Model):
    __tablename__ = "names"
    id = db.Column(db.Integer,primary_key=True)
    name = db.Column(db.String(64))

    def __repr__(self):
        return "{} (ID: {})".format(self.name, self.id)

class Hero(db.Model):
    __tablename__ = 'heroes'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(180), unique = True)
    marvelID = db.Column(db.Integer, unique = True)
    imageUrl = db.Column(db.String(400))
    comicsList = db.relationship('Comic', backref = 'hero')
        
class Comic(db.Model):
    __tablename__ = 'comics'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(180))
    imageUrl = db.Column(db.String(400))
    heroID = db.Column(db.Integer, db.ForeignKey('heroes.id'))

    def __repr__(self):
        return '{} - {}'.format(Hero.query.filter_by(id = self.heroID).first().name, self.title)


class Wish(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    comicID = db.Column(db.Integer, db.ForeignKey('comics.id'))
        

def queryAllComics():
        return Comic.query

###################
###### FORMS ######
###################

class NameForm(FlaskForm):

    def nonEmpty(self, field):
        if len(field.data.strip()) == 0:
            raise ValidationError("Name must be non-empty")

    name = StringField("Please enter your name.",validators=[Required(), nonEmpty])
    submit = SubmitField()

DC = ["Batman", "Superman", "Wonderwoman"]

class HeroForm(FlaskForm):

    def notDC(self, field):
        if field.data in DC:
            raise ValidationError("Please only search for Marvel heroes.")

    def validRange(self, field):
        if field.data < 0 or field.data > 20:
            raise ValidationError("Please enter a number between 0 and 20.")

    heroName = StringField("Enter a Marvel hero name: ", validators = [Required(), Length(1,80), notDC])
    numComics = IntegerField("How many comics with this hero would you like to search for? (0 - 20)", validators = [Required(), NumberRange(0,20), validRange])
    submit = SubmitField()
        
class wishlist(FlaskForm):
    comicWish = QuerySelectField("Pick a comic to add to your wishlist: ", query_factory = queryAllComics, allow_blank = False)
    submit = SubmitField()
        

#######################
###### VIEW FXNS ######
#######################

@app.errorhandler(404)
def fourOhFour(error):
    return render_template('error404.html')



@app.route('/', methods=['GET', 'POST'])
def home():
    form = NameForm() # User should be able to enter name after name and each one will be saved, even if it's a duplicate! Sends data with GET
    n = request.args.get('name')
    if n != None:
        newname = Name(name = n)
        db.session.add(newname)
        db.session.commit()
        return redirect(url_for('all_names'))
    return render_template('base.html',form=form)

@app.route('/names', methods=['GET', 'POST'])
def all_names():
    names = Name.query.all()
    onlyNames = [n.name for n in names]
    return render_template('name_example.html',names=onlyNames, form = NameForm())

@app.route('/heroForm')
def heroFormPage():
    return render_template('heroForm.html', heroForm = HeroForm(), form = NameForm())

@app.route('/allHeroes')
def allHeroes():
    form = HeroForm()
    allheroesQ = Hero.query.all()
    h = request.args.get('heroName')
    numComics = request.args.get('numComics')
    if numComics != None:
        numComics = int(numComics)
    allheroesList = [(hero.name, hero.imageUrl) for hero in allheroesQ]
    existHero = Hero.query.filter_by(name = h).first()
    already = existHero != None and numComics != None and len(existHero.comicsList) > numComics
    if h in DC:
        flash("Please only choose Marvel heroes")

    if not h or h in DC or already:
        return render_template('allheroes.html', heroesList = allheroesList, hasHeroes = (len(allheroesQ) > 0), form = NameForm())
    else:
        # TODO: Add error flashes
        heroTup = getOrCreateHero(h, numComics)
        print(heroTup)
        if heroTup[0]:
            flash("Hero already previously present in table")
            h = None
        if not heroTup[1]:
            flash("Error requesting hero. Please wait a minute or two and try again, or try a new query if the problem persists.")
            h = None
        allheroesQ = Hero.query.all()
        allheroesList = [(h.name, h.imageUrl) for h in allheroesQ]
        return render_template('allheroes.html', heroesList = allheroesList, addedHero = h, hasHeroes = (len(allheroesQ) > 0), form = NameForm())

@app.route('/wishlist', methods=['GET', 'POST'])
def showWishlist():
    thisWishForm = wishlist()
    if thisWishForm.validate_on_submit():
        w = thisWishForm.comicWish.data
        if not Wish.query.filter_by(comicID = w.id).first():
            w = Wish(comicID = w.id)
            db.session.add(w)
            db.session.commit()
        return redirect(url_for('showWishlist'))
    allWishes = []
    for wish in Wish.query.all():
        com = Comic.query.filter_by(id = wish.comicID).first()
        allWishes.append(com)
    print(allWishes)
    return render_template('wishlist.html', form = NameForm(), wishForm = thisWishForm, userWishes = allWishes)
        


## Code to run the application
if __name__ == '__main__':
    db.create_all()
    app.run()

