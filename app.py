import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import base64
import io
import json
import re
import shutil
import socket
import time
import traceback
import requests
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from openai import OpenAI

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

CONFIG_FILE = "config.json"

def auto_detect_proxy() -> str:
    """智能自动探测本地代理端口与系统代理"""
    for env_key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
        if os.environ.get(env_key):
            return os.environ.get(env_key)
    
    common_ports = [7897, 7890, 10809, 10808, 20811]
    for port in common_ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.15)
                if s.connect_ex(('127.0.0.1', port)) == 0:
                    return f"http://127.0.0.1:{port}"
        except Exception:
            pass
    return ""

DEFAULT_CONFIG = {
    "api_key": "",
    "base_url": "https://api.apifast.tech/v1",
    "proxy": "auto",
    "base_img_path": "pig_hero.png",
    "output_dir": "./output_pigs",
    "text_model": "gemini-2.5-flash",
    "image_model": "gemini-3.1-flash-image-preview",
}

def load_config():
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    return cfg

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

config = load_config()
os.makedirs(config["output_dir"], exist_ok=True)
os.makedirs("static", exist_ok=True)

app = FastAPI(title="AutoPig Studio")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_client(custom_cfg=None):
    cfg = custom_cfg or config
    proxy_val = cfg.get("proxy", "auto")
    
    if proxy_val == "auto" or not proxy_val:
        active_proxy = auto_detect_proxy()
    else:
        active_proxy = proxy_val

    if active_proxy:
        os.environ["HTTP_PROXY"] = active_proxy
        os.environ["HTTPS_PROXY"] = active_proxy
    else:
        os.environ.pop("HTTP_PROXY", None)
        os.environ.pop("HTTPS_PROXY", None)
    
    return OpenAI(
        api_key=cfg["api_key"] or os.environ.get("OPENAI_API_KEY", "EMPTY"),
        base_url=cfg["base_url"],
    )

def classify_models(model_ids: list[str]) -> dict:
    """智能分析扫描到的模型列表，自动识别并推荐生图模型与策划文本模型"""
    img_keywords = ["image", "dall-e", "flux", "imagen", "diffusion", "sd"]
    
    # 图像模型匹配优先级
    rec_image = None
    image_candidates = [m for m in model_ids if any(k in m.lower() for k in img_keywords)]
    
    for pref in ["gemini-3.1-flash-image-preview", "gemini-3.1-flash-image", "gemini-3-pro-image-preview", "dall-e-3", "flux"]:
        for m in model_ids:
            if pref in m.lower():
                rec_image = m
                break
        if rec_image:
            break
    if not rec_image and image_candidates:
        rec_image = image_candidates[0]

    # 策划文本模型匹配优先级
    text_priority = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gpt-4o-mini", "gpt-4o", "deepseek-chat", "claude-3-5-haiku"]
    rec_text = None
    for pref in text_priority:
        for m in model_ids:
            if pref in m.lower():
                rec_text = m
                break
        if rec_text:
            break
    if not rec_text:
        text_cands = [m for m in model_ids if m not in image_candidates]
        rec_text = text_cands[0] if text_cands else (model_ids[0] if model_ids else "gemini-2.5-flash")

    return {
        "all_models": model_ids,
        "recommended_text": rec_text or "gemini-2.5-flash",
        "recommended_image": rec_image or "gemini-3.1-flash-image-preview"
    }

def decode_image_data(text: str) -> Image.Image:
    b64_match = re.search(r'data:image/[^;]+;base64,([A-Za-z0-9+/=\s]+)', text)
    if b64_match:
        raw = re.sub(r'[\s\)\_]+', '', b64_match.group(1))
        raw += '=' * ((4 - len(raw) % 4) % 4)
        return Image.open(io.BytesIO(base64.b64decode(raw)))

    url_match = re.search(r'!\[.*?\]\((https?://[^\s\)]+)\)', text)
    if url_match:
        r = requests.get(url_match.group(1), timeout=30)
        return Image.open(io.BytesIO(r.content))

    try:
        clean = re.sub(r'[\s\)\_]+', '', text)
        clean += '=' * ((4 - len(clean) % 4) % 4)
        return Image.open(io.BytesIO(base64.b64decode(clean)))
    except Exception:
        return None

