with open("main.py", encoding="utf-8") as f:
    content = f.read()

tq_marker = '"""'
pos = 0
count = 0
positions = []
while True:
    idx = content.find(tq_marker, pos)
    if idx == -1:
        break
    line_no = content[:idx].count("\n") + 1
    positions.append((line_no, idx))
    pos = idx + 3
    count += 1

print(f"Found {count} triple-quote markers")
for line_no, idx in positions[:30]:
    print(f"  line {line_no}")
