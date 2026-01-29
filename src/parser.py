"""
Модуль для парсинга данных с сайтов магистратур ITMO
"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import json
import re


class ITMOMasterParser:
    """Парсер данных с сайта abit.itmo.ru"""
    
    def __init__(self):
        self.base_url = "https://abit.itmo.ru"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def parse_program_page(self, url: str) -> Dict:
        """
        Парсит страницу магистерской программы
        
        Args:
            url: URL страницы программы
            
        Returns:
            Словарь с данными программы
        """
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Извлекаем данные из __NEXT_DATA__
            next_data = self._extract_next_data(response.text)
            if not next_data:
                print(f"Не удалось найти __NEXT_DATA__ на странице {url}")
                return {}
            
            program_data = {
                'url': url,
                'title': self._extract_title(next_data),
                'description': self._extract_description(next_data),
                'curriculum': self._extract_curriculum(next_data),
                'courses': self._extract_courses(next_data),
                'requirements': self._extract_requirements(next_data),
                'skills': self._extract_skills(next_data),
                'career': self._extract_career(next_data)
            }
            
            return program_data
            
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {e}")
            return {}
    
    def _extract_next_data(self, html: str) -> Optional[Dict]:
        """Извлекает JSON из тега __NEXT_DATA__"""
        soup = BeautifulSoup(html, 'lxml')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if script_tag:
            try:
                return json.loads(script_tag.string)
            except json.JSONDecodeError:
                return None
        return None
    
    def _extract_title(self, next_data: Dict) -> str:
        """Извлекает название программы из __NEXT_DATA__"""
        try:
            # Путь к данным программы в Next.js
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Данные находятся в apiProgram
            if 'apiProgram' in page_props:
                api_program = page_props['apiProgram']
                if isinstance(api_program, dict):
                    title = api_program.get('title')
                    if title:
                        return str(title)
            
            return "Неизвестная программа"
        except Exception as e:
            print(f"Ошибка при извлечении заголовка: {e}")
            return "Неизвестная программа"
    
    def _extract_description(self, next_data: Dict) -> str:
        """Извлекает описание программы из __NEXT_DATA__"""
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск описания в данных программы
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    for key in ['description', 'about', 'text', 'content']:
                        if key in program and program[key]:
                            desc = str(program[key])
                            if len(desc) > 20:
                                return desc
            
            # Альтернативный путь
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['description', 'about', 'text', 'content']:
                        if key in data and data[key]:
                            desc = str(data[key])
                            if len(desc) > 20:
                                return desc
            
            return ""
        except Exception as e:
            print(f"Ошибка при извлечении описания: {e}")
            return ""
    
    def _extract_curriculum(self, next_data: Dict) -> Dict:
        """Извлекает учебный план из __NEXT_DATA__"""
        curriculum = {
            'years': [],
            'modules': []
        }
        
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск учебного плана в данных
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    # Проверяем различные ключи для учебного плана
                    for key in ['curriculum', 'studyPlan', 'study_plan', 'modules', 'disciplines']:
                        if key in program:
                            data = program[key]
                            if isinstance(data, dict):
                                if 'modules' in data:
                                    modules = data['modules']
                                    if isinstance(modules, list):
                                        for module in modules:
                                            if isinstance(module, dict):
                                                module_name = module.get('name') or module.get('title')
                                                if module_name:
                                                    curriculum['modules'].append(str(module_name))
                                            elif isinstance(module, str):
                                                curriculum['modules'].append(module)
                                if 'years' in data:
                                    years = data['years']
                                    if isinstance(years, list):
                                        curriculum['years'] = [str(y) for y in years]
                            elif isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        module_name = item.get('name') or item.get('title')
                                        if module_name:
                                            curriculum['modules'].append(str(module_name))
                                    elif isinstance(item, str):
                                        curriculum['modules'].append(item)
            
            # Альтернативный путь через data
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['curriculum', 'studyPlan', 'study_plan', 'modules', 'disciplines']:
                        if key in data:
                            curriculum_data = data[key]
                            if isinstance(curriculum_data, list):
                                for item in curriculum_data:
                                    if isinstance(item, dict):
                                        module_name = item.get('name') or item.get('title')
                                        if module_name:
                                            curriculum['modules'].append(str(module_name))
                                    elif isinstance(item, str):
                                        curriculum['modules'].append(item)
        
        except Exception as e:
            print(f"Ошибка при извлечении учебного плана: {e}")
        
        return curriculum
    
    def _extract_courses(self, next_data: Dict) -> List[Dict]:
        """Извлекает список дисциплин из __NEXT_DATA__"""
        courses = []
        
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск дисциплин в данных программы
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    for key in ['courses', 'disciplines', 'subjects', 'items']:
                        if key in program:
                            data = program[key]
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        course_name = item.get('name') or item.get('title') or item.get('subject')
                                        if course_name:
                                            course_info = {
                                                'name': str(course_name),
                                                'type': str(item.get('type', '')),
                                                'credits': str(item.get('credits', '') or item.get('zachet', '')),
                                                'semester': str(item.get('semester', '') or item.get('semestr', ''))
                                            }
                                            courses.append(course_info)
                                    elif isinstance(item, str):
                                        courses.append({'name': item, 'type': '', 'credits': '', 'semester': ''})
            
            # Альтернативный путь через data
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['courses', 'disciplines', 'subjects', 'items']:
                        if key in data:
                            courses_data = data[key]
                            if isinstance(courses_data, list):
                                for item in courses_data:
                                    if isinstance(item, dict):
                                        course_name = item.get('name') or item.get('title') or item.get('subject')
                                        if course_name:
                                            course_info = {
                                                'name': str(course_name),
                                                'type': str(item.get('type', '')),
                                                'credits': str(item.get('credits', '') or item.get('zachet', '')),
                                                'semester': str(item.get('semester', '') or item.get('semestr', ''))
                                            }
                                            courses.append(course_info)
                                    elif isinstance(item, str):
                                        courses.append({'name': item, 'type': '', 'credits': '', 'semester': ''})
        
        except Exception as e:
            print(f"Ошибка при извлечении дисциплин: {e}")
        
        return courses[:50]
    
    def _extract_requirements(self, next_data: Dict) -> List[str]:
        """Извлекает требования к поступающим из __NEXT_DATA__"""
        requirements = []
        
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск требований в данных программы
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    for key in ['requirements', 'admission', 'entry', 'requirementsList']:
                        if key in program:
                            data = program[key]
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        req_text = item.get('text') or item.get('name') or item.get('title')
                                        if req_text:
                                            requirements.append(str(req_text))
                                    elif isinstance(item, str):
                                        if len(item) > 10:
                                            requirements.append(item)
                            elif isinstance(data, str) and len(data) > 20:
                                requirements.append(data)
            
            # Альтернативный путь через data
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['requirements', 'admission', 'entry', 'requirementsList']:
                        if key in data:
                            req_data = data[key]
                            if isinstance(req_data, list):
                                for item in req_data:
                                    if isinstance(item, dict):
                                        req_text = item.get('text') or item.get('name') or item.get('title')
                                        if req_text:
                                            requirements.append(str(req_text))
                                    elif isinstance(item, str) and len(item) > 10:
                                        requirements.append(item)
        
        except Exception as e:
            print(f"Ошибка при извлечении требований: {e}")
        
        return requirements[:10]
    
    def _extract_skills(self, next_data: Dict) -> List[str]:
        """Извлекает навыки из __NEXT_DATA__"""
        skills = []
        
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск навыков в данных программы
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    for key in ['skills', 'competencies', 'outcomes', 'results']:
                        if key in program:
                            data = program[key]
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        skill_text = item.get('text') or item.get('name') or item.get('title')
                                        if skill_text:
                                            skills.append(str(skill_text))
                                    elif isinstance(item, str) and 5 < len(item) < 100:
                                        skills.append(item)
            
            # Альтернативный путь через data
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['skills', 'competencies', 'outcomes', 'results']:
                        if key in data:
                            skills_data = data[key]
                            if isinstance(skills_data, list):
                                for item in skills_data:
                                    if isinstance(item, dict):
                                        skill_text = item.get('text') or item.get('name') or item.get('title')
                                        if skill_text:
                                            skills.append(str(skill_text))
                                    elif isinstance(item, str) and 5 < len(item) < 100:
                                        skills.append(item)
        
        except Exception as e:
            print(f"Ошибка при извлечении навыков: {e}")
        
        return skills[:20]
    
    def _extract_career(self, next_data: Dict) -> List[str]:
        """Извлекает информацию о карьере из __NEXT_DATA__"""
        career = []
        
        try:
            props = next_data.get('props', {})
            page_props = props.get('pageProps', {})
            
            # Поиск информации о карьере в данных программы
            if 'program' in page_props:
                program = page_props['program']
                if isinstance(program, dict):
                    for key in ['career', 'jobs', 'employment', 'opportunities']:
                        if key in program:
                            data = program[key]
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        career_text = item.get('text') or item.get('name') or item.get('title')
                                        if career_text:
                                            career.append(str(career_text))
                                    elif isinstance(item, str) and len(item) > 10:
                                        career.append(item)
                            elif isinstance(data, dict):
                                for sub_key in ['items', 'list', 'companies']:
                                    if sub_key in data:
                                        sub_data = data[sub_key]
                                        if isinstance(sub_data, list):
                                            for item in sub_data:
                                                if isinstance(item, dict):
                                                    career_text = item.get('text') or item.get('name') or item.get('title')
                                                    if career_text:
                                                        career.append(str(career_text))
                                                elif isinstance(item, str) and len(item) > 10:
                                                    career.append(item)
            
            # Альтернативный путь через data
            if 'data' in page_props:
                data = page_props['data']
                if isinstance(data, dict):
                    for key in ['career', 'jobs', 'employment', 'opportunities']:
                        if key in data:
                            career_data = data[key]
                            if isinstance(career_data, list):
                                for item in career_data:
                                    if isinstance(item, dict):
                                        career_text = item.get('text') or item.get('name') or item.get('title')
                                        if career_text:
                                            career.append(str(career_text))
                                    elif isinstance(item, str) and len(item) > 10:
                                        career.append(item)
        
        except Exception as e:
            print(f"Ошибка при извлечении информации о карьере: {e}")
        
        return career[:10]
    
    def parse_all_programs(self, urls: List[str]) -> Dict[str, Dict]:
        """
        Парсит несколько программ
        
        Args:
            urls: Список URL программ
            
        Returns:
            Словарь с данными всех программ
        """
        programs = {}
        for url in urls:
            program_id = url.split('/')[-1]
            programs[program_id] = self.parse_program_page(url)
        return programs
    
    def save_to_json(self, data: Dict, filename: str):
        """Сохраняет данные в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_from_json(self, filename: str) -> Dict:
        """Загружает данные из JSON файла"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


if __name__ == "__main__":
    # Тестирование парсера
    parser = ITMOMasterParser()
    
    urls = [
        "https://abit.itmo.ru/program/master/ai",
        "https://abit.itmo.ru/program/master/ai_product"
    ]
    
    programs = parser.parse_all_programs(urls)
    parser.save_to_json(programs, "data/programs.json")
    
    print(f"Парсинг завершен. Сохранено {len(programs)} программ.")
