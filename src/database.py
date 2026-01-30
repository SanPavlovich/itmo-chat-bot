"""
Модуль для работы с базой данных учебных планов (MongoDB)
"""
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()


@dataclass
class Course:
    """Класс для хранения информации о дисциплине"""
    name: str
    type: str  # обязательная/выборная
    credits: str
    semester: str
    description: str = ""
    skills: List[str] = None
    
    def __post_init__(self):
        if self.skills is None:
            self.skills = []
    
    def to_dict(self) -> Dict:
        """Преобразует объект в словарь для MongoDB"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Course':
        """Создает объект из словаря MongoDB"""
        return cls(**data)


@dataclass
class MasterProgram:
    """Класс для хранения информации о магистерской программе"""
    id: str
    title: str
    url: str
    description: str
    courses: List[Course]
    requirements: List[str]
    skills: List[str]
    career: List[str]
    
    def __post_init__(self):
        if self.courses is None:
            self.courses = []
        if self.requirements is None:
            self.requirements = []
        if self.skills is None:
            self.skills = []
        if self.career is None:
            self.career = []
    
    def to_dict(self) -> Dict:
        """Преобразует объект в словарь для MongoDB"""
        data = asdict(self)
        data['courses'] = [course.to_dict() for course in self.courses]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MasterProgram':
        """Создает объект из словаря MongoDB"""
        courses = [Course.from_dict(c) for c in data.get('courses', [])]
        return cls(
            id=data.get('id', ''),
            title=data.get('title', ''),
            url=data.get('url', ''),
            description=data.get('description', ''),
            courses=courses,
            requirements=data.get('requirements', []),
            skills=data.get('skills', []),
            career=data.get('career', [])
        )


class ProgramDatabase:
    """База данных магистерских программ на MongoDB"""
    
    def __init__(self, mongodb_uri: str = None):
        """
        Инициализация подключения к MongoDB
        
        Args:
            mongodb_uri: Строка подключения к MongoDB. Если не указана, берется из переменной окружения MONGODB_URI
        """
        if mongodb_uri is None:
            mongodb_uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/chatbot_db')
        
        self.mongodb_uri = mongodb_uri
        self.client = None
        self.db = None
        self.programs_collection = None
        self.user_profiles_collection = None
        
        # Подключаемся к базе данных
        self._connect()
    
    def _connect(self):
        """Устанавливает соединение с MongoDB"""
        try:
            self.client = MongoClient(self.mongodb_uri)
            # Проверяем подключение
            self.client.admin.command('ping')
            
            # Получаем имя базы данных из URI или используем 'chatbot_db' по умолчанию
            db_name = self.mongodb_uri.split('/')[-1] if '/' in self.mongodb_uri else 'chatbot_db'
            self.db = self.client[db_name]
            
            # Получаем коллекции
            self.programs_collection = self.db['programs']
            self.user_profiles_collection = self.db['user_profiles']
            
            # Создаем индексы для оптимизации запросов
            self._create_indexes()
            
            print(f"Успешное подключение к MongoDB: {db_name}")
        except ConnectionFailure as e:
            print(f"Ошибка подключения к MongoDB: {e}")
            raise
        except Exception as e:
            print(f"Неожиданная ошибка при подключении к MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """Создает индексы для оптимизации запросов"""
        try:
            # Индекс по id программы
            self.programs_collection.create_index([('id', 1)], unique=True)
            
            # Индексы для поиска по навыкам и дисциплинам
            self.programs_collection.create_index([('skills', 1)])
            self.programs_collection.create_index([('courses.name', 'text')])
            self.programs_collection.create_index([('courses.description', 'text')])
            
            # Индекс по user_id для профилей пользователей
            self.user_profiles_collection.create_index([('user_id', 1)], unique=True)
        except PyMongoError as e:
            print(f"Предупреждение: не удалось создать индексы: {e}")
    
    def close(self):
        """Закрывает соединение с MongoDB"""
        if self.client:
            self.client.close()
            print("Соединение с MongoDB закрыто")
    
    def add_program(self, program: MasterProgram):
        """Добавляет программу в базу данных"""
        try:
            self.programs_collection.update_one(
                {'id': program.id},
                {'$set': program.to_dict()},
                upsert=True
            )
        except PyMongoError as e:
            print(f"Ошибка при добавлении программы: {e}")
            raise
    
    def get_program(self, program_id: str) -> Optional[MasterProgram]:
        """Получает программу по ID"""
        try:
            data = self.programs_collection.find_one({'id': program_id})
            if data:
                data.pop('_id', None)  # Удаляем поле _id MongoDB
                return MasterProgram.from_dict(data)
            return None
        except PyMongoError as e:
            print(f"Ошибка при получении программы: {e}")
            return None
    
    def get_all_programs(self) -> List[MasterProgram]:
        """Получает все программы"""
        try:
            programs = []
            for data in self.programs_collection.find():
                data.pop('_id', None)
                programs.append(MasterProgram.from_dict(data))
            return programs
        except PyMongoError as e:
            print(f"Ошибка при получении всех программ: {e}")
            return []
    
    def search_courses(self, query: str) -> List[Course]:
        """Ищет дисциплины по запросу"""
        try:
            query_lower = query.lower()
            results = []
            
            # Используем текстовый поиск MongoDB
            for data in self.programs_collection.find({
                '$or': [
                    {'courses.name': {'$regex': query_lower, '$options': 'i'}},
                    {'courses.description': {'$regex': query_lower, '$options': 'i'}}
                ]
            }):
                data.pop('_id', None)
                program = MasterProgram.from_dict(data)
                for course in program.courses:
                    if (query_lower in course.name.lower() or 
                        query_lower in course.description.lower()):
                        results.append(course)
            
            return results
        except PyMongoError as e:
            print(f"Ошибка при поиске дисциплин: {e}")
            return []
    
    def get_elective_courses(self, program_id: str) -> List[Course]:
        """Получает выборные дисциплины программы"""
        try:
            data = self.programs_collection.find_one({'id': program_id})
            if not data:
                return []
            
            data.pop('_id', None)
            program = MasterProgram.from_dict(data)
            return [c for c in program.courses if 'выборн' in c.type.lower()]
        except PyMongoError as e:
            print(f"Ошибка при получении выборных дисциплин: {e}")
            return []
    
    def get_user_profile(self, user_id: int) -> Dict:
        """Получает профиль пользователя"""
        try:
            data = self.user_profiles_collection.find_one({'user_id': user_id})
            if data:
                data.pop('_id', None)
                return data
            return {}
        except PyMongoError as e:
            print(f"Ошибка при получении профиля пользователя: {e}")
            return {}
    
    def update_user_profile(self, user_id: int, profile: Dict):
        """Обновляет профиль пользователя"""
        try:
            profile['user_id'] = user_id
            self.user_profiles_collection.update_one(
                {'user_id': user_id},
                {'$set': profile},
                upsert=True
            )
        except PyMongoError as e:
            print(f"Ошибка при обновлении профиля пользователя: {e}")
            raise
    
    def get_program_summary(self, program_id: str) -> str:
        """Получает краткое описание программы"""
        program = self.get_program(program_id)
        if not program:
            return "Программа не найдена"
        
        summary = f"📚 {program.title}\n\n"
        summary += f"📝 Описание: {program.description[:300]}...\n\n"
        
        if program.courses:
            summary += f"📖 Дисциплин: {len(program.courses)}\n"
        
        if program.skills:
            summary += f"💡 Навыки: {', '.join(program.skills[:5])}\n"
        
        if program.career:
            summary += f"💼 Карьера: {', '.join(program.career[:3])}\n"
        
        return summary
    
    def compare_programs(self, program_id_1: str, program_id_2: str) -> str:
        """Сравнивает две программы"""
        prog1 = self.get_program(program_id_1)
        prog2 = self.get_program(program_id_2)
        
        if not prog1 or not prog2:
            return "Одна или обе программы не найдены"
        
        comparison = f"🔍 Сравнение программ:\n\n"
        comparison += f"📚 {prog1.title}\n"
        comparison += f"📚 {prog2.title}\n\n"
        
        # Сравнение количества дисциплин
        comparison += f"📖 Дисциплин: {len(prog1.courses)} vs {len(prog2.courses)}\n"
        
        # Сравнение навыков
        skills1 = set(prog1.skills)
        skills2 = set(prog2.skills)
        common = skills1 & skills2
        unique1 = skills1 - skills2
        unique2 = skills2 - skills1
        
        if common:
            comparison += f"\n✅ Общие навыки: {', '.join(list(common)[:5])}\n"
        if unique1:
            comparison += f"🔹 Только в {prog1.title}: {', '.join(list(unique1)[:3])}\n"
        if unique2:
            comparison += f"🔸 Только в {prog2.title}: {', '.join(list(unique2)[:3])}\n"
        
        return comparison
    
    def search_programs_by_skill(self, skill: str) -> List[MasterProgram]:
        """Ищет программы по навыку"""
        try:
            programs = []
            for data in self.programs_collection.find({'skills': {'$regex': skill, '$options': 'i'}}):
                data.pop('_id', None)
                programs.append(MasterProgram.from_dict(data))
            return programs
        except PyMongoError as e:
            print(f"Ошибка при поиске программ по навыку: {e}")
            return []
    
    def search_programs_by_career(self, career: str) -> List[MasterProgram]:
        """Ищет программы по карьерному направлению"""
        try:
            programs = []
            for data in self.programs_collection.find({'career': {'$regex': career, '$options': 'i'}}):
                data.pop('_id', None)
                programs.append(MasterProgram.from_dict(data))
            return programs
        except PyMongoError as e:
            print(f"Ошибка при поиске программ по карьере: {e}")
            return []
    
    def delete_program(self, program_id: str) -> bool:
        """Удаляет программу из базы данных"""
        try:
            result = self.programs_collection.delete_one({'id': program_id})
            return result.deleted_count > 0
        except PyMongoError as e:
            print(f"Ошибка при удалении программы: {e}")
            return False
    
    def get_programs_count(self) -> int:
        """Возвращает количество программ в базе данных"""
        try:
            return self.programs_collection.count_documents({})
        except PyMongoError as e:
            print(f"Ошибка при подсчете программ: {e}")
            return 0


if __name__ == "__main__":
    # Тестирование базы данных
    db = ProgramDatabase()
    
    try:
        # Создаем тестовую программу
        test_program = MasterProgram(
            id="test",
            title="Тестовая программа",
            url="https://test.com",
            description="Описание тестовой программы",
            courses=[
                Course(name="Математика", type="обязательная", credits="5", semester="1"),
                Course(name="Программирование", type="обязательная", credits="4", semester="1"),
                Course(name="Машинное обучение", type="выборная", credits="3", semester="2"),
            ],
            requirements=["Бакалавриат"],
            skills=["Python", "ML", "Data Science"],
            career=["Data Scientist", "ML Engineer"]
        )
        
        db.add_program(test_program)
        print("Программа добавлена")
        print(db.get_program_summary("test"))
        
        # Тест поиска по навыку
        print("\nПоиск по навыку 'Python':")
        programs = db.search_programs_by_skill("Python")
        for prog in programs:
            print(f"- {prog.title}")
        
        # Тест получения количества программ
        print(f"\nВсего программ в базе: {db.get_programs_count()}")
        
    finally:
        db.close()
