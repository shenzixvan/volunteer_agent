import streamlit as st
import datetime
import pandas as pd
import json
import io
from typing import Dict, List
import requests
from dashscope import Generation
import dashscope
import hashlib
import openpyxl
from streamlit_extras.switch_page_button import switch_page
from streamlit_extras.let_it_rain import rain

# ===================== 全局配置 =====================
st.set_page_config(
    page_title="智能志愿服务智能体", 
    page_icon="🤝", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义样式
def set_custom_style():
    st.markdown("""
    <style>
    .stApp {
        background: none;
        background-color: #ffffff;
    }
    .main > div {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .stButton>button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #45a049 0%, #3d8b40 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 10px;
        font-size: 14px;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        background-color: #f5f5f5;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
        color: white;
    }
    .stSidebar {
        background-color: rgba(255, 255, 255, 0.95);
        padding: 20px 10px;
    }
    [data-testid="stVerticalBlock"] {
        transition: all 0.5s ease-in-out;
    }
    </style>
    """, unsafe_allow_html=True)

# ===================== 初始化Session State =====================
def init_session():
    required_keys = {
        "user_role": None,
        "user_info": {},
        "registered_users": [],
        "volunteer_projects": [],
        "service_demands": [],
        "workflows": [],
        "volunteer_hours": [],
        "demand_matching": [],
        "notifications": [],
        "ai_generated_content": "",
        "show_rain_effect": False,
        "project_desc_manual": "",
        "trigger_ai_generate": False
    }
    for key, default_value in required_keys.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

# ===================== 密码加密工具函数 =====================
def encrypt_password(password):
    sha256 = hashlib.sha256()
    sha256.update(password.encode('utf-8'))
    return sha256.hexdigest()

def verify_password(input_pwd, stored_pwd):
    return encrypt_password(input_pwd) == stored_pwd

# ===================== 阿里云百炼AI调用核心函数 =====================
def call_aliyun_llm(prompt, model="qwen-turbo"):
    API_KEY = "sk-5159e7a24fe14eef98a5c46dac650892"  # 替换为你的API Key
    dashscope.api_key = API_KEY
    Generation.api_key = API_KEY
    
    try:
        response = Generation.call(
            model=model,
            messages=[
                {"role": "system", "content": "你是一名专业的志愿服务智能助手，擅长生成项目描述、分析需求、设计工作流，语言简洁、专业、易懂。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000,
            result_format="text"
        )
        if response.status_code == 200:
            return response.output.text.strip()
        else:
            return f"AI调用失败：{response.code} - {response.message}"
    except Exception as e:
        return f"AI调用异常：{str(e)}"

# ===================== AI生成功能封装 =====================
def ai_generate(scene, input_text):
    if not input_text:
        return "请先输入基础信息！"
    
    prompt_templates = {
        "project_desc": f"""
        请根据以下志愿服务项目名称，生成专业、落地性强的项目描述（100-200字）：
        项目名称：{input_text}
        要求：包含项目目标、服务内容、预期效果，语言通俗易懂，符合中国志愿服务场景。
        """,
        "demand_analysis": f"""
        请结构化分析以下被服务人群的需求（分点输出，简洁明了）：
        需求内容：{input_text}
        要求：核心诉求（30字内）、适配志愿服务类型、建议服务配置、注意事项。
        """,
        "workflow_suggest": f"""
        请为以下志愿服务场景设计3-5步标准化工作流：
        场景：{input_text}
        要求：每步包含步骤名称+操作说明，具体可落地，符合志愿服务执行逻辑。
        """,
    }
    
    result = call_aliyun_llm(prompt_templates[scene])
    st.session_state["ai_generated_content"] = result
    st.session_state["show_rain_effect"] = True
    return result

# ===================== 消息通知模块 =====================
def notification_module():
    if st.session_state.user_role:
        with st.sidebar.expander("📩 消息通知", expanded=False):
            if st.session_state.notifications:
                for msg in reversed(st.session_state.notifications[-5:]):
                    st.write(f"[{msg['time']}] **{msg['title']}**")
                    st.caption(msg["content"])
            else:
                st.info("暂无新消息～")

# ===================== 登录/注册模块 =====================
def auth_module():
    if not st.session_state.user_role:
        st.sidebar.markdown("### 🔐 账号管理")
        tab1, tab2 = st.sidebar.tabs(["登录", "注册"])
        
        with tab1:
            st.subheader("欢迎回来！")
            login_username = st.text_input("用户名", placeholder="输入注册的用户名", key="login_username")
            login_password = st.text_input("密码", type="password", placeholder="输入注册的密码", key="login_password")
            
            if st.button("登录", use_container_width=True):
                try:
                    if not login_username.strip() or not login_password.strip():
                        raise ValueError("用户名和密码不能为空！")
                    
                    target_user = None
                    for u in st.session_state.registered_users:
                        if u["username"] == login_username.strip():
                            target_user = u
                            break
                    
                    if not target_user:
                        raise ValueError(f"用户名「{login_username}」不存在！")
                    if not verify_password(login_password.strip(), target_user["password"]):
                        raise ValueError("密码错误！")
                    
                    st.session_state.user_role = target_user["role"]
                    st.session_state.user_info = {"username": target_user["username"], "role": target_user["role"]}
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "登录成功",
                        "content": f"你已以「{target_user['role']}」身份登录"
                    })
                    st.session_state["show_rain_effect"] = True
                    st.rerun()
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
        
        with tab2:
            st.subheader("创建账号")
            reg_role = st.selectbox("选择注册身份", ["志愿服务组织", "志愿者", "被服务人群"], key="reg_role")
            reg_username = st.text_input("设置用户名", placeholder="字母/数字组合，如org001", key="reg_username")
            reg_password = st.text_input("设置密码", type="password", placeholder="不少于6位", key="reg_password")
            reg_confirm_pwd = st.text_input("确认密码", type="password", placeholder="再次输入密码", key="reg_confirm_pwd")
            
            if st.button("提交注册", use_container_width=True):
                try:
                    if not reg_username.strip() or not reg_password.strip() or not reg_confirm_pwd.strip():
                        raise ValueError("所有字段不能为空！")
                    if len(reg_password) < 6:
                        raise ValueError("密码长度不能少于6位！")
                    if reg_password != reg_confirm_pwd:
                        raise ValueError("两次密码不一致！")
                    
                    existing_users = [u["username"] for u in st.session_state.registered_users]
                    if reg_username.strip() in existing_users:
                        raise ValueError(f"用户名「{reg_username}」已存在！")
                    
                    new_user = {
                        "username": reg_username.strip(),
                        "password": encrypt_password(reg_password.strip()),
                        "role": reg_role,
                        "register_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.registered_users.append(new_user)
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "注册成功",
                        "content": f"「{reg_username}」注册成功，请登录！"
                    })
                    st.success("✅ 注册成功！请切换到登录页登录")
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
    else:
        st.sidebar.markdown("### 👤 当前用户")
        st.sidebar.write(f"**身份**：{st.session_state.user_role}")
        st.sidebar.write(f"**用户名**：{st.session_state.user_info['username']}")
        if st.button("退出登录", use_container_width=True):
            st.session_state.user_role = None
            st.session_state.user_info = {}
            st.rerun()

