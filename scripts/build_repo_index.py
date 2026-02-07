import json
import os
import requests

# 配置你的信息
GITHUB_USER = "Tao-Weijie"
GITHUB_REPO = "EasyTransfer"
EXTENSION_ID = "easy_transfer"

def get_releases():
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/releases"
    headers = {"Accept": "application/vnd.github.v3+json"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def build_index():
    releases = get_releases()
    versions = []

    for release in releases:
        tag = release["tag_name"]
        # 假设 tag 是 "v0.1.0"，我们需要 "0.1.0"
        version_number = tag.lstrip("v")
        
        # 寻找附件中的 ZIP 文件
        download_url = None
        for asset in release["assets"]:
            if asset["name"].endswith(".zip"):
                download_url = asset["browser_download_url"]
                break
        
        if not download_url:
            continue

        # 构建 Blender 仓库格式的条目
        entry = {
            "id": EXTENSION_ID,
            "version": version_number,
            "archive_url": download_url,
            # 这里可以添加更多 toml 里的信息，Blender 会读取
        }
        versions.append(entry)

    # 仓库 JSON 结构
    repo_data = {
        "data": versions
    }

    # 写入 index.json
    with open("index.json", "w") as f:
        json.dump(repo_data, f, indent=2)
    print("index.json created successfully.")

if __name__ == "__main__":
    build_index()