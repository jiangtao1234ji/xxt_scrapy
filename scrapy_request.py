# @Author  : kerman jt
# @Time    : 2021/1/4 下午1:29
# @File    : scrapy_request.py


import os
import re
import threading
import time

from lxml import etree
from PIL import Image
from bs4 import BeautifulSoup
import requests
from selenium import webdriver


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


def gettalk(courses_talk_url: str, all_cookie: dict, header: dict) -> str:
    '''
    获取用户课程讨论区的链接
    :param courses_talk_url: 课程的地址
    :param all_cookie: 已经获取的cookie
    :param header: 请求头
    :return: courses_talk: 课程讨论区地址
    '''

    # 获取讨论区的每个讨论的url
    course_url_response = requests.get(
        url=courses_talk_url,
        headers=header,
        cookies=all_cookie,
        timeout=10
    )
    course_talk = ""
    try:
        course_talk_response = \
            re.findall(r"<a mode=\"fuseMode\".*href=\"(.*)\" title=\"讨论\"", course_url_response.text)[0]
        course_talk = 'https://mooc1-1.chaoxing.com' + course_talk_response
    except IndexError:
        if re.findall(r"placeholder=\"输入验证码\"", course_url_response.text) != []:
            pass
    return course_talk


def getcontent(courses_talk_url: str, all_cookie: dict, header: dict) -> list:
    '''
    获取一门课程讨论区的讨论内容的链接列表
    :param courses_talk_url: 课程讨论区的地址
    :param all_cookie: 已经获取的cookie
    :param header: 请求头
    :return: content_url_list: 课程讨论区的讨论内容的链接列表
    '''
    # 课程讨论区的讨论内容的链接列表
    content_url_list = []
    # 遍历每一个课程讨论区url获取讨论话题
    course_talk_index = requests.get(
        url=courses_talk_url,
        headers=header,
        cookies=all_cookie,
        timeout=10
    )
    content_url = re.findall(r".*/bbscircle/gettopicdetail(.*)\"", course_talk_index.text)
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
    params = re.findall(r"id=\"lastGetTopicListTime\"\n.*value=\"(.*)\"", course_talk_index.text)[0]
    lastGetTopicListTime = params
    lastValue = ""
    try:
        params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", course_talk_index.text)[0]
        lastValue = params
    except IndexError as e:
        pass
    page = 2
    topicPage = 2
    # 循环获取全部页面
    if re.findall(r".*查看更多", course_talk_index.text) == []:
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
            coures_next_response = requests.post(
                url="https://mooc1-1.chaoxing.com/bbscircle/grouptopic",
                headers=header,
                data=data,
                cookies=all_cookie,
                timeout=10
            )
            content_url = re.findall(r".*/bbscircle/gettopicdetail(.*)'", course_talk_index.text)
            # content_url = set(content_url)
            for i in content_url:
                content_url_list.append("https://mooc1-1.chaoxing.com/bbscircle/gettopicdetail" + i)
            try:
                params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", coures_next_response.text)[0]
            except IndexError as e:
                break
            if lastValue == params:
                break
            lastValue = params
            page += 1
            topicPage += 1
    return content_url_list


