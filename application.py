import os
import requests
from werkzeug.security import generate_password_hash,check_password_hash

from flask import Flask, session,render_template,request,jsonify,session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
	status="Loggedout"
	try:
		user_email=session["user_email"]
		status=""
	except KeyError:
		user_email=""
	return render_template("index.html",user_email=user_email,
    	status=status)
@app.route("/registerb",methods=['GET','POST'])
def registerb():
	if request.method=="POST":
		email=request.form.get("email")
		if db.execute("SELECT id from users WHERE email=:email",{"email":email}).fetchone() is not None:
			return render_template("login.html",work=Login,error_message="User is alreday registered.Please Login")
		password=request.form.get("password")
		db.execute("INSERT INTO users (email,password) VALUES (:email,:password)",{"email":email,"password":generate_password_hash(password)})
		db.commit()
		return render_template("login.html",work="Login",message="Success")

	return render_template("login.html",work="Login")

@app.route("/register")
def register():
	return render_template("login.html",work="Register")

@app.route("/search",methods=["GET","POST"])
def search():
	if request.method=="POST":
		email=request.form.get("email")
		user=db.execute("SELECT id,password from users WHERE email=:email",{"email":email}).fetchone()
		if user is None:
			return render_template("login.html",error_message="user not registered",work="Register")
		password=request.form.get("password")
		if not check_password_hash(user.password,password):
			return render_template("login.html",error_message="Password not match ,Try Again",work="Login")
		session["user_email"]=email
		session["user_id"]=user.id
	if request.method=="GET" and "user_email" not in session:
		return render_template("login.html",error_message="Please Login first",work="Login")
	return render_template("search.html",user_email=email)	
@app.route("/logout")
def logout():
	try:
		session.pop("user_email")
	except KeyError:
		return render_template("login.html",work="Login",error_message="Please login first")
	return render_template("index.html",status="Loggedout")	

@app.route("/booklist",methods=["POST"])
def booklist():
	if "user_email" not in session:
		return render_template("login.html",work="Login",error_message="please login first")
	book_column=request.form.get("book_column")
	query=request.form.get("query")
	if(book_column=="year"):
		book_list=db.execute("SELECT * FROM books WHERE year=:query ORDER BY title",{"query":query}).fetchall()			
	else:
		book_list=db.execute("SELECT * FROM books WHERE UPPER("+book_column+") =:query ORDER BY title",{"query":query.upper()}).fetchall()
		

	if len(book_list):		
		return render_template("booklist.html",book_list=book_list,user_email=session["user_email"])
	elif book_column!="year":
		error_message="could not find books you were looking for:"
		book_list=db.execute("SELECT * FROM books WHERE UPPER("+book_column+") LIKE :query ORDER BY title",{"query":"%"+query.upper()+"%"}).fetchall()
		if not len(book_list):
			return render_template("error.html",error_message=error_message)
		return render_template("booklist.html",user_email=session["user_email"],message="You may be looking",error_message=error_message)
	else:
		return render_template("error.html",error_message=error_message)

@app.route("/detail/<int:book_id>",methods=["POST","GET"])
def detail(book_id):
	if "user_email" not in session:
		return render_template("login.html",work="Login",error_message="Please login first")
	book=db.execute("SELECT * FROM books WHERE id=:book_id",{"book_id":book_id}).fetchone()
	if book is None:
		return render_template("error.html",error_message="we gt invalid book id")
	#when request is post
	if request.method=="POST":
		user_id=session["user_id"]
		rating=request.form.get("rating")
		comment=request.form.get("comment")
		if db.execute("SELECT id FROM reviews WHERE user_id=:user_id AND book_id=:book_id",{"user_id":user_id,"book_id":book_id}) is None:
			db.execute("INSERT INTO reviews(user_id,book_id,rating,comment) VALUES(:user_id,:book_id,:rating,:comment)",{"user_id":user_id,"book_id":book_id,"rating":rating,"comment":comment})
			db.commit()
		else:
			db.execute("UPDATE reviews SET comment=:comment ,rating=:rating WHERE user_id=:user_id AND book_id=:book_id",{"user_id":user_id,"book_id":book_id,"comment":comment,"rating":rating})
			db.commit()

	"""GOOD READS API"""

	res=requests.get("https://www.goodreads.com/book/review_counts.json",params={"key":"9xKoFa97c5oFQ3PWfqVyw","isbns":book.isbn}).json()
	data=res["books"][0]
	ratings_count=data["ratings_count"]
	average_rating=data["average_rating"]
	reviews=db.execute("SELECT * FROM reviews WHERE book_id=:book_id",{"book_id":book.id}).fetchall()
	users=[]
	for review in reviews:
		email=db.execute("SELECT email FROM users WHERE id=:user_id",{"user_id":review.user_id}).fetchone().email
		users.append((email,review))
	return render_template("detail.html",book=book,users=users,ratings_count=ratings_count,average_rating=average_rating,user_email=session["user_email"])
@app.route("/api/<ISBN>", methods=["GET"])
def api(ISBN):
    book = db.execute("SELECT * FROM books WHERE isbn = :ISBN", {"ISBN": ISBN}).fetchone()
    if book is None:
        return render_template("error.html", error_message="We got an invalid ISBN. "
                                                           "Please check for the errors and try again.")
    reviews = db.execute("SELECT * FROM reviews WHERE book_id = :book_id", {"book_id": book.id}).fetchall()
    count = 0
    rating = 0
    for review in reviews:
        count += 1
        rating += review.rating
    if count:
        average_rating = rating / count
    else:
        average_rating = 0

    return jsonify(
        title=book.title,
        author=book.author,
        year=book.year,
        isbn=book.isbn,
        review_count=count,
        average_score=average_rating
    )

if __name__=="__main__":
	app.run(debug=True)