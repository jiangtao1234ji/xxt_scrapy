# @Author  : kerman jt
# @Time    : 2021/1/4 下午1:29
# @File    : scrapy_request.py


import os
import re
import threading
import aiohttp
import asyncio
import time

from lxml import etree
from PIL import Image
from bs4 import BeautifulSoup
import requests
from selenium import webdriver

import model
from model import db, Course, Talk, Reply
from flask import Flask
from flask_sqlalchemy import SQLAlchemy, event


def getcookies(base_url: str, header: dict) -> dict:
    '''
    获取登录该网站的cookie
    :param base_url: 该网站的起始网址
    :param header: 请求头
    :return: cookie
    '''
    # 存储cookie
    all_cookie = {}
    try:
        # 判断本地是否有cookie.txt文件
        if not os.path.exists('cookie.txt'):
            # 请求学习通网址
            base_response = requests.get(
                url=base_url,
                headers=header,
                timeout=10
            )

            # 更新cookie
            all_cookie.update(base_response.cookies.get_dict())

            uuid = re.findall(r'<input type = "hidden" value="(.*)" id = "uuid"/>', base_response.text)
            enc = re.findall(r'<input type = "hidden" value="(.*)" id = "enc"/>', base_response.text)
            quickCode = re.findall(r' <img src="(.*)" id="quickCode">', base_response.text)

            # 请求二维码链接，并将二维码保存在本地
            code_url = 'https://passport2.chaoxing.com'
            with open("./code.jpg", "wb")as f:
                f.write(requests.get(
                    url=code_url + quickCode[0],
                    timeout=10
                ).content)
            # 显示二维码
            im = Image.open('./code.jpg')
            im.show()

            # 等待扫码
            state = input('扫码完成？ Y/N\n')
            if state is 'Y':
                # 1. 扫完码请求登录链接
                passport_url = 'https://passport2.chaoxing.com/getauthstatus'  # 更新header
                header['Accept'] = '*/*'
                header['Host'] = 'passport2.chaoxing.com'
                header['Origin'] = 'https://passport2.chaoxing.com'
                header[
                    'Referer'] = 'https://passport2.chaoxing.com/login?fid=&newversion=true&refer=http%3A%2F%2Fi.chaoxing.com'

                data = {
                    'enc': enc,
                    'uuid': uuid
                }

                passport_response = requests.post(
                    url=passport_url,
                    headers=header,
                    data=data,
                    cookies=all_cookie,
                    timeout=10
                )
            # 更新cookie
            all_cookie.update(passport_response.cookies.get_dict())
            # 可以在这里将cookie信息保存，在以后的运行中就不用扫码了
            f = open("cookie.txt", 'w')
            f.write(str(all_cookie))
            f.close()

        else:
            # 本地已经有cookie.txt, 读取cookie
            f = open("cookie.txt", 'r')
            all_cookie = eval(f.read())
            f.close()
    except:
        # 请求超时
        print('请求cookie文件超时')
    return all_cookie


def getcourse(base_url: str, all_cookie: dict, header: dict) -> (list, dict, dict):
    '''
    获取用户课程的链接列表
    :param base_url: 该网站的起始网址
    :param all_cookie: 已经获取的cookie
    :param header: 请求头
    :return: courses_url_list, all_cookie, header: 课程地址列表 更新cookie 更新header
    '''
    # 课程地址列表
    courses_url_list = []
    header['Host'] = 'i.chaoxing.com'
    # 请求用户个人空间地址
    base_response = requests.get(
        url=base_url,
        headers=header,
        cookies=all_cookie,
        timeout=10
    )
    # 更新cookie
    all_cookie.update(base_response.cookies.get_dict())
    # 查找用户课程首页地址
    course_index_url = \
        re.findall(r"name = \"课程\"([^,]*).'([^,]*)'", base_response.text)[0][1]
    header['Host'] = 'mooc1-1.chaoxing.com'
    # 请求用户课程首页地址
    course_index_response = requests.get(
        url=course_index_url,
        headers=header,
        cookies=all_cookie,
        timeout=10
    )
    # 更新cookie
    all_cookie.update(course_index_response.cookies.get_dict())
    # print(course_index_response.text)
    # 查找所有课程的url
    course_list_response = re.findall(r"<a class=\"courseName\"\s* href='(.*)'", course_index_response.text)
    # print(course_list_response)
    # 获得所有课程的url链接
    for i in course_list_response:
        courses_url_list.append('https://mooc1-1.chaoxing.com' + i)
    return courses_url_list, all_cookie, header


