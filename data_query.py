# @Author  : kerman jt
# @Time    : 2021/1/20 下午8:17
# @File    : data_query.py

from sqlalchemy import func
import model
from model import db, Course, Talk, Reply
from flask import Flask
from flask_sqlalchemy import SQLAlchemy, event
from array import array
from utils import get_key

course_category = {'计算机': 1, '外语': 2, '理学': 3, '工学': 4, '经济管理': 5,
                   '心理学': 6, '文史哲': 7, '艺术设计': 8, '医药卫生': 9,
                   '教育教学': 10, '法学': 11, '农林园艺': 12, '体育运动': 13,
                   '音乐与舞蹈': 14, '养生保健': 15, '兴趣爱好': 16}


# 每门课程的热门话题
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


# 所有课程的前十热门课程
def query_with_courses():
    ten_popular_talks = Talk.query.order_by(Talk.reply_num.desc()).limit(20)
    top = 1
    print(f"讨论前十的话题为:\r\n")
    for i, item in enumerate(ten_popular_talks):
        if item.text == ten_popular_talks[i + 1].text:
            continue
        else:
            print(f"""第{top}:
    {item.course.name}:
    {item.user_name}
    {item.date}
    {item.text}
    回复人数为:
    {item.reply_num}
    
    """)
            top += 1
        if top == 11:
            break


# 此类别的热门话题（一个）
def get_category_top(id: int):
    courses = Course.query.order_by(Course.tag).all()
    l = []
    for course in courses:
        index = 0
        if course.tag in course_category:
            index = course_category.get(course.tag)
        if index == id:
            l.append(course)
    max_num = 0
    max_talk = Talk
    for course in l:
        talk = Talk.query.filter(course.id == Talk.course_id). \
            order_by(Talk.reply_num.desc()).first()
        if talk is None:
            continue
        if max_num < talk.reply_num:
            max_num = talk.reply_num
            max_talk = talk
    print(f"""
{get_key(course_category, id)[0]}类课程的热门话题为:
{max_talk.course.name}:
{max_talk.user_name}:{max_talk.date}
    {max_talk.text}
回复数为:{max_talk.reply_num}
    """)

# 不同类别的热门话题
def query_with_category():
    i = 1
    for k, v in course_category.items():
        print(v, k, end="   ")
        if i % 5 == 0:
            print()
        i += 1
    print()
    print("请输入你想要查询的类别(只要输入序号即可):")
    id = int(input())
    get_category_top(id)


# 删除重复的讨论数据
def del_repeat_talk():
    all_talks = Talk.query.all()
    for i in range(len(all_talks)):
        for j in range(i + 1, len(all_talks)):
            if all_talks[i].text == all_talks[j].text and \
                    all_talks[i].reply_num == all_talks[j].reply_num and \
                    all_talks[i].date == all_talks[j].date:
                db.session.delete(all_talks[j])
                # print(all_talks[i].id, all_talks[j].id)
    db.session.commit()


# 删除空白的回复数据
def del_repeat_reply():
    all_replys = Reply.query.all()
    # for reply in all_replys:
    #     if reply.text == "":
    #         db.session.delete(reply)
    # db.session.commit()
    for i in range(len(all_replys)):
        for j in range(i + 1, len(all_replys)):
            if all_replys[i].text == all_replys[j].text and \
                    all_replys[i].user_name == all_replys[j].user_name and \
                    all_replys[i].date == all_replys[j].date:
                # db.session.delete(all_replys[j])
                print(all_replys[j])


if __name__ == '__main__':
    # del_repeat_talk()
    # del_repeat_reply()
    # query_with_course()
    # query_with_courses()
    query_with_category()
