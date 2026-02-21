from typing import Optional
from pydantic import BaseModel

class {class_name}Payload(BaseModel):
    """
    DTO для передачи данных внутри фичи {class_name}.
    """
    id: int
    # Добавьте свои поля здесь
