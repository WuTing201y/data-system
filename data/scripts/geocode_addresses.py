import pandas as pd
import numpy as np
import time, openpyxl as xls

map_data = pd.read_csv('./data/clean/total-address.csv', encoding='utf-8')
print(map_data)