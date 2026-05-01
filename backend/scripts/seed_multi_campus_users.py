"""
多校区用户种子数据 — 将所有预设用户同步到各校区分库。

所有用户定义已内嵌在 seed_shards.py 中，本脚本直接调用其 main() 完成同步。
"""
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from scripts.seed_shards import main as seed_shards_main

if __name__ == "__main__":
    seed_shards_main()
