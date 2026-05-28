import requests
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

from flask import Flask, render_template,request,make_response, jsonify
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

client = genai.Client()



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
    link += "<a href=/rate>本週新片進DB</a><hr>"
    link += "<a href=/road>台中市十大肇事路口</a><hr>"
    link += "<a href=/weather>縣市天氣查詢</a><hr>"
    link += "<a href=/webdemo>聊天機器人</a><hr>"
    link += "<a href=/AI>AI</a><hr>"
    link += "<a href=/ask>詢問Gemini</a><hr>"
    return link
@app.route('/ask', methods=['GET', 'POST']) 
def ask():
    if request.method == "POST":
        user_prompt = request.form.get('prompt', '')
        if not user_prompt:
            return "請輸入內容", 400
        try:
            response = client.models.generate_content(
                model='gemini-3.1-flash-liti',
                contents=user_prompt,
            )
            return response.text
        except Exception as e:
            return f"發生錯誤: {str(e)}", 500

    else:    
        # 當使用者直接打開網頁 (GET) 時，顯示輸入框畫面
        return render_template("ask.html")


@app.route("/AI")
def AI():
    # 每次使用者拜訪該路徑時，直接使用全域的 client 呼叫模型
    response = client.models.generate_content(
        model='gemini-3.1-flash-liti',
        contents='我想查詢靜宜大學資管系的評價？',
    )
    
    # 回傳生成的文字
    return response.text


@app.route("/webdemo")
def webdemo():
    return render_template("webdemo.html")

@app.route("/webhook", methods=["POST"])
def webhook():
    # build a request object
    req = request.get_json(force=True)
    # fetch queryResult from json
    action =  req["queryResult"]["action"]
    #msg =  req["queryResult"]["queryText"]
    #info = "我是黃建鴻設計的機器人,動作：" + action + "； 查詢內容：" + msg

    if (action == "rateChoice"):
        rate =  req["queryResult"]["parameters"]["rate"]
        info = "我是黃建鴻設計的機器人,您選擇的電影分級是：" + rate  + "，相關電影：\n"
        db = firestore.client()
        collection_ref = db.collection("本週新片含分級")
        docs = collection_ref.get()
        result = ""
        for doc in docs:
            dict = doc.to_dict()
            if rate in dict["rate"]:
                result += "片名：" + dict["title"] + "\n"
                result += "介紹：" + dict["hyperlink"] + "\n\n"
        info += result

    elif (action == "input.unknown"):
        #info =  req["queryResult"]["queryText"]
        instruction_text = (
            "你是一個熱心且知識豐富的專業智慧助理。"
            "對於使用者的提問，請回覆重點的關鍵字，不要重述問題。"         
        )


        ai_config = types.GenerateContentConfig(
            max_output_tokens=500, 
            system_instruction=instruction_text
        )
        response = client.models.generate_content(
            model='gemini-3.1-flash-liti', 
            contents=req["queryResult"]["queryText"],
            config=ai_config,
        )

        if response.text:
            info = response.text
        else:
            info = "抱歉，我現在無法生成回應，請稍後再試。"



    return make_response(jsonify({"fulfillmentText": info}))


@app.route("/rate")
def rate():
    #本週新片
    url = "https://www.atmovies.com.tw/movie/new/"
    Data = requests.get(url)
    Data.encoding = "utf-8"
    sp = BeautifulSoup(Data.text, "html.parser")
    lastUpdate = sp.find(class_="smaller09").text[5:]
    print(lastUpdate)
    print()

    result=sp.select(".filmList")

    for x in result:
        title = x.find("a").text
        introduce = x.find("p").text

        movie_id = x.find("a").get("href").replace("/", "").replace("movie", "")
        hyperlink = "http://www.atmovies.com.tw/movie/" + movie_id
        picture = "https://www.atmovies.com.tw/photo101/" + movie_id + "/pm_" + movie_id + ".jpg"

        r = x.find(class_="runtime").find("img")
        rate = ""
        if r != None:
            rr = r.get("src").replace("/images/cer_", "").replace(".gif", "")
            if rr == "G":
                rate = "普遍級"
            elif rr == "P":
                rate = "保護級"
            elif rr == "F2":
                rate = "輔12級"
            elif rr == "F5":
                rate = "輔15級"
            else:
                rate = "限制級"

        t = x.find(class_="runtime").text

        t1 = t.find("片長")
        t2 = t.find("分")
        showLength = t[t1+3:t2]

        t1 = t.find("上映日期")
        t2 = t.find("上映廳數")
        showDate = t[t1+5:t2-8]

        doc = {
            "title": title,
            "introduce": introduce,
            "picture": picture,
            "hyperlink": hyperlink,
            "showDate": showDate,
            "showLength": int(showLength),
            "rate": rate,
            "lastUpdate": lastUpdate
        }

        db = firestore.client()
        doc_ref = db.collection("本週新片含分級").document(movie_id)
        doc_ref.set(doc)
    return "本週新片已爬蟲及存檔完畢，網站最近更新日期為：" + lastUpdate

@app.route("/weather", methods=["GET", "POST"])
def weather():
    R = "<h2>縣市天氣查詢</h2>"
    R += """
        <form action="/weather" method="post">
            請輸入欲查詢縣市(如: 宜蘭縣): <input type="text" name="city">
            <input type="submit" value="查詢">
        </form><hr>
    """
    
    if request.method == "POST":
        city = request.form.get("city").strip().replace("台", "臺")
        # 注意：請確保這是有效的授權碼，或是從氣象署申請自己的 key
        auth_url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
        params = {
            "Authorization": "rdec-key-123-45678-011121314", # 請替換為正確的 Key
            "locationName": city,
            "format": "JSON"
        }
        
        try:
            response = requests.get(auth_url, params=params)
            json_data = response.json()
            
            # 檢查是否有抓到對應縣市的資料
            if "records" in json_data and json_data["records"]["location"]:
                loc_data = json_data["records"]["location"][0]
                
                # 取得縣市名稱
                location_name = loc_data["locationName"]
                
                # 取得天氣現象 (Wx) - 通常在第 0 個 element
                weather_desc = loc_data["weatherElement"][0]["time"][0]["parameter"]["parameterName"]
                
                # 取得降雨機率 (PoP) - 通常在第 1 個 element
                rain_prob = loc_data["weatherElement"][1]["time"][0]["parameter"]["parameterName"]
                
                R += f"<h3>{location_name} 最新天氣預報</h3>"
                R += f"目前狀況：{weather_desc}<br>"
                R += f"降雨機率：{rain_prob}%<br>"
            else:
                R += f"<p style='color:red'>找不到「{city}」的資料。請確認輸入正確（例如：宜蘭縣）。</p>"
                
        except Exception as e:
            R += f"查詢出錯：{str(e)}"
            
    R += "<br><a href='/'>返回首頁</a>"
    return R

@app.route("/road")
def road():
    R = "<h1>台中市十大肇事路口(113年10月)作者:黃建鴻</h1><br>"

    url = " https://newdatacenter.taichung.gov.tw/api/v1/no-auth/resource.download?rid=a1b899c0-511f-4e3d-b22b-814982a97e41"
    headers = {'User-Agent': 'Mozilla/5.0'}
    Data = requests.get(url, headers=headers)
    #print(Data.text)
    JsonData = json.loads(Data.text)
    for item in JsonData:
        R += item["路口名稱"] + ",原因:"+ item["主要肇因"] + ",件數:"+ item["總件數"] +"<br>"

    return R
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
