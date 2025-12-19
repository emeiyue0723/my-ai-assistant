import streamlit as st
import base64
from PIL import Image
from openai import OpenAI

# --- 1. 全局配置区 ---
st.title("我是AI 叶明哲 🤖")

client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

# --- 2. 工具函数区 ---
# --- 图片转换函数 ---
def encode_image(img_file):
    if img_file is None:
        return None
    bytes_data = img_file.getvalue()
    base64_str = base64.b64encode(bytes_data).decode('utf-8')
    return base64_str

# --- 侧边栏设置函数 ---
def setup_sidebar():
    st.sidebar.title("🤖 我的 AI 助手")

    # 1. 定义系统提示词
    system_prompt = st.sidebar.text_input("系统提示词 (人设)", value="You are a helpful assistant.")

    # 2. 如果记忆已经存在，直接在这里更新记忆里的第一条人设
    if "messages" in st.session_state:
        st.session_state.messages[0] = {"role": "system", "content": system_prompt}

    # 3. 模型选择
    model_name = st.sidebar.selectbox(
        "选择模型",
        ["deepseek-chat", "deepseek-coder"],
        index=0
    )

    # 4. 创造力滑块
    temperature = st.sidebar.slider(
        "创造力 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.7
    )

    # 5. 图片上传
    uploaded_file = st.sidebar.file_uploader(
        "上传一张图片 (可选) 🖼️",
        type=["jpg", "png", "jpeg"]
    )

    if uploaded_file:
        st.sidebar.image(uploaded_file, caption="已上传图片", use_container_width=True)

    # 6. 清空按钮
    if st.sidebar.button("🗑️ 清空对话"):
        st.session_state.messages = [
            {"role": "system", "content": system_prompt}
        ]
        st.rerun()

    return model_name, temperature, uploaded_file

# --- 3.主程序 ---
def main():

# 1. 初始化记忆 (必须在 setup_sidebar 之前或同时检查，防止报错)
    if "messages" not in st.session_state:
        st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# 2. 调用侧边栏函数
# 这一行执行完，侧边栏就显示出来了，而且内部的逻辑会自动更新 system_prompt
    model_name, temperature, uploaded_file = setup_sidebar()


# 3. 显示历史消息
    for msg in st.session_state.messages:
        if msg["role"] == "system":continue
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# 4. 处理用户输入
    if user_input := st.chat_input("请输入你的问题..."):
    # 显示用户消息
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

    # 生成 AI 回复
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

        # 准备要发送消息副本
            messages_to_send = st.session_state.messages.copy()

        # 处理图片逻辑 (安全模式)
            if uploaded_file:
                st.warning("⚠️ 注意：当前 DeepSeek 模型暂时看不见图片，仅发送文件名。")
                new_content = user_input + f"\n[系统注：用户上传了一张名为 '{uploaded_file.name}' 的图片，但你看不见它，请根据文件名猜测或礼貌回应。]"
                messages_to_send[-1]["content"] = new_content

        # 发送请求
            response = client.chat.completions.create(
                model=model_name,  # 这里使用了侧边栏选择的模型
                messages=messages_to_send,
                temperature=temperature,  # 这里使用了侧边栏的温度
                stream=True
        )

        # 流式输出
            for chunk in response:
                content = chunk.choices[0].delta.content or ""
                full_response += content
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)

    # 存入记忆
        st.session_state.messages.append({"role": "assistant", "content": full_response})

# --- 4. 程序入口 (Magic Button) ---
if __name__ == "__main__":
    main()