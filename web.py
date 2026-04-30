import requests
from bs4 import BeautifulSoup

from flask import Flask, render_template,request
from datetime import datetime

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

# 判斷是在 Vercel 還是本地
if os.path.exists('serviceAccountKey.json'):
    # 本地環境：讀取檔案
    cred = credentials.Certificate('serviceAccountKey.json')
else:
    # 雲端環境：從環境變數讀取 JSON 字串
    firebase_config = os.getenv('FIREBASE_CONFIG')
    cred_dict = json.loads(firebase_config)
    cred = credentials.Certificate(cred_dict)

firebase_admin.initialize_app(cred)


app = Flask(__name__)


@app.route("/")
def index():
    link = "<h1>歡迎來到黃建鴻的網站20260326</h1>"
    link += "<a href=/mis>課程</a><hr>"
    link += "<a href=/today>現在日期時間</a><hr>"
    link += "<a href=/me>關於我</a><hr>"
    link += "<a href=/welcome?u=建鴻&d=靜宜資管&c=資訊管理導論>Get傳值</a><hr>"
    link += "<a href=/account>POST傳值</a><hr>"
    link += "<a href=/math>次方與根號計算</a><hr>"
    link += "<a href=/read>讀取Firestore資料</a><br>"
    link += "<a href=/search_form>教師搜尋系統(根據姓名關鍵字)</a><br>"
    link += "<a href=/spider>爬取子青老師本學期課程</a><hr>"
    link += "<a href=/movie>爬取即將上映電影</a><hr>"
    link += "<a href=/spidermovie>讀取開眼電影即將上映影片，寫入Firestore</a><br>"
    link += "<a href=/searchMovie>從資料庫搜尋電影</a><hr>"
    return link

@app.route("/searchMovie")
def searchMovie():
    # 獲取使用者輸入的關鍵字 (預設為空字串)
    keyword = request.args.get("keyword", "")
    
    # 建立搜尋表單 UI
    R = "<h2>從資料庫搜尋電影</h2>"
    R += "<form action='/searchMovie' method='GET'>"
    R += f"請輸入片名關鍵字: <input type='text' name='keyword' value='{keyword}'> "
    R += "<input type='submit' value='開始查詢'>"
    R += "</form><hr>"

    # 如果沒有輸入關鍵字，就先只顯示表單
    if not keyword:
        R += "<p>請在上方輸入關鍵字查詢資料庫中的電影。</p>"
        R += "<br><a href='/'>返回首頁</a>"
        return R

    R += f"<h3>關鍵字「{keyword}」的查詢結果：</h3>"

    # 連線到 Firestore 資料庫
    db = firestore.client()
    collection_ref = db.collection("電影2B")  # 對應你 /spidermovie 寫入的集合
    docs = collection_ref.stream()

    found_count = 0
    for doc in docs:
        movie = doc.to_dict()
        title = movie.get("title", "")
        
        # 關鍵字篩選邏輯 (轉成小寫比對，避免大小寫差異找不到)
        if keyword.lower() in title.lower():
            found_count += 1
            movie_id = doc.id
            picture = movie.get("picture", "")
            hyperlink = movie.get("hyperlink", "")
            showDate = movie.get("showDate", "")
            
            # 組合回傳的 HTML 內容，包含編號、片名、上映日期、介紹頁與海報
            R += "<div>"
            R += f"<h4>編號: {movie_id}</h4>"
            R += f"<h4>片名: {title}</h4>"
            R += f"<p>上映日期: {showDate}</p>"
            R += f"<p><a href='{hyperlink}' target='_blank'>電影介紹頁</a></p>"
            R += f"<img src='{picture}' width='200'><br>"
            R += "</div><hr>"

    # 如果沒找到符合的電影
    if found_count == 0:
        R += "<p>抱歉，資料庫中找不到符合條件的電影，請嘗試其他關鍵字或先執行爬蟲寫入資料。</p>"

    R += "<br><a href='/'>返回首頁</a>"
    return R

@app.route("/spidermovie")
def spidermovie():
    R = ""



    db = firestore.client()

    import requests
    from bs4 import BeautifulSoup
    url = "http://www.atmovies.com.tw/movie/next/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text.replace("更新時間：","")


    result=sp.select(".filmListAllX li")
    info = ""
    total = 0
    for item in result:
      total += 1
      movie_id = item.find("a").get("href").replace("/movie/", "").replace("/", "")
      title = item.find(class_="filmtitle").text
      picture = "http://www.atmovies.com.tw" + item.find("img").get("src")
      hyperlink = "http://www.atmovies.com.tw" + item.find("a").get("href")

      showDate = item.find(class_="runtime").text[5:15]
      info += movie_id + "\n" + title + "\n" + picture + "\n" + hyperlink + "\n" + showDate +"\n\n"

      doc = {
        "title": title,
        "picture": picture,
        "hyperlink": hyperlink,
        "showDate": showDate,
        "lastUpdate": lastUpdate
    }

      
      doc_ref = db.collection("電影2B").document(movie_id)
      doc_ref.set(doc)

    #print(info)
    print(lastUpdate)
    R += "網站最新更新日期:" + lastUpdate + "<br>"
    R += "總共爬取"+ str(total) + "部電影到資料庫"
    return R


