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
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
        return filepath.replace("\\", "/")
    except Exception as e:
        print(f"下载失败 {url}: {e}")
        return ""

def get_blocks(block_id):
    url = f"https://api.notion.com/v1/blocks/{block_id}/children"
    response = requests.get(url, headers=HEADERS)
    return response.json().get("results", [])

def fetch_database():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    response = requests.post(url, headers=HEADERS)
    results = response.json().get("results", [])
    
    works_list = []
    
    for index, row in enumerate(results):
        props = row["properties"]
        page_id = row["id"]
        
        # 抓取标题
        title = props.get("Title", {}).get("title", [{}])[0].get("plain_text", "") if props.get("Title", {}).get("title") else ""
        # 抓取简介
        desc = props.get("Desc", {}).get("rich_text", [{}])[0].get("plain_text", "") if props.get("Desc", {}).get("rich_text") else ""
        
        # 下载封面图
        cover_path = ""
        cover_files = props.get("Cover", {}).get("files", [])
        if cover_files:
            file_obj = cover_files[0]
            cover_url = file_obj.get("file", {}).get("url") or file_obj.get("external", {}).get("url")
            if cover_url:
                cover_path = download_image(cover_url, f"cover_{page_id}.jpg")
                
        # 抓取正文里的几十张排版图
        blocks = get_blocks(page_id)
        content_images = []
        img_counter = 1
        for block in blocks:
            if block["type"] == "image":
                img_obj = block["image"]
                img_url = img_obj.get("file", {}).get("url") or img_obj.get("external", {}).get("url")
                if img_url:
                    img_path = download_image(img_url, f"content_{page_id}_{img_counter}.jpg")
                    if img_path:
                        content_images.append(img_path)
                    img_counter += 1
        
        works_list.append({
            "id": f"work{index}",
            "title": title,
            "desc": desc,
            "cover": cover_path,
            "images": content_images # 把所有的切片图全部存起来
        })
        
    with open("works.json", "w", encoding="utf-8") as f:
        json.dump({"worksList": works_list}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    fetch_database()