# ===================== 数据导出模块 =====================
def export_data_module(data_type):
    if st.button(f"📤 导出{data_type}数据", use_container_width=True):
        try:
            data_mapping = {
                "项目": st.session_state.volunteer_projects,
                "需求": st.session_state.service_demands,
                "时长": st.session_state.volunteer_hours,
                "工作流": st.session_state.workflows,
                "用户": st.session_state.registered_users
            }
            if data_type not in data_mapping:
                raise ValueError("不支持的导出类型！")
            
            df = pd.DataFrame(data_mapping[data_type])
            if df.empty:
                raise ValueError("暂无数据可导出！")
            
            if data_type == "工作流":
                df["steps"] = df["steps"].apply(lambda x: json.dumps(x, ensure_ascii=False) if x else "")
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name=data_type)
            output.seek(0)
            
            st.download_button(
                label=f"💾 下载{data_type}数据（Excel）",
                data=output,
                file_name=f"{data_type}_数据_{datetime.date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"download_{data_type}",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"导出失败：{str(e)}")

# ===================== 数据导入模块 =====================
def import_data_module(data_type):
    st.subheader(f"📥 导入{data_type}数据")
    uploaded_file = st.file_uploader(
        f"上传{data_type}数据Excel文件",
        type=["xlsx"],
        key=f"import_{data_type}"
    )
    
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.write(f"预览导入数据（前5行）：")
            st.dataframe(df.head(), use_container_width=True)
            
            data_mapping = {
                "项目": "volunteer_projects",
                "需求": "service_demands",
                "时长": "volunteer_hours",
                "用户": "registered_users",
                "工作流": "workflows"
            }
            if data_type not in data_mapping:
                raise ValueError("不支持的导入类型！")
            
            if st.button(f"✅ 确认导入{data_type}数据", use_container_width=True):
                target_key = data_mapping[data_type]
                import_data = df.to_dict("records")
                
                if data_type == "用户":
                    for row in import_data:
                        if "password" in row and not row["password"].startswith("5e884898da28047151d0e56f8dc629277"):
                            row["password"] = encrypt_password(row["password"])
                        if "register_time" not in row:
                            row["register_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                existing_ids = []
                if data_type in ["项目", "需求", "工作流"]:
                    existing_ids = [item["id"] for item in st.session_state[target_key]]
                elif data_type == "用户":
                    existing_ids = [item["username"] for item in st.session_state[target_key]]
                elif data_type == "时长":
                    existing_ids = [f"{item['volunteer']}_{item['project_id']}_{item['date']}" for item in st.session_state[target_key]]
                
                new_data = []
                for row in import_data:
                    if data_type in ["项目", "需求", "工作流"]:
                        if row.get("id") not in existing_ids:
                            new_data.append(row)
                    elif data_type == "用户":
                        if row.get("username") not in existing_ids:
                            new_data.append(row)
                    elif data_type == "时长":
                        unique_key = f"{row.get('volunteer')}_{row.get('project_id')}_{row.get('date')}"
                        if unique_key not in existing_ids:
                            new_data.append(row)
                
                st.session_state[target_key].extend(new_data)
                st.session_state.notifications.append({
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "title": f"{data_type}数据导入成功",
                    "content": f"共导入{len(new_data)}条{data_type}数据（过滤重复{len(import_data)-len(new_data)}条）"
                })
                st.success(f"✅ 成功导入{len(new_data)}条{data_type}数据！")
        except Exception as e:
            st.error(f"导入失败：{str(e)}")

# ===================== 工作流搭建模块 =====================
def workflow_builder():
    st.subheader("🛠️ 自定义工作流搭建")
    current_role = st.session_state.user_role
    role_options = ["志愿服务组织", "志愿者", "被服务人群"]
    default_index = role_options.index(current_role) if current_role in role_options else 0

    col1, col2 = st.columns([3, 1])
    with col1:
        workflow_scene = st.text_input("工作流场景", placeholder=f"如：{current_role}服务流程", key="workflow_scene")
    with col2:
        if st.button("✨ AI生成建议", use_container_width=True):
            if workflow_scene:
                ai_result = ai_generate("workflow_suggest", workflow_scene)
                st.success("AI生成完成！")
            else:
                st.error("请输入工作流场景！")
    
    if st.session_state["ai_generated_content"]:
        with st.expander("📝 AI生成的工作流建议", expanded=True):
            st.write(st.session_state["ai_generated_content"])

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])
        with col1:
            workflow_name = st.text_input("工作流名称", placeholder=f"如：{current_role}服务流程")
            workflow_role = st.selectbox("适用身份", role_options, index=default_index)
            step_count = st.number_input("步骤数量", min_value=1, max_value=10, step=1, value=1)
            
            steps = []
            for i in range(step_count):
                st.write(f"#### 步骤 {i+1}")
                step_col1, step_col2 = st.columns([1, 2])
                with step_col1:
                    step_name = st.text_input(f"步骤名称", key=f"step_{i}_name", placeholder="如：填写项目信息")
                with step_col2:
                    step_action = st.text_area(f"操作说明", key=f"step_{i}_action", placeholder="详细描述操作要求")
                step_responsible = st.selectbox(f"责任人", ["组织管理员", "志愿者", "被服务人", "系统"], key=f"step_{i}_resp")
                
                if step_name and step_action:
                    steps.append({
                        "step_id": i+1,
                        "step_name": step_name,
                        "step_action": step_action,
                        "step_responsible": step_responsible
                    })
        
        with col2:
            st.write("### 工作流预览")
            if workflow_name and steps:
                st.write(f"**名称**：{workflow_name}")
                st.write(f"**适用**：{workflow_role}")
                st.write("**步骤**：")
                for s in steps:
                    st.write(f"- {s['step_id']}. {s['step_name']}")
        
        if st.button("💾 保存工作流", use_container_width=True):
            try:
                if not workflow_name:
                    raise ValueError("工作流名称不能为空！")
                if len(steps) == 0:
                    raise ValueError("至少配置1个步骤！")
                
                workflow = {
                    "id": len(st.session_state.workflows) + 1,
                    "name": workflow_name,
                    "role": workflow_role,
                    "creator": st.session_state.user_info["username"],
                    "create_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "steps": steps,
                    "status": "已生效"
                }
                st.session_state.workflows.append(workflow)
                st.session_state.notifications.append({
                    "time": datetime.datetime.now().strftime("%H:%M:%S"),
                    "title": "工作流创建成功",
                    "content": f"「{workflow_name}」已生效"
                })
                st.success(f"✅ 「{workflow_name}」工作流保存成功！")
                st.session_state["show_rain_effect"] = True
            except ValueError as e:
                st.error(f"❌ {str(e)}")
    
    st.write("### 📋 已搭建的工作流")
    filtered_workflows = [wf for wf in st.session_state.workflows if wf["role"] == current_role or wf["creator"] == st.session_state.user_info["username"]]
    if filtered_workflows:
        for idx, wf in enumerate(filtered_workflows):
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"📋 **{wf['name']}**（适用：{wf['role']} | 创建人：{wf['creator']}）")
                with col2:
                    if st.button("▶️ 执行", key=f"exec_{idx}", use_container_width=True):
                        st.session_state.notifications.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "title": "工作流执行中",
                            "content": f"「{wf['name']}」已启动"
                        })
                        st.success(f"✅ 「{wf['name']}」工作流已启动！")
                with col3:
                    json_data = json.dumps(wf, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📤 导出",
                        data=json_data,
                        file_name=f"{wf['name']}_工作流.json",
                        mime="application/json",
                        key=f"dl_{idx}",
                        use_container_width=True
                    )
                with st.expander("🔍 查看步骤"):
                    steps_df = pd.DataFrame(wf["steps"])
                    st.dataframe(steps_df[["step_id", "step_name", "step_action", "step_responsible"]], use_container_width=True)
    else:
        st.info("暂无已搭建的工作流～点击上方「AI生成建议」快速创建！")

