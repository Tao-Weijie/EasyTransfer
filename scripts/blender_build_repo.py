import json
import os
import requests
import tomllib  # Python 3.11


# 1. 你的插件源代码文件夹名字 (存放 blender_manifest.toml 的地方)
ADDON_FOLDER_NAME = "EasyTransfer_blender" 


def get_manifest_data():
    """读取本地的 blender_manifest.toml 文件"""
    toml_path = os.path.join(ADDON_FOLDER_NAME, "blender_manifest.toml")
    
    if not os.path.exists(toml_path):
        raise FileNotFoundError(f"❌ 找不到 TOML 文件: {toml_path}。请检查脚本里的 ADDON_FOLDER_NAME 配置。")
    
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
        print(f"✅ 成功读取 TOML: {data.get('id')} (v{data.get('version')})")
        return data

def build_index():
    # --- 1. 读取 TOML 元数据 ---
    manifest = get_manifest_data()
    
    VERSION = manifest.get("version")
    NAME = manifest.get("name")
    EXTENSION_ID = manifest.get("id")
    TYPE = manifest.get("type", "add-on")
    BLENDER_MIN = manifest.get("blender_version_min", "4.2.0")
    LICENSE = manifest.get("license", "SPDX:GPL-3.0-or-later")
    MAINTAINER = manifest.get("maintainer", "")
    TAGLINE = manifest.get("tagline", "")
    WEBSITE = manifest.get("website", "")
    TAGS = manifest.get("tags", [])

    # --- 2. 获取 GitHub 仓库信息 ---
    full_repo = os.environ.get("GITHUB_REPOSITORY")
    if full_repo:
        user, repo = full_repo.split("/")
    else:
        user = "Tao-Weijie"
        repo = "EasyTransfer"

    # --- 3. 请求 GitHub API ---
    url = f"https://api.github.com/repos/{user}/{repo}/releases"
    print(f"Fetching releases from: {url}")
    
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error fetching releases: {resp.status_code} {resp.text}")
        return

    releases = resp.json()
    data_list = []

    # --- 4. 遍历 Releases ---
    for r in releases:
        # 跳过 Draft
        if r["draft"]: continue

        # 寻找 ZIP 附件
        dl_url = None
        asset_date = r["published_at"]
        
        for asset in r["assets"]:
            # 匹配逻辑：名字含 blender 且是 zip
            if "blender" in asset["name"].lower() and asset["name"].endswith(".zip"):
                dl_url = asset["browser_download_url"]
                break
        
        if dl_url:
            # 组装条目：使用 TOML 的静态数据 + Release 的动态数据
            entry = {
                "id": EXTENSION_ID,
                "name": NAME,
                "version": VERSION, # 版本号来自 GitHub Tag
                "type": TYPE,
                "archive_url": dl_url,
                "blender_version_min": BLENDER_MIN, # 来自 TOML
                "license": LICENSE,              
                "schema_version": "1.0.0"
            }

            # 可选字段 (如果 TOML 里有就加上)
            if MAINTAINER: entry["maintainer"] = MAINTAINER
            if TAGLINE: entry["tagline"] = TAGLINE
            if WEBSITE: entry["website"] = WEBSITE
            if TAGS: entry["tags"] = TAGS
            
            data_list.append(entry)

    # --- 5. 生成 index.json ---
    repo_index = {
        "version": "v1",
        "url": f"https://{user}.github.io/{repo}/index.json",
        "data": data_list
    }
    
    with open("index.json", "w", encoding='utf-8') as f:
        json.dump(repo_index, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully generated index.json with {len(data_list)} versions.")

if __name__ == "__main__":
    build_index()