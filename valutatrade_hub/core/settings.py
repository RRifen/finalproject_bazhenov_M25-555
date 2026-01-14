import tomllib
from pathlib import Path


class SettingsLoader:
    """
    Singleton для загрузки и кеширования конфигурации приложения.
    
    Реализация через __new__ выбрана для простоты и читабельности кода.
    Альтернатива через метакласс была бы более сложной и менее понятной.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Гарантирует создание только одного экземпляра"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Инициализация конфигурации (выполняется только один раз)"""
        if self._initialized:
            return
        
        self._config = {}
        self._load_config()
        self._initialized = True
    
    def _load_config(self):
        """Загружает конфигурацию из pyproject.toml или config.json"""
        base_dir = Path()
        
        pyproject_path = base_dir / "pyproject.toml"
        if pyproject_path.exists():
            try:
                with open(pyproject_path, "rb") as f:
                    pyproject_data = tomllib.load(f)
                    if "tool" in pyproject_data and "valutatrade" in pyproject_data["tool"]:  # noqa: E501
                        self._config = pyproject_data["tool"]["valutatrade"].copy()
            except Exception:
                pass
    
    def get(self, key, default=None):
        """Получает значение конфигурации по ключу"""
        return self._config.get(key, default)
    
    def reload(self):
        """Перезагружает конфигурацию из файлов"""
        self._config = {}
        self._load_config()


settings = SettingsLoader()