@app.route("/movie")
def movie():
    # 獲取使用者輸入的關鍵字 (預設為空字串)
    keyword = request.args.get("keyword", "")
   
    R = f"<h1>電影查詢結果: {keyword}</h1>"
    # 建立一個簡單的搜尋表單回傳給前端
    search_form = """
        <form action="/movie" method="get">
            搜尋片名關鍵字: <input type="text" name="keyword">
            <input type="submit" value="查詢">
        </form><hr>
    """
    R = search_form + R

    url = "https://www.atmovies.com.tw/movie/next/"
    data = requests.get(url)
    data.encoding = "utf-8"
    sp = BeautifulSoup(data.text, "html.parser")
    result = sp.select(".filmListAllX li")

    found_count = 0
    for item in result:
        title = item.find("img").get("alt")
       
        # 關鍵字篩選邏輯：如果關鍵字在片名中，或是關鍵字為空(顯示全部)
        if keyword.lower() in title.lower():
            found_count += 1
            img_url = "https://www.atmovies.com.tw" + item.find("img").get("src")
            intro_url = "https://www.atmovies.com.tw" + item.find("a").get("href")
           
            # 組合回傳內容
            R += f"<div>"
            R += f"<h3>{title}</h3>"
            R += f"<a href='{intro_url}' target='_blank'>電影介紹頁</a><br>"
            R += f"<img src='{img_url}' width='200'><br><br>"
            R += f"</div><hr>"

    if found_count == 0:
        R += "<p>抱歉，找不到符合條件的電影。</p>"

    return R    

@app.route("/search_form")
def search_form():
    form_html = "<h2>教師搜尋系統</h2>"
    form_html += "<form action='/read2' method='GET'>"
    form_html += "請輸入姓名關鍵字: <input type='text' name='keyword' required> "
    form_html += "<input type='submit' value='開始搜尋'>"
    form_html += "</form><hr>"
    form_html += "<a href='/'>返回首頁</a>"
    return form_html

@app.route("/spider")
def spider():
    R = ""
    url = "https://www1.pu.edu.tw/~tcyang/course.html"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    #print(Data.text)
    sp = BeautifulSoup(Data.text, "html.parser")
    result=sp.select(".team-box a")
    for i in result:
        R += i.text + i.get("href")+"<br>"
    return R

@app.route("/read2")
def read2():
    Result = ""
    keyword = request.args.get("keyword", "")
    if not keyword:
        return "請輸入關鍵字再進行搜尋！"
    db = firestore.client()
    collection_ref = db.collection("資管二B2026")    
    docs = collection_ref.get()    
    for doc in docs:
        teacher = doc.to_dict()
        if keyword in teacher.get("name", ""):
            Result += str(teacher) + "<br>"
    if Result == "":
        Result = "抱歉,查無此關鍵字姓名之老師資料"
    return Result

@app.route("/read")
def read():
    Result = ""
    db = firestore.client()
    collection_ref = db.collection("資管二B2026")    
    docs = collection_ref.get()    
    for doc in docs:         
        Result += "文件內容：{}".format(doc.to_dict()) + "<br>"    
    return Result

@app.route("/mis")
def course():
    return "<h1>資訊管理導論</h1><a href=/>返回首頁</a>"
@app.route("/today")
def today():
    now = datetime.now()
    return render_template("today.html", datetime = str(now))
@app.route("/me")
def me():
    now = datetime.now()
    return render_template("about.html")
@app.route("/welcome", methods=["GET"])
def welcome():
    user = request.values.get("u")
    d = request.values.get("d")
    c = request.values.get("c")
    return render_template("welcome.html", name=user,dep = d,course=c)
@app.route("/account", methods=["GET", "POST"])
def account():
    if request.method == "POST":
        user = request.form["user"]
        pwd = request.form["pwd"]
        result = "您輸入的帳號是：" + user + "; 密碼為：" + pwd 
        return result
    else:
        return render_template("account.html")
@app.route("/math", methods=["GET", "POST"])
def math():
    if request.method == "POST":
        try:
            x = float(request.form["x"])
            y = float(request.form["y"])
            opt = request.form["opt"]
           
            if opt == "pow":
                # 次方計算：x 的 y 次方
                result = x ** y
                msg = f"{x} 的 {y} 次方 = {result}"
            elif opt == "root":
                # 根號計算：x 的 y 次根號 (即 x 的 1/y 次方)
                if x < 0 and y % 2 == 0:
                    msg = "錯誤：負數不能開偶數次方根"
                else:
                    result = x ** (1/y)
                    msg = f"{x} 的 {y} 次方根 = {result}"
            else:
                msg = "無效的運算"
        except Exception as e:
            msg = f"計算出錯：{str(e)}"
           
        return f"<h1>計算結果</h1><p>{msg}</p><a href='/math'>重新計算</a>"
   
    return render_template("math.html")
if __name__ == "__main__":
    app.run()
