import os
import json
import requests
import time
# 引入 TinyPNG 官方引擎
import tinify

# 获取保险箱里的钥匙
NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
TINYPNG_API_KEY = os.environ.get("TINYPNG_API_KEY")

# 如果配了钥匙，就激活 TinyPNG
if TINYPNG_API_KEY:
    tinify.key = TINYPNG_API_KEY

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def download_image(url, filename):
    os.makedirs("images/uploads", exist_ok=True)
    filepath = os.path.join("images/uploads", filename)
    
    if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
        print(f"⏩ [缓存跳过] 图片完整无损: {filename}")
        return filepath.replace("\\", "/")
        
    print(f"⬇️ [抓取] 正在下载: {filename}")
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
                
                # ==========================================
                # 🚀 核心：自动化 TinyPNG 压缩引擎介入
                # ==========================================
                if os.path.getsize(filepath) > 2048:
                    if TINYPNG_API_KEY:
                        original_size = os.path.getsize(filepath)
                        # 智能阀门：只压缩大于 300KB 的大图，保护免费额度
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
    print("🚀 启动高端商业级抓取与核验引擎 (含 TinyPNG 自动化压缩)...")
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
            "cover": cover_path,
            "blocks": content_blocks
        })
        
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump({"worksList": works_list}, f, ensure_ascii=False, indent=2)
    print("\n✅ 所有数据已100%抓取并自动化压缩完毕！")

if __name__ == "__main__":
    fetch_database()
