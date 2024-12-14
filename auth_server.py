from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import Error
from datetime import datetime

app = Flask(__name__)
CORS(app)


def create_connection():
    try:
        connection = psycopg2.connect(
            host="localhost",
            database="postgres",
            user="postgres",
            password="Alisher@2003",
            port="5432"
        )
        return connection
    except (Exception, Error) as error:
        print("Ошибка подключения к PostgreSQL:", error)
        return None


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    required_fields = ['username', 'password', 'first_name', 'last_name',
                       'middle_name', 'phone', 'email', 'birth_date']

    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Заполните все обязательные поля'}), 400

    connection = create_connection()
    if not connection:
        return jsonify({'error': 'Ошибка подключения к базе данных'}), 500

    try:
        cursor = connection.cursor()

        # Проверяем существование пользователя
        cursor.execute("SELECT id FROM users WHERE username = %s OR email = %s",
                       (data['username'], data['email']))
        if cursor.fetchone():
            return jsonify({'error': 'Пользователь или email уже существует'}), 409

        # Добавляем нового пользователя
        cursor.execute("""
            INSERT INTO users (
                username, password, first_name, last_name, 
                middle_name, phone, email, birth_date
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
            RETURNING id""",
                       (data['username'], data['password'], data['first_name'],
                        data['last_name'], data['middle_name'], data['phone'],
                        data['email'], data['birth_date'])
                       )
        user_id = cursor.fetchone()[0]
        connection.commit()

        return jsonify({
            'message': 'Регистрация успешна',
            'user_id': user_id
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Отсутствует имя пользователя или пароль'}), 400

    connection = create_connection()
    if not connection:
        return jsonify({'error': 'Ошибка подключения к базе данных'}), 500

    try:
        cursor = connection.cursor()
        cursor.execute("""
            SELECT id, password, first_name, last_name, middle_name, 
                   phone, email, birth_date 
            FROM users 
            WHERE username = %s""",
                       (username,)
                       )
        result = cursor.fetchone()

        if not result:
            return jsonify({'error': 'Неверные учетные данные'}), 401

        user_id, stored_password = result[0], result[1]

        if password != stored_password:  # Проверяем пароль
            return jsonify({'error': 'Неверные учетные данные'}), 401

        # Формируем полные данные пользователя
        user_data = {
            'user_id': user_id,
            'first_name': result[2],
            'last_name': result[3],
            'middle_name': result[4],
            'phone': result[5],
            'email': result[6],
            'birth_date': result[7].strftime('%Y-%m-%d') if result[7] else None
        }

        return jsonify({
            'message': 'Вход выполнен успешно',
            'user_id': user_id,
            'user_data': user_data  # Возвращаем полные данные
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()


@app.route('/api/profile/<int:user_id>', methods=['GET', 'PUT'])
def profile(user_id):
    connection = create_connection()
    if not connection:
        return jsonify({'error': 'Ошибка подключения к базе данных'}), 500

    try:
        cursor = connection.cursor()

        if request.method == 'GET':
            cursor.execute("""
                SELECT first_name, last_name, middle_name, 
                       phone, email, birth_date 
                FROM users 
                WHERE id = %s""",
                           (user_id,)
                           )
            result = cursor.fetchone()

            if not result:
                return jsonify({'error': 'Пользователь не найден'}), 404

            return jsonify({
                'first_name': result[0],
                'last_name': result[1],
                'middle_name': result[2],
                'phone': result[3],
                'email': result[4],
                'birth_date': result[5].strftime('%Y-%m-%d') if result[5] else None
            })

        elif request.method == 'PUT':
            data = request.json
            cursor.execute("""
                UPDATE users 
                SET first_name = %s, last_name = %s, middle_name = %s,
                    phone = %s, email = %s, birth_date = %s
                WHERE id = %s
                RETURNING id""",
                           (data['first_name'], data['last_name'], data['middle_name'],
                            data['phone'], data['email'], data['birth_date'], user_id)
                           )

            if cursor.rowcount == 0:
                return jsonify({'error': 'Пользователь не найден'}), 404

            connection.commit()
            return jsonify({'message': 'Профиль успешно обновлен'})

    except Exception as e:
        if request.method == 'PUT':
            connection.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        connection.close()




if __name__ == '__main__':
    app.run(debug=True, port=5000)