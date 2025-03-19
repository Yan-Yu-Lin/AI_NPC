
#!/usr/bin/env python3
import os
import argparse
import sys
from pathlib import Path


def get_default_ignore_patterns():
    """獲取預設忽略模式列表"""
    return [
        # 常見隱藏目錄和文件
        '.*',                 # 所有隱藏文件和目錄
        # 常見Python相關
        '__pycache__',
        '*.pyc', '*.pyo', '*.pyd',
        # 常見環境相關
        'venv', 'env', '.venv', '.env',
        # 常見二進制和暫存文件
        '*.exe', '*.dll', '*.so', '*.dylib',
        '*.zip', '*.tar.gz', '*.tgz', '*.7z', '*.rar',
        '*.log', '*.tmp', '*.bak',
        # 常見IDE相關
        '.idea', '.vscode',
        # 其他
        'node_modules',
        'dist', 'build',
        'archive',           # 添加 archive 目錄
        # 其他大型二進制文件
        '*.mp4', '*.avi', '*.mov', '*.mp3', '*.wav'
    ]


def is_binary_file(file_path):
    """檢查文件是否為二進制文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read(1024)  # 嘗試讀取一小部分
        return False
    except UnicodeDecodeError:
        return True


def should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
    """判斷是否應該忽略文件"""
    if file_path == output_path:
        return True
    
    file_name = file_path.name
    relative_path = str(file_path.relative_to(directory_path))
    
    # 檢查文件名和相對路徑是否匹配忽略模式
    for pattern in ignore_patterns:
        if pattern.startswith('*'):
            if file_name.endswith(pattern[1:]):
                return True
        elif pattern.endswith('*'):
            if file_name.startswith(pattern[:-1]):
                return True
        elif pattern == relative_path or pattern == file_name:
            return True
    
    # 檢查是否為二進制文件
    if any(file_name.endswith(ext) for ext in ['.exe', '.dll', '.so', '.dylib', '.zip', '.tar.gz', '.7z', '.mp4', '.mp3']):
        return True
        
    return False


def merge_files_to_markdown(directory, output_file, ignore_patterns=None, max_file_size_mb=5, 
                           include_binary=False, verbose=False):
    """
    將目錄下的所有文件合併為一個 Markdown 文件
    
    Args:
        directory: 要掃描的目錄路徑
        output_file: 輸出的 Markdown 文件路徑
        ignore_patterns: 要忽略的文件或目錄模式列表
        max_file_size_mb: 最大文件大小限制（MB）
        include_binary: 是否包含二進制文件
        verbose: 是否顯示詳細訊息
    """
    if ignore_patterns is None:
        ignore_patterns = get_default_ignore_patterns()
    
    # 轉換為絕對路徑
    directory_path = Path(directory).resolve()
    output_path = Path(output_file).resolve()
    
    # 確認目錄存在
    if not directory_path.exists() or not directory_path.is_dir():
        raise ValueError(f"目錄 '{directory}' 不存在或不是一個有效的目錄")
    
    if verbose:
        print(f"掃描目錄: {directory_path}")
        print(f"忽略模式: {ignore_patterns}")
    
    # 獲取所有文件路徑
    all_files = []
    skipped_files = []
    total_files = 0
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    
    for root, dirs, files in os.walk(directory_path):
        # 過濾要忽略的目錄
        dirs_to_remove = []
        for d in dirs:
            dir_path = Path(root) / d
            relative_dir = str(dir_path.relative_to(directory_path))
            
            # 檢查是否匹配忽略模式
            if any(
                (d.startswith('.') and '.*' in ignore_patterns) or
                d == p or relative_dir == p
                for p in ignore_patterns
            ):
                dirs_to_remove.append(d)
                if verbose:
                    print(f"忽略目錄: {relative_dir}")
        
        # 從 dirs 列表中移除要忽略的目錄，這樣 os.walk 就不會進入這些目錄
        for d in dirs_to_remove:
            dirs.remove(d)
            
        for file in files:
            total_files += 1
            file_path = Path(root) / file
            
            # 忽略要排除的文件
            if should_ignore_file(file_path, directory_path, ignore_patterns, output_path):
                skipped_files.append(str(file_path.relative_to(directory_path)))
                if verbose:
                    print(f"忽略文件: {file_path.relative_to(directory_path)}")
                continue
            
            # 檢查文件大小
            file_size = file_path.stat().st_size
            if file_size > max_file_size_bytes:
                skipped_files.append(f"{file_path.relative_to(directory_path)} (文件太大: {file_size/(1024*1024):.2f} MB)")
                if verbose:
                    print(f"忽略過大文件: {file_path.relative_to(directory_path)} ({file_size/(1024*1024):.2f} MB)")
                continue
                
            # 檢查是否為二進制文件
            if not include_binary and is_binary_file(file_path):
                skipped_files.append(f"{file_path.relative_to(directory_path)} (二進制文件)")
                if verbose:
                    print(f"忽略二進制文件: {file_path.relative_to(directory_path)}")
                continue
            
            all_files.append(file_path)
    
    # 排序文件路徑，使輸出更加有序
    all_files.sort()
    
    if verbose:
        print(f"找到 {total_files} 個文件，合併 {len(all_files)} 個文件，跳過 {len(skipped_files)} 個文件")
    
    # 寫入合併後的 Markdown 文件
    with open(output_file, 'w', encoding='utf-8') as out_file:
        out_file.write(f"# 項目文件合併\n\n")
        out_file.write(f"目錄: `{directory_path}`\n\n")
        out_file.write(f"包含 {len(all_files)} 個文件\n\n")
        
        # 如果有跳過的文件，添加一個列表
        if skipped_files and verbose:
            out_file.write("## 跳過的文件\n\n")
            for skipped in skipped_files:
                out_file.write(f"- {skipped}\n")
            out_file.write("\n")
        
        for file_path in all_files:
            # 獲取相對路徑作為標題
            relative_path = file_path.relative_to(directory_path)
            out_file.write(f"## {relative_path}\n\n")
            
            # 嘗試讀取文件內容
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 判斷文件類型並設置語法高亮
                file_extension = file_path.suffix.lstrip('.')
                if file_extension:
                    out_file.write(f"```{file_extension}\n")
                else:
                    out_file.write("```\n")
                
                out_file.write(content)
                
                # 確保內容後有換行
                if not content.endswith('\n'):
                    out_file.write('\n')
                out_file.write("```\n\n")
                
            except UnicodeDecodeError:
                out_file.write("```\n[二進制文件，內容無法顯示]\n```\n\n")
            except Exception as e:
                out_file.write(f"```\n[讀取文件時出錯: {str(e)}]\n```\n\n")
    
    return len(all_files), len(skipped_files)


def main():
    parser = argparse.ArgumentParser(description='將目錄下的所有文件合併為一個 Markdown 文件')
    parser.add_argument('directory', nargs='?', default='.', 
                     help='要掃描的目錄路徑 (預設為當前目錄)')
    parser.add_argument('-o', '--output', default='merged_files.md', 
                     help='輸出的 Markdown 文件路徑 (預設為 merged_files.md)')
    parser.add_argument('-i', '--ignore', nargs='+', 
                     help='要忽略的文件或目錄模式 (可以多個)')
    parser.add_argument('-s', '--max-size', type=float, default=5, 
                     help='最大文件大小限制（MB，預設為 5MB）')
    parser.add_argument('-b', '--include-binary', action='store_true', 
                     help='包含二進制文件 (預設不包含)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                     help='顯示詳細訊息')
    
    args = parser.parse_args()
    
    # 合併默認忽略模式和用戶指定的忽略模式
    ignore_patterns = get_default_ignore_patterns()
    if args.ignore:
        ignore_patterns.extend(args.ignore)
    
    try:
        included, skipped = merge_files_to_markdown(
            args.directory, 
            args.output, 
            ignore_patterns=ignore_patterns,
            max_file_size_mb=args.max_size,
            include_binary=args.include_binary,
            verbose=args.verbose
        )
        print(f"成功將 {included} 個文件合併到 {args.output}")
        print(f"跳過了 {skipped} 個文件")
    except Exception as e:
        print(f"合併文件時出錯: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
