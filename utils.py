# @Author  : kerman jt
# @Time    : 2021/4/3 上午10:40
# @File    : utils.py

def get_key(dict, value):
    return [k for k, v in dict.items() if v == value]
