with open('main.py', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ('\u2019', "'"),
    ('\u2018', "'"),
    ('\u201c', '"'),
    ('\u201d', '"'),
    ('\u2014', '--'),
    ('\u2013', '-'),
    ('\u2022', '*'),
    ('\u00b0', ' degrees'),
    ('\u00a9', '(c)'),
    ('\u00ae', '(R)'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done - smart chars replaced')
