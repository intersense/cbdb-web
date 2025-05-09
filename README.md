# 中国历代人物传记资料库（CBDB）Web查询系统
webUI for CBDB (SQLite version)

注意：CBDB数据库请从CBDB官网下载，这里只是查询数据库的Web系统

- 系统运行界面

<img width="1175" alt="cbdb-web-search-form" src="https://github.com/user-attachments/assets/1ee25bf0-0520-4214-9932-8a67a82742f6" />

- 安装必要的包
  - pip install fastapi uvicorn pyvis zhconv
- 运行系统
  - uvicorn main:app --port 8085 --reload
  - 打开浏览器输入：localhost:8085

## 查询示例
1. 查询朱熹的学生
<img width="1304" alt="cbdb-web-zhuxi-teaching" src="https://github.com/user-attachments/assets/b0caa743-7d28-4af0-af2b-ec1bd7e0dc2d" />

## 系统运行必须的包和软件

- fastapi
- networkx, pyvis
- cbdb.db (sqlite version)
    - CBDB官网 https://projects.iq.harvard.edu/cbdb/home
    - CBDB下载 https://github.com/cbdb-project/cbdb_sqlite/blob/master/latest.7z 下载之后解压缩
    - 将下载的cbdb sqlite版放到与main.py相同的目录，命名为cbdb.db，并将main.py中的DATABASE = '../cbdb2024.db'改为DATABASE = './cbdb.db'
