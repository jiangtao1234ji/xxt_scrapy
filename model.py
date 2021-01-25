# @Author  : kerman jt
# @Time    : 2021/1/4 下午1:31
# @File    : model.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy, event

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = ''
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), nullable=False)
    tag = db.Column(db.String(10))
    talk = db.relationship("Talk", backref="course")



class Talk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20))
    date = db.Column(db.String(20))
    text = db.Column(db.Text())
    reply_num = db.Column(db.Integer)
    reply = db.relationship("Reply", backref="talk")
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))




class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(20))
    date = db.Column(db.String(20))
    text = db.Column(db.Text())
    talk_id = db.Column(db.Integer, db.ForeignKey("talk.id"))




if __name__ == '__main__':
    db.drop_all()
    db.create_all()
