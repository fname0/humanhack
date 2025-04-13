import sys
import pymysql
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import Qt
from datetime import datetime

class NumberDisplayApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TitanIT check-in")
        self.setFixedSize(400, 300)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignCenter)
        self.number_label = QLabel("Число не загружено")
        self.number_label.setAlignment(Qt.AlignCenter)
        self.number_label.setStyleSheet("font-size: 48px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(self.number_label)
        
        self.update_button = QPushButton("Обновить число")
        self.update_button.setMinimumHeight(50)
        self.update_button.setStyleSheet("font-size: 20px;")
        self.update_button.clicked.connect(self.fetch_number_from_db)
        layout.addWidget(self.update_button)
        
        # Параметры подключения к БД (замените на свои)
        self.db_config = {
            'host': 'localhost',
            'user': 'ваш_пользователь',
            'password': 'ваш_пароль',
            'database': 'ваша_база_данных',
            'charset': 'utf8mb4',
            'cursorclass': pymysql.cursors.DictCursor
        }
        
        self.fetch_number_from_db()
    
    def fetch_number_from_db(self):
        connection = pymysql.connect(
            host="127.0.0.1",
            port=3308,
            user="root",
            password="root",
            database="titanit",
            cursorclass=pymysql.cursors.DictCursor
        )
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT `prufcode`
            FROM `titanit`.`busytable`
            WHERE 
                `cur_date` = '{datetime.now().strftime("%d.%m.%Y")}'
                AND '{datetime.now().strftime("%H:%M")}' BETWEEN `start_time` AND `end_time`
                AND place = 1;""")
            result = cursor.fetchone()
            if result:
                self.number_label.setText(str(result['prufcode']))
            else:
                self.number_label.setText("Нет данных")
        connection.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NumberDisplayApp()
    window.show()
    sys.exit(app.exec_())