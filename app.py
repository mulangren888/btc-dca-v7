import streamlit as st
import pandas as pd
import sqlite3
import requests
from datetime import datetime

st.set_page_config(layout="wide", page_title="BTC DCA V7")

# =========================
# DB
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
    c.execute("INSERT INTO tx VALUES (NULL,?,?,?,?,?,?)",
              (user, wallet, usdc, btc, price, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def load():
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT * FROM tx", conn)
    conn.close()
    return df

# =========================
# MARKET DATA
# =========================
@st.cache_data(ttl=60)
def btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price",
                         params={"ids":"bitcoin","vs_currencies":"usd"})
        return r.json()["bitcoin"]["usd"]
    except:
        return 0

@st.cache_data(ttl=300)
def fear():
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1")
        return int(r.json()["data"][0]["value"])
    except:
        return 0

# =========================
# INIT
# =========================
init_db()

df = load()

price = btc_price()
fear_index = fear()

# =========================
# SIDEBAR（左侧控制栏）
# =========================
with st.sidebar:
    st.title("⚙️ 控制面板")

    user = st.selectbox("操作者", ["碎","锋","叨"])
    wallet = st.selectbox("钱包", ["A","B","C"])

    usdc = st.number_input("USDC", 0.0, step=100.0)
    btc = st.number_input("BTC", 0.0, step=0.0001)
    price_in = st.number_input("价格", float(price))

    if st.button("➕ 提交记录"):
        insert_tx(user, wallet, usdc, btc, price_in)
        st.success("已记录")

    st.divider()
    st.write("📊 系统状态")
    st.write(f"BTC Price: {price}")
    st.write(f"Fear Index: {fear_index}")

# =========================
# HEADER METRICS（顶部）
# =========================
col1, col2, col3, col4 = st.columns(4)

col1.metric("₿ BTC Price", f"${price}")
col2.metric("😱 Fear Index", fear_index)
col3.metric("📊 Market State", "Neutral" if fear_index > 20 else "Fear")
col4.metric("🧠 Strategy", "Active")

st.divider()

# =========================
# STRATEGY CARDS（中间策略区）
# =========================
st.subheader("📊 策略信号面板")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("### 🟢 A钱包（固定定投）")
    st.info("每月27号执行")
    st.success("状态：待执行")

with c2:
    st.markdown("### 🟡 B钱包（恐惧指数）")
    if fear_index < 20:
        st.error("强烈买入信号")
    else:
        st.warning("观望")

with c3:
    st.markdown("### 🔴 C钱包（MVRV逻辑）")
    st.warning("估值模型运行中")

st.divider()

# =========================
# WALLET CARDS（核心资产区）
# =========================
st.subheader("💰 钱包资产面板")

def wallet_block(name):
    d = df[df["wallet"] == name]
    usdc_sum = d["usdc"].sum()
    btc_sum = d["btc"].sum()

    col = st.container()
    with col:
        st.markdown(f"### {name} 钱包")
        st.metric("USDC投入", f"{usdc_sum:.2f}")
        st.metric("BTC持仓", f"{btc_sum:.6f}")
        if btc_sum > 0:
            st.metric("均价", f"{usdc_sum/btc_sum:.2f}")

c1, c2, c3 = st.columns(3)
with c1: wallet_block("A")
with c2: wallet_block("B")
with c3: wallet_block("C")

st.divider()

# =========================
# CHARTS（底部图表）
# =========================
st.subheader("📈 数据分析")

if len(df) > 0:
    g = df.groupby("wallet")[["usdc","btc"]].sum()

    st.bar_chart(g["usdc"])
    st.bar_chart(g["btc"])

    st.divider()

    st.subheader("📜 交易记录")
    st.dataframe(df, use_container_width=True)
else:
    st.info("暂无数据")