# ===================== 组织端工作台（终极修复版） =====================
def org_dashboard():
    st.header("🏢 志愿服务组织工作台")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["发布项目", "项目管理", "需求对接", "数据统计", "工作流搭建"])
    
    with tab1:
        st.subheader("📢 发布志愿服务项目")
        with st.container(border=True):
            # 初始化session_state（最顶部）
            if "project_desc_manual" not in st.session_state:
                st.session_state["project_desc_manual"] = ""

            # 项目名称输入
            project_name = st.text_input("项目名称", placeholder="如：社区敬老志愿服务", key="project_name")

            # AI生成回调函数
            def ai_generate_callback():
                if project_name.strip():
                    ai_result = ai_generate("project_desc", project_name.strip())
                    st.session_state["project_desc_manual"] = ai_result
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()
                else:
                    st.error("请先填写项目名称！")

            # AI生成按钮（前置渲染）
            if st.button("✨ AI生成项目描述", use_container_width=True):
                ai_generate_callback()

            # 项目描述输入框（仅通过value绑定）
            project_desc_manual = st.text_area(
                "项目描述（手动输入/AI生成）", 
                placeholder="详细描述项目内容、要求、地点等",
                height=150,
                key="project_desc_manual",
                value=st.session_state["project_desc_manual"]
            )

            # 其他表单元素
            col1, col2, col3 = st.columns(3)
            with col1:
                project_start = st.date_input("开始时间", datetime.date.today(), key="project_start")
            with col2:
                project_end = st.date_input("结束时间", datetime.date.today() + datetime.timedelta(days=7), key="project_end")
            with col3:
                project_quota = st.number_input("招募人数", min_value=1, step=1, value=5, key="project_quota")
            
            # 发布项目按钮
            if st.button("🚀 发布项目", use_container_width=True):
                try:
                    project_desc = st.session_state["project_desc_manual"]
                    if not project_name or not project_desc:
                        raise ValueError("项目名称和描述不能为空！")
                    if project_end < project_start:
                        raise ValueError("结束时间不能早于开始时间！")
                    
                    project = {
                        "id": len(st.session_state.volunteer_projects) + 1,
                        "name": project_name,
                        "desc": project_desc,
                        "start": project_start,
                        "end": project_end,
                        "quota": project_quota,
                        "publisher": st.session_state.user_info["username"],
                        "status": "招募中",
                        "signup_list": []
                    }
                    st.session_state.volunteer_projects.append(project)
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "项目发布成功",
                        "content": f"「{project_name}」已发布"
                    })
                    st.success(f"✅ 项目「{project_name}」发布成功！")
                    st.session_state["show_rain_effect"] = True
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
    
    with tab2:
        st.subheader("📊 项目管理")
        if st.session_state.volunteer_projects:
            projects_df = pd.DataFrame(st.session_state.volunteer_projects)
            st.dataframe(projects_df.drop("desc", axis=1), use_container_width=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                project_id = st.number_input("选择项目ID", min_value=1, max_value=len(st.session_state.volunteer_projects), step=1, key="manage_project_id")
            with col2:
                new_status = st.selectbox("修改状态", ["招募中", "进行中", "已结束", "已取消"], key="new_status")
            with col3:
                if st.button("🔄 更新状态", use_container_width=True):
                    try:
                        target = [p for p in st.session_state.volunteer_projects if p["id"] == project_id][0]
                        target["status"] = new_status
                        st.session_state.notifications.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "title": "项目状态更新",
                            "content": f"「{target['name']}」状态已更新为：{new_status}"
                        })
                        st.success(f"✅ 项目「{target['name']}」状态更新成功！")
                    except IndexError:
                        st.error("❌ 项目ID不存在！")
            export_data_module("项目")
            import_data_module("项目")
        else:
            st.info("暂无发布的项目～点击「发布项目」创建第一个项目吧！")
    
    with tab3:
        st.subheader("🤝 需求对接")
        st.write("### 待对接的服务需求")
        if st.session_state.service_demands:
            pending_demands = [d for d in st.session_state.service_demands if d["status"] == "待对接"]
            if pending_demands:
                demands_df = pd.DataFrame(pending_demands)
                st.dataframe(demands_df.drop("desc", axis=1), use_container_width=True)
                
                demand_id = st.number_input("选择需求ID对接", min_value=1, max_value=len(pending_demands), step=1, key="match_demand_id")
                volunteer_name = st.text_input("分配志愿者用户名", key="match_volunteer_name")
                
                if st.button("✅ 确认对接", use_container_width=True):
                    try:
                        target = [d for d in st.session_state.service_demands if d["id"] == demand_id][0]
                        volunteer_exists = any(u["username"] == volunteer_name for u in st.session_state.registered_users if u["role"] == "志愿者")
                        if not volunteer_exists:
                            raise ValueError(f"志愿者「{volunteer_name}」不存在！")
                        
                        target["status"] = "对接中"
                        target["matching_volunteer"] = volunteer_name
                        st.session_state.demand_matching.append({
                            "demand_id": demand_id,
                            "volunteer": volunteer_name,
                            "org": st.session_state.user_info["username"],
                            "match_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.session_state.notifications.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "title": "需求对接成功",
                            "content": f"需求「{target['name']}」已分配给「{volunteer_name}」"
                        })
                        st.success(f"✅ 需求对接成功！")
                    except IndexError:
                        st.error("❌ 需求ID不存在！")
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
            else:
                st.info("暂无待对接的需求～")
        else:
            st.info("暂无服务需求～")
    
    with tab4:
        st.subheader("📈 数据统计")
        col1, col2 = st.columns(2)
        with col1:
            st.write("### 项目状态分布")
            if st.session_state.volunteer_projects:
                status_count = pd.DataFrame(st.session_state.volunteer_projects)["status"].value_counts()
                st.bar_chart(status_count, color="#4CAF50")
            else:
                st.info("暂无项目数据～")
        with col2:
            st.write("### 需求对接统计")
            if st.session_state.service_demands:
                demand_status = pd.DataFrame(st.session_state.service_demands)["status"].value_counts()
                st.pie_chart(demand_status, color=["#4CAF50", "#FF9800", "#F44336"])
            else:
                st.info("暂无需求数据～")
        export_data_module("用户")
        import_data_module("用户")
    
    with tab5:
        workflow_builder()

