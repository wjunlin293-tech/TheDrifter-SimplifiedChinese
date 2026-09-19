"""把译文里的人名 / 地名 / 组织名换回英文，称谓一并英文化。

绰号（桶屠夫、穆林吉、沙漠豌豆、深坑）保持中文 —— 那是语感所在。

用法：
    python tools/denameify.py --dry     # 只看会改什么
    python tools/denameify.py           # 实际改写 work/trans/*.json
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 顺序极其重要：长的先替换，否则「安妮·加拉尼斯」会先被「安妮」吃掉。
# 称谓组合也必须排在裸名之前。
RULES = [
    # --- 全名 + 称谓（必须排在「姓+称谓」之前，否则会变成 Gideon Dr. Roth）---
    ("吉迪恩·罗斯医生", "Dr. Gideon Roth"),
    ("吉迪恩·罗斯博士", "Dr. Gideon Roth"),
    ("安妮·加拉尼斯博士", "Dr. Annie Galanis"),
    ("安妮·加拉尼斯医生", "Dr. Annie Galanis"),
    ("桑杰·达斯瓦尼医生", "Dr. Sanjay Daswani"),
    ("桑杰·达斯瓦尼博士", "Dr. Sanjay Daswani"),
    ("索菲娅·罗斯医生", "Dr. Sophia Roth"),
    ("马克斯韦尔·霍尔登教授", "Professor Maxwell Holden"),
    ("安吉拉·格蕾丝女士", "Ms. Angela Grace"),

    # --- 带称谓的固定组合 ---
    ("纳扎里医生", "Dr. Nazari"),
    ("达斯瓦尼医生", "Dr. Daswani"),
    ("加拉尼斯博士", "Dr. Galanis"),
    ("罗斯医生", "Dr. Roth"),
    ("罗斯博士", "Dr. Roth"),
    ("克莱因博士", "Dr. Klein"),
    ("克莱因医生", "Dr. Klein"),
    ("克莱因先生", "Herr Klein"),
    ("达斯瓦尼博士", "Dr. Daswani"),
    ("加拉尼斯医生", "Dr. Galanis"),
    ("哈拉警督", "DI Hara"),
    ("哈拉警探", "Detective Hara"),
    ("格蕾丝女士", "Ms. Grace"),
    ("福布斯-耶茨女士", "Ms. Forbes-Yates"),
    ("霍尔登教授", "Professor Holden"),
    ("卡特先生", "Mr. Carter"),
    ("卡特太太", "Mrs. Carter"),
    ("卡特夫妇", "Mr. and Mrs. Carter"),
    ("罗斯警员", "Constable Ross"),
    ("克拉克女士", "Ms. Clarke"),

    # --- 全名 ---
    ("米克·卡特", "Mick Carter"),
    ("安妮·加拉尼斯", "Annie Galanis"),
    ("安吉拉·格蕾丝", "Angela Grace"),
    ("吉迪恩·罗斯", "Gideon Roth"),
    ("马克斯韦尔·霍尔登", "Maxwell Holden"),
    ("桑杰·达斯瓦尼", "Sanjay Daswani"),
    ("索菲娅·罗斯", "Sophia Roth"),
    ("朱迪思·卡特", "Judith Carter"),
    ("福布斯-耶茨", "Forbes-Yates"),
    ("S. R.y 卡哈尔", "S.R.y Cajal"),
    ("艾莉森·奥利里", "Alison O'Leary"),
    ("安德鲁·沙利文", "Andrew Sullivan"),
    ("戴维·玻姆", "David Bohm"),
    ("麦琪·墓地风", "Maggie Macabre"),
    ("老加斯", "Old Gus"),

    # --- 地名 / 组织 ---
    ("三一生物科技", "Trinity Biotech"),
    # 「大沙漠」保留中文，否则「在 the Great Wunyerra 里」读起来不像中文
    ("温耶拉大沙漠", "Wunyerra 大沙漠"),
    ("温耶拉沙漠", "Wunyerra 沙漠"),
    ("惠特兰私立医院", "Whitlam Private"),
    ("皮特街无家可归者援助中心", "the Pitt Street Homeless Support Center"),
    ("桑福德出版社", "Sandford"),
    ("《先驱报》", "the Herald"),
    ("先驱报", "the Herald"),
    ("世界关爱", "WorldCare"),
    ("断口镇", "Breaker's Cut"),
    ("赫尔路", "Hull Rd"),
    ("莫森小队", "Mawson Unit"),
    ("沃伦山公墓", "Warren Hill Cemetery"),
    ("温耶拉", "Wunyerra"),
    ("莫森", "Mawson"),
    ("惠特兰", "Whitlam"),
    ("三一", "Trinity"),

    # --- 裸名（放最后）---
    ("马克斯韦尔", "Maxwell"),
    ("加拉尼斯", "Galanis"),
    ("达斯瓦尼", "Daswani"),
    ("安吉拉", "Angela"),
    ("吉迪恩", "Gideon"),
    ("格蕾丝", "Grace"),
    ("霍尔登", "Holden"),
    ("克莱因", "Klein"),
    ("纳扎里", "Nazari"),
    ("索菲娅", "Sophia"),
    ("亚历克", "Alec"),
    ("彼得斯", "Peters"),
    ("马克斯", "Max"),
    ("米克", "Mick"),
    ("卡特", "Carter"),
    ("安妮", "Annie"),
    ("莎拉", "Sarah"),
    ("哈拉", "Hara"),
    ("罗斯", "Roth"),
    ("桑杰", "Sanjay"),
    ("比尔", "Bill"),
    ("玛芬", "Muffin"),
    ("乔", "Joe"),
]

# 这些地方出现的汉字串不是人名，替换前先保护起来
PROTECT = [
    "俄罗斯",
    "老罗斯福",
]


def convert(text):
    holds = []
    for i, p in enumerate(PROTECT):
        if p in text:
            key = "\x00%d\x00" % i
            text = text.replace(p, key)
            holds.append((key, p))
    for cn, en in RULES:
        text = text.replace(cn, en)
    for key, p in holds:
        text = text.replace(key, p)
    # 「亚历克·卡特」逐段替换后会变成 Alec·Carter，中间点还原成空格
    text = re.sub(r"(?<=[A-Za-z])·(?=[A-Za-z])", " ", text)
    return text


def main():
    dry = "--dry" in sys.argv
    files = sorted(glob.glob(os.path.join(ROOT, "work", "trans", "*.json")))
    total = changed = 0
    samples = []
    for path in files:
        data = json.load(open(path, encoding="utf-8"))
        out = {}
        hit = 0
        for k, v in data.items():
            if k.startswith("_"):
                out[k] = v
                continue
            total += 1
            nv = convert(v)
            if nv != v:
                hit += 1
                changed += 1
                if len(samples) < 12:
                    samples.append((k, v, nv))
            out[k] = nv
        if hit and not dry:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
        if hit:
            print(f"  {os.path.basename(path):<58} {hit}")
    print(f"\n{'[dry-run] ' if dry else ''}改写 {changed} / {total} 条")
    print("\n--- 样例 ---")
    for k, a, b in samples:
        print(f"[{k}] {a}\n   -> {b}")


if __name__ == "__main__":
    main()
