import re
import os

path = os.path.join(
    r"c:\Users",
    "Ete'rna'l",
    "Desktop",
    "毕设",
    "lab",
    "毕业论文",
    "毕业论文.md"
)

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# 分离正文和参考文献
ref_idx = content.find('\n# 参考文献')
body = content[:ref_idx]
refs_section = content[ref_idx:]

# 旧编号 -> 新编号映射（按首次引用顺序）
mapping = {
    1:1, 2:2, 3:3, 4:4, 5:5,
    9:6, 26:7, 15:8, 10:9, 17:10, 18:11,
    6:12, 24:13, 25:14, 7:15, 8:16,
    23:17, 32:18, 11:19, 13:20, 19:21, 20:22,
    12:23, 27:24, 14:25, 28:26, 29:27, 16:28,
    21:29, 22:30, 30:31, 31:32
}

# 替换函数：匹配 [...] 引用格式
def replace_citation(m):
    full = m.group(0)
    def num_replacer(n):
        old = int(n.group(0))
        return str(mapping.get(old, old))
    return re.sub(r'\d+', num_replacer, full)

# 在正文中替换引用编号
body_new = re.sub(r'\[(\d+(?:[,\-]\d+)*)\]', replace_citation, body)

with open(path, 'w', encoding='utf-8') as f:
    f.write(body_new + refs_section)

print('正文引用编号替换完成')
