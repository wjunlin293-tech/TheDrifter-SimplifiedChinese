import os, glob
import UnityPy
from UnityPy.helpers.TypeTreeNode import TypeTreeNode
from TypeTreeGeneratorAPI import TypeTreeGenerator

GAME = r"C:\Program Files (x86)\Steam\steamapps\common\The Drifter"
DATA = os.path.join(GAME, "TheDrifter_Data")
MANAGED = os.path.join(DATA, "Managed")
SHARED1 = os.path.join(DATA, "sharedassets1.assets")
WORK = r"C:\Users\Jeff Wu\TheDrifterCN\work"
SYSTEMTEXT_PATHID = 28977
UNITY_VER = "2020.3.49f1"

_gen = None


def generator():
    global _gen
    if _gen is None:
        g = TypeTreeGenerator(UNITY_VER)
        for dll in sorted(glob.glob(os.path.join(MANAGED, "*.dll"))):
            with open(dll, "rb") as f:
                g.load_dll(f.read())
        _gen = g
    return _gen


def _convert(raw_nodes):
    """TypeTreeGeneratorAPI nodes -> UnityPy TypeTreeNode tree."""
    flat = []
    for i, n in enumerate(raw_nodes):
        flat.append(TypeTreeNode(
            m_Type=n.m_Type, m_Name=n.m_Name, m_Level=n.m_Level,
            m_MetaFlag=n.m_MetaFlag, m_ByteSize=-1, m_Version=1,
            m_TypeFlags=0, m_Index=i, m_Children=[],
        ))
    root = flat[0]
    stack = [root]
    for node in flat[1:]:
        while len(stack) > node.m_Level:
            stack.pop()
        stack[-1].m_Children.append(node)
        stack.append(node)
    return root


def nodes_for(assembly, cls):
    return _convert(generator().get_nodes(assembly, cls))


def systemtext_nodes():
    return nodes_for("Assembly-CSharp.dll", "PowerTools.Quest.SystemText")


def load_systemtext(path=SHARED1):
    env = UnityPy.load(path)
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour" and obj.path_id == SYSTEMTEXT_PATHID:
            return env, obj
    raise RuntimeError("SystemText not found")