# ===================== 志愿者端工作台 =====================
def volunteer_dashboard():
    st.header("👨‍💼 志愿者工作台")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["项目报名", "服务时长记录", "我的项目", "需求服务", "工作流搭建"])
    
    with tab1:
        st.subheader("📝 项目报名")
        if st.session_state.volunteer_projects:
            recruit_projects = [p for p in st.session_state.volunteer_projects if p["status"] == "招募中"]
            if recruit_projects:
                projects_df = pd.DataFrame(recruit_projects)
                st.dataframe(projects_df.drop(["desc", "signup_list"], axis=1), use_container_width=True)
                
                project_id = st.number_input("选择项目ID报名", min_value=1, max_value=len(recruit_projects), step=1, key="signup_project_id")
                if st.button("✅ 确认报名", use_container_width=True):
                    try:
                        target = [p for p in st.session_state.volunteer_projects if p["id"] == project_id][0]
                        if target["status"] != "招募中":
                            raise ValueError("该项目已停止招募！")
                        if st.session_state.user_info["username"] in target["signup_list"]:
                            raise ValueError("你已报名该项目！")
                        if len(target["signup_list"]) >= target["quota"]:
                            raise ValueError("该项目招募人数已满！")
                        
                        target["signup_list"].append(st.session_state.user_info["username"])
                        st.session_state.notifications.append({
                            "time": datetime.datetime.now().strftime("%H:%M:%S"),
                            "title": "项目报名成功",
                            "content": f"你已成功报名「{target['name']}」"
                        })
                        st.success(f"✅ 成功报名项目「{target['name']}」！")
                        st.session_state["show_rain_effect"] = True
                    except ValueError as e:
                        st.error(f"❌ {str(e)}")
            else:
                st.info("暂无招募中的项目～")
        else:
            st.info("暂无志愿项目～")
    
    with tab2:
        st.subheader("⏱️ 服务时长记录")
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1:
                project_id = st.number_input("选择服务项目ID", min_value=1, max_value=len(st.session_state.volunteer_projects) if st.session_state.volunteer_projects else 1, step=1, key="hour_project_id")
                hours = st.number_input("服务时长（小时）", min_value=0.5, step=0.5, value=1.0, key="service_hours")
            with col2:
                service_date = st.date_input("服务日期", datetime.date.today(), key="service_date")
                service_note = st.text_input("服务备注", placeholder="如：为3位老人提供送餐服务", key="service_note")
            
            if st.button("📤 提交时长", use_container_width=True):
                try:
                    if not st.session_state.volunteer_projects:
                        raise ValueError("暂无项目可记录时长！")
                    target = [p for p in st.session_state.volunteer_projects if p["id"] == project_id][0]
                    if st.session_state.user_info["username"] not in target["signup_list"]:
                        raise ValueError("你未报名该项目，无法记录时长！")
                    
                    hour_record = {
                        "volunteer": st.session_state.user_info["username"],
                        "project_id": project_id,
                        "project_name": target["name"],
                        "hours": hours,
                        "date": service_date,
                        "note": service_note,
                        "status": "已提交"
                    }
                    st.session_state.volunteer_hours.append(hour_record)
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "时长提交成功",
                        "content": f"「{target['name']}」时长{hours}小时已提交"
                    })
                    st.success(f"✅ 服务时长{hours}小时提交成功！")
                    st.session_state["show_rain_effect"] = True
                except (IndexError, ValueError) as e:
                    st.error(f"❌ {str(e)}")
        
        st.write("### 📋 我的服务时长记录")
        my_hours = [h for h in st.session_state.volunteer_hours if h["volunteer"] == st.session_state.user_info["username"]]
        if my_hours:
            hours_df = pd.DataFrame(my_hours)
            st.dataframe(hours_df, use_container_width=True)
            total_hours = sum([h["hours"] for h in my_hours])
            st.write(f"🏆 累计服务时长：**{total_hours}小时**")
            export_data_module("时长")
            import_data_module("时长")
        else:
            st.info("你暂无服务时长记录～")
    
    with tab3:
        st.subheader("📊 我的项目")
        my_projects = [p for p in st.session_state.volunteer_projects if st.session_state.user_info["username"] in p.get("signup_list", [])]
        if my_projects:
            st.dataframe(pd.DataFrame(my_projects)[["id", "name", "start", "end", "status"]], use_container_width=True)
        else:
            st.info("你暂无已报名的项目～")
    
    with tab4:
        st.subheader("🤝 需求服务")
        st.write("### 分配给我的服务需求")
        my_demands = [d for d in st.session_state.service_demands if d.get("matching_volunteer") == st.session_state.user_info["username"]]
        if my_demands:
            demands_df = pd.DataFrame(my_demands)
            st.dataframe(demands_df.drop("desc", axis=1), use_container_width=True)
            
            demand_id = st.number_input("选择需求ID标记完成", min_value=1, max_value=len(my_demands), step=1, key="finish_demand_id")
            if st.button("✅ 标记为已完成", use_container_width=True):
                try:
                    target = [d for d in st.session_state.service_demands if d["id"] == demand_id][0]
                    if target["matching_volunteer"] != st.session_state.user_info["username"]:
                        raise ValueError("该需求未分配给你！")
                    
                    target["status"] = "已完成"
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "需求服务完成",
                        "content": f"「{target['name']}」已完成"
                    })
                    st.success(f"✅ 需求「{target['name']}」标记为已完成！")
                    st.session_state["show_rain_effect"] = True
                except (IndexError, ValueError) as e:
                    st.error(f"❌ {str(e)}")
        else:
            st.info("暂无分配给你的服务需求～")
    
    with tab5:
        workflow_builder()

