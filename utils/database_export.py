import json
import csv
from pathlib import Path
from datetime import datetime
from typing import Optional
import zipfile
import logging

logger = logging.getLogger(__name__)


class DatabaseExporter:
    """Экспорт всех данных бота"""
    
    def __init__(self, data_dir: str = "data", export_dir: str = "exports"):
        self.data_dir = Path(data_dir)
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
    
    async def export_all(self) -> Optional[Path]:
        """
        Экспортирует ВСЕ данные в ZIP архив
        
        Returns:
            Путь к созданному архиву или None при ошибке
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            zip_path = self.export_dir / f"mahiro_backup_{timestamp}.zip"
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Добавляем все JSON файлы из data/
                for json_file in self.data_dir.glob("*.json"):
                    zipf.write(json_file, arcname=f"data/{json_file.name}")
                
                # Добавляем user_*.json файлы
                for user_file in self.data_dir.glob("user_*.json"):
                    zipf.write(user_file, arcname=f"data/{user_file.name}")
                
                # Добавляем .env (без чувствительных данных)
                env_path = Path(".env")
                if env_path.exists():
                    zipf.write(env_path, arcname=".env.backup")
            
            logger.info(f"Database exported to {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None
    
    async def export_users_csv(self) -> Optional[Path]:
        """
        Экспортирует пользователей в CSV
        
        Returns:
            Путь к CSV файлу
        """
        try:
            from utils.user_tracker import UserTracker
            
            tracker = UserTracker()
            users = await tracker.get_all_users()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = self.export_dir / f"users_{timestamp}.csv"
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'user_id', 'username', 'first_name', 'last_name',
                    'first_seen', 'last_seen', 'message_count',
                    'successful_messages', 'blocked_messages'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for user in users:
                    writer.writerow({
                        'user_id': user.get('user_id'),
                        'username': user.get('username', ''),
                        'first_name': user.get('first_name', ''),
                        'last_name': user.get('last_name', ''),
                        'first_seen': user.get('first_seen', ''),
                        'last_seen': user.get('last_seen', ''),
                        'message_count': user.get('message_count', 0),
                        'successful_messages': user.get('successful_messages', 0),
                        'blocked_messages': user.get('blocked_messages', 0)
                    })
            
            logger.info(f"Users exported to CSV: {csv_path}")
            return csv_path
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")
            return None
    
    async def export_statistics_json(self) -> Optional[Path]:
        """
        Экспортирует статистику в JSON
        
        Returns:
            Путь к JSON файлу
        """
        try:
            from utils.statistics import Statistics
            from utils.user_tracker import UserTracker
            
            stats = Statistics()
            tracker = UserTracker()
            
            bot_stats = await stats.get_stats()
            user_stats = await tracker.get_statistics()
            
            combined_stats = {
                "bot": bot_stats,
                "users": user_stats,
                "export_date": datetime.now().isoformat()
            }
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = self.export_dir / f"statistics_{timestamp}.json"
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(combined_stats, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Statistics exported to JSON: {json_path}")
            return json_path
            
        except Exception as e:
            logger.error(f"Statistics export failed: {e}")
            return None
    
    def cleanup_old_exports(self, days: int = 7):
        """Удаляет старые экспорты"""
        try:
            from datetime import timedelta
            
            cutoff = datetime.now() - timedelta(days=days)
            
            for export_file in self.export_dir.glob("*"):
                if export_file.stat().st_mtime < cutoff.timestamp():
                    export_file.unlink()
                    logger.info(f"Deleted old export: {export_file.name}")
        
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")