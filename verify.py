#! /usr/bin/env python3

####################################################
#
#
# collect trace data and Verification
# Author: Wang Jinghua, wangjh@ios.ac.cn
#
#
####################################################

from flask import Flask,request,abort,render_template,url_for
import os
import sys
import shutil
import glob
from flask_executor import Executor
import subprocess
import threading
from database import DatabaseConnection
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
                print(f"dir: {dir}")
                shutil.move(os.path.join(pkgName_file_path, dir),
                            destination_path)
            file_found = True
            return True  # 文件移动成功，返回True
    if not file_found:
        return False  # 文件未找到，返回False

def move_and_verify(pkgName,archType,collect_type):
  destination_path = f"{base_path}/{collect_type}_{archType}/{pkgName}"
  directory_to_search = glob.glob(f"{base_path}/obs-workers/{archType}-*/root*/home/abuild/rpmbuild/PERF_TREC")
  print(f"xxx:{directory_to_search}")

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
              if collect_type == "instr":
                  executor.submit(perf_func.main,
                                  f"{base_path}/{collect_type}_x86_64/{pkgName}", 
                                  f"{base_path}/{collect_type}_riscv64/{pkgName}",
                                  pkgName, "./")
              if collect_type == "perf":
                  executor.submit(perf_func.main,
                                  f"{base_path}/{collect_type}_x86_64/{pkgName}",
                                  f"{base_path}/{collect_type}_riscv64/{pkgName}",
                                  pkgName, "./")
              retMsg += f"集齐所有trace记录，开始运行检测\n"
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

    x86_64_path = f"{base_path}/{collect_type}_x86_64/{pkgName}"
    riscv64_path = f"{base_path}/{collect_type}_riscv64/{pkgName}"
    
    if pkgName is not None and os.path.exists(x86_64_path) and os.path.exists(riscv64_path):
        if collect_type == "instr":
           executor.submit(perfInstr.main, x86_64_path, riscv64_path, pkgName, "./")
           return f"开始重新检测{pkgName}"
        elif collect_type == "perf":
           executor.submit(perfData.run_verification, conn, cursor, pkgName, x86_64_path, riscv64_path)
           return f"开始重新检测{pkgName}"
   
    return f"参数非法"

@app.route('/show_result_html/')
def show_result_html():
   html_file_path = request.args.get('path')  # 从查询参数中获取HTML文件路径
   print(html_file_path)
   return render_template(html_file_path)



if __name__ == '__main__':
    if len(sys.argv) != 6:
       print("Usage:sudo python request.py root_dir host user passwd port")
       sys.exit(1)
    base_path = sys.argv[1]
    host = sys.argv[2]
    user = sys.argv[3]
    passwd = sys.argv[4]
    port = sys.argv[5]
    # 初始化数据库连接
    #conn,cursor = create_db_connection()
    
    db = DatabaseConnection(host,user,passwd,'test')
    print(port)
    conn,cursor = db.get_connection()
    app.run(host='0.0.0.0', port=8088, debug=True)
