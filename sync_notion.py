import os
import json
import requests
import time

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
    
    # 智能缓存：不仅检查文件存在，还严格检查文件是否完整（大于2KB）
    if os.path.exists(filepath) and os.path.getsize(filepath) > 2048:
        print(f"⏩ [缓存跳过] 图片完整无损: {filename}")
        return filepath.replace("\\", "/")
        
    print(f"⬇️ [死磕抓取] 正在下载并核验: {filename}")
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            r = requests.get(url, stream=True, timeout=30)
            if r.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)
                
                # 核心完整性核查：文件体积必须正常，否则视为下载碎裂
                if os.path.getsize(filepath) > 2048:
                    return filepath.replace("\\", "/")
                else:
                    print(f"⚠️ [核查失败] 文件体积异常，可能已损坏，准备重新下载...")
            else:
                print(f"⚠️ [网络异常] 服务器响应 {r.status_code}，准备重试...")
        except Exception as e:
            print(f"⚠️ [下载卡顿] ({attempt+1}/{max_retries}): {e}")
            
        time.sleep(2) # 失败后冷静2秒再发起冲击
        
    # 终极防线：如果真的下不下来，宁可不更新，也绝不把残缺的网页发出去！
    raise Exception(f"\n❌ 【致命错误】图片 {filename} 连续3次下载失败或损坏！\n为保证作品集展示的绝对完整性，系统已强制熔断抓取任务！\n请稍后在 Actions 中重新运行 (Run workflow)。")

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
    print("🚀 启动中高端商业级抓取与核验引擎...")
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
    print("\n✅ 所有作品数据均已100%核验通过并打包完成！")

if __name__ == "__main__":
    fetch_database()
