#!/usr/bin/env python3
"""
POLYREC REAL-TIME LOG MONITOR
Мониторинг логов в реальном времени с алертами
Можно запускать параллельно с dash.py
"""

import pandas as pd
import time
import os
import glob
from datetime import datetime
from alert_system import AlertSystem
import argparse


class LogMonitor:
    """Монитор логов polyrec в реальном времени"""
    
    def __init__(self, logs_dir='./logs', arb_threshold=0.02):
        self.logs_dir = logs_dir
        self.arb_threshold = arb_threshold
        self.alert_system = AlertSystem(
            arb_threshold=arb_threshold,
            enable_sound=True,
            enable_telegram=False,
            enable_console=True,
            log_file='./monitor_alerts.log'
        )
        
        self.current_log = None
        self.last_size = 0
        self.monitoring = False
        
    def find_latest_log(self):
        """Находит последний созданный лог"""
        log_files = glob.glob(os.path.join(self.logs_dir, '*.csv'))
        
        if not log_files:
            return None
        
        # Сортируем по времени модификации
        log_files.sort(key=os.path.getmtime, reverse=True)
        return log_files[0]
    
    def check_for_new_log(self):
        """Проверяет появление нового лога"""
        latest_log = self.find_latest_log()
        
        if latest_log != self.current_log:
            if self.current_log:
                print(f"\n📝 Новый маркет! Переключаюсь на: {os.path.basename(latest_log)}")
            
            self.current_log = latest_log
            self.last_size = 0
            return True
        
        return False
    
    def analyze_new_rows(self, df):
        """Анализирует новые строки лога"""
        for idx, row in df.iterrows():
            # Вычисляем арбитраж
            if pd.notna(row.get('up_bid_1_price')) and pd.notna(row.get('down_bid_1_price')):
                arb_l1 = 1.0 - (row['up_bid_1_price'] + row['down_bid_1_price'])
                
                # Проверяем порог
                if arb_l1 >= self.arb_threshold:
                    market_data = {
                        'up_bid': row.get('up_bid_1_price', 0),
                        'down_bid': row.get('down_bid_1_price', 0),
                        'seconds_till_end': row.get('seconds_till_end', 0),
                        'volume_spike': row.get('binance_volume_spike', 0),
                        'atr_5s': row.get('binance_atr_5s', 0),
                        'up_imbalance': row.get('pm_up_imbalance', 0),
                        'down_imbalance': row.get('pm_down_imbalance', 0),
                    }
                    
                    self.alert_system.trigger_alert(
                        arb_value=arb_l1,
                        market_data=market_data
                    )
    
    def monitor_loop(self, check_interval=1.0):
        """Основной цикл мониторинга"""
        self.monitoring = True
        
        print("="*80)
        print("🔍 POLYREC REAL-TIME LOG MONITOR")
        print("="*80)
        print(f"📂 Logs directory: {self.logs_dir}")
        print(f"💰 Alert threshold: {self.arb_threshold*100:.1f}%")
        print(f"⏱️  Check interval: {check_interval}s")
        print("="*80)
        print("\n🎯 Waiting for logs...")
        
        try:
            while self.monitoring:
                # Проверяем новый лог
                self.check_for_new_log()
                
                if not self.current_log:
                    time.sleep(check_interval)
                    continue
                
                # Проверяем размер файла
                try:
                    current_size = os.path.getsize(self.current_log)
                    
                    if current_size > self.last_size:
                        # Читаем только новые строки
                        df = pd.read_csv(self.current_log)
                        
                        if len(df) > 0:
                            # Берем только новые строки
                            rows_to_skip = max(0, self.last_size // 200)  # Примерная оценка
                            new_rows = df.iloc[rows_to_skip:]
                            
                            if len(new_rows) > 0:
                                self.analyze_new_rows(new_rows)
                        
                        self.last_size = current_size
                        
                        # Показываем прогресс
                        if len(df) > 0:
                            last_row = df.iloc[-1]
                            ttl = last_row.get('seconds_till_end', 0)
                            arb = 1.0 - (last_row.get('up_bid_1_price', 0) + 
                                       last_row.get('down_bid_1_price', 0))
                            
                            print(f"📊 [{os.path.basename(self.current_log)}] "
                                  f"TTL: {ttl:3.0f}s | ARB: {arb*100:5.2f}% | "
                                  f"Alerts: {self.alert_system.alert_count}",
                                  end='\r')
                
                except Exception as e:
                    print(f"\n⚠️  Error reading log: {e}")
                
                time.sleep(check_interval)
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Monitoring stopped by user")
            self.monitoring = False
        
        # Финальная статистика
        self.print_stats()
    
    def print_stats(self):
        """Выводит статистику"""
        stats = self.alert_system.get_stats()
        
        print("\n" + "="*80)
        print("📊 MONITORING STATISTICS")
        print("="*80)
        print(f"Total alerts: {stats['total_alerts']}")
        if stats['total_alerts'] > 0:
            print(f"Average arbitrage: {stats['avg_arb']:.2f}%")
            print(f"Maximum arbitrage: {stats['max_arb']:.2f}%")
            print(f"Minimum arbitrage: {stats['min_arb']:.2f}%")
            print(f"Last alert: {stats['last_alert_time']}")
        print("="*80)
    
    def stop(self):
        """Остановка мониторинга"""
        self.monitoring = False


def main():
    parser = argparse.ArgumentParser(
        description='POLYREC Real-Time Log Monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default monitoring (2% threshold)
  python monitor.py
  
  # Custom threshold (1.5%)
  python monitor.py --threshold 0.015
  
  # Custom logs directory
  python monitor.py --logs-dir /path/to/logs
  
  # Enable Telegram alerts
  export TELEGRAM_BOT_TOKEN="your_token"
  export TELEGRAM_CHAT_ID="your_chat_id"
  python monitor.py --telegram
        """
    )
    
    parser.add_argument(
        '--logs-dir',
        default='./logs',
        help='Directory with polyrec logs (default: ./logs)'
    )
    
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.02,
        help='Arbitrage alert threshold (default: 0.02 = 2%%)'
    )
    
    parser.add_argument(
        '--interval',
        type=float,
        default=1.0,
        help='Check interval in seconds (default: 1.0)'
    )
    
    parser.add_argument(
        '--telegram',
        action='store_true',
        help='Enable Telegram alerts (requires env vars)'
    )
    
    parser.add_argument(
        '--no-sound',
        action='store_true',
        help='Disable sound alerts'
    )
    
    args = parser.parse_args()
    
    # Создаем монитор
    monitor = LogMonitor(
        logs_dir=args.logs_dir,
        arb_threshold=args.threshold
    )
    
    # Настраиваем алерты
    if args.telegram:
        monitor.alert_system.enable_telegram = True
        monitor.alert_system._init_telegram()
    
    if args.no_sound:
        monitor.alert_system.enable_sound = False
    
    # Запускаем мониторинг
    monitor.monitor_loop(check_interval=args.interval)


if __name__ == '__main__':
    main()
