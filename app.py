# app.py — 居酒屋シミュレータ (Streamlit)
# 必要ファイル (images/ フォルダ内に配置):
#   izakaya1.jpg (店内背景: fallback用にも必須)
#   menu_izakaya.jpg (メニュー表)
#   drink_lemon_sour.jpg / drink_otoko_ume.jpg / drink_sake.jpg
#   food_sashimori.jpg / food_negima.jpg / food_eihire.jpg / food_motsunikomi.jpg
#   hand_raise.png (透過: 手を上げる)
#   finger_1.png / finger_2.png / finger_3.png (人数サイン)
#   pay_cash.png / pay_card.png (支払いサイン)
#   npc_staff.png (任意: 店員アイコン)

import os
import time
from base64 import b64encode
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import streamlit as st

st.set_page_config(page_title="居酒屋シム", page_icon="🍶", layout="wide")

# ===== CSS =====
st.markdown(
    """
    <style>
      .wrap {max-width: 1100px; margin: 0 auto;}
      .hero {width:100%; height:60vh; border-radius:24px; border:1px solid #2a2a2a; object-fit:cover;}
      .dialog {margin-top: 10px; border: 1px solid #2a2a2a; border-radius: 24px; overflow: hidden; background: #0f0f14;}
      .header {padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,.08); display:flex; gap:8px; align-items:center; color:#fff;}
      .section {padding: 16px 18px;}
      .row-npc, .row-you {display:flex; gap:10px; align-items:flex-start; margin: 6px 0;}
      .row-you {justify-content:flex-end;}
      .avatar {width:48px; height:48px; border-radius:50%; object-fit:cover; border:1px solid rgba(255,255,255,.2);}  
      .bubble-npc {max-width:100%; background: rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18); color:#f6f6f6; padding:12px 14px; border-radius:14px;}
      .bubble-you {max-width:100%; background:#f2f2f2; color:#111; border:1px solid #ddd; padding:12px 14px; border-radius:14px;}
      .tri.jp {font-size:18px; line-height:1.6;}
      .tri.en {font-size:14px; opacity:.9}
      .tri.romaji {font-size:13px; opacity:.85}
      .choices {padding: 12px 18px; border-top:1px solid rgba(255,255,255,.08); background:#0b0b10; display:flex; flex-wrap:wrap; gap:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== util =====
def data_url(path: str):
    if path and os.path.exists(path):
        b64 = b64encode(open(path, "rb").read()).decode()
        ext = path.split(".")[-1].lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
        return f"data:{mime};base64,{b64}"
    return None

# ===== structures =====
@dataclass
class TriText:
    jp: str
    en: str
    romaji: str

@dataclass
class Choice:
    text: TriText
    next: str
    set: Dict[str, Any] = field(default_factory=dict)
    push: Dict[str, Any] = field(default_factory=dict)
    overlay: Optional[str] = None
    bg: Optional[str] = None   # 背景切替

@dataclass
class Node:
    npc: TriText
    choices: List[Choice]
    bg: Optional[str] = None

@dataclass
class Scenario:
    id: str
    emoji: str
    title: str
    blurb: str
    slots: Dict[str, Any]
    nodes: Dict[str, Node]
    npc_avatar: Optional[str] = None

def T(jp, en, romaji): return TriText(jp,en,romaji)
def C(jp,en,romaji,next,set=None,push=None,overlay=None,bg=None):
    return Choice(T(jp,en,romaji),next,set or {},push or {},overlay,bg)

# ===== Izakaya scenario =====
IZAKAYA = Scenario(
    id="izakaya",
    emoji="🍶",
    title="いざかや / Izakaya",
    blurb="にんずう→のみもの→すみません→たべもの→ついか→おかいけい",
    slots={"n":None,"drink":None,"food":[],"pay":None},
    nodes={
        "start": Node(
            npc=T("いらっしゃいませ。なんめいさまですか？","Welcome. How many people?","irasshaimase. nan-mei sama desu ka?"),
            choices=[
                C("ひとりです","One person","hitori desu","drink",{"n":1},overlay="images/finger_1.png"),
                C("ふたりです","Two people","futari desu","drink",{"n":2},overlay="images/finger_2.png"),
                C("さんにんです","Three people","sannin desu","drink",{"n":3},overlay="images/finger_3.png"),
            ],
            bg="images/izakaya1.jpg"
        ),
        "drink": Node(
            npc=T("さいしょの おのみものは？","What would you like to drink first?","saisho no onomimono wa?"),
            choices=[
                C("れもんさわー","Lemon sour","remon sawaa","call_staff",
                  {"drink":"lemon"},bg="images/drink_lemon_sour.jpg"),
                C("おとこうめさわー","Otoko-ume sour","otoko-ume sawaa","call_staff",
                  {"drink":"ume"},bg="images/drink_otoko_ume.jpg"),
                C("にほんしゅ","Sake","nihonshu","call_staff",
                  {"drink":"sake"},bg="images/drink_sake.jpg"),
            ],
        ),
        "call_staff": Node(
            npc=T("決まったら呼んでくださいね","Call me when you're ready","kimattara yonnde kudasaine-"),
            choices=[C("すみませんー","Excuse me!","sumimasen","menu",overlay="images/hand_raise.png")],
        ),
        "menu": Node(
            npc=T("ごちゅうもんは？","What would you like to order?","go-chuumon wa?"),
            choices=[
                # foods
                C("さしもり","Sashimi platter","sashimori","add",push={"food":"sashimori"},bg="images/food_sashimori.jpg"),
                C("ねぎま","Negima yakitori","negima","add",push={"food":"negima"},bg="images/food_negima.jpg"),
                C("えいひれ","Grilled stingray fin","eihire","add",push={"food":"eihire"},bg="images/food_eihire.jpg"),
                C("もつにこみ","Motsu nikomi","motsunikomi","add",push={"food":"motsunikomi"},bg="images/food_motsunikomi.jpg"),
                # drinks again for追加
                C("れもんさわー","Lemon sour","remon sawaa","add",{"drink":"lemon"},bg="images/drink_lemon_sour.jpg"),
                C("おとこうめさわー","Otoko-ume sour","otoko-ume sawaa","add",{"drink":"ume"},bg="images/drink_otoko_ume.jpg"),
                C("にほんしゅ","Sake","nihonshu","add",{"drink":"sake"},bg="images/drink_sake.jpg"),
            ],
            bg="images/menu_izakaya.jpg"
        ),
        "add": Node(
            npc=T("ほかにごちゅうもんは？","Anything else?","hoka ni go-chuumon wa?"),
            choices=[
                C("はい、もういっぴん","Yes, one more","hai, mou ippin","menu"),
                C("だいじょうぶ、おかいけいで","No thanks, bill please","daijoubu, okaikei de","bill"),
            ],
        ),
        "bill": Node(
            npc=T("おかいけいで よろしいですか？","Ready for the bill?","okaikei de yoroshii desu ka?"),
            choices=[
                C("げんきんで","Cash, please","genkin de","end",{"pay":"cash"},overlay="images/pay_cash.png"),
                C("かーどで","Card, please","kaado de","end",{"pay":"card"},overlay="images/pay_card.png"),
            ],
        ),
        "end": Node(
            npc=T("ありがとうございました！","Thank you very much!","arigatou gozaimashita!"),
            choices=[C("さいしょにもどる","Go back to start","saisho ni modoru","__RESET__")],
        ),
    },
    npc_avatar="images/npc_staff.png",
)

# ===== state =====
if "node_id" not in st.session_state: st.session_state.node_id="start"
if "slots" not in st.session_state: st.session_state.slots=IZAKAYA.slots.copy()
if "overlay" not in st.session_state: st.session_state.overlay=None
if "overlay_until" not in st.session_state: st.session_state.overlay_until=0
if "bg_path" not in st.session_state: st.session_state.bg_path=IZAKAYA.nodes["start"].bg

# ===== render =====
st.markdown("<div class='wrap'>", unsafe_allow_html=True)

node = IZAKAYA.nodes[st.session_state.node_id]

# 背景の決定: 存在しない場合は必ず izakaya1.jpg
fallback_bg = "images/izakaya1.jpg"
bg = node.bg or st.session_state.bg_path or fallback_bg
if not (bg and os.path.exists(bg)):
    bg = fallback_bg
bg_url = data_url(bg)

# overlay: 3秒だけ表示
overlay_url = None
if st.session_state.overlay and os.path.exists(st.session_state.overlay):
    if st.session_state.overlay_until > time.time():
        overlay_url = data_url(st.session_state.overlay)
    else:
        st.session_state.overlay = None

if bg_url:
    hero_html = f"<div style='position:relative'><img src='{bg_url}' class='hero'/>"
    if overlay_url:
        # 中央寄りに大きめ表示
        hero_html += f"<img src='{overlay_url}' style='position:absolute; bottom:10%; right:10%; width:180px;'/>"
    hero_html += "</div>"
    st.markdown(hero_html, unsafe_allow_html=True)

# header
meta = IZAKAYA
st.markdown(f"<div class='header'><span style='font-size:22px'>{meta.emoji}</span><span style='font-weight:600;margin-left:8px'>{meta.title}</span></div>", unsafe_allow_html=True)

# dialog
st.markdown("<div class='dialog'><div class='section'>", unsafe_allow_html=True)
st.markdown(f"<div class='row-npc'><div class='bubble-npc'><div class='tri jp'>{node.npc.jp}</div><div class='tri en'>{node.npc.en}</div><div class='tri romaji'><i>{node.npc.romaji}</i></div></div></div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# choices
st.markdown("<div class='choices'>", unsafe_allow_html=True)
cols = st.columns(min(len(node.choices),4) or 1)
for i,c in enumerate(node.choices):
    with cols[i%len(cols)]:
        if st.button(c.text.jp, use_container_width=True,key=f"ch-{i}-{st.session_state.node_id}"):
            for k,v in c.set.items(): st.session_state.slots[k]=v
            for k,v in c.push.items():
                lst=st.session_state.slots.get(k) or []
                if not isinstance(lst,list): lst=[lst]
                lst.append(v); st.session_state.slots[k]=lst
            if c.overlay:
                st.session_state.overlay=c.overlay
                st.session_state.overlay_until=time.time()+0.1  # 3秒表示
            if c.bg: st.session_state.bg_path=c.bg
            if c.next=="__RESET__":
                st.session_state.node_id="start"; st.session_state.slots=IZAKAYA.slots.copy()
                st.session_state.overlay=None; st.session_state.overlay_until=0
                st.session_state.bg_path=IZAKAYA.nodes["start"].bg
            else:
                st.session_state.node_id=c.next
            st.rerun()
st.markdown("</div></div>", unsafe_allow_html=True)
