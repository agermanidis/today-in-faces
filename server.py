import uuid, random
from datetime import datetime, timedelta
from flask import Flask, render_template

from db import db

app = Flask(__name__)

def get_faces():
    articles = db.articles.find({
        'faces': {'$not': {'$size': {'$gt': 0}}},
        't': {'$gt': datetime.now() - timedelta(days=1)}
    })
    ret = []
    for article in articles:
        href = article['url']
        for face_url in article['faces']:
            ret.append({'src': face_url, 'href': href})
    random.shuffle(ret)
    return ret

@app.route("/")
def index():
    return render_template('index.html', faces=get_faces())

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port = 4144)
