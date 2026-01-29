"""
Telegram-бот для помощи абитуриентам ITMO
"""
import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from src.database import ProgramDatabase
from src.parser import ITMOMasterParser
from src.recommender import CourseRecommender
from src.dialog_system import DialogSystem

# Загружаем переменные окружения
load_dotenv()

# Инициализация компонентов
db = ProgramDatabase()
recommender = CourseRecommender(db)
dialog_system = DialogSystem(db, recommender, use_openai=bool(os.getenv('OPENAI_API_KEY')))

# Инициализация бота
bot = Bot(token=os.getenv('TELEGRAM_BOT_TOKEN'))
dp = Dispatcher(storage=MemoryStorage())


# Состояния для FSM
class UserProfileStates(StatesGroup):
    background = State()
    interests = State()
    skills = State()
    goals = State()


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    welcome_text = """
🎓 Добро пожаловать в чат-бот для абитуриентов ITMO!

Я помогу вам:
• Выбрать подходящую магистерскую программу
• Узнать подробности о дисциплинах
• Получить рекомендации по выбору курсов
• Сравнить программы между собой

📋 Доступные команды:
/start - Начать работу
/programs - Список программ
/compare - Сравнить программы
/recommend - Получить рекомендации
/profile - Заполнить профиль
/help - Справка

Начните с рассказа о себе или выберите команду!
"""
    await message.answer(welcome_text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 Справка по командам:

/start - Перезапустить бота
/programs - Показать доступные магистерские программы
/compare - Сравнить программы между собой
/recommend - Получить персонализированные рекомендации
/profile - Заполнить профиль для лучших рекомендаций
/clear - Очистить историю диалога

💡 Просто задайте вопрос о программах, дисциплинах или поступлении!
"""
    await message.answer(help_text)


@dp.message(Command("programs"))
async def cmd_programs(message: Message):
    """Показывает список доступных программ"""
    programs = db.get_all_programs()
    
    if not programs:
        await message.answer("❌ Данные о программах пока не загружены. Попробуйте позже.")
        return
    
    response = "📚 Доступные магистерские программы:\n\n"
    keyboard = types.InlineKeyboardMarkup()
    
    for i, prog in enumerate(programs, 1):
        response += f"{i}. {prog.title}\n"
        keyboard.add(types.InlineKeyboardButton(
            text=f"{prog.title}",
            callback_data=f"program_{prog.id}"
        ))
    
    response += "\nНажмите на кнопку для подробностей или задайте вопрос."
    await message.answer(response, reply_markup=keyboard)


@dp.message(Command("compare"))
async def cmd_compare(message: Message):
    """Сравнивает программы"""
    programs = db.get_all_programs()
    
    if len(programs) < 2:
        await message.answer("❌ Недостаточно программ для сравнения.")
        return
    
    comparison = db.compare_programs(programs[0].id, programs[1].id)
    await message.answer(comparison)


@dp.message(Command("recommend"))
async def cmd_recommend(message: Message):
    """Показывает рекомендации"""
    user_id = message.from_user.id
    profile = db.get_user_profile(user_id)
    
    if not profile:
        await message.answer(
            "❌ Сначала заполните профиль командой /profile\n"
            "Это поможет мне дать персонализированные рекомендации."
        )
        return
    
    programs = db.get_all_programs()
    if not programs:
        await message.answer("❌ Данные о программах не загружены.")
        return
    
    # Рекомендуем программу
    program_recommendations = recommender.recommend_program(user_id)
    if program_recommendations:
        response = "🎯 Рекомендованные программы для вас:\n\n"
        for prog, score in program_recommendations:
            response += f"• {prog.title} (соответствие: {score:.0%})\n"
        await message.answer(response)
    else:
        await message.answer("Не удалось сформировать рекомендации.")


@dp.message(Command("profile"))
async def cmd_profile(message: Message, state: FSMContext):
    """Запускает процесс заполнения профиля"""
    await state.set_state(UserProfileStates.background)
    await message.answer(
        "📝 Давайте заполним ваш профиль для персонализированных рекомендаций!\n\n"
        "Вопрос 1/4: Какое у вас образование? (напишите, например: 'Бакалавр информатики')"
    )


@dp.message(Command("clear"))
async def cmd_clear(message: Message, state: FSMContext):
    """Очищает историю диалога"""
    await state.clear()
    # Сбрасываем контекст в диалоговой системе
    if message.from_user.id in dialog_system.contexts:
        del dialog_system.contexts[message.from_user.id]
    await message.answer("✅ История диалога очищена. Начните заново с команды /start")


# Обработчики состояний профиля
@dp.message(UserProfileStates.background)
async def process_background(message: Message, state: FSMContext):
    """Обрабатывает образование"""
    await state.update_data(background=message.text)
    await state.set_state(UserProfileStates.interests)
    await message.answer(
        "📝 Вопрос 2/4: Что вас интересует в IT? "
        "(напишите, например: 'Машинное обучение, NLP, разработка')"
    )


@dp.message(UserProfileStates.interests)
async def process_interests(message: Message, state: FSMContext):
    """Обрабатывает интересы"""
    await state.update_data(interests=message.text)
    await state.set_state(UserProfileStates.skills)
    await message.answer(
        "📝 Вопрос 3/4: Какие у вас навыки? "
        "(напишите, например: 'Python, SQL, Git, Docker')"
    )


@dp.message(UserProfileStates.skills)
async def process_skills(message: Message, state: FSMContext):
    """Обрабатывает навыки"""
    await state.update_data(skills=message.text)
    await state.set_state(UserProfileStates.goals)
    await message.answer(
        "📝 Вопрос 4/4: Какие у вас карьерные цели? "
        "(напишите, например: 'Стать Data Scientist, работать в ML')"
    )


@dp.message(UserProfileStates.goals)
async def process_goals(message: Message, state: FSMContext):
    """Обрабатывает цели и сохраняет профиль"""
    await state.update_data(goals=message.text)
    
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Создаем профиль
    recommender.create_user_profile(
        user_id=user_id,
        background=[data.get('background', '')],
        interests=[data.get('interests', '')],
        skills=[data.get('skills', '')],
        goals=[data.get('goals', '')]
    )
    
    await state.clear()
    await message.answer(
        "✅ Профиль сохранен!\n\n"
        "Теперь я могу давать вам персонализированные рекомендации.\n"
        "Используйте команду /recommend для получения рекомендаций."
    )


# Обработчик callback-кнопок
@dp.callback_query(F.data.startswith("program_"))
async def callback_program(callback: CallbackQuery):
    """Обрабатывает нажатие на кнопку программы"""
    program_id = callback.data.split("_")[1]
    program = db.get_program(program_id)
    
    if program:
        # Обновляем контекст
        context = dialog_system.get_or_create_context(callback.from_user.id)
        context.current_program = program_id
        
        summary = db.get_program_summary(program_id)
        
        # Добавляем кнопки действий
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton(
            text="📖 Учебный план",
            callback_data=f"plan_{program_id}"
        ))
        keyboard.add(types.InlineKeyboardButton(
            text="⭐ Рекомендации по дисциплинам",
            callback_data=f"recommend_courses_{program_id}"
        ))
        
        await callback.message.edit_text(summary, reply_markup=keyboard)
    else:
        await callback.answer("❌ Программа не найдена")
    
    await callback.answer()


@dp.callback_query(F.data.startswith("plan_"))
async def callback_plan(callback: CallbackQuery):
    """Показывает учебный план"""
    program_id = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    plan = recommender.get_study_plan(user_id, program_id)
    await callback.message.edit_text(plan)
    await callback.answer()


@dp.callback_query(F.data.startswith("recommend_courses_"))
async def callback_recommend_courses(callback: CallbackQuery):
    """Показывает рекомендации по дисциплинам"""
    program_id = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    recommendations = recommender.recommend_courses(user_id, program_id)
    response = recommender.format_recommendations(recommendations)
    
    await callback.message.edit_text(response)
    await callback.answer()


# Обработчик текстовых сообщений
@dp.message()
async def handle_message(message: Message):
    """Обрабатывает текстовые сообщения"""
    user_id = message.from_user.id
    text = message.text
    
    # Передаем сообщение в диалоговую систему
    response = dialog_system.process_message(user_id, text)
    
    # Отправляем ответ
    await message.answer(response)


# Функция для парсинга данных
async def parse_programs():
    """Парсит данные с сайтов магистратур"""
    parser = ITMOMasterParser()
    
    urls = [
        os.getenv('MASTER_AI_URL', 'https://abit.itmo.ru/program/master/ai'),
        os.getenv('MASTER_AI_PRODUCT_URL', 'https://abit.itmo.ru/program/master/ai_product')
    ]
    
    print("Начинаем парсинг данных...")
    programs_data = parser.parse_all_programs(urls)
    
    # Сохраняем в JSON
    parser.save_to_json(programs_data, "data/programs.json")
    
    # Обновляем базу данных
    for program_id, data in programs_data.items():
        from src.database import MasterProgram, Course
        courses = [Course(**c) for c in data.get('courses', [])]
        program = MasterProgram(
            id=program_id,
            title=data.get('title', ''),
            url=data.get('url', ''),
            description=data.get('description', ''),
            courses=courses,
            requirements=data.get('requirements', []),
            skills=data.get('skills', []),
            career=data.get('career', [])
        )
        db.add_program(program)
    
    print(f"Парсинг завершен. Загружено {len(programs_data)} программ.")


async def main():
    """Главная функция"""
    print("Запуск бота...")
    
    # Парсим данные при запуске
    await parse_programs()
    
    # Запускаем бота
    print("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
