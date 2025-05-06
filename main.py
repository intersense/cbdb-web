from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse,JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from zhconv import convert

import sqlite3

app = FastAPI()

# 设置静态文件路径
app.mount("/static", StaticFiles(directory="static"), name="static")
# 设置模板路径
templates = Jinja2Templates(directory="templates")

# CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 数据库文件的位置，这里是在上一级目录下的 cbdb2024.db
DATABASE = '../cbdb2024.db'

# 建立数据库连接
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# 搜索界面
@app.get("/search_form/", response_class=HTMLResponse) 
async def search_form(request: Request):
    # 查询社会关系类别，填充查询社会网络关系类型选择项
    conn = get_db_connection()
    social_network_types = conn.execute('SELECT c_assoc_code, c_assoc_desc_chn FROM assoc_codes').fetchall()
    # 提取亲属关系的类型
    kinship_sql = "SELECT c_kincode, c_kinrel_chn FROM kinship_codes WHERE c_kincode >1"
    kinship_types = conn.execute(kinship_sql).fetchall()

    conn.close()
    return templates.TemplateResponse("search_form.html", {"request": request, "social_network_types": social_network_types[2:], "kinship_types": kinship_types})
    

# 查询历史人物寿命
@app.get("/search_lifespan/", response_class=HTMLResponse)
async def search_lifespan(min_death_age: int, max_death_age: int, gender: str, request: Request):
    conn = get_db_connection()
    if gender == '男':
        g = 0
    else:
        g = 1
    sqlstr = f"SELECT * FROM biog_main WHERE c_deathyear > 0 and c_birthyear>0 and c_deathyear-c_birthyear >= {min_death_age} and c_deathyear-c_birthyear <= {max_death_age} and c_female={g}"
    persons=conn.execute(sqlstr).fetchall()
    conn.close()
    
    return templates.TemplateResponse("lifespan.html", {"request": request, "persons": persons, "min_death_age": min_death_age, "max_death_age": max_death_age})

@app.get("/search_person_id/", response_class=HTMLResponse)
async def search_person_id(person_id: str, request: Request):
    conn = get_db_connection()
    # 检索人物基本信息
    person = conn.execute('SELECT * FROM biog_main WHERE c_personid = ?', (person_id,)).fetchone()
    # 检索人物别名信息
    alt_names = conn.execute('SELECT * FROM altname_data WHERE c_personid = ?', (person_id,)).fetchall()
    # 检索人物籍贯
    birth_places = conn.execute(f'select distinct c_name_chn, x_coord, y_coord from addresses where c_addr_id in (SELECT c_addr_id FROM biog_addr_data WHERE c_addr_type = 1 and c_personid = {person_id})').fetchall()
    # 检索人物著作
    works = conn.execute(f'select * from biog_text_data b join text_codes t on b.c_textid = t.c_textid where b.c_personid={person_id}').fetchall()
    conn.close()
    return templates.TemplateResponse("person_info.html", {"request": request, "person": person, "alt_names": alt_names, "birth_places": birth_places, "works": works})

@app.get("/search_person_name/", response_class=HTMLResponse)
async def search_person_name(name: str, request: Request):
    name = convert(name, 'zh-tw')
    conn = get_db_connection()
    persons = conn.execute('SELECT * FROM biog_main WHERE c_name_chn = ?', (name,)).fetchall()

    conn.close()
    return templates.TemplateResponse("person_list.html", {"request": request, "persons": persons})
    
@app.get("/persons/{c_personid}")
async def read_person(c_personid: int):
    conn = get_db_connection()
    person = conn.execute('SELECT * FROM biog_main WHERE c_personid = ?', (c_personid,)).fetchone()
    conn.close()
    
    if person is None:
        return {"message": "Person not found"}
    return {"id": person["c_personid"], "name": person["c_name_chn"], "birth": person["c_birthyear"], "death": person["c_deathyear"]}

# 搜索官职
@app.get("/search_office", response_class=HTMLResponse)
def search_office(office:str, request: Request):
    conn = get_db_connection()
    office = convert(office, 'zh-tw')
    # 查询所有包含关键词的官职
    sql_query = f'''
        SELECT * from office_codes
        where c_office_chn like '%{office}%'
    '''
    offices = conn.execute(sql_query).fetchall()
    # 查询所有担任过该官职的人
    sql_query = f'''
        select * from biog_main where c_personid in
        (
            SELECT c_personid from posted_to_office_data
                where c_office_id in (select c_office_id from office_codes where c_office_chn like '%{office}%')
        )
    '''
    persons = conn.execute(sql_query).fetchall()
    conn.close()
    return templates.TemplateResponse("office_info.html", {"request": request, "offices": offices, "persons": persons})

# 搜索科举信息
@app.get("/search_exam", response_class=HTMLResponse)
def search_exam(exam:str, start_year:str, end_year:str, request: Request):
    conn = get_db_connection()
    exam = convert(exam, 'zh-tw')
    sql_query = f'''
        SELECT * from entry_data e join biog_main b on e.c_personid = b.c_personid
        where e.c_year >= {start_year} and e.c_year < {end_year} and e.c_entry_code in (select c_entry_code from entry_codes where c_entry_desc_chn like '%{exam}%')
        
    '''
    exams = conn.execute(sql_query).fetchall()

    conn.close()
    return templates.TemplateResponse("exam_info.html", {"request": request, "exams": exams})

