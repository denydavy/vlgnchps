#!/usr/bin/python3
from flask import Flask, render_template, url_for, request, session, escape, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, requests, json, re

secret = os.urandom(24)
GAPP_KEY = "AIzaSyDI49mvidsduT_9s7RkC35nqZFhkdW544Q"
app = Flask(__name__)
app.secret_key = secret
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///pool.db"
db = SQLAlchemy(app)

def add_new_author(name,yt_id, image):
    """
    f u pep
    """
    author = Author(name=name, yt_id=yt_id, image=image)
    db.session.add(author)
    db.session.commit()
    flash('Добавлен новый канал!', 'primary')
    
def get_authors():
    """
    f u pep
    """
    authors = Author.query.all()
    return authors

def get_author(name):
    """
    f u pep
    """
    return Author.query.filter_by(name=name).first()

def get_author_details(yt_id):
    """
    f u pep
    """
    author = Author.query.filter_by(yt_id=yt_id).first()
    return author

def load_videos_for(yt_id):
    """
    f u pep
    """
    author = Author.query.filter_by(yt_id=yt_id).first()
    videos = requests.get('https://www.googleapis.com/youtube/v3/search?part=snippet&channelId='+yt_id+'&maxResults=50&&order=date&type=video&key='+GAPP_KEY).json()
    print(videos)
    for video in videos['items']:
        if not Video.query.filter_by(name=video['snippet']['title']).first():
            entry = Video(name=video['snippet']['title'], ink=video['id']['videoId'])
            print(entry)
            author.videos.append(entry)
            db.session.commit()
    print(author.videos)

def get_yt_feed(link):
    """
    f u pep
    """
    url = ''
    if re.search('user', link) is not None:
        username = re.search('user\/(.+)', link).group(1)
        url = 'https://www.googleapis.com/youtube/v3/channels?part=snippet&forUsername='+str(username)+"&key="+GAPP_KEY
    elif re.search('channel', link) is not None:
        channel = re.search('channel\/(.+)', link).group(1)
        url = 'https://www.googleapis.com/youtube/v3/channels?part=snippet&id='+str(channel)+"&key="+GAPP_KEY
    else:
        video_id = re.search('watch\?v=(.+)', link).group(1)
        video = requests.get("https://www.googleapis.com/youtube/v3/videos?part=snippet&id="+video_id+"&key="+GAPP_KEY).json()
        profile = requests.get("https://www.googleapis.com/youtube/v3/channels?part=snippet&id="+video['items'][0]['snippet']['channelId']+"&key="+GAPP_KEY).json()
        cid = profile['items'][0]['id']
        name = profile['items'][0]['snippet']['title']
        image = profile['items'][0]['snippet']['thumbnails']['high']['url']
        author = Author.query.filter_by(yt_id=cid).first()
        if author is None:
            add_new_author(name, cid, image)
            author = Author.query.filter_by(yt_id=cid).first()          
        if Video.query.filter_by(name=video['items'][0]['snippet']['title']).first() is None:
            entry = Video(name=video['items'][0]['snippet']['title'], link=video['items'][0]['id'])
            author.videos.append(entry)
            db.session.commit()
        return None

    profile = requests.get(url).json()
    cid = profile['items'][0]['id']
    name = profile['items'][0]['snippet']['title']
    image = profile['items'][0]['snippet']['thumbnails']['high']['url']
    return (name, cid, image)

@app.route('/api/delete/videos/<yt_id>')
def delete_videos_for(yt_id):
    author = Author.query.filter_by(yt_id=yt_id).first()
    videos = Video.query.filter_by(author_id=author.id).all()
    for video in videos:
        db.session.delete(video)
    del author.videos[:]      
    db.session.commit()
    return redirect(url_for('author_page', yt_id=yt_id))

@app.route('/api/delete/author/<yt_id>')
def delete_author(yt_id):
    author = Author.query.filter_by(yt_id=yt_id).first()
    videos = Video.query.filter_by(author_id=author.id).all()
    for video in videos:
        db.session.delete(video)
    del author.videos[:]
    db.session.delete(author)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/api/load/<yt_id>', methods=['GET','POST'])
def load_videos_yt(yt_id):
    load_videos_for(yt_id)
    return redirect(url_for('author_page', yt_id=yt_id))

@app.route('/api/videos/get')
def get_all_videos():
    q = Video.query.filter_by(is_in_api=True).all()
    res = dict()
    for i in range(len(q)):
        item = dict()
        item['name'] = q[i].name
        item['link'] = q[i].link
        item['author'] = Author.query.filter_by(id=q[i].author_id).first().name
        res[i] = item
    return json.dumps(res, ensure_ascii=False)

@app.route('/api/availability/<link>', methods=['GET'])
def add_video_to_api(link):
    res = Video.query.filter_by(link=link).first()
    if not res.is_in_api:
        res.is_in_api = True
    else:
        res.is_in_api = False
    db.session.commit()
    return redirect(url_for('author_page', yt_id=Author.query.filter_by(id=res.author_id).first().yt_id))

class Author(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    yt_id = db.Column(db.String(80), nullable=False)
    image = db.Column(db.String(300))
    videos = db.relationship('Video', backref='author')

    def __repr__(self):
        return "<Author %r,%s,%s>" % (self.name, self.image, self.yt_id)


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), unique=True)
    link = db.Column(db.String(300), unique=True)
    pub_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_in_api = db.Column(db.Boolean, default=True)
    author_id = db.Column(db.Integer, db.ForeignKey('author.id'))
    def __repr__(self):
        return "<Video %r>" % self.link


@app.template_filter('isInApi')
def isInApi(video):
    res = Video.query.filter_by(link=video.link, is_in_api=video.is_in_api).first()
    if res.is_in_api:
        return "checked"
    else:
        return ''

@app.route('/', methods=['GET',"POST"])
def index():
    if request.method == "POST":
        if not get_author(request.form['author']):
            try:
                meta = get_yt_feed(request.form['author'])
                if meta is not None:
                    add_new_author(meta[0], meta[1], meta[2])
            except Exception as e:
                print(str(e))
                flash('Ошибка соединения с YOUTUBE-API', 'danger')
                authors = get_authors()
                return render_template('index.html', authors=authors)      
        authors = get_authors()
        flash(u'Видео успешно добавлено!', 'success') 
        return render_template('index.html', authors=authors)
    authors = get_authors()
    return render_template('index.html', authors=authors)

@app.route('/author/<yt_id>', methods=['GET','POST'])
def author_page(yt_id):
    if request.method == "POST":
        return redirect(url_for('load_videos_yt', yt_id=yt_id))
    return render_template('channel.html', author=get_author_details(yt_id))    

@app.route("/back")
def back():
    return redirect(url_for('index'))

if __name__ == "__main__":
    db.create_all()
    app.run(host="0.0.0.0",port="5001")
    