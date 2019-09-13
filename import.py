import csv
from sqlalchemy import create_engine
import os
from sqlalchemy.orm import scoped_session,sessionmaker

engine = create_engine("postgres://jncywohmgzwfov:f11190e46d93c3ff6362e054acae0e57c62f3ba1a4f7df3ed2fbf3de27844725@ec2-174-129-209-212.compute-1.amazonaws.com:5432/d9m1nvcfr8d6fv")
db=scoped_session(sessionmaker(bind=engine))

def main():
	f=open("books.csv","r")
	reader=csv.reader(f)
	next(reader)
	for isbn,title,author,year in reader:
		db.execute("INSERT INTO books (isbn,title,author,year) VALUES (:isbn,:title,:author,:year)",{"isbn":isbn,"title":title,"author":author,"year":year})
		db.commit()
		print(f"ADDED book with ISBN:{isbn} Title:{title} Author:{author} Year:{year}")
if __name__=='__main__':
	main()		