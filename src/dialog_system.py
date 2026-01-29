"""
Модуль диалоговой системы с фильтрацией релевантных вопросов
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from openai import OpenAI
import os


@dataclass
class DialogContext:
    """Контекст диалога с пользователем"""
    user_id: int
    current_program: Optional[str] = None
    questions_asked: List[str] = None
    stage: str = "greeting"  # greeting, profile, recommendation, chat
    
    def __post_init__(self):
        if self.questions_asked is None:
            self.questions_asked = []


class RelevanceFilter:
    """Фильтр релевантности вопросов"""
    
    # Ключевые слова, связанные с обучением в магистратуре
    EDUCATION_KEYWORDS = [
        'магистратур', 'программ', 'обучени', 'учебн', 'дисциплин', 'курс',
        'предмет', 'экзамен', 'зачет', 'семестр', 'лекци', 'практик',
        'поступлени', 'абитуриент', 'конкурс', 'балл', 'документ',
        'диплом', 'аттестат', 'специальност', 'направлени', 'професси',
        'карьер', 'трудоустройств', 'навык', 'компетенци', 'знани',
        'итмо', 'университет', 'факультет', 'кафедр', 'преподавател',
        'выборн', 'обязательн', 'электив', 'модул', 'блок', 'план',
        'ai', 'искусственн', 'интеллект', 'машинн', 'обучени', 'ml',
        'data', 'science', 'аналитик', 'разработчик', 'программист',
        'проект', 'исследован', 'научн', 'практика', 'стажировк',
        'грант', 'стипенди', 'оплата', 'бюджет', 'контракт',
        'рекомендац', 'совет', 'выбор', 'подход', 'подходит'
    ]
    
    # Ключевые слова для неактуальных тем
    IRRELEVANT_KEYWORDS = [
        'погод', 'новост', 'спорт', 'футбол', 'музык', 'фильм', 'кино',
        'игр', 'анекдот', 'шутк', 'рецепт', 'готовк', 'кухн',
        'политик', 'религи', 'медицин', 'болезн', 'лекарств',
        'автомобил', 'машин', 'ремонт', 'строительств', 'недвижимост',
        'криптовалют', 'биткоин', 'инвест', 'акци', 'бирж',
        'знакомств', 'отношени', 'любов', 'семь', 'дет'
    ]
    
    def __init__(self, use_openai: bool = False):
        self.use_openai = use_openai
        self.client = None
        if use_openai:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
    
    def is_relevant(self, question: str, context: Optional[DialogContext] = None) -> Tuple[bool, str]:
        """
        Проверяет, является ли вопрос релевантным теме магистратуры
        
        Args:
            question: Вопрос пользователя
            context: Контекст диалога
            
        Returns:
            Кортеж (является_релевантным, причина)
        """
        question_lower = question.lower()
        
        # Проверяем на явно нерелевантные темы
        for keyword in self.IRRELEVANT_KEYWORDS:
            if keyword in question_lower:
                return False, f"Вопрос относится к теме '{keyword}', которая не связана с обучением в магистратуре"
        
        # Проверяем на релевантные ключевые слова
        education_matches = sum(1 for kw in self.EDUCATION_KEYWORDS if kw in question_lower)
        
        if education_matches >= 1:
            return True, "Вопрос связан с обучением в магистратуре"
        
        # Если используем OpenAI для более точной проверки
        if self.use_openai and self.client:
            return self._check_with_openai(question, context)
        
        # Если нет явных ключевых слов, проверяем контекст
        if context and context.current_program:
            # Если пользователь уже в контексте программы, считаем вопрос релевантным
            return True, "Вопрос в контексте обсуждения программы"
        
        # Короткие вопросы могут быть релевантными в контексте диалога
        if len(question.split()) <= 3 and context and context.stage != "greeting":
            return True, "Короткий вопрос в контексте диалога"
        
        return False, "Вопрос не содержит ключевых слов, связанных с обучением в магистратуре"
    
    def _check_with_openai(self, question: str, context: Optional[DialogContext] = None) -> Tuple[bool, str]:
        """Использует OpenAI для проверки релевантности"""
        try:
            system_prompt = """Ты - фильтр релевантности для чат-бота о магистратуре ITMO.
Твоя задача - определить, относится ли вопрос к теме обучения в магистратуре ITMO.
Отвечай ТОЛЬКО в формате: YES|NO|причина

