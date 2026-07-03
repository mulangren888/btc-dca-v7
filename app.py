import streamlit as st
import sqlite3
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(layout="wide")

# =========================
# DATABASE
# =========================
DB = "data.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS tx (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        wallet TEXT,
        usdc REAL,
        btc REAL,
        price REAL,
        time TEXT
    )
    """)
    conn.commit()
    conn.close()

def insert_tx(user, wallet, usdc, btc, price):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    INSERT INTO tx VALUES (NULL,?,?,?,?,?,?)
    """, (user, wallet, usdc, btc, price, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load_df():
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM tx", conn)
    conn.close()
    return df


# =========================
# MARKET DATA
# =========================
@st.cache_data(ttl=60)
def get_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"}
        )
        return r.json()["bitcoin"]["usd"]
    except:
        return None


@st.cache_data(ttl=300)
def get_fear():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1")
        return int(r.json()["data"][0]["value"])
    except:
        return None


@st.cache_data(ttl=300)
def get_mvrv():
    try:
        r = requests.get("https://api.blockchaincenter.net/data/mvrv-zscore")
        return float(r.json().get("mvrv", None))
    except:
        return None


# =========================
# STRATEGY ENGINE
# =========================

def b_signal(fear):
    if fear is None:
        return "NO DATA", 0
    if fear < 10:
        return "EXTREME FEAR", 9
    if fear < 20:
        return "FEAR", 6
    return "NEUTRAL", 0


def c_signal(mvrv):
    if mvrv is None:
        return "NO DATA", 0
    if mvrv < 1:
        return "UNDERVALUE", 17
    if mvrv < 1.2:
        return "LOW", 8
    return "OVERVALUED", 0


def a_signal(day):
    return "BUY (27th rule)" if day == 27 else "WAIT"


# =========================
# INIT
# =========================
init_db()

st.title("🚀 BTC DCA V7 - 智能共享决策面板")

# =========================
# LIVE DATA PANEL
# =========================
price = get_price()
fear = get_fear()
mvrv = get_mvrv()

col1, col2, col3 = st.columns(3)

col1.metric("₿ BTC Price", f"${price}" if price else "N/A")
col2.metric("😱 Fear Index", fear if fear else "N/A")
col3.metric("📊 MVRV", mvrv if mvrv else "N/A")

st.divider()

# =========================
# SIGNAL PANEL
# =========================
st.subheader("🧠 自动策略信号")

day = datetime.now().day

b_label, b_buy = b_signal(fear)
c_label, c_buy = c_signal(mvrv)
a_label = a_signal(day)

st.write(f"🟢 A钱包：{a_label}")

st.write(f"🟡 B钱包：Fear={fear} → {b_label} → 建议买 {b_buy} 份")

st.write(f"🔴 C钱包：MVRV={mvrv} → {c_label} → 建议买 {c_buy} 份")

st.divider()

# =========================
# INPUT
# =========================
st.subheader("🧑‍🤝‍🧑 记录交易")

user = st.selectbox("操作者", ["碎", "锋", "叨"])
wallet = st.selectbox("钱包", ["A", "B", "C"])

usdc = st.number_input("USDC", 0.0, step=100.0)
btc = st.number_input("BTC", 0.0, step=0.0001)
price_in = st.number_input("价格", price or 0)

if st.button("提交"):
    insert_tx(user, wallet, usdc, btc, price_in)
    st.success("已记录")

# =========================
# DATA VIEW
# =========================
df = load_df()

st.divider()

if len(df) > 0:
    st.subheader("📊 交易记录")
    st.dataframe(df, use_container_width=True)

    st.subheader("📈 钱包统计")

    summary = df.groupby("wallet")[["usdc", "btc"]].sum().reset_index()

    st.bar_chart(summary.set_index("wallet")[["btc"]])
    st.bar_chart(summary.set_index("wallet")[["usdc"]])

    st.subheader("💰 总览")

    total_usdc = df["usdc"].sum()
    total_btc = df["btc"].sum()

    st.metric("总投入", round(total_usdc, 2))
    st.metric("BTC持仓", round(total_btc, 6))

    if total_btc > 0:
        st.metric("平均成本", round(total_usdc / total_btc, 2))
else:
    st.info("暂无数据")