async def gettalk(client: aiohttp.ClientSession, courses_talk_url: list) -> (str, str):
    '''
    获取用户课程讨论区的地址
    :param client: aiohttp的client session连接
    :param courses_talk_url: 每个课程的地址
    :param all_cookie: 已经获取的cookie
    :param header: 请求头
    :return: course_talk, course_name: 课程讨论区地址, 课程名
    '''
    # 获取课程讨论区url
    text = await fetch_html(client, courses_talk_url)
    course_talk = ""
    try:
        course_talk_response = \
            re.findall(r"<a mode=\"fuseMode\".*href=\"(.*)\" title=\"讨论\"", text)[0]
        course_talk = 'https://mooc1-1.chaoxing.com' + course_talk_response
        course_name = re.findall(r'<a.*href="javascript:;".*onclick=".*>\s*(.*)', text)[0]
    except IndexError:
        if re.findall(r"placeholder=\"输入验证码\"", text) != []:
            pass
    return course_talk, course_name


async def fetch_html(client: aiohttp.ClientSession, url: str) -> str:
    '''
    获取html页面内容
    :param client: aiohttp的client session连接
    :param url: 链接地址
    :return: html页面内容
    '''
    async with client.get(url, timeout=60) as resp:
        return await resp.text()


async def getcontent(client: aiohttp.ClientSession(), courses_talk_url: str) -> list:
    '''
    获取一门课程讨论区的讨论内容的链接列表
    :param client: aiohttp的client session连接
    :param courses_talk_url: 课程讨论区地址
    :return: 课程讨论区的讨论内容的链接列表
    '''
    # 课程讨论区的讨论内容的链接列表
    content_url_list = []
    # 获取讨论区讨论内容url
    text = await fetch_html(client, courses_talk_url)
    content_url = re.findall(r".*/bbscircle/gettopicdetail(.*)\"", text)
    # content_url = set(content_url)
    for i in content_url:
        i = i.replace("')", "")
        content_url_list.append("https://mooc1-1.chaoxing.com/bbscircle/gettopicdetail" + i)
    # 获取post参数
    params = re.findall(r".*courseId=(.*)&clazzid=(.*)&showChooseClazzId=(.*)&ut=(.*)&enc=(.*)&cpi=(.*)&openc=(.*)",
                        courses_talk_url)
    courseId = params[0][0]
    clazzid = params[0][1]
    showChooseClazzId = params[0][2]
    ut = params[0][3]
    enc = params[0][4]
    cpi = params[0][5]
    openc = params[0][6]
    params = re.findall(r"id=\"lastGetTopicListTime\"\n.*value=\"(.*)\"", text)[0]
    lastGetTopicListTime = params
    lastValue = ""
    try:
        params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
        lastValue = params
    except IndexError as e:
        pass
    page = 2
    topicPage = 2
    # 循环获取全部页面
    if re.findall(r".*查看更多", text) == []:
        return content_url_list
    else:
        while True:
            data = {
                "courseId": courseId,
                "clazzid": clazzid,
                "page": page,
                "enc": enc,
                "topicPage": topicPage,
                "folderId": "",
                "showChooseClazzId": showChooseClazzId,
                "lastGetTopicListTime": lastGetTopicListTime,
                "ut": ut,
                "lastValue": lastValue,
                "cpi": cpi,
                "openc": openc
            }
            async with client.post('https://mooc1-1.chaoxing.com/bbscircle/grouptopic', data=data) as resp:
                text = await resp.text()
            content_url = re.findall(r".*/bbscircle/gettopicdetail(.*)'", text)
            # content_url = set(content_url)
            for i in content_url:
                content_url_list.append("https://mooc1-1.chaoxing.com/bbscircle/gettopicdetail" + i)
            try:
                params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
            except IndexError as e:
                break
            if lastValue == params:
                break
            lastValue = params
            page += 1
            topicPage += 1
    return content_url_list