Примеры:
YES|Вопрос о программе обучения
NO|Вопрос о погоде
YES|Вопрос о поступлении
NO|Вопрос о политике"""

            context_info = ""
            if context and context.current_program:
                context_info = f"\nКонтекст: пользователь обсуждает программу {context.current_program}"
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Вопрос: {question}{context_info}"}
                ],
                max_tokens=50,
                temperature=0
            )
            
            result = response.choices[0].message.content.strip()
            if result.startswith("YES"):
                return True, result.split("|", 1)[1] if "|" in result else "Релевантный вопрос"
            else:
                return False, result.split("|", 1)[1] if "|" in result else "Нерелевантный вопрос"
                
        except Exception as e:
            # При ошибке возвращаем False для безопасности
            return False, f"Ошибка проверки: {str(e)}"
    
    def extract_intent(self, question: str) -> str:
        """
        Извлекает намерение пользователя из вопроса
        
        Returns:
            Тип намерения: info, compare, recommend, search, other
        """
        question_lower = question.lower()
        
        # Сравнение программ
        if any(kw in question_lower for kw in ['сравн', 'разниц', 'отлич', 'лучш', 'против']):
            return 'compare'
        
        # Рекомендации
        if any(kw in kw in question_lower for kw in ['посовет', 'рекоменд', 'как выбрать', 'что выбрать']):
            return 'recommend'
        
        # Поиск информации
        if any(kw in question_lower for kw in ['где', 'как', 'когда', 'сколько', 'какой', 'какие']):
            return 'search'
        
        # Общая информация
        if any(kw in question_lower for kw in ['расскаж', 'что', 'кто', 'почему', 'зачем']):
            return 'info'
        
        return 'other'


class DialogSystem:
    """Диалоговая система для общения с абитуриентами"""
    
    def __init__(self, db, recommender, use_openai: bool = False):
        self.db = db
        self.recommender = recommender
        self.relevance_filter = RelevanceFilter(use_openai=use_openai)
        self.contexts: Dict[int, DialogContext] = {}
        self.use_openai = use_openai
        self.client = None
        if use_openai:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.client = OpenAI(api_key=api_key)
        
        # Загружаем ответы на типовые вопросы
        self.faq_answers = self._load_faq()
    
    def _load_faq(self) -> Dict[str, str]:
        """Загружает ответы на типовые вопросы"""
        return {
            'привет': "Привет! Я помогу вам разобраться с магистерскими программами ITMO. "
                     "Могу рассказать о программах, сравнить их, порекомендовать дисциплины. "
                     "О чём хотите узнать?",
            'помощь': "Я могу помочь вам со следующими вопросами:\n"
                     "• Рассказать о магистерских программах\n"
                     "• Сравнить программы между собой\n"
                     "• Рекомендовать выборные дисциплины\n"
                     "• Помочь с выбором программы\n\n"
                     "Для начала расскажите о своём бэкграунде и интересах.",
            'программы': "Доступные магистерские программы:\n"
                        "• Искусственный интеллект (AI)\n"
                        "• AI Product\n\n"
                        "Напишите номер программы или название, чтобы узнать подробнее.",
            'поступление': "Для поступления в магистратуру ITMO необходимо:\n"
                          "• Бакалаврская степень\n"
                          "• Портфолио\n"
                          "• Собеседование\n\n"
                          "Подробности на сайте abit.itmo.ru"
        }
    
    def get_or_create_context(self, user_id: int) -> DialogContext:
        """Получает или создает контекст диалога"""
        if user_id not in self.contexts:
            self.contexts[user_id] = DialogContext(user_id=user_id)
        return self.contexts[user_id]
    
    def _generate_llm_response(self, question: str, context: DialogContext) -> Optional[str]:
        """
        Генерирует ответ с помощью LLM
        
        Args:
            question: Вопрос пользователя
            context: Контекст диалога
            
        Returns:
            Сгенерированный ответ или None при ошибке
        """
        if not self.use_openai or not self.client:
            return None
        
        try:
            # Собираем информацию о программах для контекста
            programs_info = ""
            programs = self.db.get_all_programs()
            if programs:
                programs_info = "\n".join([f"- {p.title}: {p.description[:100]}..." for p in programs])
            
            # Формируем системный промпт
            system_prompt = """Ты - полезный ассистент для абитуриентов магистратуры ITMO.
