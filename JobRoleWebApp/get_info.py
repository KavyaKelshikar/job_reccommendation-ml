import pandas as pd

df = pd.read_csv('dataset/resume.csv')
with open('dataset_info.txt', 'w', encoding='utf-8') as f:
    f.write(f'Shape: {df.shape}\n')
    f.write(f'Columns: {df.columns.tolist()}\n')
    f.write('Missing values:\n')
    f.write(f'{df.isnull().sum()}\n')
    f.write('Category Value Counts:\n')
    f.write(f'{df["Category"].value_counts()}\n')
