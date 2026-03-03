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

def generate_smart_tags(title, desc, content_text):
    if not GEMINI_API_KEY: return []
    prompt = f"""你是一个顶级的餐饮品牌策划总监。请深入阅读以下作品的标题、简介及正文，为其提炼出最核心、最具商业价值的 3 个标签。标签必须高度具体、有锐度，如：贵州烙锅, 云南菜, 空间设计, 老字号年轻化, 包装升级 等。绝对不要生成“品牌策划”等废话。
    规则：只返回 3 个标签，英文逗号分隔，不要带#号。
    标题：{title}\n简介：{desc}\n正文：{content_text[:1500]}"""
    try:
        response = ai_model.generate_content(prompt)
        return [t.strip() for t in response.text.strip().replace('，', ',').split(',') if t.strip()][:3]
    except: return []

def download_image(url, filename):
    os.makedirs("images/uploads", exist_ok=True)
    filepath = os.path.join("images/uploads", filename)
    if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
        original_size = os.path.getsize(filepath)
        if TINYPNG_API_KEY and original_size > 300 * 1024:
            print(f"🗜️ [缓存清洗] 揪出历史遗留大图: {filename}")
            try:
                tinify.from_file(filepath).to_file(filepath)
            except: pass
        return filepath.replace("\\", "/")
        
    max_retries = 3
    download_headers = { "User-Agent": "Mozilla/5.0", "Accept": "image/avif,image/webp,image/*,*/*;q=0.8" }
    for attempt in range(max_retries):
        try:
            r = requests.get(url, stream=True, timeout=30, headers=download_headers)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192): f.write(chunk)
                if os.path.getsize(filepath) > 2048:
                    if TINYPNG_API_KEY and os.path.getsize(filepath) > 300 * 1024:
                        try: tinify.from_file(filepath).to_file(filepath)
                        except: pass
                    return filepath.replace("\\", "/")
        except: time.sleep(2) 
    raise Exception(f"\n❌ 【致命错误】图片 {filename} 下载失败！")

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
        except: break
    return blocks

def extract_text_for_ai(blocks):
    text = ""
    for block in blocks:
        b_type = block["type"]
        if b_type in ["heading_1", "heading_2", "heading_3", "paragraph", "quote"]:
            for rt in block[b_type].get("rich_text", []): text += rt.get("plain_text", "")
            text += "\n"
    return text

def parse_rich_text(rich_text_list):
    if not rich_text_list: return ""
    html_content = ""
    for rt in rich_text_list:
        text = rt.get("plain_text", "").replace("\n", "<br>")
        ann = rt.get("annotations", {})
        if ann.get("bold"): text = f"<strong>{text}</strong>"
        if ann.get("italic"): text = f"<em>{text}</em>"
        if ann.get("underline"): text = f"<u>{text}</u>"
        if ann.get("strikethrough"): text = f"<del>{text}</del>"
        href = rt.get("href")
        if href: text = f"<a href='{href}' class='underline text-blue-500 hover:text-blue-700' target='_blank'>{text}</a>"
        html_content += text
    return html_content

def fetch_database():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    results = response.json().get("results", [])
    works_list = []
    
    for row in results:
        props = row["properties"]
        page_id = row["id"]
        title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "") if props.get("Title", {}).get("title") else ""
        desc = props.get("Desc", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("Desc", {}).get("rich_text") else ""
        
        # 🚀 读取排序字段 (默认 999 垫底)
        sort_prop = props.get("排序", props.get("Sort", {}))
        sort_order = 999
        if sort_prop and "number" in sort_prop and sort_prop["number"] is not None:
            sort_order = int(sort_prop["number"])
            
        # 🚀 读取精选状态 (Checkbox)
        featured_prop = props.get("精选", props.get("Featured", {}))
        is_featured = False
        if featured_prop and "checkbox" in featured_prop:
            is_featured = bool(featured_prop["checkbox"])

        print(f"\n👉 解析: 《{title}》 | 排序: {sort_order} | 精选: {is_featured}")
        
        cover_path = ""
        cover_files = props.get("Cover", {}).get("files", [])
        if cover_files:
            cover_url = cover_files[0].get("file", {}).get("url") or cover_files[0].get("external", {}).get("url")
            if cover_url: cover_path = download_image(cover_url, f"cover_{page_id}.jpg")
        
        all_blocks = get_all_blocks(page_id)
        smart_tags = generate_smart_tags(title, desc, extract_text_for_ai(all_blocks))

        content_blocks = []
        img_counter = 1
        for block in all_blocks:
            b_type = block["type"]
            if b_type == "image":
                img_url = block["image"].get("file", {}).get("url") or block["image"].get("external", {}).get("url")
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
            "sort": sort_order,      # 写入JSON
            "featured": is_featured, # 写入JSON
            "blocks": content_blocks
        })
        
    # 🚀 核心：按照数字进行绝对排序 (数字越小越靠前，没填的999排最后)
    works_list.sort(key=lambda x: x["sort"])
    
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump({"worksList": works_list}, f, ensure_ascii=False, indent=2)
    print("\n✅ 数据排序并打包完成！")

if __name__ == "__main__":
    fetch_database()