Твоя задача - отвечать на вопросы о магистерских программах, дисциплинах, поступлении и обучении.

Правила:
1. Отвечай на русском языке
2. Будь вежливым и дружелюбным
3. Если не знаешь точного ответа, предложи обратиться на сайт abit.itmo.ru
4. Используй предоставленную информацию о программах
5. Отвечай кратко и по существу (до 200 слов)"""

            # Формируем контекст для LLM
            context_info = f"""
Контекст диалога:
- Стадия: {context.stage}
- Текущая программа: {context.current_program or 'не выбрана'}
- Заданные вопросы: {', '.join(context.questions_asked[-3:]) if context.questions_asked else 'нет'}

Доступные программы:
{programs_info}
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{context_info}\n\nВопрос пользователя: {question}"}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Ошибка генерации LLM-ответа: {e}")
            return None
    
    def process_message(self, user_id: int, message: str) -> str:
        """
        Обрабатывает сообщение пользователя
        
        Args:
            user_id: ID пользователя
            message: Сообщение пользователя
            
        Returns:
            Ответ бота
        """
        context = self.get_or_create_context(user_id)
        
        # Проверяем релевантность вопроса
        is_relevant, reason = self.relevance_filter.is_relevant(message, context)
        
        if not is_relevant:
            return f"❌ К сожалению, я могу отвечать только на вопросы, связанные с обучением в магистратуре ITMO.\n\n" \
                   f"Причина: {reason}\n\n" \
                   f"Спросите меня о программах, дисциплинах, поступлении или рекомендациях по обучению."
        
        # Определяем намерение
        intent = self.relevance_filter.extract_intent(message)
        
        # Обрабатываем в зависимости от стадии диалога
        if context.stage == "greeting":
            return self._handle_greeting(context, message, intent)
        elif context.stage == "profile":
            return self._handle_profile(context, message, intent)
        elif context.stage == "recommendation":
            return self._handle_recommendation(context, message, intent)
        else:
            return self._handle_chat(context, message, intent)
    
    def _handle_greeting(self, context: DialogContext, message: str, intent: str) -> str:
        """Обработка приветственной стадии"""
        message_lower = message.lower()
        
        # Проверяем FAQ
        for keyword, answer in self.faq_answers.items():
            if keyword in message_lower:
                return answer
        
        # Если пользователь хочет узнать о программах
        if 'программ' in message_lower or 'магистратур' in message_lower:
            programs = self.db.get_all_programs()
            if programs:
                response = "📚 Доступные магистерские программы:\n\n"
                for i, prog in enumerate(programs, 1):
                    response += f"{i}. {prog.title}\n"
                response += "\nНапишите номер или название программы, чтобы узнать подробнее."
                return response
            else:
                return "К сожалению, данные о программах пока не загружены. Попробуйте позже."
        
        # Переходим к сбору профиля
        context.stage = "profile"
        return "👋 Отлично! Чтобы я мог дать вам персонализированные рекомендации, расскажите немного о себе:\n\n" \
               "1. Какое у вас образование?\n" \
               "2. Какие у вас навыки?\n" \
               "3. Что вас интересует в IT?\n" \
               "4. Какие у вас карьерные цели?"
    
    def _handle_profile(self, context: DialogContext, message: str, intent: str) -> str:
        """Обработка стадии сбора профиля"""
        # Сохраняем информацию о пользователе
        profile_data = self.db.get_user_profile(context.user_id)
        
        # Простая обработка - сохраняем как интересы
        if not profile_data.get('background'):
            profile_data['background'] = [message]
            self.db.update_user_profile(context.user_id, profile_data)
            return "📝 Принято! Расскажите о своих навыках и интересах в IT."
        elif not profile_data.get('interests'):
            profile_data['interests'] = [message]
            self.db.update_user_profile(context.user_id, profile_data)
            return "📝 Хорошо! А какие у вас карьерные цели?"
        elif not profile_data.get('goals'):
            profile_data['goals'] = [message]
            self.db.update_user_profile(context.user_id, profile_data)
            context.stage = "recommendation"
            return "✅ Спасибо! Теперь я могу дать вам рекомендации.\n\n" \
                   "Хотите:\n" \
                   "1. Сравнить программы\n" \
                   "2. Получить рекомендации по дисциплинам\n" \
                   "3. Узнать подробнее о конкретной программе"
        
        context.stage = "chat"
        return self._handle_chat(context, message, intent)
    
    def _handle_recommendation(self, context: DialogContext, message: str, intent: str) -> str:
        """Обработка стадии рекомендаций"""
        message_lower = message.lower()
        
        if 'сравн' in message_lower or intent == 'compare':
            programs = self.db.get_all_programs()
            if len(programs) >= 2:
                return self.db.compare_programs(programs[0].id, programs[1].id)
            else:
                return "Недостаточно программ для сравнения."
        
        if 'дисциплин' in message_lower or 'электив' in message_lower:
            if context.current_program:
                recommendations = self.recommender.recommend_courses(
                    context.user_id, context.current_program
                )
                return self.recommender.format_recommendations(recommendations)
            else:
                programs = self.db.get_all_programs()
                if programs:
                    context.current_program = programs[0].id
                    recommendations = self.recommender.recommend_courses(
                        context.user_id, context.current_program
                    )
                    return f"📖 Рекомендации для программы {programs[0].title}:\n\n" + \
                           self.recommender.format_recommendations(recommendations)
        
        # Если пользователь указал программу
        programs = self.db.get_all_programs()
        for prog in programs:
            if prog.title.lower() in message_lower or prog.id in message_lower:
                context.current_program = prog.id
                return self.db.get_program_summary(prog.id)
        
        context.stage = "chat"
        return self._handle_chat(context, message, intent)
    
    def _handle_chat(self, context: DialogContext, message: str, intent: str) -> str:
        """Обработка общего чата"""
        message_lower = message.lower()
        
        # Сначала пробуем получить ответ от LLM
        llm_response = self._generate_llm_response(message, context)
        if llm_response:
            # Сохраняем вопрос в контекст
            context.questions_asked.append(message)
            return llm_response
        
        # Поиск дисциплин
        if intent == 'search' or 'дисциплин' in message_lower or 'курс' in message_lower:
            courses = self.db.search_courses(message)
            if courses:
                response = f"🔍 Найдено {len(courses)} дисциплин:\n\n"
                for course in courses[:5]:
                    response += f"• {course.name}\n"
                return response
            else:
                return "По вашему запросу дисциплины не найдены."
        
        # Информация о программе
        programs = self.db.get_all_programs()
        for prog in programs:
            if prog.title.lower() in message_lower or prog.id in message_lower:
                context.current_program = prog.id
                return self.db.get_program_summary(prog.id)
        
        # Рекомендации
        if 'рекоменд' in message_lower or 'посовет' in message_lower:
            if context.current_program:
                recommendations = self.recommender.recommend_courses(
                    context.user_id, context.current_program
                )
                return self.recommender.format_recommendations(recommendations)
            else:
                return "Сначала выберите программу для получения рекомендаций."
        
        # Учебный план
        if 'план' in message_lower or 'учебн' in message_lower:
            if context.current_program:
                return self.recommender.get_study_plan(context.user_id, context.current_program)
            else:
                return "Сначала выберите программу."
        
        # Сравнение
        if 'сравн' in message_lower or intent == 'compare':
            if len(programs) >= 2:
                return self.db.compare_programs(programs[0].id, programs[1].id)
        
        # Ответ по умолчанию
        return "Я не совсем понял вопрос. Попробуйте спросить о:\n" \
               "• Программах магистратуры\n" \
               "• Дисциплинах и учебном плане\n" \
               "• Рекомендациях по выбору курсов\n" \
               "• Сравнении программ"


if __name__ == "__main__":
    # Тестирование диалоговой системы
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    from src.database import ProgramDatabase
    from src.recommender import CourseRecommender
    
    db = ProgramDatabase()
    recommender = CourseRecommender(db)
    dialog = DialogSystem(db, recommender)
    
    # Тестовые сообщения
    test_messages = [
        "Привет!",
        "Какие программы есть?",
        "Расскажи о программе AI",
        "Какие дисциплины есть?",
        "Посоветуй что-нибудь",
        "Какая погода?"
    ]
    
    for msg in test_messages:
        print(f"User: {msg}")
        print(f"Bot: {dialog.process_message(1, msg)}\n")
