# @Author  : kerman jt
# @Time    : 2021/4/3 上午11:49
# @File    : data_analysis.py

from model import db, Course, Talk, Reply
import re
import jieba
import numpy as np


def data_pretreatment(sentences):
    chinese_path = "./chinese_stop_word"
    english_path = "./english_stop_word"
    chinese_stopwords = [line.strip() for line in open(chinese_path, encoding="utf-8").readlines()]
    english_stopwords = [line.strip() for line in open(english_path, encoding="utf-8").readlines()]
    english_count = {}
    chinese_count = {}
    for sentence in sentences:
        s3 = prehandle_str(sentence.text)
        if s3.encode('utf-8').isalpha():
            for word in sentence.text.split():
                if word not in english_stopwords:
                    english_count[word] = english_count.get(word, 0) + 1
        else:
            seg_list = jieba.cut(sentence.text)  # 默认是精确模式
            for word in seg_list:
                if word not in chinese_stopwords:
                    if len(word) == 1:
                        continue
                    else:
                        chinese_count[word] = chinese_count.get(word, 0) + 1
    return english_count, chinese_count


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


def get_top_words(sentences, name):
    english_count, chinese_count = data_pretreatment(sentences)
    english_dict = sorted(english_count.items(), key=lambda x: x[1], reverse=True)
    chinese_dict = sorted(chinese_count.items(), key=lambda x: x[1], reverse=True)
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
    english_top_dict = english_dict[:30]
    chinese_top_dict = chinese_dict[:30]
    all_num = 0
    for i in range(30):
        num = chinese_top_dict[i][1]
        all_num += num
    thr = all_num / len(sentences)
    l = []
    res_text = []
    res = []
    for sentence in sentences:
        count = 0
        for i in range(30):
            word, num = chinese_top_dict[i]
            # count += sentence.text.count(word, 0, len(sentence.text))
            if sentence.text.find(word) != -1:
                count += 1
        if count >= thr:
            l.append(sentence)
    r4 = "[\"]+|[0-9]|\\【.*?】+|\\《.*?》+|\\#.*?#+|[.!/_,$&%^*()<>+""'?@|:~{}#]+|[——！\\\，。=？、：“”‘’￥……（）《》【】]"
    for i in l:
        s = prehandle_str(i.text)
        if s not in res_text:
            res_text.append(s)
            res.append(i)
    repeat_thr = 0.6
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
    for i in ans:
        print(i.text)


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


if __name__ == '__main__':
    talk_sentences = Talk.query.all()
    reply_sentences = Reply.query.all()
    get_top_words(talk_sentences, "talk")
    # get_top_words(reply_sentences, "reply")