def save_to_db(r, s, user_name: str, date: str, text: str) -> (str, str, str):
    '''
    获取要保存到数据库的内容字段
    :param r: 正则匹配内容
    :param s: html页面
    :param user_name: 用户名
    :param date: 日期
    :param text: 内容
    :return: 用户名,日期,内容
    '''
    if r[0][0] == "":
        user_name = ""
    else:
        user_name = r[0][0]
    if r[1][1] == "":
        date = ""
    else:
        date = r[1][1]
    try:
        if (r[2][2] == ""):
            text = ""
        elif (r[2][2] == '>'):
            r = re.findall(r'<h3 class="bt ol">\s*.*\s*(.*)', s)
            text = r[0]
        elif (r[2][2].find("<br>") != -1):
            newstr = r[2][2].replace("<br>", " ")
            text = newstr
        elif (r[2][2].find("<BR>") != -1):
            newstr = r[2][2].replace("<BR>", " ")
            text = newstr
        elif (r[2][2].find("<img src=") != -1):
            text = ""
        else:
            text = r[2][2]
    except IndexError as e:
        r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
        if r == []:
            text = ""
        elif (r[0] == ""):
            text = ""
        elif (r[0].find("<br>") != -1):
            newstr = r[0].replace("<br>", " ")
            text = newstr
        elif (r[0].find("<img src=") != -1):
            text = ""
        else:
            text = r[0]
    return user_name, date, text


def write_to_file(r, s, course_name):
    '''
    保存内容到文件
    :param r: 正则匹配内容
    :param s: html页面
    :param course_name: 课程名
    :return:
    '''
    # 保存到文件
    with open(f'/home/kerman/paperdata/{course_name}', 'a') as f:
        if r[0][0] == "":
            pass
        else:
            f.write(r[0][0] + "\r\n")
        if r[1][1] == "":
            pass
        else:
            f.write(r[1][1] + "\r\n")
        try:
            if (r[2][2] == ""):
                pass
            elif (r[2][2].find("<br>") != -1):
                newstr = r[2][2].replace("<br>", " ")
                f.write(newstr + "\r\n")
            elif (r[2][2].find("<BR>") != -1):
                newstr = r[2][2].replace("<BR>", " ")
                f.write(newstr + "\r\n")
            elif (r[2][2].find("<img src=") != -1):
                pass
            else:
                f.write(r[2][2] + "\r\n")
        except IndexError as e:
            r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
            if r == []:
                pass
            elif (r[0] == ""):
                pass
            elif (r[0].find("<br>") != -1):
                newstr = r.replace("<br>", " ")
                f.write(newstr + "\r\n")
            elif (r[0].find("<img src=") != -1):
                pass
            else:
                f.write(r[0] + "\r\n")


