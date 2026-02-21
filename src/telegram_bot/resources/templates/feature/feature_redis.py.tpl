# 1. Фабрика (DI)
def create_orchestrator(container):
    """
    Фабрика для создания оркестратора фичи {class_name}.
    Здесь можно подключить необходимые репозитории или API-клиенты.
    """
    from .logic.orchestrator import {class_name}Orchestrator

    return {class_name}Orchestrator(settings=container.settings)