def savecontent(content_url_list: list, all_cookie: dict, header: dict, num: int):
    '''
    保存一门课程的讨论区的所有内容
    :param content_url_list: 课程讨论区的讨论内容的链接列表
    :param all_cookie: 已经获取的cookie
    :param header: 请求头
    :param num: 文件数量
    '''
    for content_url in content_url_list:
        content_index = requests.get(
            url=content_url,
            headers=header,
            cookies=all_cookie,
            timeout=10
        )
        # 用xpath匹配出所有的讨论内容并保存
        selector = etree.HTML(content_index.text)

        for i in selector.xpath("//div[@class='fr oneRight']"):
            # 转化为string
            s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
            r = re.findall(r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*id=\"topicContent\"(.*)</p>", s)
            # 保存到文件
            with open(f'/home/kerman/paperdata/data{num}', 'a') as f:
                if r[0][0] == "":
                    continue
                else:
                    f.write(r[0][0] + "\r\n")
                if r[1][1] == "":
                    continue
                else:
                    f.write(r[1][1] + "\r\n")
                try:
                    if (r[2][2] == ""):
                        continue
                    elif (r[2][2].find("<br>") != -1):
                        newstr = r[2][2].replace("<br>", " ")
                        f.write(newstr + "\r\n")
                    elif (r[2][2].find("<BR>") != -1):
                        newstr = r[2][2].replace("<BR>", " ")
                        f.write(newstr + "\r\n")
                    elif (r[2][2].find("<img src=") != -1):
                        continue
                    else:
                        f.write(r[2][2] + "\r\n")
                except IndexError as e:
                    r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                    if (r[0] == ""):
                        continue
                    elif (r[0].find("<br>") != -1):
                        newstr = r.replace("<br>", " ")
                        f.write(newstr + "\r\n")
                    elif (r[0].find("<img src=") != -1):
                        continue
                    else:
                        f.write(r[0] + "\r\n")
        with open(f'/home/kerman/paperdata/data{num}', 'a') as f:
            f.write("回复:" + "\r\n")
        for i in selector.xpath("//div[@class='fr secondRight']"):
            # 转化为string
            s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
            r = re.findall(r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<", s)

            # print(r[0][0], r[1][1], r[2][2])
            # 保存到文件
            with open(f'/home/kerman/paperdata/data{num}', 'a') as f:
                if r[0][0] == "":
                    continue
                else:
                    f.write(r[0][0] + "\r\n")
                if r[1][1] == "":
                    continue
                else:
                    f.write(r[1][1] + "\r\n")
                try:
                    if (r[2][2] == ""):
                        continue
                    elif (r[2][2].find("<br>") != -1):
                        newstr = r[2][2].replace("<br>", " ")
                        f.write(newstr + "\r\n")
                    elif (r[2][2].find("<img src=") != -1):
                        continue
                    else:
                        f.write(r[2][2] + "\r\n")
                except IndexError as e:
                    r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                    if (r[0] == ""):
                        continue
                    elif (r[0].find("<br>") != -1):
                        newstr = r.replace("<br>", " ")
                        f.write(newstr + "\r\n")
                    elif (r[0].find("<img src=") != -1):
                        continue
                    else:
                        f.write(r[0] + "\r\n")
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
            pagesize = re.findall(r"var.*pageSize.*\"(.*)\"", content_index.text)[0]
        except IndexError as e:
            pass
        order = ""
        try:
            order = re.findall(r".*order.*\"(.*)\"", content_index.text)[0]
        except IndexError as e:
            pass
        uuid = ""
        try:
            uuid = re.findall(r".*uuid.*'(.*)'", content_index.text)[0]
        except IndexError as e:
            pass
        lastValue = ""
        try:
            params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", content_index.text)[0]
            lastValue = params
        except IndexError as e:
            pass
        if re.findall(r"查看更多", content_index.text) == []:
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
                content_next_response = requests.post(
                    url="https://mooc1-1.chaoxing.com/bbscircle/getreplysbytopicId",
                    headers=header,
                    data=data,
                    cookies=all_cookie,
                    timeout=10
                )

                try:
                    params = re.findall(r"id=\"lastValue\" value=\"(.*)\"", content_next_response.text)[0]
                except IndexError as e:
                    break
                if lastValue == params:
                    break
                lastValue = params
                selector = etree.HTML(content_next_response.text)
                for i in selector.xpath("//div[@class='fr secondRight']"):
                    # 转化为string
                    s = (etree.tostring(i, encoding="utf-8", pretty_print=True, method="html")).decode()
                    r = re.findall(
                        r".*<span class=\"name\">(.*)<|.*<p class=\"gray\">(.*)<|.*name=\"replyfirstname\">(.*)<", s)
                    # print(r[0][0], r[1][1], r[2][2])
                    # 保存到文件
                    with open(f'/home/kerman/paperdata/data{num}', 'a') as f:
                        if r[0][0] == "":
                            continue
                        else:
                            f.write(r[0][0] + "\r\n")
                        if r[1][1] == "":
                            continue
                        else:
                            f.write(r[1][1] + "\r\n")
                        try:
                            if (r[2][2] == ""):
                                continue
                            elif (r[2][2].find("<br>") != -1):
                                newstr = r[2][2].replace("<br>", " ")
                                f.write(newstr + "\r\n")
                            elif (r[2][2].find("<img src=") != -1):
                                continue
                            else:
                                f.write(r[2][2] + "\r\n")
                        except IndexError as e:
                            r = re.findall(r"<h3 class=\"bt ol\">(.*)</h3>", s)
                            if (r[0] == ""):
                                continue
                            elif (r[0].find("<br>") != -1):
                                newstr = r[0].replace("<br>", " ")
                                f.write(newstr + "\r\n")
                            elif (r[0].find("<img src=") != -1):
                                continue
                            else:
                                f.write(r[0] + "\r\n")


def main():
    # 起始网址
    base_url = 'http://i.chaoxing.com'
    # 请求头
    header = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'
    }
    # 获取cookie
    all_cookie = getcookies(base_url, header)
    # 获取用户课程列表
    courses_url_list, all_cookie, header = getcourse(base_url, all_cookie, header)
    # print(courses_url_list)
    num = 1
    #线程池
    threads = []
    tt = time.time()
    for courses_talk_url in courses_url_list:
        # 获取一门课程讨论区的链接地址
        course_talk = gettalk(courses_talk_url, all_cookie, header)
        # 获取一门课程讨论区的讨论内容的链接列表
        content_url_list = getcontent(course_talk, all_cookie, header)
        # print(content_url_list)
        #保存讨论内容
        content_produce = threading.Thread(target=savecontent, args=[content_url_list, all_cookie, header, num])
        threads.append(content_produce)
        num += 1
    for t in threads:
        # t.setDaemon(True)
        t.start()
    print(time.time()-tt)

if __name__ == '__main__':
    main()
