import streamlit as st
import base64
from PIL import Image  # 👈 刚刚装的 Pillow 库
from openai import OpenAI


# --- 新增：图片转码函数 ---
def encode_image(uploaded_file):
    if uploaded_file is None:
        return None
    # 1. 读取图片的二进制数据
    bytes_data = uploaded_file.getvalue()
    # 2. 把它转成 base64 编码的字符串
    base64_str = base64.b64encode(bytes_data).decode('utf-8')
    return base64_str
# -------------------------

# ... (下面是 client = OpenAI(...) 的代码)
# 1. 这里的 Key 记得换成你自己的！
# client = OpenAI(
#     api_key="sk-321a4847b3554f389484b6cf9ccf29fb",
#     base_url="https://api.deepseek.com"
# )
client = OpenAI(
    api_key=st.secrets["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com"
)

# --- 侧边栏配置 ---
st.sidebar.title("🎨 个性化设置")

# 1. 人设输入框 (默认值设为之前的通用助手)
system_prompt = st.sidebar.text_input(
    "给 AI 设定一个人设 (System Prompt)",
    value="你是一个乐于助人的 AI 助手"
)

# 2. 创造力滑块 (范围 0.0 到 2.0)
temperature_value = st.sidebar.slider(
    "创造力 (Temperature)",
    min_value=0.0,
    max_value=2.0,
    value=1.3
)

# --- 新增：图片上传 ---
uploaded_file = st.sidebar.file_uploader("上传一张图片 (可选) 🖼️", type=["jpg", "png", "jpeg"])

if uploaded_file:
    # 如果用户上传了图片，就在侧边栏显示个缩略图
    st.sidebar.image(uploaded_file, caption="已上传图片", use_container_width=True)
# ---------------------

# 3. 清空对话按钮
if st.sidebar.button("🗑️ 清空对话"):
    # 把记忆列表重置，只保留当前的人设
    st.session_state.messages = [
        {"role": "system", "content": system_prompt}
    ]
    st.rerun()  # 👈 关键！强制刷新页面，立刻让屏幕变干净

# 强制把记忆里的第一条 (System Message) 更新为侧边栏的内容
if "messages" in st.session_state:
    st.session_state.messages[0] = {"role": "system", "content": system_prompt}
# -----------------

st.title("我的 AI 助手 🤖")

# --- 关键修改开始 ---
# 检查 session_state 这个“保险箱”里有没有 'messages' 这个钥匙
if "messages" not in st.session_state:
    # 如果没有，说明是第一次打开，初始化一个空列表，并预置人设
    st.session_state.messages = [
        {"role": "system", "content": "你是一个乐于助人的 AI 助手"}
    ]
# --- 关键修改结束 ---

# 1. 遍历记忆里的每一条消息
for msg in st.session_state.messages:
    # (可选) 我们一般不把 system 提示词显示在界面上，这里做一个过滤
    if msg["role"] == "system":
        continue

    # 2. 根据角色自动显示对应的头像和气泡
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 接收用户的输入
if user_input := st.chat_input("请输入你的问题..."):
    # 1. 显示用户的话
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2. 显示 AI 的回复
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""  # 👈 关键！必须在这里先定义它，哪怕是空的

        # --- 新增的图片处理逻辑 ---
        messages_to_send = st.session_state.messages.copy()

        if uploaded_file:
            #image_str = encode_image(uploaded_file)
            # 构造混合消息 (DeepSeek V3 目前可能不支持，但格式是通用的)
            # new_msg = {
            #     "role": "user",
            #     "content": [
            #         {"type": "text", "text": user_input},
            #         {
            #             "type": "image_url",
            #             "image_url": {
            #                 "url": f"data:image/jpeg;base64,{image_str}"
            #             }
            #         }
            #     ]
            # }
            # 替换最后一条消息为带图的消息
            # 1. 在界面上提示用户
            st.warning("⚠️ 注意：当前 DeepSeek 模型暂时看不见图片，仅发送文件名。")

            # 2. 我们不发送 image_url (因为会报错)，而是把图片名字拼接到文字后
            # 这样 AI 知道你传了图，虽然它看不见内容
            new_content = user_input + f"\n[系统注：用户上传了一张名为 '{uploaded_file.name}' 的图片，但你看不见它，请根据文件名猜测或礼貌回应。]"

            # 3. 更新要发送的消息（保持纯文本格式）
            messages_to_send[-1]["content"] = new_content

            #messages_to_send[-1] = new_msg
        # -------------------------

        # 发起请求
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages_to_send,
            stream=True
        )

        # 循环接收碎片
        for chunk in response:
            content = chunk.choices[0].delta.content or ""
            full_response += content
            message_placeholder.markdown(full_response + "▌")

        message_placeholder.markdown(full_response)

    # 3. 存入记忆
    # 因为 full_response 刚才在上面定义过了，这里就不会报错了
    st.session_state.messages.append({"role": "assistant", "content": full_response})