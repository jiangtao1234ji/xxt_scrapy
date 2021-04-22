# @Author  : kerman jt
# @Time    : 2021/4/3 上午11:49
# @File    : data_analysis.py
import datetime

from sqlalchemy import func

from model import db, Course, Talk, Reply
import re
import jieba
import numpy as np
from datetime import date
from sqlalchemy.sql.functions import func
from typing import Union


# def data_pretreatment(sentences):
#     chinese_path = "./chinese_stop_word"
#     english_path = "./english_stop_word"
#     chinese_stopwords = [line.strip() for line in open(chinese_path, encoding="utf-8").readlines()]
#     english_stopwords = [line.strip() for line in open(english_path, encoding="utf-8").readlines()]
#     english_count = {}
#     chinese_count = {}
#     for sentence in sentences:
#         s3 = prehandle_str(sentence.text)
#         if s3.encode('utf-8').isalpha():
#             for word in sentence.text.split():
#                 if word not in english_stopwords:
#                     english_count[word] = english_count.get(word, 0) + 1
#         else:
#             seg_list = jieba.cut(sentence.text)  # 默认是精确模式
#             for word in seg_list:
#                 if word not in chinese_stopwords:
#                     if len(word) == 1:
#                         continue
#                     else:
#                         chinese_count[word] = chinese_count.get(word, 0) + 1
#     return english_count, chinese_count


def prehandle_str(s: str) -> str:
    # 过滤不了\\ \ 中文（）还有————
    r1 = u'[a-zA-Z0-9’!"#$%&\'()*+,-./:;<=>?@，。?★、…【】《》？“”‘’！[\\]^_`{|}~]+'  # 用户也可以在此进行自定义过滤字符
    # 者中规则也过滤不完全
    r2 = "[\s+\.\!\/_,$%^*(+\"\']+|[+——！，。？、~@#￥%……&*（）]+"
    # \\\可以过滤掉反向单杠和双杠，/可以过滤掉正向单杠和双杠，第一个中括号里放的是英文符号，第二个中括号里放的是中文符号，第二个中括号前不能少|，否则过滤不完全
    r3 = "[.!//_,$&%^*()<>+\"'?@#-|:~{}]+|[——！\\\\，。=？、：“”‘’《》【】￥……（）]+"
    # 去掉括号和括号内的所有内容
    r4 = "[\"]+|[0-9]|\\【.*?】+|\\《.*?》+|\\#.*?#+|[.!/_,$&%^*()<>+""'?@|:~{}#]+|[——！\\\，。=？、：“”‘’￥……（）《》【】]"
    sentence = re.sub(r4, '', s).strip()
    s1 = sentence.replace(" ", " ")
    s2 = s1.replace("-", "")
    s3 = s2.replace(" ", "")
    return s3


def get_top_words(chinese_dict, english_dict, sentences, today):
    # english_write = open(f'./{name}_english_top_word', mode='w', encoding='UTF-8')
    # chinese_write = open(f'./{name}_chinese_top_word', mode='w', encoding='UTF-8')
    # english_write.write(f"{name}英文前30高频词:\n")
    # for i in range(30):
    #     word, count = english_dict[i]
    #     english_write.write("{:<10}{:>7}\n".format(word, count))
    # chinese_write.write(f"{name}中文前30高频词:\n")
    # for i in range(30):
    #     word, count = chinese_dict[i]
    #      chinese_write.write("{:<10}{:>7}\n".format(word, count))
    if chinese_dict == {} and english_dict == {} and sentences == []:
        print(f"{today}没有讨论话题!!!")
        return
    english_top_dict = {}
    chinese_top_dict = {}
    try:
        english_top_dict = english_dict[:30]
    except:
        pass
    try:
        chinese_top_dict = chinese_dict[:30]
    except:
        pass
    all_score = 0
    average_score = 0
    for word, score in chinese_top_dict:
        all_score += score
    average_score = all_score / len(chinese_top_dict)
    l = []
    res_text = []
    res = []
    for sentence in sentences:
        count_score = 0
        n = min(len(chinese_dict), 30)
        for i in range(n):
            word, score = chinese_top_dict[i]
            # count += sentence.text.count(word, 0, len(sentence.text))
            if sentence.text.find(word) != -1:
                count_score += score
        if count_score >= average_score:
            l.append(sentence)
    for i in l:
        s = prehandle_str(i.text)
        if s not in res_text:
            res_text.append(s)
            res.append(i)
    repeat_thr = 0.8
    ans = [res[0]]
    for i in res:
        cnt = 0
        for j in ans:
            s1 = prehandle_str(i.text)
            s2 = prehandle_str(j.text)
            vec1, vec2 = get_word_vector(s1, s2)
            dist = cos_dist(vec1, vec2)
            if dist > repeat_thr:
                break
            cnt += 1
        if cnt == len(ans):
            ans.append(i)
    # for i in ans:
    #         print(f"""
    # {i.course.name}
    # {i.user_name}:{i.date}
    # {i.text}
    # {i.reply_num}
    #         """)
    print()
    print()
    print(f"{today}的热点话题为:")
    for i in ans:
        print(f"""
{i.course.name}:
{i.user_name}:
内容为:{i.text}""")
        print()
    print(len(ans))


