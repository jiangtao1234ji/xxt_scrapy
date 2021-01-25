# @Author  : kerman jt
# @Time    : 2021/1/20 下午8:17
# @File    : data_analysis.py
from sqlalchemy import func

import model
from model import db, Course, Talk, Reply
from flask import Flask
from flask_sqlalchemy import SQLAlchemy, event


def query_with_course():
    all_courses = Course.query.all()
    all_popular_talks = []
    for item in all_courses:
        all_popular_talks.append(Talk.query.order_by(Talk.reply_num.desc()). \
                                 filter_by(course_id=item.id).first())
    for course, talk in zip(all_courses, all_popular_talks):
        if talk is None:
            print(f"{course.name}:没有讨论话题!!!")
        else:
            print(f"""{course.name}的热门话题为:
{talk.user_name}
{talk.date}
{talk.text}
回复人数为:
{talk.reply_num}
                    
                    """)


def query_with_courses():
    ten_popular_talks = Talk.query.order_by(Talk.reply_num.desc()).limit(10).all()
    top = 1
    print(f"讨论前十的话题为:\r\n")
    for item in ten_popular_talks:
        print(f"""第{top}:
{item.course.name}:
{item.user_name}
{item.date}
{item.text}
回复人数为:
{item.reply_num}

""")
        top += 1


if __name__ == '__main__':
    # query_with_course()
    query_with_courses()
