from pathlib import Path
import json
import aiofiles
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class DonationSystem:
    """Система донатов через Telegram Stars"""
    
    def __init__(self, storage_dir: str = "data"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.donations_file = self.storage_dir / "donations.json"
        self.user_balances_file = self.storage_dir / "star_balances.json"
    
    async def _load_donations(self) -> List[Dict]:
        """Загрузка всех донатов"""
        if not self.donations_file.exists():
            return []
        
        try:
            async with aiofiles.open(self.donations_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading donations: {e}")
            return []
    
    async def _save_donations(self, donations: List[Dict]):
        """Сохранение донатов"""
        try:
            async with aiofiles.open(self.donations_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(donations, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Error saving donations: {e}")
    
    async def _load_balances(self) -> Dict[str, int]:
        """Загрузка балансов звёзд"""
        if not self.user_balances_file.exists():
            return {}
        
        try:
            async with aiofiles.open(self.user_balances_file, 'r', encoding='utf-8') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading balances: {e}")
            return {}
    
    async def _save_balances(self, balances: Dict[str, int]):
        """Сохранение балансов"""
        try:
            async with aiofiles.open(self.user_balances_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(balances, ensure_ascii=False, indent=2))
        except Exception as e:
            logger.error(f"Error saving balances: {e}")
    
    async def record_donation(
        self,
        user_id: int,
        username: str,
        first_name: str,
        stars_amount: int,
        transaction_id: str
    ) -> bool:
        """
        Записывает донат
        
        Args:
            user_id: ID пользователя
            username: username
            first_name: имя
            stars_amount: количество звёзд
            transaction_id: ID транзакции от Telegram
        
        Returns:
            True если успешно
        """
        try:
            donations = await self._load_donations()
            
            donation = {
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "stars": stars_amount,
                "transaction_id": transaction_id,
                "timestamp": datetime.now().isoformat(),
                "refunded": False
            }
            
            donations.append(donation)
            await self._save_donations(donations)
            
            # Добавляем звёзды на баланс
            await self.add_stars(user_id, stars_amount)
            
            logger.info(f"Donation recorded: {user_id} - {stars_amount} stars")
            return True
            
        except Exception as e:
            logger.error(f"Error recording donation: {e}")
            return False
    
    async def refund_donation(self, transaction_id: str) -> bool:
        """
        Возврат доната
        
        Args:
            transaction_id: ID транзакции
        
        Returns:
            True если успешно
        """
        try:
            donations = await self._load_donations()
            
            for donation in donations:
                if donation["transaction_id"] == transaction_id:
                    if donation["refunded"]:
                        logger.warning(f"Donation already refunded: {transaction_id}")
                        return False
                    
                    # Помечаем как возвращённый
                    donation["refunded"] = True
                    donation["refund_date"] = datetime.now().isoformat()
                    
                    # Убираем звёзды с баланса
                    await self.remove_stars(donation["user_id"], donation["stars"])
                    
                    await self._save_donations(donations)
                    
                    logger.info(f"Donation refunded: {transaction_id}")
                    return True
            
            logger.warning(f"Donation not found: {transaction_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error refunding donation: {e}")
            return False
    
    async def get_user_donations(self, user_id: int) -> List[Dict]:
        """Получить все донаты пользователя"""
        donations = await self._load_donations()
        return [d for d in donations if d["user_id"] == user_id]
    
    async def get_total_donated(self, user_id: int) -> int:
        """Общая сумма донатов пользователя (без возвратов)"""
        donations = await self.get_user_donations(user_id)
        return sum(d["stars"] for d in donations if not d.get("refunded", False))
    
    async def get_all_donations(self) -> List[Dict]:
        """Все донаты"""
        return await self._load_donations()
    
    async def get_top_donors(self, limit: int = 10) -> List[Dict]:
        """Топ донатеров"""
        donations = await self._load_donations()
        
        # Группируем по пользователям
        user_totals = {}
        for d in donations:
            if d.get("refunded"):
                continue
            
            user_id = d["user_id"]
            if user_id not in user_totals:
                user_totals[user_id] = {
                    "user_id": user_id,
                    "username": d["username"],
                    "first_name": d["first_name"],
                    "total_stars": 0
                }
            
            user_totals[user_id]["total_stars"] += d["stars"]
        
        # Сортируем
        top_donors = sorted(
            user_totals.values(),
            key=lambda x: x["total_stars"],
            reverse=True
        )
        
        return top_donors[:limit]
    
    async def get_balance(self, user_id: int) -> int:
        """Получить баланс звёзд пользователя"""
        balances = await self._load_balances()
        return balances.get(str(user_id), 0)
    
    async def add_stars(self, user_id: int, amount: int):
        """Добавить звёзды на баланс"""
        balances = await self._load_balances()
        current = balances.get(str(user_id), 0)
        balances[str(user_id)] = current + amount
        await self._save_balances(balances)
        
        logger.info(f"Added {amount} stars to user {user_id}. New balance: {balances[str(user_id)]}")
    
    async def remove_stars(self, user_id: int, amount: int) -> bool:
        """Убрать звёзды с баланса"""
        balances = await self._load_balances()
        current = balances.get(str(user_id), 0)
        
        if current < amount:
            logger.warning(f"Not enough stars for user {user_id}: {current} < {amount}")
            return False
        
        balances[str(user_id)] = current - amount
        await self._save_balances(balances)
        
        logger.info(f"Removed {amount} stars from user {user_id}. New balance: {balances[str(user_id)]}")
        return True
    
    async def get_statistics(self) -> Dict:
        """Статистика донатов"""
        donations = await self._load_donations()
        
        active_donations = [d for d in donations if not d.get("refunded", False)]
        refunded_donations = [d for d in donations if d.get("refunded", False)]
        
        total_stars = sum(d["stars"] for d in active_donations)
        total_refunded = sum(d["stars"] for d in refunded_donations)
        
        return {
            "total_donations": len(donations),
            "active_donations": len(active_donations),
            "refunded_donations": len(refunded_donations),
            "total_stars_donated": total_stars,
            "total_stars_refunded": total_refunded,
            "unique_donors": len(set(d["user_id"] for d in active_donations))
        }


# Глобальный экземпляр
donation_system = DonationSystem()