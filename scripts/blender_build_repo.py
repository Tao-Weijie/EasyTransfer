import json
import os
import requests
import tomllib  
import hashlib  

ADDON_FOLDER_NAME = "EasyTransfer_blender" 

def get_manifest_data():
    """读取本地 TOML"""
    toml_path = os.path.join(ADDON_FOLDER_NAME, "blender_manifest.toml")
    if not os.path.exists(toml_path):
        raise FileNotFoundError(f"❌ 找不到 TOML: {toml_path}")
    
    with open(toml_path, "rb") as f:
        return tomllib.load(f)

def get_sha256_hash(url):
    """下载文件并计算 SHA256 (流式处理，防止内存溢出)"""
    print(f"   Calculatng hash for: {url} ...")
    sha256_hash = hashlib.sha256()
    try:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=8192):
                sha256_hash.update(chunk)
        return f"sha256:{sha256_hash.hexdigest()}"
    except Exception as e:
        print(f"   ⚠️ Hash calculation failed: {e}")
        return ""

def build_index():
    # --- 1. 读取本地 TOML ---
    manifest = get_manifest_data()
    
    # 提取公共数据
    TOML_VERSION = manifest.get("version")
    EXTENSION_ID = manifest.get("id")
    TYPE = manifest.get("type", "add-on")
    BLENDER_MIN = manifest.get("blender_version_min", "4.2.0")
    
    lic = manifest.get("license", "SPDX:GPL-3.0-or-later")
    LICENSE_LIST = [lic] if isinstance(lic, str) else lic
    
    MAINTAINER = manifest.get("maintainer", "")
    TAGLINE = manifest.get("tagline", "")
    WEBSITE = manifest.get("website", "")
    TAGS = manifest.get("tags", [])
    NAME = manifest.get("name", "EasyTransfer")

    # --- 2. 环境信息 ---
    full_repo = os.environ.get("GITHUB_REPOSITORY", "Tao-Weijie/EasyTransfer")
    current_git_tag = os.environ.get("GITHUB_REF_NAME", "")
    user, repo = full_repo.split("/")

    # --- 3. 获取 Releases ---
    url = f"https://api.github.com/repos/{user}/{repo}/releases"
    print(f"Fetching releases from: {url}")
    
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Error: {resp.status_code} {resp.text}")
        return

    releases = resp.json()
    data_list = []

    # --- 4. 遍历并构建标准格式 ---
    for r in releases:
        release_tag = r["tag_name"]
        
        # 匹配版本号逻辑
        if release_tag == current_git_tag:
            final_version = TOML_VERSION
            print(f"👉 [New] {release_tag} -> {final_version}")
        else:
            final_version = release_tag.lstrip("v")
            print(f"   [Old] {release_tag} -> {final_version}")

        if r["draft"]: continue

        # 寻找 ZIP 资源
        target_asset = None
        for asset in r["assets"]:
            if "blender" in asset["name"].lower() and asset["name"].endswith(".zip"):
                target_asset = asset
                break
        
        if target_asset:
            dl_url = target_asset["browser_download_url"]
            file_size = target_asset["size"] # GitHub API 直接提供大小
            
            # ⚠️ 关键步骤：计算 Hash

            file_hash = get_sha256_hash(dl_url)

            # === 严格对照你提供的标准格式构建 Entry ===
            entry = {
                "id": EXTENSION_ID,
                "name": NAME,
                "tagline": TAGLINE,
                "version": final_version,
                "type": TYPE,
                "archive_size": file_size,  # ✅ 新增：文件大小 (Int)
                "archive_hash": file_hash,  # ✅ 新增：SHA256 Hash
                "archive_url": dl_url,
                "blender_version_min": BLENDER_MIN,
                "maintainer": MAINTAINER,
                "tags": TAGS,
                "license": LICENSE_LIST,    # ✅ 修正：列表格式
                "website": WEBSITE,
                "schema_version": "1.0.0"   # ✅ 条目级 Schema
            }
            data_list.append(entry)

    # --- 5. 生成根 JSON ---
    repo_index = {
        "version": "1",    # 列表 API 版本 (官方通常用 "1")
        "blocklist": [],   # ✅ 新增：黑名单字段 (标准格式要求)
        "data": data_list
    }
    
    with open("index.json", "w", encoding='utf-8') as f:
        json.dump(repo_index, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Generated standard index.json with {len(data_list)} items.")

if __name__ == "__main__":
    build_index()