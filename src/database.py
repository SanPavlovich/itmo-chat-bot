"""
Модуль для работы с базой данных учебных планов
"""
import json
import os
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


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


class ProgramDatabase:
    """База данных магистерских программ"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.programs_file = os.path.join(data_dir, "programs.json")
        self.user_profiles_file = os.path.join(data_dir, "user_profiles.json")
        self.programs: Dict[str, MasterProgram] = {}
        self.user_profiles: Dict[int, Dict] = {}
        
        # Создаем директорию если не существует
        os.makedirs(data_dir, exist_ok=True)
        
        # Загружаем данные
        self.load_programs()
        self.load_user_profiles()
    
    def load_programs(self):
        """Загружает программы из JSON файла"""
        try:
            with open(self.programs_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for program_id, program_data in data.items():
                    courses = [Course(**c) for c in program_data.get('courses', [])]
                    self.programs[program_id] = MasterProgram(
                        id=program_id,
                        title=program_data.get('title', ''),
                        url=program_data.get('url', ''),
                        description=program_data.get('description', ''),
                        courses=courses,
                        requirements=program_data.get('requirements', []),
                        skills=program_data.get('skills', []),
                        career=program_data.get('career', [])
                    )
        except FileNotFoundError:
            print(f"Файл {self.programs_file} не найден. База данных пуста.")
    
    def save_programs(self):
        """Сохраняет программы в JSON файл"""
        data = {}
        for program_id, program in self.programs.items():
            data[program_id] = {
                'id': program.id,
                'title': program.title,
                'url': program.url,
                'description': program.description,
                'courses': [asdict(c) for c in program.courses],
                'requirements': program.requirements,
                'skills': program.skills,
                'career': program.career
            }
        
        with open(self.programs_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_program(self, program: MasterProgram):
        """Добавляет программу в базу данных"""
        self.programs[program.id] = program
        self.save_programs()
    
    def get_program(self, program_id: str) -> Optional[MasterProgram]:
        """Получает программу по ID"""
        return self.programs.get(program_id)
    
    def get_all_programs(self) -> List[MasterProgram]:
        """Получает все программы"""
        return list(self.programs.values())
    
    def search_courses(self, query: str) -> List[Course]:
        """Ищет дисциплины по запросу"""
        query_lower = query.lower()
        results = []
        
        for program in self.programs.values():
            for course in program.courses:
                if (query_lower in course.name.lower() or 
                    query_lower in course.description.lower()):
                    results.append(course)
        
        return results
    
    def get_elective_courses(self, program_id: str) -> List[Course]:
        """Получает выборные дисциплины программы"""
        program = self.get_program(program_id)
        if not program:
            return []
        
        return [c for c in program.courses if 'выборн' in c.type.lower()]
    
    def load_user_profiles(self):
        """Загружает профили пользователей"""
        try:
            with open(self.user_profiles_file, 'r', encoding='utf-8') as f:
                self.user_profiles = json.load(f)
        except FileNotFoundError:
            self.user_profiles = {}
    
    def save_user_profiles(self):
        """Сохраняет профили пользователей"""
        with open(self.user_profiles_file, 'w', encoding='utf-8') as f:
            json.dump(self.user_profiles, f, ensure_ascii=False, indent=2)
    
    def get_user_profile(self, user_id: int) -> Dict:
        """Получает профиль пользователя"""
        return self.user_profiles.get(user_id, {})
    
    def update_user_profile(self, user_id: int, profile: Dict):
        """Обновляет профиль пользователя"""
        self.user_profiles[user_id] = profile
        self.save_user_profiles()
    
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
    
    def compare_programs(self, program_id1: str, program_id2: str) -> str:
        """Сравнивает две программы"""
        prog1 = self.get_program(program_id1)
        prog2 = self.get_program(program_id2)
        
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


if __name__ == "__main__":
    # Тестирование базы данных
    db = ProgramDatabase()
    
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
