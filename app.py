import streamlit as st
import base64
import PyPDF2  # 👈 新增：专门处理 PDF 的库
from PIL import Image
from openai import OpenAI

# 1. 配置 DeepSeek 客户端
client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)


# --- 工具函数 1：图片转码 ---
def encode_image(img_file):
    if img_file is None:
        return None
    bytes_data = img_file.getvalue()
    base64_str = base64.b64encode(bytes_data).decode('utf-8')
    return base64_str


# --- 工具函数 2：PDF 转文字 (新增！) ---
def extract_text_from_pdf(pdf_file):
    """
    专门负责把 PDF 文件变成纯文本字符串
    """
    if pdf_file is None:
        return ""

    # 使用 PyPDF2 读取文件
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""

    # 一页一页地把字扣出来
    for page in pdf_reader.pages:
        # 如果某一页提取到了字，就拼接到总文本里
        text += page.extract_text() + "\n"

    return text


# --- 侧边栏设置函数 ---
def setup_sidebar():
    st.sidebar.title("🤖 科技项目助手 (Pro版)")

    # --- 1. 新增：工作模式选择器 ---
    task_type = st.sidebar.selectbox(
        "选择任务模式 🛠️",
        ["通用助手", "公文润色/仿写", "项目申报书撰写", "会议纪要整理"],
        index=0
    )

    # --- 2. 根据模式自动生成人设 (Prompt Engineering) ---
    # 这里是让 AI 变聪明的关键！我们把专家的经验写进预设里。
    prompts = {
        "通用助手": "你是一名资深的科技项目专家，擅长解答各类技术和管理问题。",

        "公文润色/仿写": "你是一名在政府机关或国企工作多年的公文写作专家。你的语言风格庄重、严谨、简练。你擅长使用排比、对仗等修辞手法，熟悉公文的格式规范（如通知、请示、函等）。请根据用户提供的素材，优化其措辞，使其符合官方公文标准。",

        "项目申报书撰写": "你是一名有着丰富成功经验的科技项目申报顾问。你深知评审专家的关注点（如：创新性、经济效益、技术路线的可行性）。请根据用户提供的背景材料，撰写逻辑清晰、数据详实、极具说服力的申报材料章节。",

        "会议纪要整理": "你是一名高效的行政秘书。请根据用户提供的会议录音转录文本或笔记，提炼出：1. 会议主题；2. 核心决议；3. 待办事项(Action Items)及责任人。语言要干练，去除口语废话。"
    }

    # 自动获取对应的人设
    default_prompt = prompts[task_type]

    # 允许用户在预设基础上微调
    system_prompt = st.sidebar.text_area("系统人设 (可微调)", value=default_prompt, height=150)

    # 3. 实时更新记忆
    if "messages" in st.session_state:
        st.session_state.messages[0] = {"role": "system", "content": system_prompt}

    # 4. 模型选择
    model_name = st.sidebar.selectbox(
        "选择模型",
        ["deepseek-chat", "deepseek-coder"],
        index=0
    )

    # 5. 创造力滑块 (不同模式建议不同的创造力)
    # 如果是写申报书，稍微高一点(0.5)以此获得灵感；如果是改公文，低一点(0.2)保证严谨
    default_temp = 0.5 if task_type == "项目申报书撰写" else 0.2

    temperature = st.sidebar.slider(
        "创造力 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=default_temp
    )

    # 6. 文件上传
    uploaded_file = st.sidebar.file_uploader(
        "上传参考资料 (PDF/图片) 📂",
        type=["jpg", "png", "jpeg", "pdf"]
    )

    if uploaded_file:
        if uploaded_file.type.startswith('image'):
            st.sidebar.image(uploaded_file, caption="已上传图片", use_container_width=True)
        elif uploaded_file.type == "application/pdf":
            st.sidebar.success(f"📄 已加载文档: {uploaded_file.name}")

    # 7. 清空按钮
    if st.sidebar.button("🗑️ 清空对话"):
        st.session_state.messages = [
            {"role": "system", "content": system_prompt}
        ]
        st.rerun()

    return model_name, temperature, uploaded_file


# ===========================
# --- 主程序逻辑 ---
# ===========================
def main():
    st.title("📄 四川平高-科技公文助手")  # 定制化标题

    # A. 初始化记忆
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "system", "content": "你是一名资深的科技项目专家。"}
        ]

    # B. 调用侧边栏
    model_name, temperature, uploaded_file = setup_sidebar()

    # C. 显示历史消息
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # D. 处理用户输入
    if user_input := st.chat_input("请输入你的指令 (例如：根据附件总结关键点)..."):

        # 1. 显示用户输入
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})

        # 2. 生成 AI 回复
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            # --- 关键逻辑：处理附件 ---
            messages_to_send = st.session_state.messages.copy()

            if uploaded_file:
                # === 情况 1：PDF ===
                if uploaded_file.type == "application/pdf":
                    with st.spinner("正在阅读 PDF 文档，请稍候... 📖"):
                        # 调用我们写的函数提取文字
                        pdf_text = extract_text_from_pdf(uploaded_file)

                    # 构造新的提示词：[背景资料] + [用户问题]
                    # 我们截取前 10000 个字防止超出 Token 限制（一般来说 DeepSeek 都能吃得下）
                    new_content = f"【背景参考资料】：\n{pdf_text[:20000]}\n\n【用户指令】：{user_input}"

                    # 替换掉最后一条消息的内容
                    messages_to_send[-1]["content"] = new_content

                    # 界面提示
                    st.toast(f"✅ 已提取 PDF 内容 ({len(pdf_text)} 字符)，正在分析...", icon="🧠")

                # === 情况 2：图片 ===
                elif uploaded_file.type.startswith('image'):
                    st.warning("⚠️ 提示：DeepSeek 暂只支持文本，已发送文件名供参考。")
                    new_content = user_input + f"\n[系统注：用户上传了图片 '{uploaded_file.name}']"
                    messages_to_send[-1]["content"] = new_content

            # 3. 发送请求
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages_to_send,
                    temperature=temperature,
                    stream=True
                )

                # 4. 流式渲染
                for chunk in response:
                    content = chunk.choices[0].delta.content or ""
                    full_response += content
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)

                # 存入记忆
                st.session_state.messages.append({"role": "assistant", "content": full_response})

            except Exception as e:
                st.error(f"❌ 请求出错了: {e}")


# 程序入口
if __name__ == "__main__":
    main()