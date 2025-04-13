from datetime import datetime, timedelta
import cv2
import pymysql
import pymysql.cursors
import time

freeDict = {
    '1': '1', '2': '1', '3': '1', '4': '1', '5': '1',
    '6': '1', '7': '1', '8': '1', '9': '1', '10': '1',
    '11': '1', '12': '1', '13': '1', '14': '1'
}

def draw_numbers(koord, n, image, font, fontScale, color, thickness):
    cv2.putText(image, n, koord, font, fontScale, color, thickness, cv2.LINE_AA)

while True:
    connection = pymysql.connect(
        host="127.0.0.1",
        port=3308,
        user="root",
        password="root",
        database="titanit",
        cursorclass=pymysql.cursors.DictCursor
    )
    
    with connection.cursor() as cursor:
        current_time_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        # Получаем все забронированные места на эту дату и время
        cursor.execute(f"""
            SELECT `place`
            FROM `titanit`.`busytable`
            WHERE 
                `cur_date` = '{datetime.now().strftime("%d.%m.%Y")}'
                AND '{datetime.now().strftime("%H:%M")}' BETWEEN `start_time` AND `end_time`;
        """)
        booked_places = [str(row['place']) for row in cursor.fetchall()]
        
        cursor.execute(f"""
            SELECT `place` FROM `titanit`.`busytable`
            WHERE `cur_date` = '{datetime.now().strftime("%d.%m.%Y")}'
            AND `end_time` <= ADDTIME('{datetime.now().strftime("%H:%M")}', '00:15')
            AND `end_time` >= '{datetime.now().strftime("%H:%M")}'
        """)

        orange_places = [str(row['place']) for row in cursor.fetchall()]

        cursor.execute("""SELECT 
            place,
            ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM `titanit`.`busytable` WHERE check_in = 1), 2) AS occupancy_percentage
        FROM 
            `titanit`.`busytable`
        WHERE 
            check_in = 1
        GROUP BY 
            place""")
        perc = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0,
    6: 0, 7: 0, 8: 0, 9: 0, 10: 0,
    11: 0, 12: 0, 13: 0, 14: 0}
        for i in cursor.fetchall():
            perc[i['place']] = int(float(str(i['occupancy_percentage'])))


        # Все возможные места (из freeDict)
        all_places = list(freeDict.keys())
        
        # Свободные места = все места минус забронированные, где значение '1' в freeDict
        available_places = [
            place for place in all_places 
            if place not in booked_places and freeDict.get(place) == '1'
        ]

    if 'connection' in locals():
        connection.close()

    image = cv2.imread('banket.jpg')
    font = cv2.FONT_HERSHEY_SIMPLEX
    fontScale = 1
    color = (0, 0, 0)
    thickness = 2

    koord_arr = [(166, 240),
                (246, 240),
                (326, 240),
                (584, 158),
                (688, 158),
                (792, 158),
                (894, 158),
                (998, 158),
                (1090, 370),
                (570, 588),
                (674, 588),
                (778, 588),
                (880, 588),
                (984, 588),
                ]

    zaliv_arr = [
        [(153, 251), (199, 203)],
        [(233,251), (280,203)],
        [(313,251), (359,203)],
        [(566, 92), (621, 195)],
        [(670,93), (725,195)],
        [(774,94), (829,197)],
        [(877,95), (931,198)],
        [(979,97), (1034,200)],
        [(1068,211), (1130,521)],
        [(566,533), (621,636)],
        
        [(670,530), (725,634)],
        [(774,530), (829,632)],
        [(877,529), (931, 632)],
        [(979, 528), (1034,630)],
    ]

    for n in range(1, 15):
        if str(n) not in available_places:
            if str(n) in orange_places:
                cv2.rectangle(image, zaliv_arr[n-1][0], zaliv_arr[n-1][1], (55, 96, 255), cv2.FILLED)
            else:
                cv2.rectangle(image, zaliv_arr[n-1][0], zaliv_arr[n-1][1], (00, 00, 255), cv2.FILLED)
        draw_numbers(koord_arr[n-1], str(n), image, font, fontScale, color, thickness)

    for n in range(1,4):
        draw_numbers((koord_arr[n-1][0]-15, koord_arr[n-1][1]+50), f"{str(perc[n])}%", image, font, fontScale, color, thickness)
    for n in range(4, 9):
        draw_numbers((koord_arr[n-1][0]-25, koord_arr[n-1][1]+68), f"{str(perc[n])}%", image, font, fontScale, color, thickness)
    draw_numbers((1070, 400), f"{str(perc[9])}%", image, font, fontScale, color, thickness)
    for n in range(10, 15):
        draw_numbers((koord_arr[n-1][0]-5, koord_arr[n-1][1]-68), f"{str(perc[n])}%", image, font, fontScale, color, thickness)   

    cv2.imwrite(r'C:\Users\79287\Desktop\maza\front\src\assets\img.jpg', image)

    time.sleep(60)