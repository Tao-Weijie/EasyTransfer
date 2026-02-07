import json
import os
import requests


full_repo = os.environ.get("GITHUB_REPOSITORY")
if full_repo:
    user, repo = full_repo.split("/")
else:
    # 本地测试时的默认值 (请修改为你自己的)
    user = "Tao-Weijie"
    repo = "EasyTransfer"

# 2. 配置你的插件 ID (必须与 blender_manifest.toml 里的一致！)
EXTENSION_ID = "easy_transfer" 

def build_index():
    url = f"https://api.github.com/repos/{user}/{repo}/releases"
    print(f"Fetching releases from: {url}")
    
    resp = requests.get(url)
    if resp.status_code != 200:
        print("Error fetching releases:", resp.text)
        return

    releases = resp.json()
    versions = []

    for r in releases:
        tag = r["tag_name"]
        # 去掉 'v' 前缀: v0.1.0 -> 0.1.0
        ver_num = tag.lstrip("v")
        
        # 找 Blender 的 ZIP 包
        dl_url = None
        for asset in r["assets"]:
            # 这里的判断逻辑是：文件名包含 'blender' 且是 zip
            if "blender" in asset["name"].lower() and asset["name"].endswith(".zip"):
                dl_url = asset["browser_download_url"]
                break
        
        if dl_url:
            versions.append({
                "id": EXTENSION_ID,
                "version": ver_num,
                "archive_url": dl_url
            })

    # --- 关键修改：添加头部信息以通过 Blender 验证 ---
    repo_data = {
        "schema_version": "1.0.0",
        "url": f"https://{user}.github.io/{repo}/index.json",
        "data": versions
    }
    
    # 写入文件
    with open("index.json", "w") as f:
        json.dump(repo_data, f, indent=2)
    print("index.json created successfully!")

if __name__ == "__main__":
    build_index()