# ===================== 被服务人工作台 =====================
def demand_dashboard():
    st.header("🙋 被服务人群工作台")
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["发布需求", "需求跟踪", "服务评价", "我的需求", "工作流搭建"])
    
    with tab1:
        st.subheader("📢 发布服务需求")
        with st.container(border=True):
            demand_name = st.text_input("需求名称", placeholder="如：独居老人日常陪伴", key="demand_name")
            demand_desc = st.text_area("需求描述", placeholder="详细描述需求内容、时间、地点等", height=150, key="demand_desc")
            
            if st.button("✨ AI分析需求", use_container_width=True):
                if demand_desc:
                    ai_result = ai_generate("demand_analysis", demand_desc)
                    with st.expander("📝 AI需求分析结果", expanded=True):
                        st.write(ai_result)
                else:
                    st.error("请先填写需求描述！")
            
            col1, col2 = st.columns(2)
            with col1:
                demand_location = st.text_input("需求地点", placeholder="如：XX社区XX小区", key="demand_location")
            with col2:
                demand_time = st.date_input("期望服务时间", datetime.date.today(), key="demand_time")
            
            if st.button("🚀 发布需求", use_container_width=True):
                try:
                    if not demand_name or not demand_desc:
                        raise ValueError("需求名称和描述不能为空！")
                    
                    demand = {
                        "id": len(st.session_state.service_demands) + 1,
                        "name": demand_name,
                        "desc": demand_desc,
                        "location": demand_location,
                        "expect_time": demand_time,
                        "publisher": st.session_state.user_info["username"],
                        "status": "待对接",
                        "matching_volunteer": ""
                    }
                    st.session_state.service_demands.append(demand)
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "需求发布成功",
                        "content": f"「{demand_name}」已发布，等待组织对接"
                    })
                    st.success(f"✅ 需求「{demand_name}」发布成功！")
                    st.session_state["show_rain_effect"] = True
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
    
    with tab2:
        st.subheader("📊 需求跟踪")
        my_demands = [d for d in st.session_state.service_demands if d["publisher"] == st.session_state.user_info["username"]]
        if my_demands:
            demands_df = pd.DataFrame(my_demands)
            st.dataframe(demands_df.drop("desc", axis=1), use_container_width=True)
            import_data_module("需求")
        else:
            st.info("你暂无发布的需求～")
    
    with tab3:
        st.subheader("⭐ 服务评价")
        finished_demands = [d for d in st.session_state.service_demands if d["publisher"] == st.session_state.user_info["username"] and d["status"] == "已完成"]
        if finished_demands:
            demand_id = st.number_input("选择需求ID评价", min_value=1, max_value=len(finished_demands), step=1, key="eval_demand_id")
            rating = st.slider("满意度评分", 1, 5, 5, key="eval_rating")
            comment = st.text_area("评价内容", placeholder="如：志愿者服务很贴心，解决了我的实际问题", key="eval_comment")
            
            if st.button("✅ 提交评价", use_container_width=True):
                try:
                    target = [d for d in st.session_state.service_demands if d["id"] == demand_id][0]
                    if target["status"] != "已完成":
                        raise ValueError("该需求未完成，无法评价！")
                    
                    st.session_state.notifications.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "title": "评价提交成功",
                        "content": f"你已对「{target['name']}」进行{rating}星评价"
                    })
                    st.success(f"✅ 评价提交成功！感谢你的反馈～")
                except (IndexError, ValueError) as e:
                    st.error(f"❌ {str(e)}")
        else:
            st.info("你暂无已完成的需求可评价～")
    
    with tab4:
        st.subheader("📋 我的需求")
        my_demands = [d for d in st.session_state.service_demands if d["publisher"] == st.session_state.user_info["username"]]
        if my_demands:
            st.dataframe(pd.DataFrame(my_demands)[["id", "name", "status", "expect_time", "location"]], use_container_width=True)
            export_data_module("需求")
        else:
            st.info("你暂无发布的需求～")
    
    with tab5:
        workflow_builder()

# ===================== 主函数 =====================
def main():
    set_custom_style()
    init_session()
    
    if st.session_state.get("show_rain_effect", False):
        rain(
            emoji="🎉",
            font_size=20,
            falling_speed=5,
            animation_length="short",
        )
        st.session_state["show_rain_effect"] = False
    
    st.sidebar.markdown("# 🤝 智能志愿服务智能体")
    auth_module()
    notification_module()
    
    if st.session_state.user_role == "志愿服务组织":
        org_dashboard()
    elif st.session_state.user_role == "志愿者":
        volunteer_dashboard()
    elif st.session_state.user_role == "被服务人群":
        demand_dashboard()
    else:
        st.markdown("# 🤝 智能志愿服务智能体")
        st.markdown("### 一站式志愿服务管理平台")
        st.markdown("#### 支持组织发布项目、志愿者报名服务、被服务人发布需求")
        st.info("请先在左侧栏注册/登录，体验完整功能～")

if __name__ == "__main__":
    main()
