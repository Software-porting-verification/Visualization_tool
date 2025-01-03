#! /usr/bin/env python3

####################################################
#
#
# collect trace data and Verification
# Author: Wang Jinghua, wangjh@ios.ac.cn
#
#
####################################################

from flask import Flask,request,abort,render_template,url_for,send_from_directory
import os
import sys
import shutil
import glob
from flask_executor import Executor
import subprocess
import threading
from database import create_db_connection, write_to_mysql
# 获取 PerfInstr 目录的绝对路径
perf_instr_path = os.path.abspath('./PerfInstr')
sys.path.append(perf_instr_path)
# 现在你可以从 PerfInstr 导入 perf_func
from PerfInstr.perf_func import main 

app = Flask(__name__, static_url_path='/static')
executor = Executor(app)
pkg_success_flags = {}
dictLock = threading.Lock()

conn = None
cursor = None
root_dir = None

def find_pkgName_file(directory, pkgName):
    for dir in os.listdir(directory):
        if dir == pkgName:
            return os.path.join(directory, dir)
    return None


def mv_dir(directory, pkgName, destination_path):
    file_found = False
    print(f"source_directory: {directory}")
    print(f"pkgName:{pkgName}")
    for source_directory in directory:
        pkgName_file_path = find_pkgName_file(source_directory, pkgName)
        if pkgName_file_path:
            for dir in os.listdir(pkgName_file_path):
                # 检查目录是否为空
                dir_path = os.path.join(pkgName_file_path, dir)
                if os.path.isdir(dir_path) and not os.listdir(dir_path):
                    print(f"Directory {dir_path} is empty.")
                else:
                    print(f"Directory {dir_path} is not empty.")
                shutil.move(os.path.join(pkgName_file_path, dir),
                            destination_path)
            file_found = True
            return True  # 文件移动成功，返回True
    if not file_found:
        return False  # 文件未找到，返回False

def move_and_verify(pkgName,archType,collect_type):
  destination_path = f"{base_path}/{collect_type}_{archType}/{pkgName}"
  directory_to_search = glob.glob(f"{base_path}/obs-workers/{archType}-*/root*/home/abuild/rpmbuild/PERF_TREC")
  result_dir = f"{base_path}/{collect_type}/result_dir"

  if not os.path.exists(result_dir):
      os.makedirs(result_dir)

  if os.path.exists(destination_path):
      shutil.rmtree(destination_path)
  os.makedirs(destination_path)
  
  mv_dir_result = mv_dir(directory_to_search, pkgName, destination_path)
  
  retMsg = ""
  if mv_dir_result:
      with dictLock:
          pkg_success_flags.setdefault(pkgName,{}).setdefault(collect_type,set()).add(archType)
          retMsg = f"{archType} 架构文件移动成功\n"
          retMsg += f"已收集到以下构架的trace记录：{' '.join(pkg_success_flags[pkgName][collect_type])}\n"
          if len(pkg_success_flags[pkgName][collect_type]) == 2:
              retMsg += f"集齐所有trace记录，开始运行检测\n"
              if collect_type == "instr":
                  future = executor.submit(main,
                                  f"{base_path}/{collect_type}_x86_64/{pkgName}", 
                                  f"{base_path}/{collect_type}_riscv64/{pkgName}",
                                  pkgName, result_dir)
                  result = future.result();
                  write_to_mysql(conn,cursor,pkgName, result, f"{result_dir}/{pkgName}.html")
       
              if collect_type == "perf":
                  future = executor.submit(main,
                                  f"{base_path}/{collect_type}_x86_64/{pkgName}",
                                  f"{base_path}/{collect_type}_riscv64/{pkgName}",
                                  pkgName, result_dir)
                  result = future.result();
                  write_to_mysql(conn,cursor,pkgName, result, f"{result_dir}/{pkgName}.html")
              pkg_success_flags[pkgName][collect_type].clear()
  else:
      retMsg = f"文件移动失败：文件未找到\n"

  return retMsg

@app.route('/collectTrace',methods=['GET'])
def collect_trace():
   pkgName = request.args.get('pkgName')
   archType = request.args.get('archType')
   collect_type = request.args.get('collect_type')
   retMsg = move_and_verify(pkgName, archType, collect_type)
   return retMsg


@app.route('/verify')
def restart_verification():
    pkgName = request.args.get('pkgName')
    collect_type = request.args.get('collect_type')
    result_dir = f"{base_path}/{collect_type}/result_dir"

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    x86_64_path = f"{base_path}/{collect_type}_x86_64/{pkgName}"
    riscv64_path = f"{base_path}/{collect_type}_riscv64/{pkgName}"
 
    if pkgName is not None and os.path.exists(x86_64_path) and os.path.exists(riscv64_path):
        if collect_type == "instr":
           future = executor.submit(main, x86_64_path, riscv64_path, pkgName, result_dir)
           result = future.result();
           write_to_mysql(conn,cursor,pkgName, result, f"{result_dir}/{pkgName}.html")
           return f"{pkgName}检测完成"
        elif collect_type == "perf":
           future = executor.submit(main, x86_64_path, riscv64_path, pkgName, result_dir)
           result = future.result();
           write_to_mysql(conn,cursor,pkgName, result, f"{result_dir}/{pkgName}.html")
           return f"{pkgName}检测完成"
   
    return f"参数非法"

@app.route('/show_result_html/')
def show_result_html():
    path = request.args.get('path')
    # 获取绝对路径
    safe_path = os.path.abspath(path)
    # 提取目录和文件名
    directory = os.path.dirname(safe_path)  # 获取文件所在目录
    filename = os.path.basename(safe_path)  # 获取文件名

    return send_from_directory(directory, filename)

if __name__ == '__main__':
    if len(sys.argv) != 6:
       print("Usage:sudo python request.py root_dir host user passwd port")
       sys.exit(1)
    base_path = sys.argv[1]
    # 初始化数据库连接
    conn,cursor = create_db_connection()
    app.run(host='0.0.0.0', port=8088, debug=True)