async def savecontent_to_db(course: Course, client: aiohttp.ClientSession, content_url_list: list, all_cookie: dict,
                            course_name: str):
    '''
    保存一门课程的讨论区的所有内容
    :param course: course表
    :param client: aiohttp的client session连接
    :param content_url_list: 课程讨论区的讨论内容的链接列表
    :param all_cookie: 已经获取的cookie
    :param course_name: 课程名
    '''
    tt1 = time.time()
    async with aiohttp.ClientSession(cookies=all_cookie) as client:
        talk_list = []
        for content_url in content_url_list:
            tt = time.time()
            text = await fetch_html(client, content_url)
            # 用xpath匹配出所有的讨论内容并保存
            selector = etree.HTML(text)
            user_name = ""
            date = ""
            content = ""
            for i in selector.xpath("//div[@class='fr oneRight']"):
                # 转化为string
                s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                r = re.findall(r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*id=\"topicContent\"(.*)</p>",
                               s)
                # 保存到文件
                # write_to_file(r, s, course_name)
                # 获取所需字段
                # talk_user_name, talk_date, talk_content = save_to_db(r, s, user_name, date, content)
                if r[0][0] == "":
                    talk_user_name = ""
                else:
                    talk_user_name = r[0][0]
                if r[1][1] == "":
                    talk_date = ""
                else:
                    talk_date = r[1][1]
                try:
                    if (r[2][2] == ""):
                        talk_content = ""
                    elif (r[2][2] == '>'):
                        r = re.findall(r'<h3 class="bt ol">\s*.*\s*(.*)', s)
                        talk_content = r[0]
                    elif (r[2][2].find("<br>") != -1):
                        newstr = r[2][2].replace("<br>", " ")
                        talk_content = newstr
                    elif (r[2][2].find("<BR>") != -1):
                        newstr = r[2][2].replace("<BR>", " ")
                        talk_content = newstr
                    elif (r[2][2].find("<img src=") != -1):
                        talk_content = ""
                    else:
                        talk_content = r[2][2]
                except IndexError as e:
                    r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                    if r == []:
                        talk_content = ""
                    elif (r[0] == ""):
                        talk_content = ""
                    elif (r[0].find("<br>") != -1):
                        newstr = r[0].replace("<br>", " ")
                        talk_content = newstr
                    elif (r[0].find("<img src=") != -1):
                        talk_content = ""
                    else:
                        talk_content = r[0]
            # with open(f'/home/kerman/paperdata/{course_name}', 'a') as f:
            #     f.write("回复:" + "\r\n")
            # 回复数量
            reply_num = 0
            reply_list = []
            for i in selector.xpath("//div[@class='fr secondRight']"):
                # 转化为string
                s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                r = re.findall(
                    r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<", s)

                # print(r[0][0], r[1][1], r[2][2])
                # 保存到文件
                # write_to_file(r,s,course_name)
                # 保存到数据库
                # reply_user_name, reply_date, reply_content = save_to_db(r, s, user_name, date, content)
                if r[0][0] == "":
                    reply_user_name = ""
                else:
                    reply_user_name = r[0][0]
                if r[1][1] == "":
                    reply_date = ""
                else:
                    reply_date = r[1][1]
                try:
                    if (r[2][2] == ""):
                        reply_content = ""
                    elif (r[2][2] == '>'):
                        r = re.findall(r'<h3 class="bt ol">\s*.*\s*(.*)', s)
                        reply_content = r[0]
                    elif (r[2][2].find("<br>") != -1):
                        newstr = r[2][2].replace("<br>", " ")
                        reply_content = newstr
                    elif (r[2][2].find("<BR>") != -1):
                        newstr = r[2][2].replace("<BR>", " ")
                        reply_content = newstr
                    elif (r[2][2].find("<img src=") != -1):
                        reply_content = ""
                    else:
                        reply_content = r[2][2]
                except IndexError as e:
                    r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                    if r == []:
                        reply_content = ""
                    elif (r[0] == ""):
                        reply_content = ""
                    elif (r[0].find("<br>") != -1):
                        newstr = r[0].replace("<br>", " ")
                        reply_content = newstr
                    elif (r[0].find("<img src=") != -1):
                        reply_content = ""
                    else:
                        reply_content = r[0]
                reply_num += 1
                try:
                    if Reply.query.filter_by(user_name=reply_user_name, date=reply_date).all() == []:
                        # reply_dict = {"user_name": reply_user_name, "date": reply_date, "text": reply_content,
                        #               "flag_id": flag_id}
                        reply = Reply(user_name=reply_user_name, date=reply_date, text=reply_content)
                        reply_list.append(reply)
                        # db.session.add(reply)
                        # db.session.commit()
                except Exception:
                    pass
            print(f"tt:{time.time() - tt}")
            # 获取post参数
            params = re.findall(r".*courseId=(.*)&clazzid=(.*)&topicid=(.*)"
                                r"&showChooseClazzId=(.*)&ut=(.*)&folderId=(.*)&cpi=(.*)"
                                r"&openc=(.*)&enc", content_url)
            clazzid = params[0][1]
            topicid = params[0][2]
            cpi = params[0][6]
            ut = params[0][4]
            openc = params[0][7]
            pagesize = ""
            try:
                pagesize = re.findall(r"var.*pageSize.*\"(.*)\"", text)[0]
            except IndexError as e:
                pass
            order = ""
            try:
                order = re.findall(r".*order.*\"(.*)\"", text)[0]
            except IndexError as e:
                pass
            uuid = ""
            try:
                uuid = re.findall(r".*uuid.*'(.*)'", text)[0]
            except IndexError as e:
                pass
            lastValue = ""
            try:
                params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
                lastValue = params
            except IndexError as e:
                pass
            if re.findall(r"查看更多", text) == []:
                if Talk.query.filter_by(user_name=talk_user_name, date=talk_date).all() == []:
                    # talk_dict = {"user_name": talk_user_name, "date": talk_date, "text": talk_content,
                    #              "reply_num": reply_num, "flag_id": flag_id}
                    talk = Talk(user_name=talk_user_name, date=talk_date, text=talk_content, reply_num=reply_num)
                    # for i in reply_list:
                    #     talk.reply.append(i)
                    # db.session.execute(Reply.__table__.insert(), reply_list)
                    talk.reply = reply_list
                    talk_list.append(talk)
                    # db.session.add(talk)
                    # db.session.commit()
                continue
            else:
                tt = time.time()
                while True:
                    if lastValue == "0":
                        break
                    # tt = time.time()
                    data = {
                        "clazzid": clazzid,
                        "topicid": topicid,
                        "pagesize": pagesize,
                        "order": order,
                        "cpi": cpi,
                        "ut": ut,
                        "openc": openc,
                        "uuid": uuid,
                        "lastValue": lastValue
                    }
                    # print(time.time()-tt)
                    # tt = time.time()
                    async with client.post('https://mooc1-1.chaoxing.com/bbscircle/getreplysbytopicId',
                                           data=data) as resp:
                        text = await resp.text()
                    # print(time.time() - tt)
                    try:
                        params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
                    except IndexError as e:
                        break
                    if lastValue == params:
                        break
                    lastValue = params
                    selector = etree.HTML(text)
                    for i in selector.xpath("//div[@class='fr secondRight']"):
                        # 转化为string
                        s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                        r = re.findall(
                            r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<",
                            s)
                        # print(r[0][0], r[1][1], r[2][2])
                        # 保存到文件
                        # write_to_file(r, s, course_name)
                        # 保存到数据库
                        # reply_user_name, reply_date, reply_content = save_to_db(r, s, user_name, date, content)
                        if r[0][0] == "":
                            reply_user_name = ""
                        else:
                            reply_user_name = r[0][0]
                        if r[1][1] == "":
                            reply_date = ""
                        else:
                            reply_date = r[1][1]
                        try:
                            if (r[2][2] == ""):
                                reply_content = ""
                            elif (r[2][2] == '>'):
                                r = re.findall(r'<h3 class="bt ol">\s*.*\s*(.*)', s)
                                reply_content = r[0]
                            elif (r[2][2].find("<br>") != -1):
                                newstr = r[2][2].replace("<br>", " ")
                                reply_content = newstr
                            elif (r[2][2].find("<BR>") != -1):
                                newstr = r[2][2].replace("<BR>", " ")
                                reply_content = newstr
                            elif (r[2][2].find("<img src=") != -1):
                                reply_content = ""
                            else:
                                reply_content = r[2][2]
                        except IndexError as e:
                            r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                            if r == []:
                                reply_content = ""
                            elif (r[0] == ""):
                                reply_content = ""
                            elif (r[0].find("<br>") != -1):
                                newstr = r[0].replace("<br>", " ")
                                reply_content = newstr
                            elif (r[0].find("<img src=") != -1):
                                reply_content = ""
                            else:
                                reply_content = r[0]
                        reply_num += 1
                        try:
                            if Reply.query.filter_by(user_name=reply_user_name, date=reply_date).all() == []:
                                # reply_dict = {"user_name": reply_user_name, "date": reply_date, "text": reply_content,
                                #               "flag_id": flag_id}
                                reply = Reply(user_name=reply_user_name, date=reply_date, text=reply_content)
                                reply_list.append(reply)
                                # db.session.add(reply)
                                # db.session.commit()
                        except Exception:
                            pass

                print(f"while循环:{time.time() - tt}")
                if Talk.query.filter_by(user_name=talk_user_name, date=talk_date).all() == []:
                    # talk_dict = {"user_name": talk_user_name, "date": talk_date, "text": talk_content,
                    #              "reply_num": reply_num, "flag_id": flag_id}
                    talk = Talk(user_name=talk_user_name, date=talk_date, text=talk_content, reply_num=reply_num)
                    # for i in reply_list:
                    #   talk.reply.append(i)
                    talk.reply = reply_list
                    # db.session.execute(Reply.__table__.insert(), reply_list)
                    talk_list.append(talk)
                    # db.session.add(talk)
                    # db.session.commit()
        # for i in talk_list:
        #     course.talk.append(i)
        # db.session.execute(Talk.__table__.insert(), talk_list)
        course.talk = talk_list
        # course_dict = {"name": course_name, "tag": None, "flag_id": flag_id}
        db.session.add(course)
        # db.session.execute(Course.__table__.insert(), course_dict)
        db.session.commit()
    print(f"总循环:{time.time() - tt1}")


async def savecontent_to_file(client: aiohttp.ClientSession, content_url_list: list, all_cookie: dict,
                              course_name: str):
    '''
    保存一门课程的讨论区的所有内容
    :param course: course表
    :param client: aiohttp的client session连接
    :param content_url_list: 课程讨论区的讨论内容的链接列表
    :param all_cookie: 已经获取的cookie
    :param course_name: 课程名
    '''

    async with aiohttp.ClientSession(cookies=all_cookie) as client:
        talk_list = []
        for content_url in content_url_list:
            text = await fetch_html(client, content_url)
            # 用xpath匹配出所有的讨论内容并保存
            selector = etree.HTML(text)
            for i in selector.xpath("//div[@class='fr oneRight']"):
                # 转化为string
                s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                r = re.findall(r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*id=\"topicContent\"(.*)</p>",
                               s)
                # 保存到文件
                write_to_file(r, s, course_name)
            with open(f'/home/kerman/paperdata/{course_name}', 'a') as f:
                f.write("回复:" + "\r\n")
            # 回复数量
            reply_num = 0
            for i in selector.xpath("//div[@class='fr secondRight']"):
                # 转化为string
                s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                r = re.findall(
                    r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<", s)
                reply_num += 1
                # print(r[0][0], r[1][1], r[2][2])
                # 保存到文件
                write_to_file(r, s, course_name)

            # 获取post参数
            params = re.findall(r".*courseId=(.*)&clazzid=(.*)&topicid=(.*)"
                                r"&showChooseClazzId=(.*)&ut=(.*)&folderId=(.*)&cpi=(.*)"
                                r"&openc=(.*)&enc", content_url)
            clazzid = params[0][1]
            topicid = params[0][2]
            cpi = params[0][6]
            ut = params[0][4]
            openc = params[0][7]
            pagesize = ""
            try:
                pagesize = re.findall(r"var.*pageSize.*\"(.*)\"", text)[0]
            except IndexError as e:
                pass
            order = ""
            try:
                order = re.findall(r".*order.*\"(.*)\"", text)[0]
            except IndexError as e:
                pass
            uuid = ""
            try:
                uuid = re.findall(r".*uuid.*'(.*)'", text)[0]
            except IndexError as e:
                pass
            lastValue = ""
            try:
                params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
                lastValue = params
            except IndexError as e:
                pass
            if re.findall(r"查看更多", text) == []:
                continue
            else:
                while True:
                    if lastValue == "0":
                        break
                    data = {
                        "clazzid": clazzid,
                        "topicid": topicid,
                        "pagesize": pagesize,
                        "order": order,
                        "cpi": cpi,
                        "ut": ut,
                        "openc": openc,
                        "uuid": uuid,
                        "lastValue": lastValue
                    }
                    async with client.post('https://mooc1-1.chaoxing.com/bbscircle/getreplysbytopicId',
                                           data=data) as resp:
                        text = await resp.text()
                    try:
                        params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", text)[0]
                    except IndexError as e:
                        break
                    if lastValue == params:
                        break
                    lastValue = params
                    selector = etree.HTML(text)
                    for i in selector.xpath("//div[@class='fr secondRight']"):
                        # 转化为string
                        s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                        r = re.findall(
                            r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<",
                            s)
                        # print(r[0][0], r[1][1], r[2][2])
                        # 保存到文件
                        write_to_file(r, s, course_name)
                        reply_num += 1
            with open(f'/home/kerman/paperdata/{course_name}', 'a') as f:
                f.write("回复数:" + reply_num + "\r\n")


# 保存到数据库
async def db_main():
    # 起始网址
    base_url = 'http://i.chaoxing.com'
    # 请求头
    header = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    }
    # 获取cookie
    all_cookie = getcookies(base_url, header)
    # 获取用户课程的链接列表
    courses_url_list, all_cookie, header = getcourse(base_url, all_cookie, header)
    # 线程池
    threads = []
    task_list = []
    tt = time.time()
    for courses_talk_url in courses_url_list[40:]:
        # 获取一门课程讨论区的链接地址
        async with aiohttp.ClientSession(cookies=all_cookie) as client:
            course_talk, course_name = await gettalk(client, courses_talk_url)
        # 获取一门课程讨论区的讨论内容的链接列表
        async with aiohttp.ClientSession(cookies=all_cookie) as client:
            content_url_list = await getcontent(client, course_talk)
        if Course.query.filter_by(name=course_name).all() == []:
            course = Course(name=course_name, tag=None)
            # 保存讨论内容
            task = asyncio.create_task(
                savecontent_to_db(course, client, content_url_list, all_cookie, course_name))
            task_list.append(task)
    # for t in threads:
    #     t.start()
    for task in task_list:
        await task
    print(time.time() - tt)


# 保存到文件
# async def file_main():
#     # 起始网址
#     base_url = 'http://i.chaoxing.com'
#     # 请求头
#     header = {
#         'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
#     }
#     # 获取cookie
#     all_cookie = getcookies(base_url, header)
#     # 获取用户课程的链接列表
#     courses_url_list, all_cookie, header = getcourse(base_url, all_cookie, header)
#     num = 1
#     threads = []
#     task_list = []
#     tt = time.time()
#     for courses_talk_url in courses_url_list:
#         # 获取一门课程讨论区的链接地址
#         async with aiohttp.ClientSession(cookies=all_cookie) as client:
#             course_talk, course_name = await gettalk(client, courses_talk_url)
#         # 获取一门课程讨论区的讨论内容的链接列表
#         async with aiohttp.ClientSession(cookies=all_cookie) as client:
#             content_url_list = await getcontent(client, course_talk)
#         # 保存讨论内容
#         task = asyncio.create_task(
#             savecontent_to_file(client, content_url_list, all_cookie, course_name))
#         task_list.append(task)
#     for task in task_list:
#         await task
#     print(time.time() - tt)


if __name__ == '__main__':
    # db.drop_all()
    # db.create_all()
    asyncio.run(db_main())
