"""JinshiAgent Web UI — 基于 Streamlit 的对话界面

功能特点：
    - 多轮对话：支持上下文连续对话
    - 工具调用展示：显示 Agent 的工具调用过程
    - 设置面板：可配置 API Key、模型参数、服务地址
    - 记忆管理：查看/搜索/删除长期记忆
    - 多 Agent 模式：支持 Orchestrator / Pipeline / RoundRobin

启动方式::

    streamlit run web/app.py

    # 或指定服务端口
    streamlit run web/app.py --server.port 8501
"""

from __future__ import annotations

import json
import sys
import os

# 确保 src 目录在 Python 路径中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "http://localhost:8000"


def get_api_url() -> str:
    """获取 API 服务地址。"""
    return st.session_state.get("api_url", DEFAULT_API_URL)


def get_api_headers() -> dict[str, str]:
    """获取 API 请求头（含认证）。"""
    headers = {"Content-Type": "application/json"}
    api_key = st.session_state.get("api_key", "")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def api_get(path: str, params: dict | None = None) -> dict | None:
    """发送 GET 请求到 API 服务。"""
    try:
        resp = httpx.get(
            f"{get_api_url()}{path}",
            headers=get_api_headers(),
            params=params,
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API 错误: {resp.status_code} - {resp.text}")
            return None
    except httpx.ConnectError:
        st.error("无法连接到 API 服务，请确认服务已启动")
        return None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def api_post(path: str, data: dict) -> dict | None:
    """发送 POST 请求到 API 服务。"""
    try:
        resp = httpx.post(
            f"{get_api_url()}{path}",
            headers=get_api_headers(),
            json=data,
            timeout=60.0,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API 错误: {resp.status_code} - {resp.text}")
            return None
    except httpx.ConnectError:
        st.error("无法连接到 API 服务，请确认服务已启动")
        return None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


def api_delete(path: str) -> dict | None:
    """发送 DELETE 请求到 API 服务。"""
    try:
        resp = httpx.delete(
            f"{get_api_url()}{path}",
            headers=get_api_headers(),
            timeout=30.0,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"API 错误: {resp.status_code} - {resp.text}")
            return None
    except Exception as e:
        st.error(f"请求失败: {e}")
        return None


# ---------------------------------------------------------------------------
# 初始化 Session State
# ---------------------------------------------------------------------------


def init_session_state() -> None:
    """初始化 Streamlit session state。"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = None
    if "api_url" not in st.session_state:
        st.session_state.api_url = DEFAULT_API_URL
    if "api_key" not in st.session_state:
        st.session_state.api_key = os.getenv("JINSHI_API_KEY", "")
    if "system_prompt" not in st.session_state:
        st.session_state.system_prompt = "你是一个有用的 AI 助手。"
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o"


# ---------------------------------------------------------------------------
# 页面组件
# ---------------------------------------------------------------------------


def render_sidebar() -> None:
    """渲染侧边栏设置面板。"""
    with st.sidebar:
        st.header("设置")

        # API 连接配置
        st.subheader("API 连接")
        st.session_state.api_url = st.text_input(
            "API 地址",
            value=st.session_state.api_url,
            help="JinshiAgent API 服务的地址",
        )
        st.session_state.api_key = st.text_input(
            "API 密钥",
            value=st.session_state.api_key,
            type="password",
            help="如果服务端配置了 JINSHI_API_KEY，需要提供对应密钥",
        )

        # 健康检查
        if st.button("检查服务状态"):
            health = api_get("/health")
            if health:
                st.success(f"服务正常 | 版本: {health.get('version', 'N/A')}")
                st.json(health)

        st.divider()

        # 对话配置
        st.subheader("对话配置")
        st.session_state.system_prompt = st.text_area(
            "系统提示词",
            value=st.session_state.system_prompt,
            height=100,
        )

        # 会话管理
        st.subheader("会话管理")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("新建会话"):
                st.session_state.session_id = None
                st.session_state.messages = []
                st.rerun()
        with col2:
            if st.button("重置对话"):
                if st.session_state.session_id:
                    api_post(f"/chat/sessions/{st.session_state.session_id}/reset", {})
                st.session_state.messages = []
                st.rerun()

        # 显示活跃会话
        sessions = api_get("/chat/sessions")
        if sessions:
            st.subheader(f"活跃会话 ({len(sessions)})")
            for s in sessions[:10]:
                with st.expander(f"{s['session_id']} ({s['history_length']} 条)"):
                    st.write(f"Agent: {s['agent_name']}")
                    st.write(f"记忆: {'是' if s['has_long_term_memory'] else '否'}")
                    if st.button("切换", key=f"switch_{s['session_id']}"):
                        st.session_state.session_id = s["session_id"]
                        st.rerun()

        st.divider()

        # 工具信息
        tools = api_get("/tools")
        if tools:
            st.subheader(f"已注册工具 ({len(tools)})")
            for t in tools:
                st.markdown(f"**{t['name']}**: {t['description'][:50]}")


def render_chat() -> None:
    """渲染主聊天区域。"""
    st.title("JinshiAgent")
    st.caption("AI Agent 工具框架 — 对话界面")

    # 显示历史消息
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                st.markdown(content)
        elif role == "tool":
            with st.chat_message("assistant", avatar="🔧"):
                st.code(content, language="text")

    # 聊天输入
    if prompt := st.chat_input("输入消息..."):
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 调用 API
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                result = api_post("/chat", {
                    "message": prompt,
                    "session_id": st.session_state.session_id,
                    "system_prompt": st.session_state.system_prompt,
                })

                if result:
                    # 更新会话 ID
                    st.session_state.session_id = result["session_id"]

                    # 显示回答
                    response_text = result["response"]
                    st.markdown(response_text)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response_text,
                    })

                    # 显示工具调用
                    for tc in result.get("tool_calls", []):
                        tool_content = f"[工具调用] {tc.get('content', '')}"
                        st.session_state.messages.append({
                            "role": "tool",
                            "content": tool_content,
                        })

                    # 显示统计信息
                    st.caption(
                        f"会话: {result['session_id']} | "
                        f"历史: {result['history_length']} 条 | "
                        f"工具调用: {len(result.get('tool_calls', []))} 次"
                    )


def render_memory_page() -> None:
    """渲染记忆管理页面。"""
    st.title("记忆管理")
    st.caption("长期语义记忆 — 查看、搜索、删除")

    # 记忆统计
    count_data = api_get("/memory/count")
    if count_data:
        st.metric("记忆条数", count_data["count"])
        st.caption(f"后端: {count_data.get('backend', 'N/A')}")

    # 搜索记忆
    st.subheader("搜索记忆")
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        search_query = st.text_input("搜索查询", key="mem_search_query")
    with search_col2:
        search_n = st.number_input("返回条数", min_value=1, max_value=50, value=5)

    if search_query and st.button("搜索"):
        results = api_post("/memory/search", {
            "query": search_query,
            "n_results": search_n,
        })
        if results:
            for r in results:
                score = r.get("score")
                score_str = f" (相似度: {score:.2f})" if score else ""
                with st.expander(f"{r['content'][:60]}...{score_str}"):
                    st.write(f"**ID:** {r['id']}")
                    st.write(f"**内容:** {r['content']}")
                    st.json(r.get("metadata", {}))
                    if st.button("删除", key=f"del_{r['id']}"):
                        api_delete(f"/memory/{r['id']}")
                        st.success("已删除")
                        st.rerun()

    # 添加记忆
    st.subheader("添加记忆")
    add_content = st.text_area("记忆内容", key="mem_add_content")
    add_col1, add_col2 = st.columns(2)
    with add_col1:
        add_role = st.selectbox("角色", ["system", "user", "assistant", "tool"], key="mem_add_role")
    with add_col2:
        add_topic = st.text_input("主题", key="mem_add_topic")

    if add_content and st.button("添加"):
        result = api_post("/memory/add", {
            "content": add_content,
            "role": add_role,
            "topic": add_topic,
        })
        if result:
            st.success(f"已添加 | ID: {result.get('memory_id', 'N/A')}")
            st.rerun()

    # 浏览所有记忆
    st.subheader("浏览全部记忆")
    all_memories = api_get("/memory/all", params={"limit": 50})
    if all_memories:
        for m in all_memories:
            with st.expander(f"{m['content'][:60]}..."):
                st.write(f"**ID:** {m['id']}")
                st.write(f"**内容:** {m['content']}")
                st.json(m.get("metadata", {}))
                if st.button("删除", key=f"del_all_{m['id']}"):
                    api_delete(f"/memory/{m['id']}")
                    st.success("已删除")
                    st.rerun()


def render_multi_agent_page() -> None:
    """渲染多 Agent 协作页面。"""
    st.title("多 Agent 协作")
    st.caption("支持 Orchestrator / Pipeline / RoundRobin 三种协作模式")

    # 任务输入
    task = st.text_area("任务描述", height=100, key="ma_task")

    # 模式选择
    mode = st.selectbox(
        "协作模式",
        ["orchestrator", "pipeline", "round_robin"],
        format_func=lambda x: {
            "orchestrator": "主从模式 (Orchestrator)",
            "pipeline": "流水线模式 (Pipeline)",
            "round_robin": "轮询模式 (Round Robin)",
        }[x],
    )

    # 显示模式说明
    mode_desc = {
        "orchestrator": "主 Agent 拆解任务，分配给子 Agent 执行，汇总结果",
        "pipeline": "多个 Agent 顺序执行，前一个的输出是后一个的输入",
        "round_robin": "每个 Agent 依次对同一任务进行补充处理",
    }
    st.info(f"**{mode}**: {mode_desc[mode]}")

    # 执行
    if task and st.button("执行任务"):
        with st.spinner("执行中..."):
            result = api_post("/multi-agent/run", {
                "task": task,
                "mode": mode,
            })
            if result:
                st.success(f"任务完成 | 状态: {result['status']}")
                st.markdown("### 执行结果")
                st.markdown(result["output"])
                if result.get("metadata"):
                    st.json(result["metadata"])


# ---------------------------------------------------------------------------
# 主程序
# ---------------------------------------------------------------------------


def main() -> None:
    """主入口。"""
    init_session_state()

    # 页面导航
    page = st.sidebar.radio(
        "页面导航",
        ["对话", "记忆管理", "多 Agent 协作"],
        label_visibility="collapsed",
    )

    # 渲染侧边栏
    render_sidebar()

    # 渲染主页面
    if page == "对话":
        render_chat()
    elif page == "记忆管理":
        render_memory_page()
    elif page == "多 Agent 协作":
        render_multi_agent_page()


if __name__ == "__main__":
    main()
