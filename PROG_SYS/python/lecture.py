import csv
import json


def read_csv(file_path):
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        data = list(reader)
    return data

def read_json(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def read_txt(file_path):
    with open(file_path, 'r') as file:
        data_dic = {}
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, value = line.split('=', 1)
            data_dic[key.strip()] = value.strip()
    return data_dic






