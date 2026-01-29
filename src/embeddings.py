"""
Модуль для работы с эмбеддингами на основе модели ru-bge-m3
"""
from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingModel:
    """Класс для работы с эмбеддингами на основе ru-bge-m3"""
    
    def __init__(self, model_name: str = "BAAI/bge-m3"):
        """
        Инициализация модели эмбеддингов
        
        Args:
            model_name: Название модели (по умолчанию ru-bge-m3)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def encode(self, text: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Получить эмбеддинг для текста или списка текстов
        
        Args:
            text: Текст или список текстов для кодирования
            normalize: Нормализовать ли векторы (для косинусного сходства)
            
        Returns:
            Массив эмбеддингов
        """
        embeddings = self.model.encode(
            text,
            normalize_embeddings=normalize,
            show_progress_bar=False
        )
        return embeddings
    
    def encode_course(self, course_name: str, course_description: str = "", 
                     course_tags: List[str] = None) -> np.ndarray:
        """
        Получить эмбеддинг для дисциплины
        
        Args:
            course_name: Название дисциплины
            course_description: Описание дисциплины
            course_tags: Теги дисциплины
            
        Returns:
            Эмбеддинг дисциплины
        """
        # Формируем текст для кодирования
        text_parts = [course_name]
        
        if course_description:
            text_parts.append(course_description)
        
        if course_tags:
            text_parts.extend(course_tags)
        
        text = " ".join(text_parts)
        return self.encode(text)
    
    def encode_user_profile(self, background: List[str], interests: List[str],
                           skills: List[str], goals: List[str]) -> np.ndarray:
        """
        Получить эмбеддинг для профиля пользователя
        
        Args:
            background: Образование и опыт
            interests: Интересы
            skills: Навыки
            goals: Карьерные цели
            
        Returns:
            Эмбеддинг профиля пользователя
        """
        # Формируем текст для кодирования
        text_parts = []
        
        if background:
            text_parts.extend(background)
        
        if interests:
            text_parts.extend(interests)
        
        if skills:
            text_parts.extend(skills)
        
        if goals:
            text_parts.extend(goals)
        
        text = " ".join(text_parts)
        return self.encode(text)
    
    def encode_program(self, program_title: str, program_description: str,
                      skills: List[str], career: List[str]) -> np.ndarray:
        """
        Получить эмбеддинг для магистерской программы
        
        Args:
            program_title: Название программы
            program_description: Описание программы
            skills: Навыки, которые дает программа
            career: Карьерные перспективы
            
        Returns:
            Эмбеддинг программы
        """
        text_parts = [program_title]
        
        if program_description:
            text_parts.append(program_description)
        
        if skills:
            text_parts.extend(skills)
        
        if career:
            text_parts.extend(career)
        
        text = " ".join(text_parts)
        return self.encode(text)
    
    def compute_similarity(self, embedding1: np.ndarray, 
                          embedding2: np.ndarray) -> float:
        """
        Вычислить косинусное сходство между двумя эмбеддингами
        
        Args:
            embedding1: Первый эмбеддинг
            embedding2: Второй эмбеддинг
            
        Returns:
            Значение сходства от 0 до 1
        """
        # Косинусное сходство для нормализованных векторов = скалярное произведение
        return float(np.dot(embedding1, embedding2))
    
    def batch_encode(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Пакетное кодирование текстов
        
        Args:
            texts: Список текстов для кодирования
            batch_size: Размер пакета
            
        Returns:
            Массив эмбеддингов
        """
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=False
        )


# Глобальный экземпляр модели для повторного использования
_model_instance = None


def get_embedding_model(model_name: str = "BAAI/bge-m3") -> EmbeddingModel:
    """
    Получить или создать глобальный экземпляр модели эмбеддингов
    
    Args:
        model_name: Название модели
        
    Returns:
        Экземпляр EmbeddingModel
    """
    global _model_instance
    if _model_instance is None:
        _model_instance = EmbeddingModel(model_name)
    return _model_instance
