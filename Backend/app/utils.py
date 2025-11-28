import csv
import json
import pandas
from io import BytesIO

def parse_testcase_excel(content: bytes): #type hints
    df = pandas.read_excel(BytesIO(content))  #BytesIO allows pandas to read the bytes as if it were a file
    #Each row becomes a row in pandas, Each Excel column becomes a DataFrame column
    return df.to_dict(orient='records') #Each row becomes a dictionary, All rows return inside a list