from datetime import datetime
import pymysql
import pymysql.cursors
from flask import Flask, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 

@app.route('/active')
def active():
    current_date = datetime.now().strftime("%d.%m.%Y")
    current_time = datetime.now().strftime("%H:%M")
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        query = f"""
        SELECT * FROM busytable
        WHERE 
            STR_TO_DATE(cur_date, '%d.%m.%Y') > STR_TO_DATE('{current_date}', '%d.%m.%Y') OR 
            (
                STR_TO_DATE(cur_date, '%d.%m.%Y') = STR_TO_DATE('{current_date}', '%d.%m.%Y') AND 
                TIME_FORMAT(STR_TO_DATE(end_time, '%H:%i'), '%H:%i') >= TIME_FORMAT(STR_TO_DATE('{current_time}', '%H:%i'), '%H:%i')
            )
        ORDER BY 
            STR_TO_DATE(cur_date, '%d.%m.%Y'), 
            TIME_FORMAT(STR_TO_DATE(start_time, '%H:%i'), '%H:%i')
        """
        cursor.execute(query)
        res = cursor.fetchall()
    return res if res else ""

@app.route('/inactive')
def inactive():
    current_date = datetime.now().strftime("%d.%m.%Y")
    current_time = datetime.now().strftime("%H:%M")
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        query = f"""
        SELECT * FROM busytable
        WHERE NOT(
            STR_TO_DATE(cur_date, '%d.%m.%Y') > STR_TO_DATE('{current_date}', '%d.%m.%Y') OR 
            (
                STR_TO_DATE(cur_date, '%d.%m.%Y') = STR_TO_DATE('{current_date}', '%d.%m.%Y') AND 
                TIME_FORMAT(STR_TO_DATE(end_time, '%H:%i'), '%H:%i') >= TIME_FORMAT(STR_TO_DATE('{current_time}', '%H:%i'), '%H:%i')
            ))
        ORDER BY 
            STR_TO_DATE(cur_date, '%d.%m.%Y'), 
            TIME_FORMAT(STR_TO_DATE(start_time, '%H:%i'), '%H:%i')
        """
        cursor.execute(query)
        res = cursor.fetchall()
    return res if res else ""



@app.route('/delete',methods=['POST'])
def delete():
    id = request.json['id']
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute(f"DELETE FROM `busytable` WHERE (`id` = '{id}');")
    connection.commit()
    return 'ok'

@app.route('/users',methods=['GET'])
def users():
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM users;")
        return cursor.fetchall()

@app.route('/comms',methods=['GET'])
def comms():
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM comm;")
        return cursor.fetchall()

@app.route('/changeblock',methods=['POST'])
def changeblock():
    id = request.json['id']
    banned = request.json['banned']
    connection = pymysql.connect(host="127.0.0.1", port=3308, user="root", password="root", database="titanit", cursorclass=pymysql.cursors.DictCursor)
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE `users` SET `banned`={banned}, `warn` = '{3 if banned == '1' else 0}' WHERE `id` = {id};")
    connection.commit()
    return 'ok'

if __name__ == '__main__':
    app.run(host= '0.0.0.0', port="5000")