"""
Модуль для работы с векторной базой данных Qdrant
"""
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
import os
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
    FilterSelector
)
from src.embeddings import EmbeddingModel, get_embedding_model


@dataclass
class CourseVector:
    """Векторное представление дисциплины"""
    course_id: str
    program_id: str
    name: str
    description: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class ProgramVector:
    """Векторное представление программы"""
    program_id: str
    title: str
    description: str
    embedding: List[float]
    metadata: Dict[str, Any]


class QdrantVectorDB:
    """Класс для работы с Qdrant векторной базой данных"""
    
    # Названия коллекций
    COURSES_COLLECTION = "courses"
    PROGRAMS_COLLECTION = "programs"
    PROFILES_COLLECTION = "user_profiles"
    
    def __init__(self, url: str = None, api_key: str = None, 
                 embedding_model: EmbeddingModel = None):
        """
        Инициализация подключения к Qdrant
        
        Args:
            url: URL Qdrant сервера (по умолчанию localhost:6333)
            api_key: API ключ для Qdrant Cloud (опционально)
            embedding_model: Модель эмбеддингов
        """
        self.url = url or os.getenv("QDRANT_URL", "http://localhost:6333")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        
        # Инициализация клиента Qdrant
        self.client = QdrantClient(
            url=self.url,
            api_key=self.api_key
        )
        
        # Инициализация модели эмбеддингов
        self.embedding_model = embedding_model or get_embedding_model()
        self.embedding_dim = self.embedding_model.embedding_dim
        
        # Создаем коллекции при инициализации
        self._ensure_collections_exist()
    
    def _ensure_collections_exist(self):
        """Создает коллекции, если они не существуют"""
        # Коллекция для дисциплин
        if not self.client.collection_exists(self.COURSES_COLLECTION):
            self.client.create_collection(
                collection_name=self.COURSES_COLLECTION,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
        
        # Коллекция для программ
        if not self.client.collection_exists(self.PROGRAMS_COLLECTION):
            self.client.create_collection(
                collection_name=self.PROGRAMS_COLLECTION,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
        
        # Коллекция для профилей пользователей
        if not self.client.collection_exists(self.PROFILES_COLLECTION):
            self.client.create_collection(
                collection_name=self.PROFILES_COLLECTION,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE
                )
            )
    
    def add_course(self, course_id: str, program_id: str, name: str,
                  description: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Добавляет дисциплину в векторную базу
        
        Args:
            course_id: ID дисциплины
            program_id: ID программы
            name: Название дисциплины
            description: Описание дисциплины
            metadata: Дополнительные метаданные
            
        Returns:
            True если успешно, иначе False
        """
        try:
            # Получаем эмбеддинг
            embedding = self.embedding_model.encode_course(name, description)
            
            # Создаем точку
            point = PointStruct(
                id=course_id,
                vector=embedding.tolist(),
                payload={
                    "program_id": program_id,
                    "name": name,
                    "description": description,
                    **(metadata or {})
                }
            )
            
            # Добавляем в коллекцию
            self.client.upsert(
                collection_name=self.COURSES_COLLECTION,
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Ошибка при добавлении дисциплины: {e}")
            return False
    
    def add_program(self, program_id: str, title: str, description: str,
                   skills: List[str], career: List[str],
                   metadata: Dict[str, Any] = None) -> bool:
        """
        Добавляет программу в векторную базу
        
        Args:
            program_id: ID программы
            title: Название программы
            description: Описание программы
            skills: Навыки
            career: Карьерные перспективы
            metadata: Дополнительные метаданные
            
        Returns:
            True если успешно, иначе False
        """
        try:
            # Получаем эмбеддинг
            embedding = self.embedding_model.encode_program(
                title, description, skills, career
            )
            
            # Создаем точку
            point = PointStruct(
                id=program_id,
                vector=embedding.tolist(),
                payload={
                    "title": title,
                    "description": description,
                    "skills": skills,
                    "career": career,
                    **(metadata or {})
                }
            )
            
            # Добавляем в коллекцию
            self.client.upsert(
                collection_name=self.PROGRAMS_COLLECTION,
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Ошибка при добавлении программы: {e}")
            return False
    
    def add_user_profile(self, user_id: int, background: List[str],
                        interests: List[str], skills: List[str],
                        goals: List[str]) -> bool:
        """
        Добавляет профиль пользователя в векторную базу
        
        Args:
            user_id: ID пользователя
            background: Образование и опыт
            interests: Интересы
            skills: Навыки
            goals: Карьерные цели
            
        Returns:
            True если успешно, иначе False
        """
        try:
            # Получаем эмбеддинг
            embedding = self.embedding_model.encode_user_profile(
                background, interests, skills, goals
            )
            
            # Создаем точку
            point = PointStruct(
                id=str(user_id),
                vector=embedding.tolist(),
                payload={
                    "background": background,
                    "interests": interests,
                    "skills": skills,
                    "goals": goals
                }
            )
            
            # Добавляем в коллекцию
            self.client.upsert(
                collection_name=self.PROFILES_COLLECTION,
                points=[point]
            )
            return True
        except Exception as e:
            print(f"Ошибка при добавлении профиля пользователя: {e}")
            return False
    
    def search_courses(self, query_embedding: List[float], 
                      program_id: str = None, limit: int = 5,
                      score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Ищет похожие дисциплины
        
        Args:
            query_embedding: Эмбеддинг запроса
            program_id: ID программы для фильтрации (опционально)
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог схожести
            
        Returns:
            Список найденных дисциплин с оценками
        """
        # Создаем фильтр по программе если указан
        query_filter = None
        if program_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="program_id",
                        match=MatchValue(value=program_id)
                    )
                ]
            )
        
        # Выполняем поиск
        results = self.client.search(
            collection_name=self.COURSES_COLLECTION,
            query_vector=query_embedding,
            query_filter=query_filter,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Форматируем результаты
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "name": result.payload.get("name"),
                "description": result.payload.get("description"),
                "program_id": result.payload.get("program_id"),
                "metadata": {k: v for k, v in result.payload.items() 
                           if k not in ["name", "description", "program_id"]}
            })
        
        return formatted_results
    
    def search_programs(self, query_embedding: List[float],
                       limit: int = 5, 
                       score_threshold: float = 0.0) -> List[Dict[str, Any]]:
        """
        Ищет похожие программы
        
        Args:
            query_embedding: Эмбеддинг запроса
            limit: Максимальное количество результатов
            score_threshold: Минимальный порог схожести
            
        Returns:
            Список найденных программ с оценками
        """
        # Выполняем поиск
        results = self.client.search(
            collection_name=self.PROGRAMS_COLLECTION,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold
        )
        
        # Форматируем результаты
        formatted_results = []
        for result in results:
            formatted_results.append({
                "id": result.id,
                "score": result.score,
                "title": result.payload.get("title"),
                "description": result.payload.get("description"),
                "skills": result.payload.get("skills", []),
                "career": result.payload.get("career", []),
                "metadata": {k: v for k, v in result.payload.items() 
                           if k not in ["title", "description", "skills", "career"]}
            })
        
        return formatted_results
    
    def recommend_courses_for_user(self, user_id: int, program_id: str = None,
                                  limit: int = 5) -> List[Dict[str, Any]]:
        """
        Рекомендует дисциплины для пользователя на основе его профиля
        
        Args:
            user_id: ID пользователя
            program_id: ID программы для фильтрации (опционально)
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список рекомендованных дисциплин с оценками
        """
        try:
            # Получаем эмбеддинг профиля пользователя
            profile_result = self.client.retrieve(
                collection_name=self.PROFILES_COLLECTION,
                ids=[str(user_id)]
            )
            
            if not profile_result:
                return []
            
            profile_embedding = profile_result[0].vector
            
            # Ищем похожие дисциплины
            return self.search_courses(
                profile_embedding,
                program_id=program_id,
                limit=limit
            )
        except Exception as e:
            print(f"Ошибка при поиске рекомендаций: {e}")
            return []
    
    def recommend_programs_for_user(self, user_id: int, 
                                   limit: int = 5) -> List[Dict[str, Any]]:
        """
        Рекомендует программы для пользователя на основе его профиля
        
        Args:
            user_id: ID пользователя
            limit: Максимальное количество рекомендаций
            
        Returns:
            Список рекомендованных программ с оценками
        """
        try:
            # Получаем эмбеддинг профиля пользователя
            profile_result = self.client.retrieve(
                collection_name=self.PROFILES_COLLECTION,
                ids=[str(user_id)]
            )
            
            if not profile_result:
                return []
            
            profile_embedding = profile_result[0].vector
            
            # Ищем похожие программы
            return self.search_programs(
                profile_embedding,
                limit=limit
            )
        except Exception as e:
            print(f"Ошибка при поиске рекомендаций программ: {e}")
            return []
    
    def delete_collection(self, collection_name: str) -> bool:
        """
        Удаляет коллекцию
        
        Args:
            collection_name: Название коллекции
            
        Returns:
            True если успешно, иначе False
        """
        try:
            self.client.delete_collection(collection_name)
            return True
        except Exception as e:
            print(f"Ошибка при удалении коллекции: {e}")
            return False
    
    def get_collection_info(self, collection_name: str) -> Dict[str, Any]:
        """
        Получает информацию о коллекции
        
        Args:
            collection_name: Название коллекции
            
        Returns:
            Информация о коллекции
        """
        try:
            info = self.client.get_collection(collection_name)
            return {
                "name": collection_name,
                "points_count": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance": info.config.params.vectors.distance
            }
        except Exception as e:
            print(f"Ошибка при получении информации о коллекции: {e}")
            return {}


# Глобальный экземпляр для повторного использования
_db_instance = None


def get_vector_db(url: str = None, api_key: str = None,
                 embedding_model: EmbeddingModel = None) -> QdrantVectorDB:
    """
    Получить или создать глобальный экземпляр векторной базы данных
    
    Args:
        url: URL Qdrant сервера
        api_key: API ключ для Qdrant Cloud
        embedding_model: Модель эмбеддингов
        
    Returns:
        Экземпляр QdrantVectorDB
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = QdrantVectorDB(url, api_key, embedding_model)
    return _db_instance
