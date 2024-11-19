import pymysql
import sys

host = sys.argv[2]
user = sys.argv[3]
passwd = sys.argv[4]
port = sys.argv[5]
def create_db_connection():
   # 创建数据库连接的函数
   try:
       conn = pymysql.connect(
           host=host,
           user=user,
           password=passwd,
           database='test'
       )
       if conn:
           print('Connected to MySQL database')
           cursor = conn.cursor()
           # 创建表
           cursor.execute('''
                CREATE TABLE IF NOT EXISTS Instr_reports (
                    id int AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) UNIQUE,
                    number int DEFAULT 0,
                    port int,
                    ip VARCHAR(255),
                    report_dir VARCHAR(255)
                )
            ''')

           cursor.execute('''
               CREATE TABLE IF NOT EXISTS Perf_reports (
                   id int AUTO_INCREMENT PRIMARY KEY,
                   name VARCHAR(255) UNIQUE,
                   number int,
                   port int,
                   ip VARCHAR(255),
                   report_dir VARCHAR(255)
               )
           ''') 
           conn.commit()
           return conn,cursor
   except pymysql.Error as e:
       print(e)
       return None,None

def get_connection(self):
    if self.conn is None or self.cursor is None:
        self.create_connection()
    return self.conn,self.cursor

def write_to_mysql(conn,cursor,pkgName,result_count,result_dir):
    try:
       cursor.execute('INSERT INTO Instr_reports (name,number,port,ip,report_dir) VALUES (%s,IFNULL(%s, 0),%s,%s,%s) ON DUPLICATE KEY UPDATE number=IFNULL(%s, 0),port=%s,ip=%s,report_dir=%s',(pkgName,result_count,port,host,result_dir,result_count,port,host,result_dir))
       conn.commit()  # Don't forget to commit the transaction
    except pymysql.MySQLError as e:
        print(f"Error executing query: {e}")
        conn.rollback()  # Rollback in case of an erro