# CBDB数据库中人物的作品
@app.get("/sources/", response_class=HTMLResponse)
async def source(request: Request):
    conn = get_db_connection()
    sources = conn.execute('SELECT * FROM text_codes').fetchall()
    conn.close()
    return templates.TemplateResponse("sources.html", {"request": request, "sources": sources})

# 展示地图
@app.get("/show-map/", response_class=HTMLResponse)
async def show_map(x_coord:str, y_coord:str, person_name:str, request: Request):
    print(x_coord, y_coord)
    return templates.TemplateResponse("show_map.html", {"request": request, "x_coord": x_coord, "y_coord": y_coord, "person_name": person_name})

# 按地理位置搜索人物
@app.get("/search_placename/", response_class=HTMLResponse)
async def search_placename(placename: str, request: Request):
    conn = get_db_connection()
    placename = convert(placename, 'zh-tw')
    sql_query = f'''
        select * from biog_main where c_personid in
        (
            select c_personid from biog_addr_data where c_addr_id in
            (
                select c_addr_id from addresses where c_name_chn like '%{placename}%'
            )
        )
    '''
    persons = conn.execute(sql_query).fetchall()
    conn.close()
    return templates.TemplateResponse("person_list.html", {"request": request, "persons": persons})

def get_social_network_personid(person_id, types=None):
    conn = get_db_connection()
    # 如果提供了关系类型，只返回该类型的关系，构造关系类别查询条件
    if types is not None:
        type_condition1 = f" and a.c_assoc_code IN ({','.join(types)}) "
        type_condition2 = f" a.c_assoc_code IN ({','.join(types)}) and "
    else:
        type_condition1 = ""
        type_condition2 = ""

    sql_query = f'''
        WITH RECURSIVE network AS (
        -- Non-recursive part: Find one's person ID and directly related students (same as before)
        SELECT 
            p.c_personid AS person_id,
            p.c_name AS person_name, 
            p.c_name_chn AS person_name_chn,
            CAST(NULL as integer) as via_id,
            CAST(NULL AS VARCHAR(255)) AS via_name,
            CAST(NULL AS VARCHAR(255)) AS via_name_chn,
            a.c_assoc_desc AS assoc_desc,
            a.c_assoc_desc_chn AS assoc_desc_chn,
            0 AS distance 
        FROM BIOG_MAIN p
        LEFT JOIN ASSOC_DATA ad ON p.c_personid = ad.c_personid
        LEFT JOIN ASSOC_CODES a ON ad.c_assoc_code = a.c_assoc_code
        WHERE p.c_personid = {person_id} {type_condition1}
        
        UNION ALL
        
        -- Recursive part: Find other people related to known people as 'Student of Y'
        SELECT
            n.c_personid AS person_id,
            n.c_name AS person_name,
            n.c_name_chn AS person_name_chn, 
            p.person_id as via_id,
            p.person_name AS via_name,
            p.person_name_chn AS via_name_chn,
            a.c_assoc_desc AS assoc_desc,
            a.c_assoc_desc_chn AS assoc_desc_chn,
            p.distance + 1 AS distance
        FROM network p
        JOIN ASSOC_DATA ad ON p.person_id = ad.c_assoc_id AND ad.c_personid = n.c_personid -- Ensure known person is the teacher and student is the new person
        JOIN BIOG_MAIN n ON n.c_personid <> p.person_id -- Get the student's information
        JOIN ASSOC_CODES a ON ad.c_assoc_code = a.c_assoc_code
        WHERE {type_condition2} p.distance < 5 -- Limit recursion depth
        )
        SELECT DISTINCT 
            person_id,
            person_name,
            person_name_chn,
            via_id,
            via_name,
            via_name_chn,
            assoc_desc,
            assoc_desc_chn,
            distance 
        FROM network
        ORDER BY distance;
    '''
    print(sql_query)
    social_network = conn.execute(sql_query).fetchall()
    conn.close()
    return social_network

