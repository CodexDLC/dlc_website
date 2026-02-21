import pathlib
import shutil
import tempfile

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores import FluentRuntimeCore
from loguru import logger as log
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from src.telegram_bot.core.config import BotSettings
from src.telegram_bot.middlewares.i18n_middleware import FSMContextI18nManager


def compile_locales(base_path: pathlib.Path) -> str:
    """
    Собирает все .ftl файлы из подпапок языков в структуру /tmp/bot_locales/{lang}/messages.ftl.
    """
    tmp_dir = pathlib.Path(tempfile.gettempdir()) / "bot_locales"

    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)

    tmp_dir.mkdir(parents=True, exist_ok=True)

    if not base_path.exists():
        log.warning(f"LocalesCompiler | Source path not found: {base_path}")
        return str(tmp_dir / "{locale}")

    for lang_dir in base_path.iterdir():
        if not lang_dir.is_dir():
            continue

        lang = lang_dir.name
        compiled_content = []

        for ftl_file in lang_dir.glob("*.ftl"):
            try:
                content = ftl_file.read_text(encoding="utf-8")
                compiled_content.append(f"### Source: {ftl_file.name} ###\n{content}\n")
            except Exception as e:
                log.error(f"LocalesCompiler | Error reading {ftl_file}: {e}")

        if compiled_content:
            lang_tmp_dir = tmp_dir / lang
            lang_tmp_dir.mkdir(exist_ok=True)

            output_file = lang_tmp_dir / "messages.ftl"
            try:
                output_file.write_text("\n".join(compiled_content), encoding="utf-8")
                log.debug(f"LocalesCompiler | Compiled {lang} into {output_file}")
            except Exception as e:
                log.error(f"LocalesCompiler | Error writing {output_file}: {e}")

    return str(tmp_dir / "{locale}")


async def build_bot(settings: BotSettings, redis_client: Redis) -> tuple[Bot, Dispatcher]:
    """
    Создает и конфигурирует экземпляры Bot и Dispatcher.
    """
    log.info("BotFactory | status=started")

    if not settings.bot_token:
        log.critical("BotFactory | status=failed reason='BOT_TOKEN not found'")
        raise RuntimeError("BOT_TOKEN не найден.")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))

    # --- Redis Check ---
    try:
        await redis_client.ping()
    except RedisConnectionError as e:
        log.critical(f"RedisCheck | status=failed error='{e}'")
        raise RuntimeError("Не удалось подключиться к Redis.") from e

    storage = RedisStorage(redis=redis_client)
    dp = Dispatcher(storage=storage, settings=settings)

    # --- I18n Setup ---
    base_path = pathlib.Path(__file__).parent.parent / "resources" / "locales"
    locales_path = compile_locales(base_path)

    i18n_middleware = I18nMiddleware(
        core=FluentRuntimeCore(path=locales_path),
        manager=FSMContextI18nManager(),
        default_locale="de",
    )
    i18n_middleware.setup(dp)

    log.info("BotFactory | status=finished")
    return bot, dp
