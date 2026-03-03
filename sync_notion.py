import os
import json
import requests
import time
import tinify
import google.generativeai as genai

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
TINYPNG_API_KEY = os.environ.get("TINYPNG_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if TINYPNG_API_KEY:
    tinify.key = TINYPNG_API_KEY

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def generate_smart_tags(title, desc):
    if not GEMINI_API_KEY or not title:
        return ["品牌全案", "视觉设计", "商业落地"]
    
    prompt = f"""
    你是一个资深的餐饮品牌策划总监。
    请分析以下作品的标题和简介，为其提取最核心、最具商业价值的 3 个标签。
    例如：空间设计, 老字号年轻化, 云南菜, 包装升级, IP打造 等。
    【规则】：只返回 3 个词，用英文逗号分隔，不要有任何多余的废话。
    标题：{title}
    简介：{desc}
    """
    try:
        response = ai_model.generate_content(prompt)
        tags_text = response.text.strip().replace('，', ',')
        tags = [t.strip() for t in tags_text.split(',') if t.strip()]
        return tags[:3]
    except Exception as e:
        print(f"⚠️ [AI 大脑罢工]: {e}")
        return ["品牌策划", "视觉统筹", "商业设计"]

def download_image(url, filename):
    os.makedirs("images/uploads", exist_ok=True)
    filepath = os.path.join("images/uploads", filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
        original_size = os.path.getsize(filepath)
        if TINYPNG_API_KEY and original_size > 300 * 1024:
            print(f"🗜️ [缓存清洗] 揪出历史遗留大图: {filename}，原大小: {original_size / 1024:.1f} KB")
            try:
                source = tinify.from_file(filepath)
                source.to_file(filepath)
                new_size = os.path.getsize(filepath)
                print(f"✅ [补压成功] 历史大图完美瘦身！现大小: {new_size / 1024:.1f} KB (减重 {100 - (new_size/original_size)*100:.1f}%)")
            except Exception as e:
                print(f"⚠️ [补压异常] 压缩服务连接失败，安全保留原图: {e}")
        else:
            print(f"⏩ [缓存跳过] 图片完整且体积极其健康: {filename}")
        return filepath.replace("\\", "/")
        
    print(f"⬇️ [抓取] 正在下载新图: {filename}")
    max_retries = 3
    
    download_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
    }
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, stream=True, timeout=30, headers=download_headers)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                
                if os.path.getsize(filepath) > 2048:
                    if TINYPNG_API_KEY:
                        original_size = os.path.getsize(filepath)
                        if original_size > 300 * 1024:
                            print(f"🗜️ [TinyPNG] 触发无损压缩！原图大小: {original_size / 1024:.1f} KB")
                            try:
                                source = tinify.from_file(filepath)
                                source.to_file(filepath)
                                new_size = os.path.getsize(filepath)
                                print(f"✅ [TinyPNG] 压缩成功！压后大小: {new_size / 1024:.1f} KB (瘦身了 {100 - (new_size/original_size)*100:.1f}%)")
                            except Exception as e:
                                print(f"⚠️ [TinyPNG] 压缩服务异常，安全回退至原图: {e}")
                    return filepath.replace("\\", "/")
                else:
                    print(f"⚠️ [核查失败] 文件体积异常，准备重新下载...")
            else:
                print(f"⚠️ [网络异常] 服务器拒绝响应 {r.status_code}，准备重试...")
        except Exception as e:
            print(f"⚠️ [下载卡顿] ({attempt+1}/{max_retries}): {e}")
            
        time.sleep(2) 
        
    raise Exception(f"\n❌ 【致命错误】图片 {filename} 连续3次下载失败或损坏！")

def get_all_blocks(block_id):
    blocks = []
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    has_more = True
    next_cursor = None
    while has_more:
        params = {"page_size": 100}
        if next_cursor: params["start_cursor"] = next_cursor
        try:
            response = requests.get(url, headers=HEADERS, params=params).json()
            blocks.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")
        except Exception as e:
            print(f"获取区块失败: {e}")
            break
    return blocks

def parse_rich_text(rich_text_list):
    if not rich_text_list: return ""
    html_content = ""
    for rt in rich_text_list:
        text = rt.get("plain_text", "").replace("\n", "<br>")
        annotations = rt.get("annotations", {})
        if annotations.get("bold"): text = f"<strong>{text}</strong>"
        if annotations.get("italic"): text = f"<em>{text}</em>"
        if annotations.get("underline"): text = f"<u>{text}</u>"
        if annotations.get("strikethrough"): text = f"<del>{text}</del>"
        href = rt.get("href")
        if href: text = f"<a href='{href}' class='underline text-blue-500 hover:text-blue-700 transition-colors' target='_blank'>{text}</a>"
        html_content += text
    return html_content

def fetch_database():
    print("🚀 启动高端商业级抓取与核验引擎 (含 TinyPNG & Gemini AI)...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    results = response.json().get("results", [])
    works_list = []
    
    for index, row in enumerate(results):
        props = row["properties"]
        page_id = row["id"]
        title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "") if props.get("Title", {}).get("title") else ""
        desc = props.get("Desc", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("Desc", {}).get("rich_text") else ""
        
        print(f"\n👉 正在解析并核验作品: 《{title}》")
        
        cover_path = ""
        cover_files = props.get("Cover", {}).get("files", [])
        if cover_files:
            file_obj = cover_files[0]
            cover_url = file_obj.get("file", {}).get("url") or file_obj.get("external", {}).get("url")
            if cover_url: cover_path = download_image(cover_url, f"cover_{page_id}.jpg")
        
        # 🤖 召唤 Gemini 进行深度语义分析打标
        print(f"🧠 [AI 分析] 正在为《{title}》提炼商业标签...")
        smart_tags = generate_smart_tags(title, desc)
        print(f"🏷️ [AI 标签] 提炼完成: {smart_tags}")

        all_blocks = get_all_blocks(page_id)
        content_blocks = []
        img_counter = 1
        
        for block in all_blocks:
            b_type = block["type"]
            if b_type == "image":
                img_obj = block["image"]
                img_url = img_obj.get("file", {}).get("url") or img_obj.get("external", {}).get("url")
                if img_url:
                    img_path = download_image(img_url, f"content_{page_id}_{img_counter}.jpg")
                    if img_path: content_blocks.append({"type": "image", "src": img_path})
                    img_counter += 1
            elif b_type == "heading_1":
                html = parse_rich_text(block["heading_1"]["rich_text"])
                if html: content_blocks.append({"type": "h1", "html": html})
            elif b_type in ["heading_2", "heading_3"]:
                html = parse_rich_text(block[b_type]["rich_text"])
                if html: content_blocks.append({"type": "h2", "html": html})
            elif b_type == "paragraph":
                html = parse_rich_text(block["paragraph"]["rich_text"])
                if html: content_blocks.append({"type": "p", "html": html})
            elif b_type == "quote":
                html = parse_rich_text(block["quote"]["rich_text"])
                if html: content_blocks.append({"type": "quote", "html": html})
            elif b_type == "divider":
                content_blocks.append({"type": "divider"})

        works_list.append({
            "id": f"work_{page_id.replace('-', '')}",
            "title": title,
            "desc": desc,
            "tags": smart_tags,
            "cover": cover_path,
            "blocks": content_blocks
        })
        
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump({"worksList": works_list}, f, ensure_ascii=False, indent=2)
    print("\n✅ 所有数据已100%抓取并自动化处理完毕！")

if __name__ == "__main__":
    fetch_database()
