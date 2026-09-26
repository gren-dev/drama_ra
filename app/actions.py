"""把页面里"去终端跑 python xxx"的提示变成可以直接点的按钮。

点击后用当前解释器在项目根目录跑命令，输出实时显示在页面里；
成功后清掉缓存并刷新页面，数据立刻更新。
"""
import subprocess
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
HOME = Path.home()


def _scrub(text: str) -> str:
    return text.replace(str(ROOT) + "/", "").replace(str(HOME), "~")


def run_command(args: list[str], label: str) -> bool:
    """在 st.status 面板里跑一条命令并流式显示输出。返回是否成功。"""
    cmd = [sys.executable, *args]
    with st.status(f"正在{label}…", expanded=True) as box:
        st.code("$ python " + " ".join(args), language="bash")
        holder = st.empty()
        lines: list[str] = []
        proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, bufsize=1, env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"})
        for line in proc.stdout:
            lines.append(_scrub(line.rstrip()))
            holder.code("\n".join(lines[-40:]) or "…", language="text")
        code = proc.wait()
        st.session_state["last_action"] = {"label": label, "ok": code == 0,
                                           "tail": next((l for l in reversed(lines) if l.strip()), "")}
        if code == 0:
            box.update(label=f"{label}完成", state="complete", expanded=False)
            return True
        box.update(label=f"{label}失败（退出码 {code}）", state="error", expanded=True)
        return False


def action(msg: str, label: str, args: list[str], key: str, help: str | None = None) -> None:
    """一段说明 + 一个按钮。msg 用 HTML 渲染成空状态样式。"""
    from app import theme
    theme.empty_state(msg)
    last = st.session_state.get("last_action")
    if last and last["label"] == label:
        st.caption(("✅ " if last["ok"] else "❌ ") + f"上次「{label}」：{last['tail'][:120]}")
    if st.button(label, key=f"act_{key}", help=help, type="primary"):
        if run_command(args, label):
            st.cache_data.clear()
            st.toast(f"{label}完成，页面已刷新")
            st.rerun()
