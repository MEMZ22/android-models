import os
import re
import json
import requests
import shutil
from packaging import version
from urllib.parse import urljoin

def load_repositories(config_path='repo.json'):
    """加载仓库配置文件"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"配置文件 {config_path} 不存在")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)['repositories']

def get_local_version(file_path, version_pattern):
    """从本地文件名提取版本号"""
    if not os.path.exists(file_path):
        return None
    
    match = re.search(version_pattern, os.path.basename(file_path))
    if match:
        return match.group(1)
    return None

def get_latest_release(repo):
    """从GitHub API获取最新release信息"""
    api_url = f"https://api.github.com/repos/{repo}/releases/latest"
    response = requests.get(api_url)
    response.raise_for_status()
    return response.json()

def find_asset_url(release, asset_pattern):
    """根据模式查找release中的资产URL"""
    for asset in release['assets']:
        if re.search(asset_pattern, asset['name']):
            return asset['browser_download_url']
    return None

def download_file(url, save_path):
    """下载文件"""
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(save_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return save_path

def update_repository(repo_config):
    """更新单个仓库"""
    try:
        repo = repo_config['github_repo']
        local_file = repo_config['local_file']
        version_pattern = repo_config['version_pattern']
        asset_pattern = repo_config.get('asset_pattern', version_pattern)
        repo_name = repo_config['name']
        
        print(f"\n=== 检查 {repo_name} 更新 ===")
        
        # 获取本地版本
        local_ver_str = get_local_version(local_file, version_pattern)
        if not local_ver_str:
            print(f"未找到本地文件 {local_file} 或无法提取版本号")
            return False
        local_ver = version.parse(local_ver_str)
        print(f"本地版本: {local_ver}")
        
        # 获取最新release
        print("正在检查最新版本...")
        release = get_latest_release(repo)
        remote_ver_str = release['tag_name'].lstrip('v')  # 移除可能的'v'前缀
        remote_ver = version.parse(remote_ver_str)
        print(f"最新版本: {remote_ver}")
        
        # 比较版本
        if remote_ver <= local_ver:
            print("当前已是最新版本，无需更新")
            return True
        
        # 查找下载链接
        asset_url = find_asset_url(release, asset_pattern)
        if not asset_url:
            print("未找到匹配的资产文件")
            return False
        
        # 下载新版本
        print(f"正在下载新版本: {asset_url}")
        temp_file = f"{local_file}.tmp"
        download_file(asset_url, temp_file)
        
        # 替换旧文件
        print(f"正在更新文件: {local_file}")
        if os.path.exists(local_file):
            os.remove(local_file)
        os.rename(temp_file, local_file)
        
        print(f"{repo_name} 更新完成!")
        return True
        
    except Exception as e:
        print(f"{repo_name} 更新发生错误: {str(e)}")
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
        return False

def main():
    try:
        # 加载所有仓库配置
        repositories = load_repositories()
        print(f"共找到 {len(repositories)} 个仓库配置，开始批量更新检查...")
        
        # 逐个更新仓库
        for repo in repositories:
            update_repository(repo)
        
        print("\n=== 所有仓库更新检查完成 ===")

    except Exception as e:
        print(f"程序发生错误: {str(e)}")

if __name__ == "__main__":
    main()