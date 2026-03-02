import os
import json
import requests

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def download_image(url, filename):
    os.makedirs("images/uploads", exist_ok=True)
    filepath = os.path.join("images/uploads", filename)
    if os.path.exists(filepath):
        print(f"⏩ [缓存跳过] 图片已存在: {filename}")
        return filepath.replace("\\", "/")
        
    print(f"⬇️ [全新抓取] 下载高清图: {filename}")
    try:
        r = requests.get(url, stream=True, timeout=30) # 加入超时防卡死
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        return filepath.replace("\\", "/")
    except Exception as e:
        print(f"❌ [报错] 下载失败 {url}: {e}")
        return ""

# 【史诗级升级一】：突破100块限制的“无限翻页引擎”
def get_all_blocks(block_id):
    blocks = []
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    has_more = True
    next_cursor = None
    
    while has_more:
        params = {"page_size": 100}
        if next_cursor:
            params["start_cursor"] = next_cursor
            
        try:
            response = requests.get(url, headers=HEADERS, params=params).json()
            blocks.extend(response.get("results", []))
            has_more = response.get("has_more", False)
            next_cursor = response.get("next_cursor")
        except Exception as e:
            print(f"获取区块失败: {e}")
            break
            
    return blocks

# 【史诗级升级二】：一比一还原排版的“富文本解析器”
def parse_rich_text(rich_text_list):
    if not rich_text_list: return ""
    html_content = ""
    for rt in rich_text_list:
        text = rt.get("plain_text", "").replace("\n", "<br>")
        annotations = rt.get("annotations", {})
        
        # 还原加粗、斜体、下划线、删除线
        if annotations.get("bold"): text = f"<strong>{text}</strong>"
        if annotations.get("italic"): text = f"<em>{text}</em>"
        if annotations.get("underline"): text = f"<u>{text}</u>"
        if annotations.get("strikethrough"): text = f"<del>{text}</del>"
        
        # 还原超链接
        href = rt.get("href")
        if href: text = f"<a href='{href}' class='underline text-blue-500 hover:text-blue-700 transition-colors' target='_blank'>{text}</a>"
        
        html_content += text
    return html_content

def fetch_database():
    print("🚀 启动中高端商业级抓取引擎...")
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    results = response.json().get("results", [])
    
    works_list = []
    
    for index, row in enumerate(results):
        props = row["properties"]
        page_id = row["id"]
        
        title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "") if props.get("Title", {}).get("title") else ""
        desc = props.get("Desc", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("Desc", {}).get("rich_text") else ""
        
        print(f"\n👉 正在解析作品: 《{title}》")
        
        cover_path = ""
        cover_files = props.get("Cover", {}).get("files", [])
        if cover_files:
            file_obj = cover_files[0]
            cover_url = file_obj.get("file", {}).get("url") or file_obj.get("external", {}).get("url")
            if cover_url: cover_path = download_image(cover_url, f"cover_{page_id}.jpg")
                
        # 核心：抓取所有图文混合区块
        all_blocks = get_all_blocks(page_id)
        content_blocks = []
        img_counter = 1
        
        for block in all_blocks:
            b_type = block["type"]
            
            # 处理图片
            if b_type == "image":
                img_obj = block["image"]
                img_url = img_obj.get("file", {}).get("url") or img_obj.get("external", {}).get("url")
                if img_url:
                    img_path = download_image(img_url, f"content_{page_id}_{img_counter}.jpg")
                    if img_path:
                        content_blocks.append({"type": "image", "src": img_path})
                    img_counter += 1
                    
            # 处理大标题 (H1)
            elif b_type == "heading_1":
                html = parse_rich_text(block["heading_1"]["rich_text"])
                if html: content_blocks.append({"type": "h1", "html": html})
                
            # 处理中标题 (H2/H3)
            elif b_type in ["heading_2", "heading_3"]:
                html = parse_rich_text(block[b_type]["rich_text"])
                if html: content_blocks.append({"type": "h2", "html": html})
                
            # 处理普通正文段落
            elif b_type == "paragraph":
                html = parse_rich_text(block["paragraph"]["rich_text"])
                if html: content_blocks.append({"type": "p", "html": html})
                
            # 处理金句引用 (Quote)
            elif b_type == "quote":
                html = parse_rich_text(block["quote"]["rich_text"])
                if html: content_blocks.append({"type": "quote", "html": html})
                
            # 处理分割线
            elif b_type == "divider":
                content_blocks.append({"type": "divider"})

        works_list.append({
            "id": f"work_{page_id.replace('-', '')}",
            "title": title,
            "desc": desc,
            "cover": cover_path,
            "blocks": content_blocks  # 全新结构：保存了排版顺序的图文数组
        })
        
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump({"worksList": works_list}, f, ensure_ascii=False, indent=2)
    print("\n✅ 所有数据抓取并深度解析完毕！")

if __name__ == "__main__":
    fetch_database()
