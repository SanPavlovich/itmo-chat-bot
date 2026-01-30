# Настройка MongoDB для проекта

## Установка MongoDB

### macOS (с Homebrew)
```bash
brew tap mongodb/brew
brew install mongodb-community
```

### Linux (Ubuntu/Debian)
```bash
sudo apt-get install mongodb
```

### Windows
Скачайте установщик с официального сайта: https://www.mongodb.com/try/download/community

## Запуск MongoDB

### macOS
```bash
brew services start mongodb-community
```

### Linux
```bash
sudo systemctl start mongodb
# или
sudo service mongodb start
```

### Windows
Запустите MongoDB как службу через меню "Службы" или используйте команду:
```bash
net start MongoDB
```

## Проверка статуса MongoDB

```bash
# macOS
brew services list | grep mongodb

# Linux
sudo systemctl status mongodb

# Windows
sc query MongoDB
```

## Остановка MongoDB

### macOS
```bash
brew services stop mongodb-community
```

### Linux
```bash
sudo systemctl stop mongodb
```

### Windows
```bash
net stop MongoDB
```

## Настройка подключения

В файле `.env` укажите строку подключения к MongoDB:

```env
MONGODB_URI=mongodb://localhost:27017/chatbot_db
```

Для MongoDB Atlas (облачная база данных):
```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/chatbot_db?retryWrites=true&w=majority
```

## Инициализация данных

После запуска MongoDB выполните:
```bash
.venv/bin/python scripts/init_data.py
```

## Устранение проблем

### Ошибка "Connection refused"
Убедитесь, что MongoDB запущена:
```bash
# macOS/Linux
ps aux | grep mongod

# Windows
tasklist | findstr mongod
```

### Ошибка "Authentication failed"
Если вы используете MongoDB с аутентификацией, добавьте учетные данные в строку подключения:
```env
MONGODB_URI=mongodb://username:password@localhost:27017/chatbot_db
```

### Проверка подключения
```bash
mongosh
# или
mongo
```

## Мониторинг MongoDB

### MongoDB Compass (GUI)
Скачайте с: https://www.mongodb.com/try/download/compass

### Командная строка
```bash
mongosh
> use chatbot_db
> show collections
> db.programs.find()
```
