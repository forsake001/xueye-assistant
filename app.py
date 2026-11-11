# ============================================
# 学业助手：学分达成看板 + AI选课咨询
# 华为开发者大赛·智能体创新赛参赛作品
# ============================================
import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI
import os

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="学业助手",
    page_icon="📚",
    layout="wide"
)

# ---------- MaaS 客户端初始化 ----------
def get_maas_client():
    """从环境变量或 streamlit secrets 读取 API Key，返回 MaaS 客户端"""
    api_key = os.getenv("MAAS_API_KEY", "")
    if not api_key:
        try:
            api_key = st.secrets.get("MAAS_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://api.modelarts-maas.com/openai/v1"
    )

# ---------- 主标题 ----------
st.title("📚 学业助手：学分达成与选课推荐")
st.caption("大数据管理与应用专业 · 华为云码道 CodeArts 开发")

# ============================================
# 侧边栏：上传培养方案
# ============================================
st.sidebar.header("① 上传培养方案")
uploaded_file = st.sidebar.file_uploader(
    "上传培养方案 Excel（.xlsx）",
    type=["xlsx", "xls"]
)

curriculum_df = None
if uploaded_file is not None:
    try:
        curriculum_df = pd.read_excel(uploaded_file)
        st.sidebar.success(f"已加载：{uploaded_file.name}")
        st.sidebar.write(f"共 {len(curriculum_df)} 门课程")
    except Exception as e:
        st.sidebar.error(f"读取失败：{e}")

# ============================================
# 三个功能页签
# ============================================
tab1, tab2, tab3 = st.tabs(["📊 学分达成看板", "📝 已修课程管理", "🤖 AI 选课咨询"])

# ---------- Tab1：学分达成看板 ----------
with tab1:
    st.header("学分达成看板")

    if curriculum_df is None:
        st.info("👈 请先在左侧上传培养方案 Excel 文件")
    else:
        st.subheader("培养方案课程列表")
        st.dataframe(curriculum_df, use_container_width=True)

        # 按课程类别统计学分
        if "课程类别" in curriculum_df.columns and "学分" in curriculum_df.columns:
            st.subheader("各类别学分分布")
            cat_credits = curriculum_df.groupby("课程类别")["学分"].sum().reset_index()
            fig = px.pie(
                cat_credits,
                values="学分",
                names="课程类别",
                title="培养方案学分结构"
            )
            st.plotly_chart(fig, use_container_width=True)

            total_credits = curriculum_df["学分"].sum()
            st.metric("培养方案总学分", f"{total_credits} 学分")

# ---------- Tab2：已修课程管理 ----------
with tab2:
    st.header("已修课程管理")

    # 初始化 session_state
    if "completed_courses" not in st.session_state:
        st.session_state.completed_courses = []

    # 添加课程表单
    with st.form("add_course_form", clear_on_submit=True):
        st.subheader("添加已修课程")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            c_name = st.text_input("课程名称", placeholder="例如：Python程序设计")
        with col2:
            c_credit = st.number_input("学分", min_value=0.5, max_value=6.0, value=2.0, step=0.5)
        with col3:
            c_cat = st.selectbox(
                "课程类别",
                ["通识教育", "学科基础", "专业核心", "专业选修", "集中实践", "创新创业"]
            )
        with col4:
            c_grade = st.slider("成绩", 0, 100, 80)

        submitted = st.form_submit_button("✅ 添加到已修列表")
        if submitted and c_name.strip():
            st.session_state.completed_courses.append({
                "课程名称": c_name.strip(),
                "学分": c_credit,
                "课程类别": c_cat,
                "成绩": c_grade
            })
            st.success(f"已添加：{c_name}（{c_credit}学分，{c_grade}分）")
        elif submitted:
            st.warning("请填写课程名称")

    # 展示已修课程
    if st.session_state.completed_courses:
        st.subheader("已修课程列表")
        done_df = pd.DataFrame(st.session_state.completed_courses)
        st.dataframe(done_df, use_container_width=True)

        col_del = st.columns([3, 1])
        with col_del[1]:
            if st.button("🗑️ 清空已修列表"):
                st.session_state.completed_courses = []
                st.rerun()

        # 达成率对比图
        if curriculum_df is not None and "课程类别" in curriculum_df.columns:
            st.subheader("学分达成对比")
            total_by_cat = curriculum_df.groupby("课程类别")["学分"].sum().reset_index()
            done_by_cat = done_df.groupby("课程类别")["学分"].sum().reset_index()

            compare = total_by_cat.merge(
                done_by_cat, on="课程类别", how="left", suffixes=("_总要求", "_已修")
            )
            compare["学分_已修"] = compare["学分_已修"].fillna(0)
            compare["达成率%"] = (compare["学分_已修"] / compare["学分_总要求"] * 100).round(1)

            fig = px.bar(
                compare,
                x="课程类别",
                y=["学分_已修", "学分_总要求"],
                barmode="group",
                title="各类别学分：已修 vs 要求"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(compare, use_container_width=True)

            done_total = done_df["学分"].sum()
            req_total = curriculum_df["学分"].sum()
            st.metric("总体学分达成", f"{done_total} / {req_total} 学分", f"{round(done_total/req_total*100,1)}%")
    else:
        st.info("还没有添加已修课程，从上方表单添加吧")

# ---------- Tab3：AI 选课咨询 ----------
with tab3:
    st.header("AI 选课咨询")
    st.write("输入你的问题，AI 结合你的已修课程情况给出建议")

    user_q = st.text_area(
        "你的问题",
        placeholder="例如：我大三上学期想留时间准备实习，应该怎么选课比较轻松？",
        height=100
    )

    if st.button("🚀 咨询 AI") and user_q.strip():
        client = get_maas_client()
        if client is None:
            st.warning("⚠️ 未检测到 MAAS_API_KEY，AI 功能暂不可用。")
            st.info("请在 PowerShell 执行：`setx MAAS_API_KEY 你的密钥`，然后重启 VS Code。")
        else:
            with st.spinner("AI 正在分析..."):
                # 把已修课程拼进上下文
                context = ""
                if st.session_state.completed_courses:
                    done_df = pd.DataFrame(st.session_state.completed_courses)
                    context = f"\n学生已修课程情况：\n{done_df.to_string(index=False)}\n"

                try:
                    resp = client.chat.completions.create(
                        model="openPangu-2.0-Flash",
                        messages=[
                            {"role": "system", "content":
                                "你是一个高校学业规划助手，熟悉大数据管理与应用专业的培养方案。"
                                "根据学生的已修课程和问题，给出具体、可操作的选课建议，"
                                "说明理由，并提醒学分缺口。回答控制在300字以内，分点列出。"},
                            {"role": "user", "content": f"{context}\n学生问题：{user_q}"}
                        ],
                        temperature=0.7
                    )
                    st.success("AI 建议如下：")
                    st.write(resp.choices[0].message.content)
                except Exception as e:
                    st.error(f"调用 MaaS 失败：{e}")
