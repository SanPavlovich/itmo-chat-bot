"""
Модуль для рекомендаций по выбору дисциплин
"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.database import Course, MasterProgram, ProgramDatabase
from src.vector_db import QdrantVectorDB, get_vector_db
from src.embeddings import EmbeddingModel, get_embedding_model


@dataclass
class UserProfile:
    """Профиль абитуриента"""
    user_id: int
    background: List[str]  # Образование и опыт
    interests: List[str]  # Интересы
    skills: List[str]  # Текущие навыки
    goals: List[str]  # Карьерные цели
    preferred_program: str = ""  # Предпочитаемая программа


class CourseRecommender:
    """Система рекомендаций дисциплин"""
    
    def __init__(self, db: ProgramDatabase, vector_db: QdrantVectorDB = None,
                 use_vector_search: bool = True):
        """
        Инициализация системы рекомендаций
        
        Args:
            db: База данных программ
            vector_db: Векторная база данных Qdrant (опционально)
            use_vector_search: Использовать ли векторный поиск
        """
        self.db = db
        self.vector_db = vector_db or get_vector_db()
        self.use_vector_search = use_vector_search
        self.embedding_model = get_embedding_model()
    
    def create_user_profile(self, user_id: int, background: List[str],
                           interests: List[str], skills: List[str],
                           goals: List[str]) -> UserProfile:
        """Создает профиль пользователя"""
        profile = UserProfile(
            user_id=user_id,
            background=background,
            interests=interests,
            skills=skills,
            goals=goals
        )
        
        # Сохраняем в MongoDB
        self.db.update_user_profile(user_id, {
            'background': background,
            'interests': interests,
            'skills': skills,
            'goals': goals,
            'preferred_program': ''
        })
        
        # Сохраняем в векторную базу для рекомендаций
        if self.use_vector_search:
            self.vector_db.add_user_profile(
                user_id=user_id,
                background=background,
                interests=interests,
                skills=skills,
                goals=goals
            )
        
        return profile
    
    def recommend_courses(self, user_id: int, program_id: str,
                         limit: int = 5) -> List[Tuple[Course, float]]:
        """
        Рекомендует выборные дисциплины для пользователя
        
        Args:
            user_id: ID пользователя
            program_id: ID программы
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список кортежей (дисциплина, оценка релевантности)
        """
        # Используем векторный поиск если включен
        if self.use_vector_search:
            return self._recommend_courses_vector(user_id, program_id, limit)
        
        # Иначе используем классический метод
        return self._recommend_courses_classic(user_id, program_id, limit)
    
    def _recommend_courses_vector(self, user_id: int, program_id: str,
                                 limit: int = 5) -> List[Tuple[Course, float]]:
        """
        Рекомендует дисциплины с использованием векторного поиска
        
        Args:
            user_id: ID пользователя
            program_id: ID программы
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список кортежей (дисциплина, оценка релевантности)
        """
        # Получаем рекомендации из векторной базы
        vector_results = self.vector_db.recommend_courses_for_user(
            user_id=user_id,
            program_id=program_id,
            limit=limit
        )
        
        # Преобразуем результаты в формат (Course, float)
        recommendations = []
        for result in vector_results:
            course_id = result.get("id")
            score = result.get("score", 0.0)
            
            # Получаем объект Course из базы данных
            program = self.db.get_program(program_id)
            if program:
                for course in program.courses:
                    if course.name == result.get("name"):
                        recommendations.append((course, score))
                        break
        
        return recommendations
    
    def _recommend_courses_classic(self, user_id: int, program_id: str,
                                  limit: int = 5) -> List[Tuple[Course, float]]:
        """
        Рекомендует дисциплины классическим методом (без векторного поиска)
        
        Args:
            user_id: ID пользователя
            program_id: ID программы
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список кортежей (дисциплина, оценка релевантности)
        """
        profile_data = self.db.get_user_profile(user_id)
        if not profile_data:
            return []
        
        program = self.db.get_program(program_id)
        if not program:
            return []
        
        # Получаем выборные дисциплины
        elective_courses = self.db.get_elective_courses(program_id)
        
        # Вычисляем релевантность для каждой дисциплины
        recommendations = []
        for course in elective_courses:
            score = self._calculate_relevance(course, profile_data, program)
            recommendations.append((course, score))
        
        # Сортируем по убыванию релевантности
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations[:limit]
    
    def _calculate_relevance(self, course: Course, profile: Dict, 
                           program: MasterProgram) -> float:
        """
        Вычисляет релевантность дисциплины для пользователя
        
        Args:
            course: Дисциплина
            profile: Профиль пользователя
            program: Программа обучения
            
        Returns:
            Оценка релевантности от 0 до 1
        """
        score = 0.0
        course_text = (course.name + " " + course.description).lower()
        
        # Проверяем совпадение с интересами
        interests = profile.get('interests', [])
        for interest in interests:
            if interest.lower() in course_text:
                score += 0.3
        
        # Проверяем совпадение с целями
        goals = profile.get('goals', [])
        for goal in goals:
            if goal.lower() in course_text:
                score += 0.25
        
        # Проверяем совпадение с навыками программы
        for skill in program.skills:
            if skill.lower() in course_text:
                score += 0.15
        
        # Проверяем бэкграунд - если дисциплина дополняет знания
        background = profile.get('background', [])
        for bg in background:
            # Если дисциплина развивает существующие знания
            if bg.lower() in course_text:
                score += 0.1
        
        # Нормализуем оценку
        return min(score, 1.0)
    
    def recommend_program(self, user_id: int) -> List[Tuple[MasterProgram, float]]:
        """
        Рекомендует подходящую программу на основе профиля пользователя
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список кортежей (программа, оценка соответствия)
        """
        # Используем векторный поиск если включен
        if self.use_vector_search:
            return self._recommend_program_vector(user_id)
        
        # Иначе используем классический метод
        return self._recommend_program_classic(user_id)
    
    def _recommend_program_vector(self, user_id: int) -> List[Tuple[MasterProgram, float]]:
        """
        Рекомендует программы с использованием векторного поиска
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список кортежей (программа, оценка соответствия)
        """
        # Получаем рекомендации из векторной базы
        vector_results = self.vector_db.recommend_programs_for_user(
            user_id=user_id,
            limit=10
        )
        
        # Преобразуем результаты в формат (MasterProgram, float)
        recommendations = []
        for result in vector_results:
            program_id = result.get("id")
            score = result.get("score", 0.0)
            
            # Получаем объект MasterProgram из базы данных
            program = self.db.get_program(program_id)
            if program:
                recommendations.append((program, score))
        
        return recommendations
    
    def _recommend_program_classic(self, user_id: int) -> List[Tuple[MasterProgram, float]]:
        """
        Рекомендует программы классическим методом (без векторного поиска)
        
        Args:
            user_id: ID пользователя
            
        Returns:
            Список кортежей (программа, оценка соответствия)
        """
        profile_data = self.db.get_user_profile(user_id)
        if not profile_data:
            return []
        
        programs = self.db.get_all_programs()
        recommendations = []
        
        for program in programs:
            score = self._calculate_program_match(program, profile_data)
            recommendations.append((program, score))
        
        # Сортируем по убыванию соответствия
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        return recommendations
    
    def _calculate_program_match(self, program: MasterProgram, 
                                profile: Dict) -> float:
        """
        Вычисляет соответствие программы профилю пользователя
        
        Args:
            program: Магистерская программа
            profile: Профиль пользователя
            
        Returns:
            Оценка соответствия от 0 до 1
        """
        score = 0.0
        
        # Проверяем совпадение навыков программы с интересами
        interests = profile.get('interests', [])
        program_text = program.description.lower() + " " + " ".join(program.skills).lower()
        
        for interest in interests:
            if interest.lower() in program_text:
                score += 0.2
        
        # Проверяем совпадение с карьерными целями
        goals = profile.get('goals', [])
        career_text = " ".join(program.career).lower()
        
        for goal in goals:
            if goal.lower() in career_text:
                score += 0.3
        
        # Проверяем соответствие бэкграунда требованиям
        background = profile.get('background', [])
        for req in program.requirements:
            for bg in background:
                if bg.lower() in req.lower():
                    score += 0.15
        
        # Нормализуем оценку
        return min(score, 1.0)
    
    def get_study_plan(self, user_id: int, program_id: str) -> str:
        """
        Формирует рекомендованный учебный план
        
        Args:
            user_id: ID пользователя
            program_id: ID программы
            
        Returns:
            Текст с рекомендованным планом
        """
        program = self.db.get_program(program_id)
        if not program:
            return "Программа не найдена"
        
        profile_data = self.db.get_user_profile(user_id)
        
        plan = f"📋 Рекомендованный учебный план: {program.title}\n\n"
        
        # Обязательные дисциплины
        mandatory = [c for c in program.courses if 'обяз' in c.type.lower()]
        if mandatory:
            plan += "📌 Обязательные дисциплины:\n"
            for course in mandatory[:10]:
                plan += f"  • {course.name} ({course.semester} семестр)\n"
            plan += "\n"
        
        # Рекомендованные выборные дисциплины
        recommended = self.recommend_courses(user_id, program_id, limit=5)
        if recommended:
            plan += "⭐ Рекомендованные выборные дисциплины:\n"
            for course, score in recommended:
                plan += f"  • {course.name} (релевантность: {score:.0%})\n"
            plan += "\n"
        
        # Советы по обучению
        plan += "💡 Рекомендации по обучению:\n"
        if profile_data:
            interests = profile_data.get('interests', [])
            if interests:
                plan += f"  • Фокусируйтесь на дисциплинах, связанных с: {', '.join(interests[:3])}\n"
            
            goals = profile_data.get('goals', [])
            if goals:
                plan += f"  • Для достижения целей ({', '.join(goals[:2])}) выбирайте соответствующие элективы\n"
        
        return plan
    
    def format_recommendations(self, recommendations: List[Tuple[Course, float]]) -> str:
        """Форматирует рекомендации для вывода"""
        if not recommendations:
            return "Нет рекомендаций"
        
        result = "🎯 Рекомендованные дисциплины:\n\n"
        for i, (course, score) in enumerate(recommendations, 1):
            result += f"{i}. {course.name}\n"
            result += f"   Релевантность: {score:.0%}\n"
            if course.description:
                result += f"   {course.description[:100]}...\n"
            result += "\n"
        
        return result
    
    def index_courses(self, program_id: str = None) -> int:
        """
        Индексирует дисциплины в векторную базу
        
        Args:
            program_id: ID программы для индексации (опционально)
            
        Returns:
            Количество проиндексированных дисциплин
        """
        if not self.use_vector_search:
            return 0
        
        count = 0
        
        if program_id:
            # Индексируем дисциплины одной программы
            program = self.db.get_program(program_id)
            if program:
                for course in program.courses:
                    success = self.vector_db.add_course(
                        course_id=f"{program_id}_{course.name}",
                        program_id=program_id,
                        name=course.name,
                        description=course.description,
                        metadata={
                            "type": course.type,
                            "semester": course.semester
                        }
                    )
                    if success:
                        count += 1
        else:
            # Индексируем все дисциплины
            programs = self.db.get_all_programs()
            for program in programs:
                for course in program.courses:
                    success = self.vector_db.add_course(
                        course_id=f"{program.program_id}_{course.name}",
                        program_id=program.program_id,
                        name=course.name,
                        description=course.description,
                        metadata={
                            "type": course.type,
                            "semester": course.semester
                        }
                    )
                    if success:
                        count += 1
        
        return count
    
    def index_programs(self) -> int:
        """
        Индексирует программы в векторную базу
        
        Returns:
            Количество проиндексированных программ
        """
        if not self.use_vector_search:
            return 0
        
        count = 0
        programs = self.db.get_all_programs()
        
        for program in programs:
            success = self.vector_db.add_program(
                program_id=program.program_id,
                title=program.title,
                description=program.description,
                skills=program.skills,
                career=program.career,
                metadata={
                    "requirements": program.requirements
                }
            )
            if success:
                count += 1
        
        return count


if __name__ == "__main__":
    # Тестирование системы рекомендаций
    db = ProgramDatabase()
    recommender = CourseRecommender(db)
    
    # Создаем тестовый профиль
    profile = recommender.create_user_profile(
        user_id=123,
        background=["Бакалавр информатики", "Python", "Математика"],
        interests=["Машинное обучение", "NLP", "Компьютерное зрение"],
        skills=["Python", "SQL", "Git"],
        goals=["Data Scientist", "ML Engineer"]
    )
    
    print("Профиль создан:", profile)
    
    # Тестируем рекомендации
    if db.programs:
        program_id = list(db.programs.keys())[0]
        recommendations = recommender.recommend_courses(123, program_id)
        print("\nРекомендации:")
        print(recommender.format_recommendations(recommendations))