# ================= 接口路由 =================

@app.get("/api/hero-image")
def get_hero_image_api():
    base_img = config.get("base_img_path", "pig_hero.png")
    if os.path.exists(base_img):
        return FileResponse(base_img)
    return JSONResponse(status_code=404, content={"message": "Hero image not found"})

@app.get("/api/oink-sound")
def get_oink_sound_api():
    sound_path = "oink.wav"
    if os.path.exists(sound_path):
        return FileResponse(sound_path, media_type="audio/wav")
    return JSONResponse(status_code=404, content={"message": "Sound file not found"})

@app.get("/api/config")
def get_config_api():
    cfg = load_config()
    cfg["detected_proxy"] = auto_detect_proxy() or "直连 (未检测到本地代理)"
    return cfg

@app.post("/api/config")
def save_config_api(cfg: dict):
    global config
    config.update(cfg)
    save_config(config)
    os.makedirs(config["output_dir"], exist_ok=True)
    return {"status": "ok", "config": config}

@app.post("/api/test-connection")
def test_connection_api(cfg: dict):
    try:
        client = get_client(cfg)
        start_t = time.time()
        models_data = client.models.list()
        latency = int((time.time() - start_t) * 1000)
        model_ids = [m.id for m in models_data.data]
        classification = classify_models(model_ids)
        return {
            "status": "success",
            "latency": latency,
            "models_count": len(model_ids),
            "models": model_ids,
            "recommended_text": classification["recommended_text"],
            "recommended_image": classification["recommended_image"]
        }
    except Exception as e:
        err_trace = traceback.format_exc()
        return {
            "status": "error",
            "message": str(e),
            "log": f"【错误类型】: {type(e).__name__}\n【错误详情】: {str(e)}\n\n【完整调用栈日志】:\n{err_trace}"
        }

@app.post("/api/generate-plan")
def generate_plan_api(payload: dict):
    count = int(payload.get("count", 3))
    style_vibe = payload.get("style_vibe", "趣味职业与生活角色")
    
    existing = []
    if os.path.exists(config["output_dir"]):
        for f in os.listdir(config["output_dir"]):
            if f.startswith("pig_") and f.endswith(".png"):
                slug = re.sub(r'_\d+$', '', f[4:-4])
                existing.append(slug)
    
    exclude_text = f"请勿重复或相似以下已有主题：{', '.join(set(existing))}。" if existing else ""
    
    system_prompt = (
        "你是顶级游戏美术设计师。构思小猪主题，仅返回纯JSON数组格式，严禁返回任何Markdown标签或额外文字。\n"
        "每个对象包含：\n"
        "- theme: 中文主题名\n"
        "- features: 1-2个极其简洁明确的中文特征道具\n"
        "- slug: 适合作为文件名的英文简短单词 (如 pirate, chef)"
    )
    user_prompt = f"请设计 {count} 个视觉特征鲜明但配饰极简的小猪角色。风格偏好：{style_vibe}。{exclude_text}"

    client = get_client()
    chosen_text_model = config.get("text_model", "gemini-2.5-flash")
    models_to_try = [chosen_text_model]
    for m in ["gemini-2.5-flash", "gemini-2.0-flash", "gpt-4o-mini", "gemini-3-flash-preview"]:
        if m not in models_to_try:
            models_to_try.append(m)
    
    last_err = None
    for model in models_to_try:
        try:
            res = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.85
            )
            content = res.choices[0].message.content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                content = "\n".join(lines).strip()

            tasks = json.loads(content)
            return {"status": "ok", "tasks": tasks}
        except Exception as e:
            last_err = e
            continue

    return JSONResponse(status_code=500, content={"status": "error", "message": f"策划失败: {str(last_err)}"})

