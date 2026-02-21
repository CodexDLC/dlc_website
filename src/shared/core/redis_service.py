# mypy: ignore-errors
import json
from collections.abc import Callable
from typing import Any

from loguru import logger as log
from redis.asyncio import Redis
from redis.asyncio.client import Pipeline
from redis.exceptions import RedisError


class RedisService:
    """
    Сервис для взаимодействия с Redis, предоставляющий асинхронные методы
    для работы с различными структурами данных Redis (хеши, множества, списки, ZSET, строки, JSON, Streams).
    """

    def __init__(self, client: Redis):
        self.redis_client = client
        log.debug(f"RedisService | status=initialized client={client}")

    async def execute_pipeline(self, builder_func: Callable[[Pipeline], None]) -> list[Any]:
        """Выполняет последовательность команд в пайплайне Redis."""
        try:
            async with self.redis_client.pipeline() as pipe:
                builder_func(pipe)
                results = await pipe.execute()

            log.debug(f"RedisPipeline | action=execute status=success commands_count={len(results)}")
            return results

        except RedisError:
            log.exception("RedisPipeline | action=execute status=failed reason='Redis error'")
            return []
        except Exception as e:
            log.exception(f"RedisPipeline | action=execute status=failed reason='Builder error' error='{e}'")
            return []

    # --- RedisJSON Methods ---

    async def json_set(self, key: str, path: str, obj: Any, nx: bool = False, xx: bool = False) -> bool:
        """Устанавливает значение JSON по указанному пути."""
        try:
            result = await self.redis_client.json().set(key, path, obj, nx=nx, xx=xx)
            log.debug(f"RedisJSON | action=set status=success key='{key}' path='{path}'")
            return bool(result)
        except RedisError:
            log.exception(f"RedisJSON | action=set status=failed reason='Redis error' key='{key}'")
            return False

    async def json_get(self, key: str, path: str = "$") -> Any:
        """Получает значение JSON по указанному пути."""
        try:
            result = await self.redis_client.json().get(key, path)
            log.debug(f"RedisJSON | action=get status=found key='{key}' path='{path}'")
            return result
        except RedisError:
            log.exception(f"RedisJSON | action=get status=failed reason='Redis error' key='{key}'")
            return None

    async def json_arrappend(self, key: str, path: str, *args: Any) -> int:
        """Добавляет элементы в массив JSON."""
        try:
            count = await self.redis_client.json().arrappend(key, path, *args)
            log.debug(f"RedisJSON | action=arrappend status=success key='{key}' count={count}")
            return int(count) if count else 0
        except RedisError:
            log.exception(f"RedisJSON | action=arrappend status=failed reason='Redis error' key='{key}'")
            return 0

    async def json_del(self, key: str, path: str = "$") -> int:
        """Удаляет значение JSON по указанному пути."""
        try:
            result = await self.redis_client.json().delete(key, path)
            log.debug(f"RedisJSON | action=del status=success key='{key}' path='{path}' count={result}")
            return int(result) if result else 0
        except RedisError:
            log.exception(f"RedisJSON | action=del status=failed reason='Redis error' key='{key}'")
            return 0

    # --- Hash Methods ---

    async def set_hash_json(self, key: str, field: str, data: dict[str, Any]) -> None:
        """Сериализует словарь в JSON-строку и сохраняет её в указанное поле хеша Redis."""
        try:
            data_json = json.dumps(data)
            await self.redis_client.hset(key, field, data_json)
            log.debug(f"RedisHash | action=set_json status=success key='{key}' field='{field}'")
        except TypeError:
            log.error(f"RedisHash | action=set_json status=failed reason='JSON serialization error' key='{key}'")
        except RedisError:
            log.exception(f"RedisHash | action=set_json status=failed reason='Redis error' key='{key}'")

    async def get_hash_json(self, key: str, field: str) -> dict[str, Any] | None:
        """Получает JSON-строку из поля хеша Redis и десериализует её в словарь."""
        try:
            data_json = await self.redis_client.hget(key, field)
            if data_json:
                log.debug(f"RedisHash | action=get_json status=found key='{key}' field='{field}'")
                return json.loads(data_json)
            log.debug(f"RedisHash | action=get_json status=not_found key='{key}' field='{field}'")
            return None
        except json.JSONDecodeError:
            log.error(f"RedisHash | action=get_json status=failed reason='JSON deserialization error' key='{key}'")
            return None
        except RedisError:
            log.exception(f"RedisHash | action=get_json status=failed reason='Redis error' key='{key}'")
            return None

    async def set_hash_field(self, key: str, field: str, value: str) -> None:
        """Устанавливает значение одного поля в хеше Redis."""
        try:
            await self.redis_client.hset(key, field, value)
            log.debug(f"RedisHash | action=set_field status=success key='{key}' field='{field}'")
        except RedisError:
            log.exception(f"RedisHash | action=set_field status=failed reason='Redis error' key='{key}'")

    async def set_hash_fields(self, key: str, data: dict[str, Any]) -> None:
        """Устанавливает несколько полей и их значений в хеше Redis."""
        try:
            await self.redis_client.hset(key, mapping=data)
            log.debug(f"RedisHash | action=set_fields status=success key='{key}' fields={list(data.keys())}")
        except RedisError:
            log.exception(f"RedisHash | action=set_fields status=failed reason='Redis error' key='{key}'")

    async def get_hash_field(self, key: str, field: str) -> str | None:
        """Получает строковое значение одного поля из хеша Redis."""
        try:
            value = await self.redis_client.hget(key, field)
            if value:
                log.debug(f"RedisHash | action=get_field status=found key='{key}' field='{field}'")
                return value
            log.debug(f"RedisHash | action=get_field status=not_found key='{key}' field='{field}'")
            return None
        except RedisError:
            log.exception(f"RedisHash | action=get_field status=failed reason='Redis error' key='{key}'")
            return None

    async def get_all_hash(self, key: str) -> dict[str, str] | None:
        """Получает все поля и их строковые значения из хеша Redis."""
        try:
            data_dict = await self.redis_client.hgetall(key)
            if data_dict:
                log.debug(f"RedisHash | action=get_all status=found key='{key}' fields_count={len(data_dict)}")
                return data_dict
            log.debug(f"RedisHash | action=get_all status=not_found key='{key}'")
            return None
        except RedisError:
            log.exception(f"RedisHash | action=get_all status=failed reason='Redis error' key='{key}'")
            return None

    async def delete_hash_key(self, key: str) -> None:
        """Удаляет весь хеш по указанному ключу Redis."""
        try:
            await self.redis_client.delete(key)
            log.debug(f"RedisHash | action=delete_key status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisHash | action=delete_key status=failed reason='Redis error' key='{key}'")

    # --- Set Methods ---

    async def add_to_set(self, key: str, value: str | int) -> None:
        """Добавляет значение в множество Redis."""
        try:
            await self.redis_client.sadd(key, str(value))
            log.debug(f"RedisSet | action=add status=success key='{key}' value='{value}'")
        except RedisError:
            log.exception(f"RedisSet | action=add status=failed reason='Redis error' key='{key}'")

    async def get_set_members(self, key: str) -> set[str]:
        """Возвращает все элементы множества Redis."""
        try:
            members = await self.redis_client.smembers(key)
            log.debug(f"RedisSet | action=get_all status=success key='{key}' members_count={len(members)}")
            return members
        except RedisError:
            log.exception(f"RedisSet | action=get_all status=failed reason='Redis error' key='{key}'")
            return set()

    async def is_set_member(self, key: str, value: str | int) -> bool:
        """Проверяет, является ли указанное значение элементом множества Redis."""
        try:
            is_member = await self.redis_client.sismember(key, str(value))
            log.debug(
                f"RedisSet | action=is_member status=checked key='{key}' value='{value}' result={bool(is_member)}"
            )
            return bool(is_member)
        except RedisError:
            log.exception(f"RedisSet | action=is_member status=failed reason='Redis error' key='{key}'")
            return False

    async def remove_from_set(self, key: str, value: str | int) -> None:
        """Удаляет указанное значение из множества Redis."""
        try:
            await self.redis_client.srem(key, str(value))
            log.debug(f"RedisSet | action=remove status=success key='{key}' value='{value}'")
        except RedisError:
            log.exception(f"RedisSet | action=remove status=failed reason='Redis error' key='{key}'")

    # --- List Methods ---

    async def push_to_list(self, key: str, value: str) -> None:
        """Добавляет элемент в конец списка Redis (RPUSH)."""
        try:
            await self.redis_client.rpush(key, value)
            log.debug(f"RedisList | action=push status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisList | action=push status=failed reason='Redis error' key='{key}'")

    async def pop_from_list_left(self, key: str) -> str | None:
        """Удаляет и возвращает первый элемент списка Redis (LPOP)."""
        try:
            value = await self.redis_client.lpop(key)
            if value:
                log.debug(f"RedisList | action=lpop status=success key='{key}'")
                return str(value)
            return None
        except RedisError:
            log.exception(f"RedisList | action=lpop status=failed reason='Redis error' key='{key}'")
            return None

    async def get_list_range(self, key: str, start: int = 0, end: int = -1) -> list[str]:
        """Возвращает диапазон элементов из списка Redis."""
        try:
            result = await self.redis_client.lrange(key, start, end)
            log.debug(f"RedisList | action=get_range status=success key='{key}' count={len(result)}")
            return result
        except RedisError:
            log.exception(f"RedisList | action=get_range status=failed reason='Redis error' key='{key}'")
            return []

    async def get_list_length(self, key: str) -> int:
        """Возвращает длину списка Redis."""
        try:
            count = await self.redis_client.llen(key)
            log.debug(f"RedisList | action=len status=success key='{key}' count={count}")
            return int(count) if count else 0
        except RedisError:
            log.exception(f"RedisList | action=len status=failed reason='Redis error' key='{key}'")
            return 0

    # --- Key/String Methods ---

    async def expire(self, key: str, time: int) -> bool:
        """Устанавливает время жизни (TTL) для ключа."""
        try:
            result = await self.redis_client.expire(key, time)
            log.debug(f"RedisKey | action=expire status=success key='{key}' ttl={time}")
            return bool(result)
        except RedisError:
            log.exception(f"RedisKey | action=expire status=failed reason='Redis error' key='{key}'")
            return False

    async def key_exists(self, key: str) -> bool:
        """Проверяет существование ключа в Redis."""
        try:
            exists = await self.redis_client.exists(key)
            log.debug(f"RedisKey | action=exists status=checked key='{key}' result={bool(exists)}")
            return bool(exists)
        except RedisError:
            log.exception(f"RedisKey | action=exists status=failed reason='Redis error' key='{key}'")
            return False

    async def set_value(self, key: str, value: str, ttl: int | None = None) -> None:
        """Устанавливает строковое значение для ключа Redis."""
        try:
            await self.redis_client.set(key, value, ex=ttl)
            log.debug(f"RedisString | action=set status=success key='{key}' ttl={ttl}")
        except RedisError:
            log.exception(f"RedisString | action=set status=failed reason='Redis error' key='{key}'")

    async def get_value(self, key: str) -> str | None:
        """Получает строковое значение по ключу Redis."""
        try:
            val = await self.redis_client.get(key)
            if val is not None:
                log.debug(f"RedisString | action=get status=found key='{key}'")
                return str(val)
            log.debug(f"RedisString | action=get status=not_found key='{key}'")
            return None
        except RedisError:
            log.exception(f"RedisString | action=get status=failed reason='Redis error' key='{key}'")
            return None

    async def delete_key(self, key: str) -> None:
        """Удаляет ключ любого типа из Redis."""
        try:
            await self.redis_client.delete(key)
            log.debug(f"RedisKey | action=delete status=success key='{key}'")
        except RedisError:
            log.exception(f"RedisKey | action=delete status=failed reason='Redis error' key='{key}'")

    async def delete_by_pattern(self, pattern: str) -> int:
        """Удаляет ключи из Redis, соответствующие заданному паттерну."""
        try:
            keys_to_delete = [k async for k in self.redis_client.scan_iter(match=pattern)]
            deleted_count = 0
            if keys_to_delete:
                deleted_count = await self.redis_client.delete(*keys_to_delete)
            log.debug(f"RedisKey | action=delete_by_pattern status=success pattern='{pattern}' deleted={deleted_count}")
            return int(deleted_count)
        except RedisError:
            log.exception(f"RedisKey | action=delete_by_pattern status=failed reason='Redis error' pattern='{pattern}'")
            return 0

    # --- Stream Methods ---

    async def stream_add(self, stream_name: str, data: dict[str, Any]) -> str | None:
        """
        Добавляет событие в стрим Redis.

        Автоматически выполняет санитизацию данных:
        - Конвертирует boolean значения в строки ('True'/'False')
        - Фильтрует поля со значением None
        """
        try:
            sanitized_data = {k: (str(v) if isinstance(v, bool) else v) for k, v in data.items() if v is not None}
            result = await self.redis_client.xadd(stream_name, sanitized_data)
            log.debug(f"RedisStream | action=add status=success stream='{stream_name}' id='{result}'")
            return str(result) if result else None
        except RedisError:
            log.exception(f"RedisStream | action=add status=failed reason='Redis error' stream='{stream_name}'")
            return None

    async def stream_create_group(self, stream_name: str, group_name: str) -> None:
        """Создает группу потребителей (если не существует)."""
        try:
            await self.redis_client.xgroup_create(stream_name, group_name, id="0", mkstream=True)
            log.debug(f"RedisStream | action=create_group status=success stream='{stream_name}' group='{group_name}'")
        except RedisError as e:
            if "BUSYGROUP" in str(e):
                log.debug(
                    f"RedisStream | action=create_group status=exists stream='{stream_name}' group='{group_name}'"
                )
            else:
                log.exception(
                    f"RedisStream | action=create_group status=failed reason='Redis error' stream='{stream_name}' group='{group_name}'"
                )

    async def stream_read_group(
        self, stream_name: str, group_name: str, consumer_name: str, count: int = 10
    ) -> list[tuple[Any, ...]]:
        """Читает новые события из стрима для группы."""
        try:
            streams = await self.redis_client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=count,
            )
            if streams:
                log.debug(
                    f"RedisStream | action=read_group status=success stream='{stream_name}' count={len(streams[0][1])}"
                )
                return streams[0][1]
            return []
        except RedisError:
            log.exception(f"RedisStream | action=read_group status=failed reason='Redis error' stream='{stream_name}'")
            return []

    async def stream_ack(self, stream_name: str, group_name: str, event_id: str) -> None:
        """Подтверждает обработку события."""
        try:
            await self.redis_client.xack(stream_name, group_name, event_id)
            log.debug(f"RedisStream | action=ack status=success stream='{stream_name}' id='{event_id}'")
        except RedisError:
            log.exception(
                f"RedisStream | action=ack status=failed reason='Redis error' stream='{stream_name}' id='{event_id}'"
            )