def get_word_vector(s1, s2):
    """
    :param s1: 句子1
    :param s2: 句子2
    :return: 返回句子的余弦相似度
    """
    # 分词
    cut1 = jieba.cut(s1)
    cut2 = jieba.cut(s2)
    list_word1 = (','.join(cut1)).split(',')
    list_word2 = (','.join(cut2)).split(',')

    # 列出所有的词,取并集
    key_word = list(set(list_word1 + list_word2))
    # 给定形状和类型的用0填充的矩阵存储向量
    word_vector1 = np.zeros(len(key_word))
    word_vector2 = np.zeros(len(key_word))

    # 计算词频
    # 依次确定向量的每个位置的值
    for i in range(len(key_word)):
        # 遍历key_word中每个词在句子中的出现次数
        for j in range(len(list_word1)):
            if key_word[i] == list_word1[j]:
                word_vector1[i] += 1
        for k in range(len(list_word2)):
            if key_word[i] == list_word2[k]:
                word_vector2[i] += 1

    # 输出向量
    # print(word_vector1)
    # print(word_vector2)
    return word_vector1, word_vector2


def cos_dist(vec1, vec2):
    """
    :param vec1: 向量1
    :param vec2: 向量2
    :return: 返回两个向量的余弦相似度
    """
    dist1 = float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))
    return dist1


def data_time(year, month, day):
    if month < 10 and day < 10:
        return f'{year}-0{month}-0{day}'
    elif month < 10 and day >= 10:
        return f'{year}-0{month}-{day}'
    elif month >= 10 and day < 10:
        return f'{year}-{month}-0{day}'
    else:
        return f'{year}-{month}-{day}'


chinese_path = "./chinese_stop_word"
english_path = "./english_stop_word"
chinese_stopwords = [line.strip() for line in open(chinese_path, encoding="utf-8").readlines()]
english_stopwords = [line.strip() for line in open(english_path, encoding="utf-8").readlines()]