@app.post("/api/render-image")
def render_image_api(payload: dict):
    theme = payload.get("theme")
    features = payload.get("features")
    extra_feedback = payload.get("extra_feedback", "")
    
    base_img_path = config.get("base_img_path", "pig_hero.png")
    if not os.path.exists(base_img_path):
        return JSONResponse(status_code=400, content={"status": "error", "message": f"基准参考图 '{base_img_path}' 不存在！"})

    with open(base_img_path, "rb") as f:
        hero_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        f"请为参考图中的这只小猪设计【{theme}】造型（带有简单的{features}）。\n"
        f"严格要求：\n"
        f"1. 必须完全基于原图小猪进行创作，保持小猪趴卧的四足动物形态与原图相同的浅色调配色，严禁画成双腿站立的人物姿态。\n"
        f"2. 保持与参考图一致的二维手绘矢量画风。\n"
        f"3. 装饰配饰保持极简点缀，不要过于复杂繁琐。\n"
        f"4. 背景为纯白色，无任何背景场景。"
    )
    if extra_feedback:
        prompt += f"\n5. 额外微调修改要求：{extra_feedback}"

    client = get_client()
    chosen_image_model = config.get("image_model", "gemini-3.1-flash-image-preview")
    models_to_try = [chosen_image_model]
    for m in ["gemini-3.1-flash-image-preview", "gemini-3.1-flash-image", "gemini-3-pro-image-preview", "dall-e-3"]:
        if m not in models_to_try:
            models_to_try.append(m)
    
    for m in models_to_try:
        try:
            resp = client.chat.completions.create(
                model=m,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{hero_b64}"}}
                        ]
                    }
                ]
            )
            raw = resp.choices[0].message.content
            img = decode_image_data(raw)
            if img:
                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                return {"status": "ok", "image_b64": f"data:image/png;base64,{img_str}"}
        except Exception:
            continue

    return JSONResponse(status_code=500, content={"status": "error", "message": "图像生成失败，请检查提示词或模型通道"})

@app.post("/api/save-image")
def save_image_api(payload: dict):
    slug = payload.get("slug", "custom")
    img_b64 = payload.get("image_b64", "")
    
    if not img_b64:
        return JSONResponse(status_code=400, content={"status": "error", "message": "无图片数据"})

    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]
    
    img_bytes = base64.b64decode(img_b64)
    out_dir = config["output_dir"]
    os.makedirs(out_dir, exist_ok=True)
    
    base_name = f"pig_{slug}"
    save_path = os.path.join(out_dir, f"{base_name}.png")
    counter = 2
    while os.path.exists(save_path):
        save_path = os.path.join(out_dir, f"{base_name}_{counter}.png")
        counter += 1

    with open(save_path, "wb") as f:
        f.write(img_bytes)

    return {"status": "ok", "filename": os.path.basename(save_path), "path": save_path}

@app.post("/api/delete-image")
def delete_image_api(payload: dict):
    filename = payload.get("filename")
    if not filename:
        return JSONResponse(status_code=400, content={"status": "error", "message": "缺少文件名"})
    
    target_path = os.path.join(config["output_dir"], filename)
    if os.path.exists(target_path):
        try:
            os.remove(target_path)
            return {"status": "ok"}
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})
    return JSONResponse(status_code=404, content={"status": "error", "message": "文件不存在"})

@app.get("/api/gallery")
def get_gallery_api():
    out_dir = config["output_dir"]
    if not os.path.exists(out_dir):
        return {"images": []}
    
    images = []
    for f in sorted(os.listdir(out_dir), reverse=True):
        if f.endswith(".png") or f.endswith(".jpg"):
            path = os.path.join(out_dir, f)
            with open(path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            images.append({
                "filename": f,
                "data": f"data:image/png;base64,{b64}",
                "size": f"{os.path.getsize(path) / 1024:.1f} KB"
            })
    return {"images": images}

@app.post("/api/upload-base-img")
async def upload_base_img_api(file: UploadFile = File(...)):
    dest_path = "pig_hero.png"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    config["base_img_path"] = dest_path
    save_config(config)
    return {"status": "ok", "path": dest_path}

app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)