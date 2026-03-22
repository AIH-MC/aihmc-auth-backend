import aiomysql
import logging
from libs.config_loader import settings

class Database:
    def __init__(self):
        self.config = settings.db
        self.pool = None

    async def get_pool(self):
        if not self.pool:
            self.pool = await aiomysql.create_pool(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                db=self.config['db_name'],
                autocommit=True,
                cursorclass=aiomysql.DictCursor
            )
        return self.pool

    # 封装读取：支持 db.query(sql, var1, var2...)
    async def query(self, sql, *args):
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, args) # 底层自动处理参数化
                    return await cur.fetchall()
        except Exception as e:
            logging.error(f"读取失败: {e} | SQL: {sql}")
            return False

    # 封装操作：支持 db.execute(sql, var1, var2...)
    async def execute(self, sql, *args):
        try:
            pool = await self.get_pool()
            async with pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(sql, args)
                    return True
        except Exception as e:
            logging.error(f"操作失败: {e} | SQL: {sql}")
            return False