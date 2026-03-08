#!/usr/bin/env python3
"""
POLYREC ALERT SYSTEM
Система уведомлений для арбитражных возможностей
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
import threading
from dotenv import load_dotenv

load_dotenv()

class AlertSystem:
    """Система алертов с поддержкой звука, Telegram, консоли и логирования"""
    
    def __init__(self, 
                 arb_threshold: float = 0.02,
                 telegram_token: Optional[str] = None,
                 telegram_chat_id: Optional[str] = None,
                 enable_sound: bool = True,
                 enable_telegram: bool = False,
                 enable_console: bool = True,
                 log_file: str = './alerts.log'):
        
        self.arb_threshold = arb_threshold
        self.enable_sound = enable_sound
        self.enable_telegram = enable_telegram
        self.enable_console = enable_console
        self.log_file = log_file
        
        # Telegram настройки
        self.telegram_token = telegram_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = telegram_chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        # Счетчики
        self.alert_count = 0
        self.last_alert_time = 0
        self.cooldown_seconds = 2  # Минимальный интервал между алертами
        
        # История алертов
        self.alert_history = []
        
        # Инициализация
        self._init_telegram()
        self._init_sound()
        
    def _init_telegram(self):
        """Инициализация Telegram бота"""
        if self.enable_telegram and self.telegram_token and self.telegram_chat_id:
            try:
                import requests
                self.telegram_available = True
                print("✅ Telegram alerts: ENABLED")
            except ImportError:
                print("⚠️  Telegram alerts: DISABLED (install 'requests' library)")
                self.telegram_available = False
        else:
            self.telegram_available = False
            if self.enable_telegram:
                print("⚠️  Telegram alerts: DISABLED (missing token or chat_id)")
    
    def _init_sound(self):
        """Инициализация звуковых алертов"""
        if self.enable_sound:
            # Пробуем разные методы звука
            self.sound_method = None
            
            # Метод 1: системный beep
            if os.system('which beep > /dev/null 2>&1') == 0:
                self.sound_method = 'beep'
                print("✅ Sound alerts: ENABLED (beep)")
            # Метод 2: терминальный bell
            elif sys.platform != 'win32':
                self.sound_method = 'bell'
                print("✅ Sound alerts: ENABLED (terminal bell)")
            else:
                print("⚠️  Sound alerts: DISABLED (no beep available)")
                self.enable_sound = False
        else:
            print("ℹ️  Sound alerts: DISABLED")
    
    def play_sound(self):
        """Воспроизведение звукового алерта"""
        if not self.enable_sound:
            return
        
        try:
            if self.sound_method == 'beep':
                # Короткие beeps
                os.system('beep -f 1000 -l 100')
                time.sleep(0.1)
                os.system('beep -f 1500 -l 100')
                time.sleep(0.1)
                os.system('beep -f 2000 -l 100')
            elif self.sound_method == 'bell':
                # Терминальный bell
                print('\a' * 3, end='', flush=True)
        except Exception as e:
            pass  # Тихо игнорируем ошибки звука
    
    def send_telegram(self, message: str):
        """Отправка сообщения в Telegram"""
        if not self.telegram_available:
            return
        
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            data = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            # Отправляем асинхронно, чтобы не блокировать
            threading.Thread(target=lambda: requests.post(url, data=data)).start()
            
        except Exception as e:
            print(f"⚠️  Telegram error: {e}")
    
    def log_to_file(self, alert_data: Dict[str, Any]):
        """Логирование алерта в файл"""
        try:
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                **alert_data
            }
            
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"⚠️  Log error: {e}")
    
    def console_alert(self, message: str, color: str = 'red'):
        """Вывод алерта в консоль с цветом"""
        if not self.enable_console:
            return
        
        # ANSI цвета
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'reset': '\033[0m'
        }
        
        color_code = colors.get(color, colors['red'])
        reset_code = colors['reset']
        
        # Рамка
        border = "=" * 80
        
        print(f"\n{color_code}{border}")
        print(f"🚨 ARBITRAGE ALERT!")
        print(message)
        print(f"{border}{reset_code}\n")
    
    def trigger_alert(self, 
                     arb_value: float,
                     market_data: Dict[str, Any],
                     force: bool = False):
        """
        Триггер алерта
        
        Args:
            arb_value: Размер арбитража (0.0-1.0)
            market_data: Данные о маркете
            force: Игнорировать cooldown
        """
        
        # Проверка cooldown
        current_time = time.time()
        if not force and (current_time - self.last_alert_time) < self.cooldown_seconds:
            return
        
        # Проверка порога
        if arb_value < self.arb_threshold:
            return
        
        self.last_alert_time = current_time
        self.alert_count += 1
        
        # Формируем данные алерта
        alert_data = {
            'alert_id': self.alert_count,
            'arb_percent': round(arb_value * 100, 3),
            'arb_usd': round(arb_value, 4),
            **market_data
        }
        
        # Формируем сообщения
        console_msg = self._format_console_message(alert_data)
        telegram_msg = self._format_telegram_message(alert_data)
        
        # Отправляем алерты
        self.console_alert(console_msg, color='green')
        self.play_sound()
        self.send_telegram(telegram_msg)
        self.log_to_file(alert_data)
        
        # Сохраняем в историю
        self.alert_history.append(alert_data)
        
        # Ограничиваем размер истории
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]
    
    def _format_console_message(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения для консоли"""
        msg = f"""
Alert #{data['alert_id']} | {datetime.now().strftime('%H:%M:%S')}

💰 ARBITRAGE: {data['arb_percent']:.2f}% (${data['arb_usd']:.4f})

📊 Market Data:
   UP Bid:    ${data.get('up_bid', 0):.3f}
   DOWN Bid:  ${data.get('down_bid', 0):.3f}
   Sum:       ${data.get('up_bid', 0) + data.get('down_bid', 0):.3f}
   
   Time Left: {data.get('seconds_till_end', 0):.0f}s
   Vol Spike: {data.get('volume_spike', 0):.1f}x
   ATR 5s:    {data.get('atr_5s', 0):.2f}
   Imbalance: UP={data.get('up_imbalance', 0):.2f} | DOWN={data.get('down_imbalance', 0):.2f}

🎯 ACTION: Execute arbitrage NOW!
        """
        return msg.strip()
    
    def _format_telegram_message(self, data: Dict[str, Any]) -> str:
        """Форматирование сообщения для Telegram"""
        msg = f"""
🚨 <b>ARBITRAGE ALERT #{data['alert_id']}</b>

💰 Profit: <b>{data['arb_percent']:.2f}%</b> (${data['arb_usd']:.4f})

📊 Prices:
• UP Bid: ${data.get('up_bid', 0):.3f}
• DOWN Bid: ${data.get('down_bid', 0):.3f}

⏱ Time: {data.get('seconds_till_end', 0):.0f}s left
📈 Vol Spike: {data.get('volume_spike', 0):.1f}x
🌊 ATR: {data.get('atr_5s', 0):.2f}

🎯 Execute NOW!
        """
        return msg.strip()
    
    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики алертов"""
        if not self.alert_history:
            return {
                'total_alerts': 0,
                'avg_arb': 0,
                'max_arb': 0,
                'min_arb': 0
            }
        
        arb_values = [a['arb_percent'] for a in self.alert_history]
        
        return {
            'total_alerts': len(self.alert_history),
            'avg_arb': sum(arb_values) / len(arb_values),
            'max_arb': max(arb_values),
            'min_arb': min(arb_values),
            'last_alert_time': self.alert_history[-1].get('timestamp', 'N/A') if self.alert_history else 'N/A'
        }


# Пример использования
if __name__ == '__main__':
    # Создаем систему алертов
    alert_system = AlertSystem(
        arb_threshold=0.02,  # 2%
        enable_sound=True,
        enable_telegram=False,  # Включить, если есть токен
        enable_console=True,
    )
    
    print("\n🎯 Alert System initialized!")
    print(f"   Threshold: {alert_system.arb_threshold*100}%")
    print(f"   Sound: {alert_system.enable_sound}")
    print(f"   Telegram: {alert_system.telegram_available}")
    print(f"   Console: {alert_system.enable_console}")
    print(f"   Log file: {alert_system.log_file}")
    
    # Тестовый алерт
    print("\n🧪 Testing alert system...")
    
    test_data = {
        'up_bid': 0.02,
        'down_bid': 0.96,
        'seconds_till_end': 120,
        'volume_spike': 5.2,
        'atr_5s': 1.5,
        'up_imbalance': 0.3,
        'down_imbalance': -0.3,
    }
    
    alert_system.trigger_alert(
        arb_value=0.022,  # 2.2%
        market_data=test_data,
        force=True
    )
    
    # Статистика
    stats = alert_system.get_stats()
    print(f"\n📊 Stats: {stats}")
