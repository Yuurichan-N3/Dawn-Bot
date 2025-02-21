import asyncio
import json
import os
import pytz
from datetime import datetime
from aiohttp import ClientSession, ClientTimeout, ClientResponseError
from aiohttp_socks import ProxyConnector
from fake_useragent import FakeUserAgent
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from tqdm import tqdm
import logging
from uuid import uuid4

# Setup timezone
wib = pytz.timezone('Asia/Jakarta')

# Setup logging with RichHandler
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%Y-%m-%d %H:%M:%S %Z]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("DawnBot")

# Setup rich console
console = Console()

# Banner
BANNER = """
╔══════════════════════════════════════════════╗
║       🌟 DAWN BOT - Automated Earnings       ║
║   Automate your AeroPres account tasks!      ║
║  Developed by: https://t.me/sentineldiscus   ║
╚══════════════════════════════════════════════╝
"""

class Dawn:
    def __init__(self) -> None:
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Host": "www.aeropres.in",
            "Origin": "chrome-extension://fpdkjdnhkakefebpekbdhillbhonfjjp",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "cross-site",
            "User-Agent": FakeUserAgent().random
        }
        self.extension_id = "fpdkjdnhkakefebpekbdhillbhonfjjp"
        self.proxies = []
        self.proxy_index = 0

    def clear_terminal(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
    
    async def load_auto_proxies(self):
        url = "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/all.txt"
        try:
            async with ClientSession(timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url) as response:
                    response.raise_for_status()
                    content = await response.text()
                    with open('auto_proxy.txt', 'w') as f:
                        f.write(content)

                    self.proxies = content.splitlines()
                    if not self.proxies:
                        logger.warning("No proxies found in the downloaded list!")
                        return
                    
                    logger.info(f"Proxies successfully downloaded. Loaded {len(self.proxies)} proxies.")
                    await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Failed to load proxies: {e}")
            return []

    async def load_manual_proxy(self):
        try:
            if not os.path.exists('proxy.txt'):
                logger.error("Proxy file 'proxy.txt' not found!")
                return

            with open('proxy.txt', "r") as f:
                self.proxies = f.read().splitlines()

            logger.info(f"Loaded {len(self.proxies)} proxies.")
            await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Failed to load manual proxies: {e}")
            self.proxies = []

    def get_next_proxy(self):
        if not self.proxies:
            logger.warning("No proxies available!")
            return None
        proxy = self.proxies[self.proxy_index]
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy
    
    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def load_accounts(self):
        try:
            if not os.path.exists('accounts.json'):
                logger.error("File 'accounts.json' tidak ditemukan.")
                return []
            with open('accounts.json', 'r') as file:
                data = json.load(file)
                return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def generate_app_id(self):
        return uuid4().hex
    
    def hide_email(self, email):
        local, domain = email.split('@', 1)
        hide_local = local[:3] + '*' * 3 + local[-3:]
        return f"{hide_local}@{domain}"
    
    def hide_token(self, token):
        return token[:3] + '*' * 3 + token[-3:]
        
    async def cek_ip(self, proxy=None):
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=20)) as session:
                async with session.get('https://ipinfo.io/json') as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception:
            return None
        
    async def user_data(self, app_id: str, token: str, proxy=None):
        url = f"https://www.aeropres.in/api/atom/v1/userreferral/getpoint?appid={app_id}"
        headers = {
            **self.headers,
            "Authorization": f"Bearer {token}",  # Fixed typo: "Berear" -> "Bearer"
            "Content-Type": "application/json",
        }
        connector = ProxyConnector.from_url(proxy) if proxy else None
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=20)) as session:
                async with session.get(url=url, headers=headers) as response:
                    if response.status == 400:
                        logger.warning(f"Token {self.hide_token(token)} is expired")
                        return None
                    response.raise_for_status()
                    result = await response.json()
                    return result['data']['rewardPoint']
        except Exception:
            return None
        
    async def send_keepalive(self, app_id: str, token: str, email: str, proxy=None, retries=60):
        url = f"https://www.aeropres.in/chromeapi/dawn/v1/userreward/keepalive?appid={app_id}"
        data = json.dumps({"username": email, "extensionid": self.extension_id, "numberoftabs": 0, "_v": "1.1.1"})
        headers = {
            **self.headers,
            "Authorization": f"Bearer {token}",  # Fixed typo: "Berear" -> "Bearer"
            "Content-Length": str(len(data)),
            "Content-Type": "application/json",
        }
        for attempt in tqdm(range(retries), desc=f"Keepalive attempts for {self.hide_email(email)}", leave=False):
            connector = ProxyConnector.from_url(proxy) if proxy else None
            try:
                async with ClientSession(connector=connector, timeout=ClientTimeout(total=10)) as session:
                    async with session.post(url=url, headers=headers, data=data) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception:
                if attempt < retries - 1:
                    await asyncio.sleep(1)
                    continue
                return None

    async def question(self):
        while True:
            try:
                console.print("Input number => Enter")
                console.print("1. Gunakan proxy gratis ")
                console.print("2. Gunakan proxy pribadi ")
                console.print("3. (Jalankan tanpa proxy ")
                choose = int(console.input("[bold green]Choose [1/2/3] -> [/]").strip())
                if choose in [1, 2, 3]:
                    proxy_type = (
                        "With Auto Proxy" if choose == 1 else 
                        "With Manual Proxy" if choose == 2 else 
                        "Without Proxy"
                    )
                    console.print(f"[green]Run {proxy_type} Selected.[/]")
                    await asyncio.sleep(1)
                    return choose
                else:
                    console.print("[red]Please enter either 1, 2 or 3.[/]")
            except ValueError:
                console.print("[red]Invalid input. Enter a number (1, 2 or 3).[/]")

    async def process_accounts(self, app_id: str, token: str, email: str, use_proxy: bool):
        hide_email = self.hide_email(email)
        table = Table(title=f"Processing {hide_email}")
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Details", style="yellow")

        proxy = None
        if use_proxy:
            proxy = self.check_proxy_schemes(self.get_next_proxy())

        my_ip = await self.cek_ip(proxy)
        if my_ip:
            logger.info(f"IP: {my_ip['ip']} | Country: {my_ip['country']}-{my_ip['region']}")
            table.add_row("IP Check", "Success", f"{my_ip['ip']} ({my_ip['country']})")
        else:
            table.add_row("IP Check", "Failed", "N/A")

        await asyncio.sleep(1)
        user = await self.user_data(app_id, token, proxy)
        if not user:
            logger.error(f"Account {hide_email} - Login Failed with Proxy {proxy or 'None'}")
            table.add_row("Login", "Failed", "N/A")
            console.print(table)
            return
        
        total_points = sum(value for key, value in user.items() if 'points' in key and isinstance(value, (int, float)))
        logger.info(f"Account {hide_email} - Login Success | Balance: {total_points:.0f} Points")
        table.add_row("Login", "Success", f"Balance: {total_points:.0f} Points")

        console.print(f"Trying to send ping for {hide_email}...", end="\r")
        await asyncio.sleep(1)

        keepalive = await self.send_keepalive(app_id, token, email, proxy)
        status = "Success" if keepalive else "Failed"
        logger.info(f"Ping for {hide_email} - Keep Alive {'Recorded' if keepalive else 'Not Recorded'}")
        table.add_row("Keepalive", status, f"Proxy: {proxy or 'None'}")

        console.print(table)

    async def main(self):
        try:
            console.print(BANNER)
            accounts = self.load_accounts()
            if not accounts:
                logger.error("No accounts loaded from 'accounts.json'.")
                return
            
            use_proxy_choice = await self.question()
            use_proxy = use_proxy_choice in [1, 2]

            self.clear_terminal()
            console.print(BANNER)
            logger.info(f"Account's Total: {len(accounts)}")

            last_proxy_update = None
            proxy_update_interval = 1800

            if use_proxy and use_proxy_choice == 1:
                await self.load_auto_proxies()
                last_proxy_update = datetime.now()
            elif use_proxy and use_proxy_choice == 2:
                await self.load_manual_proxy()

            while True:
                if use_proxy and use_proxy_choice == 1:
                    if not last_proxy_update or (datetime.now() - last_proxy_update).total_seconds() > proxy_update_interval:
                        await self.load_auto_proxies()
                        last_proxy_update = datetime.now()

                for account in tqdm(accounts, desc="Processing accounts"):
                    app_id = self.generate_app_id()
                    token = account.get('Token')
                    email = account.get('Email', 'Unknown Email')

                    if not token:
                        logger.warning(f"Account {email} - Token Not Found in 'accounts.json'")
                        continue

                    await self.process_accounts(app_id, token, email, use_proxy)
                    await asyncio.sleep(3)

                with tqdm(total=120, desc="Waiting for next cycle", unit="s") as pbar:
                    for _ in range(120):
                        await asyncio.sleep(1)
                        pbar.update(1)
                        pbar.set_description(f"Waiting for next cycle ({self.format_seconds(pbar.n)}/{self.format_seconds(120)})")

        except Exception as e:
            logger.error(f"Error: {e}")

if __name__ == "__main__":
    try:
        bot = Dawn()
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        console.print("[bold red][EXIT] Dawn - BOT[/]")
