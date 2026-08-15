# 🐷 AutoPig Studio (量产小猪工坊)

基于 FastAPI + Vue 3 的自动化批量小猪角色生成工作台。严格根据原型参考图保持画风一致，全自动构思主题、批量云端渲染、实时微调并一键导出。

---

## ✨ 核心特性

- 🎨 **画风严格锁定**：基于基准原型图（四足趴卧姿态、手绘矢量风格）进行二次创作，避免变形走样。
- ⚡ **智能量产策划**：AI 全自动策划趣味角色特征，内置自动去重机制，避免生成重复主题。
- 🔍 **智能网络嗅探**：本地网络代理端口自动侦测（支持 Clash、v2ray 等），无需复杂手动网络配置。
- 💾 **资产闭环管理**：支持单张微调重绘、即时保存、本地图库多维度浏览与一键管理。
- 📦 **免安装绿色便携**：Windows 解压即用，内置独立 Python 运行环境。

---

## 🚀 快速开始

### 方式一：下载绿色发布包（推荐，开箱即用）

1. 前往 [Releases 页面](../../releases) 下载最新的 `AutoPig-Studio-v1.0.0-Windows.zip`。
2. 解压压缩包到任意英文路径文件夹。
3. 双击运行 **`start.bat`**，程序将自动启动并在浏览器中打开控制台。
4. 前往「API与高级设置」填入你的 API Key 与 Base URL，点击「测试连接状态」，验证通过即可开始使用。

---

### 方式二：从源码运行

```bash
# 1. 克隆代码仓库
git clone [https://github.com/Gusare124/AutoPig-Studio.git](https://github.com/Gusare124/AutoPig-Studio.git)
cd AutoPig-Studio

# 2. 创建并激活虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 3. 安装项目依赖
pip install fastapi uvicorn openai pillow requests

# 4. 启动服务
python app.py
