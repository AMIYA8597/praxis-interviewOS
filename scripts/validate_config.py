import os
import sys
import asyncio
import psycopg2
import redis.asyncio as redis
from colorama import init, Fore, Style

init(autoreset=True)

async def check_redis(url: str) -> tuple[bool, str]:
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=2)
        await client.ping()
        await client.close()
        return True, "OK"
    except Exception as e:
        return False, str(e)

def check_postgres(url: str) -> tuple[bool, str]:
    try:
        conn = psycopg2.connect(url, connect_timeout=2)
        conn.close()
        return True, "OK"
    except Exception as e:
        return False, str(e).strip()

async def check_supabase(url: str, key: str) -> tuple[bool, str]:
    try:
        from supabase import create_client
        client = create_client(url, key)
        # Lightweight check: get bucket list
        client.storage.list_buckets()
        return True, "OK"
    except Exception as e:
        return False, str(e)

async def main():
    print(f"{Fore.CYAN}=== PRAXIS Configuration Validator ==={Style.RESET_ALL}\n")
    
    # We load pydantic-settings manually here to catch validation errors
    try:
        from packages.config.settings import Settings
        settings = Settings()
    except Exception as e:
        print(f"{Fore.RED}FATAL CONFIGURATION ERROR:{Style.RESET_ALL}")
        print(e)
        sys.exit(1)
        
    print(f"{Fore.GREEN}Settings schema loaded successfully!{Style.RESET_ALL}\n")
    
    table = []
    
    # Check Postgres
    db_status, db_err = check_postgres(settings.DATABASE_URL)
    table.append(("DATABASE_URL", "SET", "PASS" if db_status else "FAIL", db_err if not db_status else ""))
    
    # Check Redis
    redis_status, redis_err = await check_redis(settings.REDIS_URL)
    table.append(("REDIS_URL", "SET", "PASS" if redis_status else "FAIL", redis_err if not redis_status else ""))
    
    # Check Storage Backend
    table.append(("STORAGE_BACKEND", "SET", "PASS", settings.STORAGE_BACKEND))
    
    # Check Supabase
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        supa_status, supa_err = await check_supabase(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        table.append(("SUPABASE Config", "SET", "PASS" if supa_status else "FAIL", supa_err if not supa_status else ""))
    else:
        table.append(("SUPABASE Config", "MISSING", "SKIP", "Supabase URL/Key not provided"))

    # Print table
    col_width = [25, 10, 10, 50]
    header = f"{'VARIABLE'.ljust(col_width[0])}{'STATUS'.ljust(col_width[1])}{'CHECK'.ljust(col_width[2])}DETAILS"
    print(header)
    print("-" * len(header))
    
    all_passed = True
    for var, stat, chk, det in table:
        color = Fore.GREEN if chk == "PASS" else (Fore.RED if chk == "FAIL" else Fore.YELLOW)
        det_trunc = det[:47] + "..." if len(det) > 50 else det
        row = f"{var.ljust(col_width[0])}{stat.ljust(col_width[1])}{color}{chk.ljust(col_width[2])}{Style.RESET_ALL}{det_trunc}"
        print(row)
        if chk == "FAIL":
            all_passed = False
            
    print("\nLocal Only Ready:", settings.local_only_ready())
    
    if not all_passed:
        print(f"\n{Fore.RED}Validation failed. Check the errors above.{Style.RESET_ALL}")
        sys.exit(1)
    else:
        print(f"\n{Fore.GREEN}All checks passed successfully.{Style.RESET_ALL}")

if __name__ == "__main__":
    asyncio.run(main())