@app.post("/search_social_network/", response_class=HTMLResponse)
async def search_social_network(request:Request, social_types: list = Form('social_types'), person_id: int = Form('person_id')):
    c_personid = person_id
    #social_types = Form('social_types')
    print(social_types)
    print(person_id)
    # 根据人物id和关系类型查询社会网络
    social_network = get_social_network_personid(person_id, social_types)
    
    # 保存网络到CSV文件
    import csv
    with open('static/social_network.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['source', 'target', 'assoc_desc_chn'])
        for row in social_network:
            writer.writerow([row['via_name_chn'], row['person_name_chn'], row['assoc_desc_chn']])
    
    # 可视化网络，保存为HTML文件
    import networkx as nx

    # Initialize an empty directed graph
    G = nx.DiGraph()

    # Iterate over the rows in the social_network result
    for row in social_network:
        person_id, person_name, person_name_chn, via_id, via_name, via_name_chn, assoc_desc, assoc_desc_chn, distance = row
        # Add nodes for both the person and the "via" person if they don't already exist
        if person_id not in G:
            G.add_node(person_id, name=person_name, label=person_name_chn)
        if via_id and via_id not in G:
            G.add_node(via_id, name=via_name, name_chn=via_name_chn)
        # Add an edge from the "via" person to the person if via_id is not None
        if via_id:
            G.add_edge(via_id, person_id, assoc_desc=assoc_desc, assoc_desc_chn=assoc_desc_chn, label=assoc_desc_chn, distance=distance)
    
    from pyvis.network import Network

    # 假设G是你已经创建的networkx图
    # 初始化pyvis网络，设置为notebook模式以便在Jupyter笔记本中显示
    nt = Network('600px', '1300px', notebook=True)
    nt.show_buttons(filter_=['nodes', 'edges', 'physics'])
    
    # 使用pyvis的内置方法从networkx图转换
    nt.from_nx(G)

    # 显示网络图。如果你不在Jupyter笔记本中，可以将其保存为HTML文件并在浏览器中打开
    #nt.show('network.html')
    # 保存为HTML文件到static文件夹
    nt.save_graph("static/network.html")

    if social_network is None:
        return {"message": "Social Network not found"}
    print(c_personid)

    return templates.TemplateResponse("social_network.html", {"request": request, "social_network": social_network, "c_personid": c_personid})


@app.post("/search_kinship/", response_class=HTMLResponse)
async def search_kinship(request: Request, kinship_types: list = Form('kinship_types'), person_id: int = Form('person_id')):
    conn = get_db_connection()
    print(kinship_types)
    type_condition2 = f" ({','.join(kinship_types)})"
    # 根据人物id查询亲属关系
    kinship_person_id_sql = f"""
            WITH RECURSIVE kinship_tree AS (
        -- 锚点成员：根据输入的 c_personid 查找目标人物
        SELECT
            bm.c_personid,
            bm.c_name_chn AS name,
            bm.c_birthyear AS birth_year,
            bm.c_deathyear AS death_year,
            CAST(bm.c_name_chn AS TEXT) AS relationship_path,
            0 AS depth
        FROM biog_main AS bm
        WHERE bm.c_personid = {person_id}  -- 替换 :person_id 为目标人物的 ID

        UNION ALL

        -- 递归查询：查找与当前人物有亲属关系的人物 (限制深度)
        SELECT
            k.c_kin_id,
            bm.c_name_chn AS name,
            bm.c_birthyear AS birth_year,
            bm.c_deathyear AS death_year,
            kt.relationship_path || ' -> ' || kc.c_kinrel_chn AS relationship_path,
            kt.depth + 1 AS depth
        FROM kinship_tree AS kt
        JOIN kin_data AS k
            ON kt.c_personid = k.c_personid
        JOIN biog_main AS bm
            ON k.c_kin_id = bm.c_personid
        JOIN kinship_codes AS kc
            ON k.c_kin_code = kc.c_kincode
        WHERE kt.depth < 5 and k.c_kin_code in {type_condition2} -- 限制查询深度
        )

        SELECT
        kt.name AS person_name,  -- 查询人物姓名
        kt.birth_year AS person_birth_year,  -- 查询人物生年
        kt.death_year AS person_death_year,  -- 查询人物卒年
        k.c_kin_id AS kin_id,  -- 亲属 ID
        bm.c_name_chn AS kin_name,  -- 亲属姓名
        bm.c_birthyear AS kin_birth_year,  -- 亲属生年
        bm.c_deathyear AS kin_death_year,  -- 亲属卒年
        kc.c_kinrel_chn AS relationship  -- 与查询人物的关系
        FROM kinship_tree AS kt
        LEFT JOIN kin_data AS k
        ON kt.c_personid = k.c_personid
        LEFT JOIN biog_main AS bm
        ON k.c_kin_id = bm.c_personid
        LEFT JOIN kinship_codes AS kc
        ON k.c_kin_code = kc.c_kincode
        ORDER BY kt.depth, bm.c_birthyear
        """
    print(kinship_person_id_sql)
    kinships = conn.execute(kinship_person_id_sql).fetchall()
    conn.close()
    return templates.TemplateResponse("kinship.html", {"request": request, "kinships": kinships})

@app.get("/about/", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/test-form/", response_class=HTMLResponse)
async def test_form(request: Request):
    return templates.TemplateResponse("test_form.html", {"request": request})

@app.post("/test-form/", response_class=HTMLResponse)
async def test_form_post(request: Request, name: str = Form(...)):
    # 处理表单数据
    #print(f"Name: {name}")
    name = convert(name, 'zh-hant')
    html_content = f"""
    <html>
    <head>
        <title>Form Submission</title>
    </head>
    <body>
        <h1>Form Submitted</h1>
        <p>Name: {name}</p>
        <a href="/test-form">Go back</a>
    </body>
    </html>
    """
    return html_content