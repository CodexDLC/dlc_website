import os

from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger


class TemplateRenderer:
    def __init__(self, templates_dir: str):
        """
        Инициализация Jinja2 Environment.
        :param templates_dir: Путь к папке с шаблонами.
        """
        if not os.path.exists(templates_dir):
            logger.error(f"Templates directory not found: {templates_dir}")
            raise FileNotFoundError(f"Templates directory not found: {templates_dir}")

        self.env = Environment(loader=FileSystemLoader(templates_dir), autoescape=select_autoescape(["html", "xml"]))
        logger.info(f"TemplateRenderer initialized with dir: {templates_dir}")

    def render(self, template_name: str, context: dict) -> str:
        """
        Рендеринг шаблона с переданным контекстом.
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except Exception as e:
            logger.error(f"Error rendering template {template_name}: {e}")
            raise e