def get_word_score(Obj: Union[Talk, Reply], before_n_day: str, date: str) -> (dict, dict, list):
    if Obj.query.filter(func.date_format(Talk.date, "%Y-%m-%d") == func.date_format(date, "%Y-%m-%d")).all() == []:
        return {}, {}, []
    obj_sentences = Obj.query.filter(
        func.date_format(Talk.date, "%Y-%m-%d").between(func.date_format(before_n_day, "%Y-%m-%d"),
                                                        func.date_format(date, "%Y-%m-%d"))).all()
    sentences = []
    global chinese_stopwords
    global english_stopwords
    now_english_count = {}
    all_english_count = {}
    now_chinese_count = {}
    all_chinese_count = {}
    english_score = {}
    chinese_score = {}
    chinese_word_now_score = {}
    chinese_all_score = 0
    chinese_m = 0
    chinese_all_word_num = 0
    chinese_f = 0
    chinese_s = {}
    english_word_now_score = {}
    english_all_score = 0
    english_m = 0
    english_all_word_num = 0
    english_f = 0
    english_s = {}
    flag = 0
    for obj in obj_sentences:
        s = prehandle_str(obj.text)
        if s.encode('utf-8').isalpha():
            flag = 1
            for word in obj.text.split():
                if word not in english_stopwords:
                    if func.date_format(obj.date, "%Y-%m-%d") == func.date_format(date, "%Y-%m-%d"):
                        now_english_count[word] = now_english_count.get(word, 0) + 1
                        all_english_count[word] = all_english_count.get(word, 0) + 1
                        sentences.append(obj)
                    else:
                        all_english_count[word] = all_english_count.get(word, 0) + 1

        else:
            flag = 2
            seg_list = jieba.cut(obj.text)  # 默认是精确模式
            for word in seg_list:
                if word not in chinese_stopwords:
                    if len(word) == 1:
                        continue
                    else:
                        if obj.date[:10] == date:
                            now_chinese_count[word] = now_chinese_count.get(word, 0) + 1
                            all_chinese_count[word] = all_chinese_count.get(word, 0) + 1
                            sentences.append(obj)
                        else:
                            all_chinese_count[word] = all_chinese_count.get(word, 0) + 1
    if flag == 1:
        for word, num in now_english_count.items():
            english_word_now_score[word] = num / all_english_count[word]
            english_all_score += num / all_english_count[word]
        for word, num in all_english_count.items():
            english_all_word_num += num
        english_m = english_all_score / len(now_english_count)
        english_f = english_all_word_num / (len(all_english_count) * days(date, before_n_day))
        for word, num in now_english_count.items():
            english_s[word] = english_m + (english_word_now_score[word] - english_m) * num / (num + english_f)
        english_score = sorted(english_s.items(), key=lambda x: x[1], reverse=True)
    if flag == 2:
        for word, num in now_chinese_count.items():
            chinese_word_now_score[word] = num / all_chinese_count[word]
            chinese_all_score += num / all_chinese_count[word]
        for word, num in all_chinese_count.items():
            chinese_all_word_num += num
        chinese_m = chinese_all_score / len(now_chinese_count)
        chinese_f = chinese_all_word_num / (len(all_chinese_count) * days(date, before_n_day))
        for word, num in now_chinese_count.items():
            chinese_s[word] = chinese_m + (chinese_word_now_score[word] - chinese_m) * num / (num + chinese_f)
        chinese_score = sorted(chinese_s.items(), key=lambda x: x[1], reverse=True)

    return chinese_score, english_score, sentences


def days(str1, str2):
    date1 = datetime.datetime.strptime(str1[0:10], "%Y-%m-%d")
    date2 = datetime.datetime.strptime(str2[0:10], "%Y-%m-%d")

    num = (date1 - date2).days
    return num + 1


def get_top_topic(obj, start_year, start_month, start_day, end_year, end_month, end_day, n):
    start_date = data_time(start_year, start_month, start_day)
    end_date = data_time(end_year, end_month, end_day)
    day_nums = days(end_date, start_date)
    t = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    for i in range(day_nums):
        chinese_dict = {}
        english_dict = {}
        sentences = []
        today = (t + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        d_today = datetime.datetime.strptime(today, "%Y-%m-%d")
        before_n_day = (d_today - datetime.timedelta(days=n)).strftime("%Y-%m-%d")
        chinese_dict, english_dict, sentences = get_word_score(obj, before_n_day, today)
        get_top_words(chinese_dict, english_dict, sentences, today)


if __name__ == '__main__':
    # talk_sentences = Talk.query.all()
    # reply_sentences = Reply.query.all()

    start_year = 2020
    start_month = 2
    start_day = 11
    end_year = 2020
    end_month = 2
    end_day = 20
    n = 2
    get_top_topic(Talk, start_year, start_month, start_day, end_year, end_month, end_day, n)

    # talk_sentences = get_word_now_score(Talk, before_n_day, date)
    # get_top_words(talk_sentences, "talk")
    # get_top_words(reply_sentences, "reply")
