from typing import Union, Optional, List
import asyncpg
from asyncpg import Connection
from asyncpg.pool import Pool
from data import config
from telethon import TelegramClient
from telethon.types import Message


class Database:
    def __init__(self):
        self.pool: Optional[Pool] = None

    async def create(self):
        """PostgreSQL bilan ulanishni yaratish."""
        self.pool = await asyncpg.create_pool(
            user=config.DB_USER,
            password=config.DB_PASS,
            host=config.DB_HOST,
            database=config.DB_NAME,
            port=config.DB_PORT,
            ssl=False
        )

    async def execute(
        self,
        command: str,
        *args,
        fetch: bool = False,
        fetchval: bool = False,
        fetchrow: bool = False,
        execute: bool = False,
    ) -> Union[List[asyncpg.Record], asyncpg.Record, str, int, None]:
        """SQL buyruqlarini bajarish."""
        if self.pool is None:
            raise ConnectionError("Database pool is not initialized!")

        async with self.pool.acquire() as connection:
            connection: Connection
            async with connection.transaction():
                if fetch:
                    return await connection.fetch(command, *args)
                elif fetchval:
                    return await connection.fetchval(command, *args)
                elif fetchrow:
                    return await connection.fetchrow(command, *args)
                elif execute:
                    return await connection.execute(command, *args)
        return None
    

    async def create_table_users(self):
        sql = """
        CREATE TABLE IF NOT EXISTS Users (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL,
            telegram_id BIGINT NOT NULL UNIQUE,
            username VARCHAR(255) NULL,
            language VARCHAR(10) DEFAULT 'uz',
            is_admin BOOLEAN DEFAULT FALSE,
            latitude DOUBLE PRECISION NULL,  # Foydalanuvchi joylashuvi (kenglik)
            longitude DOUBLE PRECISION NULL, # Foydalanuvchi joylashuvi (uzunlik)
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await self.execute(sql, execute=True)

    async def create_table_bot_clients(self):
        sql = """
        CREATE TABLE IF NOT EXISTS bot_clients (
            id SERIAL PRIMARY KEY,
            phone_number VARCHAR(20) NOT NULL UNIQUE,
            api_id BIGINT NOT NULL,
            api_hash VARCHAR(255) NOT NULL,
            session_name VARCHAR(255) NOT NULL UNIQUE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await self.execute(sql, execute=True)

    async def create_table_films(self):
        sql = """
        CREATE TABLE IF NOT EXISTS Films (
            id SERIAL PRIMARY KEY,
            film_name VARCHAR(255) NOT NULL,
            starting_code VARCHAR(50) NOT NULL UNIQUE,
            total_series INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        await self.execute(sql, execute=True)

    @staticmethod
    def format_args(sql, parameters: dict):
        sql += " AND ".join(
            [f"{item} = ${num}" for num, item in enumerate(parameters.keys(), start=1)]
        )
        return sql, tuple(parameters.values())

    # User related methods
    async def add_user(self, full_name, telegram_id, username=None, language='uz', is_admin=False):
        sql = """
        INSERT INTO Users (full_name, telegram_id, username, language, is_admin) 
        VALUES($1, $2, $3, $4, $5) 
        RETURNING *
        """
        return await self.execute(sql, full_name, telegram_id, username, language, is_admin, fetchrow=True)
    
    async def add_bot_client(self, phone_number: str, api_id: int, api_hash: str, session_name: str):
        sql = """
        INSERT INTO bot_clients (phone_number, api_id, api_hash, session_name) 
        VALUES($1, $2, $3, $4) 
        RETURNING *
        """
        return await self.execute(sql, phone_number, api_id, api_hash, session_name, fetchrow=True)

    
    
    ##################### Films Table #############################################


    async def add_film(self, film_name: str, starting_code: str, total_series: int):
        # Generate search_code from starting_code (e.g., "M.S.A.V-1" -> "M.S.A")
        search_code = starting_code.split('_')[0]
        sql = """
        INSERT INTO Films (film_name, starting_code, total_series) 
        VALUES($1, $2, $3) 
        RETURNING *
        """
        return await self.execute(sql, film_name, starting_code, search_code, total_series, fetchrow=True)

    async def get_film_by_starting_code(self, starting_code: str):
        sql = "SELECT * FROM Films WHERE starting_code = $1"
        return await self.execute(sql, starting_code, fetchrow=True)

    async def get_film_series(self, search_code: str):
        sql = "SELECT * FROM Films WHERE search_code = $1 ORDER BY starting_code"
        return await self.execute(sql, search_code, fetch=True)
    
    
    async def save_user_location(self, telegram_id: int, latitude: float, longitude: float):
        sql = """
        UPDATE Users
        SET latitude = $1, longitude = $2
        WHERE telegram_id = $3;
        """
        await self.execute(sql, latitude, longitude, telegram_id, execute=True)
        
    
    
    ###################################################################################
    
    
    ########################### Telethon Client Codes ###################################


    async def get_bot_client(self, **kwargs):
        sql = "SELECT * FROM bot_clients WHERE "
        sql, parameters = self.format_args(sql, parameters=kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def get_active_bot_clients(self):
        sql = "SELECT * FROM bot_clients WHERE is_active = TRUE"
        return await self.execute(sql, fetch=True)

    async def update_bot_client_status(self, client_id: int, is_active: bool):
        sql = "UPDATE bot_clients SET is_active=$2 WHERE id=$1"
        return await self.execute(sql, client_id, is_active, execute=True)

    async def delete_bot_client(self, client_id: int):
        sql = "DELETE FROM bot_clients WHERE id=$1"
        return await self.execute(sql, client_id, execute=True)

    # Telethon client management methods
    async def initialize_client(self, client_id: int):
        """Initialize a Telethon client for a specific bot client"""
        client_data = await self.get_bot_client(id=client_id)
        if not client_data:
            raise ValueError("Bot client not found")

        if client_id in self.active_clients:
            return self.active_clients[client_id]

        client = TelegramClient(
            client_data['session_name'],
            client_data['api_id'],
            client_data['api_hash']
        )
        await client.start()
        self.active_clients[client_id] = client
        return client


    async def cleanup_clients(self):
        """Close all active Telethon clients"""
        for client in self.active_clients.values():
            await client.disconnect()
        self.active_clients.clear()
    
    ################################ End Telethon client #######################################

    async def select_all_users(self):
        sql = "SELECT * FROM Users ORDER BY id"
        return await self.execute(sql, fetch=True)

    async def select_user(self, **kwargs):
        sql = "SELECT * FROM Users WHERE "
        sql, parameters = self.format_args(sql, parameters=kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def count_users(self):
        sql = "SELECT COUNT(*) FROM Users"
        return await self.execute(sql, fetchval=True)

    async def update_user_username(self, username, telegram_id):
        sql = "UPDATE Users SET username=$1 WHERE telegram_id=$2"
        return await self.execute(sql, username, telegram_id, execute=True)

    async def update_user_language(self, language, telegram_id):
        sql = "UPDATE Users SET language=$1 WHERE telegram_id=$2"
        return await self.execute(sql, language, telegram_id, execute=True)

    async def set_user_admin(self, telegram_id, is_admin=True):
        sql = "UPDATE Users SET is_admin=$1 WHERE telegram_id=$2"
        return await self.execute(sql, is_admin, telegram_id, execute=True)

    # Film related methods
    async def add_film(self, film_name: str, starting_code: str, total_series: int):
        sql = """
        INSERT INTO Films (film_name, starting_code, total_series) 
        VALUES($1, $2, $3) 
        RETURNING *
        """
        return await self.execute(sql, film_name, starting_code, total_series, fetchrow=True)

    async def get_film(self, **kwargs):
        sql = "SELECT * FROM Films WHERE "
        sql, parameters = self.format_args(sql, parameters=kwargs)
        return await self.execute(sql, *parameters, fetchrow=True)

    async def get_all_films(self, limit=None, offset=None):
        sql = "SELECT * FROM Films ORDER BY created_at DESC"
        if limit:
            sql += f" LIMIT {limit}"
        if offset:
            sql += f" OFFSET {offset}"
        return await self.execute(sql, fetch=True)

    async def get_films_by_code_prefix(self, code_prefix: str):
        sql = "SELECT * FROM Films WHERE starting_code LIKE $1 || '%' ORDER BY starting_code"
        return await self.execute(sql, code_prefix, fetch=True)

    async def update_film(self, film_id: int, **kwargs):
        update_fields = [f"{key} = ${i+2}" for i, key in enumerate(kwargs.keys())]
        sql = f"UPDATE Films SET {', '.join(update_fields)} WHERE id = $1 RETURNING *"
        parameters = [film_id] + list(kwargs.values())
        return await self.execute(sql, *parameters, fetchrow=True)

    async def delete_film(self, film_id: int):
        sql = "DELETE FROM Films WHERE id = $1 RETURNING *"
        return await self.execute(sql, film_id, fetchrow=True)

    async def count_films(self):
        sql = "SELECT COUNT(*) FROM Films"
        return await self.execute(sql, fetchval=True)

    # Cleanup methods
    async def delete_users(self):
        await self.execute("DELETE FROM Users WHERE TRUE", execute=True)

    async def delete_films(self):
        await self.execute("DELETE FROM Films WHERE TRUE", execute=True)

    async def drop_users(self):
        await self.execute("DROP TABLE Users", execute=True)

    async def drop_films(self):
        await self.execute("DROP TABLE Films", execute=True)