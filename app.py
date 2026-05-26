import asyncio
from flask import Flask, render_template, request
import aiohttp

app = Flask(__name__)

BASE_URL = "https://jsonplaceholder.typicode.com"
TIMEOUT = aiohttp.ClientTimeout(total=10)


# -------------------------------
# Асинхронная функция получения JSON
# -------------------------------
async def fetch_json(session, url):
    """
    Универсальная асинхронная функция для GET-запросов.
    """
    try:
        async with session.get(url, timeout=TIMEOUT) as response:
            response.raise_for_status()
            return await response.json()
    except Exception as e:
        print(f"Ошибка запроса {url}: {e}")
        return None


# -------------------------------
# Поиск пользователей
# -------------------------------
async def search_users(username_query, email_query):
    """
    Асинхронно получает список пользователей
    и фильтрует по username и/или email.
    """
    async with aiohttp.ClientSession() as session:
        users = await fetch_json(session, f"{BASE_URL}/users")

    if not users:
        return []

    results = []

    for user in users:
        match_username = True
        match_email = True

        if username_query:
            match_username = username_query.lower() in user["username"].lower()

        if email_query:
            match_email = email_query.lower() in user["email"].lower()

        if match_username and match_email:
            results.append(user)

    return results


# -------------------------------
# Получение автора поста
# -------------------------------
async def get_author(session, user_id):
    """
    Асинхронно получает имя автора по userId.
    """
    user = await fetch_json(session, f"{BASE_URL}/users/{user_id}")

    if user and isinstance(user, dict):
        return user.get("name", "Неизвестно")

    return "Неизвестно"


# -------------------------------
# Поиск постов
# -------------------------------
async def search_posts(title_query, body_query):
    """
    Асинхронно получает посты, фильтрует их,
    затем параллельно получает авторов через asyncio.gather.
    """
    async with aiohttp.ClientSession() as session:
        posts = await fetch_json(session, f"{BASE_URL}/posts")

        if not posts:
            return []

        filtered = []

        for post in posts:
            match_title = True
            match_body = True

            if title_query:
                match_title = title_query.lower() in post["title"].lower()

            if body_query:
                match_body = body_query.lower() in post["body"].lower()

            if match_title and match_body:
                filtered.append(post)

        # Параллельно получаем авторов
        tasks = [get_author(session, post["userId"]) for post in filtered]
        authors = await asyncio.gather(*tasks)

        # Добавляем имя автора в каждый пост
        for post, author in zip(filtered, authors):
            post["author"] = author

        return filtered


@app.route("/", methods=["GET", "POST"])
async def index():
    users = []
    posts = []
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        title = request.form.get("title")
        body = request.form.get("body")

        try:
            tasks = []

            # Если есть критерии пользователей
            if username or email:
                tasks.append(search_users(username, email))
            else:
                tasks.append(asyncio.sleep(0, result=[]))

            # Если есть критерии постов
            if title or body:
                tasks.append(search_posts(title, body))
            else:
                tasks.append(asyncio.sleep(0, result=[]))

            # Параллельное выполнение
            users, posts = await asyncio.gather(*tasks)

        except Exception as e:
            error = f"Ошибка выполнения запроса: {e}"

    return render_template("index.html", users=users, posts=posts, error=error)


if __name__ == "__main__":
    app.run(debug=True)