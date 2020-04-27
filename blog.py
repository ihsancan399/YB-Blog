import re
from flask import Flask, render_template,flash,redirect,url_for,session,logging,request,g
import requests
from bs4 import BeautifulSoup
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps


#Kullanıcı Giriş Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapın...","danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanıcı Kayıt Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25),validators.DataRequired(message="Lütfen İsim Soyisim Giriniz!")])
    username = StringField("Kullanıcı Adı", validators=[validators.Length(min=5, max=35),validators.DataRequired(message="Lütfen Bir Kullanıcı Adı Giriniz")])
    email = StringField("Email Adresi", validators=[validators.Length(min=10, max=45),validators.Email(message="Lütfen Geçerli bir Email Adresi giriniz!")])
    password = PasswordField("Parola",validators=[
        validators.DataRequired(message="Lütfen bir parola girin!"),
        validators.EqualTo(fieldname = "confirm",message="Parola Uyuşmuyor!"),
        validators.Length(min=8,max=30)
    ])
    confirm = PasswordField("Parola Doğrulama")

#Kullanıcı Çıkış Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")
app = Flask(__name__)

 

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "ybblog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)

#Anasayfa
@app.route("/")
def index():
    return render_template("index.html")

#Hakkımda
@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author = %s"
    result = cursor.execute(sorgu,(session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        return render_template("dashboard.html",articles = articles)
    else:
        return render_template("dashboard.html")

#Register
@app.route("/register",methods = ["GET","POST"])
def register():
    form1 = RegisterForm(request.form)
    if request.method == "POST" and form1.validate():
        name = form1.name.data
        username = form1.username.data
        email = form1.email.data
        password = sha256_crypt.encrypt(form1.password.data)
        cursor = mysql.connection.cursor()
        sorgu = "Insert into users(name,username,email,password) VALUES(%s,%s,%s,%s)"
        cursor.execute(sorgu,(name,username,email,password))
        mysql.connection.commit()
        cursor.close()
        flash("Başarıyla Kayıt Oldunuz.","success")
        return redirect(url_for("login"))
    else:    
        return render_template("register.html",form1 = form1)

#Covid-19
@app.route("/corona")
def corona():
    url = "https://www.worldometers.info/coronavirus/"
    r = requests.get(url)
    s = BeautifulSoup(r.text, "html.parser")
    data = s.find_all("div", class_="maincounter-number")
    deaths = str(data[1].text.strip()).split(",")
    deaths = int(deaths[0]+deaths[1])
    cured = str(data[2].text.strip()).split(",")
    cured = int(cured[0]+cured[1])
    closed_cases = "Toplam Kapanmış Vaka Sayısı : {: ,}".format(deaths + cured)
    percent = (deaths * 100) / (deaths + cured).__round__()
    percent1 = "Ölme Riski : %{}".format(percent.__round__())
    return render_template("corona.html", percent1=percent1, data=data, deaths=deaths, cured=cured, closed_cases=closed_cases)

#Login
@app.route("/login",methods=["GET","POST"])
def login():
    form1 = LoginForm(request.form)
    if request.method == "POST":
        username = form1.username.data
        password_entered = form1.password.data
        cursor = mysql.connection.cursor()
        sorgu = "Select * From users where username = %s"
        result = cursor.execute(sorgu,(username,))
        if result > 0:
            data = cursor.fetchone()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered,real_password):
                flash("Başarıyla Giriş Yaptınız...","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parola Yanlış!","danger")
                return redirect(url_for("login"))
        else:
            flash("Böyle Bir kullanıcı bulunmuyor!","danger")
            return redirect(url_for("login"))
    return render_template("login.html",form1 = form1)

#Logout
@app.route("/logout")
def logout():
    session.clear()
    flash("Başarıyla Çıkış Yaptınız!","success")
    return redirect(url_for("index"))
#Makale ekle
@app.route("/addarticles",methods = ["GET","POST"])
def addArticle():
    form1 = ArticleForm(request.form)
    if request.method == "POST" and form1.validate():
        title = form1.title.data
        content = form1.content.data
        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles (title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()
        flash("Makale Başarıyla Eklendi...","success")
        return redirect(url_for("dashboard"))
    return render_template("addarticles.html",form1 = form1)

class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[
        validators.Length(min=4,max=50)])
    content =TextAreaField("Makale İçeriği",validators=[
        validators.Length(min=10)])

@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles"
    result = cursor.execute(sorgu)
    if result > 0:
        articles = cursor.fetchall()
        return render_template("articles.html",articles = articles)
    else:
        return render_template("articles.html")
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where id = %s"
    result = cursor.execute(sorgu,(id,))
    if result > 0:
        article = cursor.fetchone()
        return render_template("article.html",article = article)
    else:
        return render_template("article.html") 
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    sorgu = "Select * from articles where author = %s and id = %s"
    result = cursor.execute(sorgu,(session["username"],id))
    if result > 0:
      sorgu2 = "Delete from articles where id = %s" 
      cursor.execute(sorgu2,(id,))
      mysql.connection.commit()
      return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya bu işleme yetkiniz yok","danger")
        return redirect(url_for("index"))
@app.route("/edit/<string:id>",methods = ["GET","POST"]) 
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id = %s and author = %s"
        result = cursor.execute(sorgu,(id,session["username"]))
        if result == 0:
           flash("Böyle bir makale yok veya bu işleme yetkiniz yok", "danger")
           return redirect(url_for("index"))
        else:
            article = cursor.fetchone()
            form1 = ArticleForm()
            form1.title.data = article["title"]
            form1.content.data = article["content"]
            return render_template("update.html",form1 = form1)
    else:
        form1 = ArticleForm(request.form)
        newTitle = form1.title.data
        newContent = form1.content.data
        sorgu2 = "Update articles Set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(sorgu2,(newTitle,newContent,id))
        mysql.connection.commit()
        flash("Makale başarıyla güncellendi...","success")
        return redirect(url_for("dashboard"))
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where title like '%" + keyword + "%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Makale Bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html",articles = articles)
if __name__ == "__main__":
    app.run(debug=True)
