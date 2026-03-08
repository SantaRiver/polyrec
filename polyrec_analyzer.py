#!/usr/bin/env python3
"""
POLYREC LOG ANALYZER
Автоматический анализатор всех логов для поиска арбитражных возможностей
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
import json
import warnings
warnings.filterwarnings('ignore')

class PolyrecAnalyzer:
    def __init__(self, logs_dir='./logs'):
        self.logs_dir = logs_dir
        self.results = []
        
    def calculate_arbitrage_levels(self, df):
        """Вычисляет арбитраж на всех уровнях ликвидности"""
        arb_levels = {}
        
        for level in range(1, 6):
            up_col = f'up_bid_{level}_price'
            down_col = f'down_bid_{level}_price'
            
            if up_col in df.columns and down_col in df.columns:
                arb = 1.0 - (df[up_col] + df[down_col])
                arb = arb.fillna(0)
                arb_levels[f'L{level}'] = {
                    'mean': arb.mean(),
                    'max': arb.max(),
                    'median': arb.median(),
                    'std': arb.std(),
                    'count_profitable': (arb > 0.015).sum(),  # >1.5 центов
                    'count_very_profitable': (arb > 0.025).sum(),  # >2.5 центов
                }
        
        return arb_levels
    
    def analyze_single_log(self, filepath):
        """Анализирует один CSV лог"""
        try:
            df = pd.read_csv(filepath)
            
            # Базовая информация
            market_slug = df['market_slug'].iloc[0] if 'market_slug' in df.columns else 'unknown'
            duration = df['seconds_till_end'].iloc[0] if 'seconds_till_end' in df.columns else 0
            
            # Вычисляем арбитраж на всех уровнях
            arb_levels = self.calculate_arbitrage_levels(df)
            
            # Лучший момент для арбитража
            if 'up_bid_1_price' in df.columns and 'down_bid_1_price' in df.columns:
                df['arb_l1'] = 1.0 - (df['up_bid_1_price'] + df['down_bid_1_price'])
                df['arb_l1'] = df['arb_l1'].fillna(0)
                
                best_moment_idx = df['arb_l1'].idxmax()
                best_moment = df.loc[best_moment_idx]
                
                best_arb = {
                    'arb': best_moment['arb_l1'],
                    'timestamp': best_moment.get('timestamp_et', 'N/A'),
                    'seconds_till_end': best_moment.get('seconds_till_end', 0),
                    'volume_spike': best_moment.get('binance_volume_spike', 0),
                    'atr_5s': best_moment.get('binance_atr_5s', 0),
                    'up_imbalance': best_moment.get('pm_up_imbalance', 0),
                    'down_imbalance': best_moment.get('pm_down_imbalance', 0),
                }
            else:
                best_arb = None
            
            # Волатильность
            volatility = {
                'atr_5s_mean': df['binance_atr_5s'].mean() if 'binance_atr_5s' in df.columns else 0,
                'atr_5s_max': df['binance_atr_5s'].max() if 'binance_atr_5s' in df.columns else 0,
            }
            
            # Volume spikes
            volume = {
                'spike_count': (df['binance_volume_spike'] > 2.0).sum() if 'binance_volume_spike' in df.columns else 0,
                'max_spike': df['binance_volume_spike'].max() if 'binance_volume_spike' in df.columns else 0,
            }
            
            # Результат маркета
            if 'pm_up_microprice' in df.columns and 'pm_down_microprice' in df.columns:
                final_up = df['pm_up_microprice'].iloc[-1]
                final_down = df['pm_down_microprice'].iloc[-1]
                
                if final_up > 0.9:
                    winner = 'UP'
                elif final_down > 0.9:
                    winner = 'DOWN'
                else:
                    winner = 'UNKNOWN'
            else:
                winner = 'UNKNOWN'
            
            result = {
                'filepath': filepath,
                'filename': os.path.basename(filepath),
                'market_slug': market_slug,
                'duration_seconds': duration,
                'record_count': len(df),
                'arb_levels': arb_levels,
                'best_moment': best_arb,
                'volatility': volatility,
                'volume': volume,
                'winner': winner,
                'timestamp': df['timestamp_et'].iloc[0] if 'timestamp_et' in df.columns else 'N/A',
            }
            
            return result
            
        except Exception as e:
            print(f"❌ Ошибка при анализе {filepath}: {e}")
            return None
    
    def analyze_all_logs(self):
        """Анализирует все логи в директории"""
        log_files = glob.glob(os.path.join(self.logs_dir, '*.csv'))
        
        if not log_files:
            print(f"⚠️  Логи не найдены в {self.logs_dir}")
            return []
        
        print(f"📂 Найдено {len(log_files)} логов")
        print("🔍 Анализирую...")
        
        for i, filepath in enumerate(log_files, 1):
            print(f"   [{i}/{len(log_files)}] {os.path.basename(filepath)}", end='\r')
            result = self.analyze_single_log(filepath)
            if result:
                self.results.append(result)
        
        print(f"\n✅ Проанализировано: {len(self.results)} маркетов")
        return self.results
    
    def find_best_opportunities(self, min_arb=0.015, top_n=10):
        """Находит лучшие арбитражные возможности"""
        opportunities = []
        
        for result in self.results:
            if result['best_moment'] and result['best_moment']['arb'] >= min_arb:
                opportunities.append({
                    'filename': result['filename'],
                    'arb': result['best_moment']['arb'],
                    'timestamp': result['best_moment']['timestamp'],
                    'ttl': result['best_moment']['seconds_till_end'],
                    'vol_spike': result['best_moment']['volume_spike'],
                    'atr': result['best_moment']['atr_5s'],
                    'winner': result['winner'],
                })
        
        # Сортируем по размеру арбитража
        opportunities.sort(key=lambda x: x['arb'], reverse=True)
        
        return opportunities[:top_n]
    
    def generate_summary_report(self):
        """Генерирует итоговый отчет"""
        if not self.results:
            print("❌ Нет данных для анализа")
            return
        
        print("\n" + "="*100)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ПО ВСЕМ МАРКЕТАМ")
        print("="*100)
        
        # Общая статистика
        total_markets = len(self.results)
        total_records = sum(r['record_count'] for r in self.results)
        
        print(f"\n📈 Общая статистика:")
        print(f"   Всего маркетов: {total_markets}")
        print(f"   Всего записей: {total_records:,}")
        print(f"   Средняя длительность лога: {np.mean([r['duration_seconds'] for r in self.results]):.0f} секунд")
        
        # Статистика по арбитражу L1
        arb_l1_means = [r['arb_levels'].get('L1', {}).get('mean', 0) for r in self.results if r['arb_levels'].get('L1')]
        arb_l1_maxes = [r['arb_levels'].get('L1', {}).get('max', 0) for r in self.results if r['arb_levels'].get('L1')]
        
        print(f"\n💰 Арбитраж L1 (лучший бид):")
        print(f"   Средний по всем маркетам: ${np.mean(arb_l1_means)*100:.3f}%")
        print(f"   Максимальный средний: ${np.max(arb_l1_means)*100:.3f}%")
        print(f"   Глобальный максимум: ${np.max(arb_l1_maxes)*100:.3f}%")
        
        # Маркеты с прибыльным арбитражем
        profitable_count = sum(1 for r in self.results 
                               if r['arb_levels'].get('L1', {}).get('count_profitable', 0) > 0)
        
        print(f"\n🎯 Прибыльные маркеты (арб > $0.015):")
        print(f"   Количество: {profitable_count} ({profitable_count/total_markets*100:.1f}%)")
        
        # Волатильность
        avg_volatility = np.mean([r['volatility']['atr_5s_mean'] for r in self.results])
        max_volatility = np.max([r['volatility']['atr_5s_max'] for r in self.results])
        
        print(f"\n🌊 Волатильность:")
        print(f"   Средняя ATR 5s: {avg_volatility:.2f}")
        print(f"   Максимальная ATR 5s: {max_volatility:.2f}")
        
        # Volume spikes
        total_spikes = sum(r['volume']['spike_count'] for r in self.results)
        max_spike = max(r['volume']['max_spike'] for r in self.results)
        
        print(f"\n📈 Volume Spikes:")
        print(f"   Всего спайков (>2x): {total_spikes}")
        print(f"   Максимальный спайк: {max_spike:.1f}x")
        
        # ТОП-10 лучших возможностей
        print(f"\n" + "="*100)
        print("🏆 ТОП-10 ЛУЧШИХ АРБИТРАЖНЫХ ВОЗМОЖНОСТЕЙ")
        print("="*100)
        
        top_opportunities = self.find_best_opportunities(min_arb=0.0, top_n=10)
        
        if not top_opportunities:
            print("❌ Арбитражных возможностей не найдено")
        else:
            print(f"\n{'#':<4} {'Файл':<45} {'ARB%':>7} {'TTL':>6} {'VolSpk':>8} {'ATR':>7} {'Result':<8}")
            print("-"*100)
            for i, opp in enumerate(top_opportunities, 1):
                print(f"{i:<4} {opp['filename']:<45} {opp['arb']*100:6.2f}% "
                      f"{opp['ttl']:5.0f}s {opp['vol_spike']:7.1f}x "
                      f"{opp['atr']:6.2f} {opp['winner']:<8}")
        
        # Рейтинг маркетов по среднему арбитражу
        print(f"\n" + "="*100)
        print("📊 ТОП-10 МАРКЕТОВ ПО СРЕДНЕМУ АРБИТРАЖУ")
        print("="*100)
        
        markets_by_avg_arb = sorted(
            [r for r in self.results if r['arb_levels'].get('L1')],
            key=lambda x: x['arb_levels']['L1']['mean'],
            reverse=True
        )[:10]
        
        print(f"\n{'#':<4} {'Файл':<45} {'Средний ARB':>12} {'Макс ARB':>10} {'Записей':>9}")
        print("-"*100)
        for i, market in enumerate(markets_by_avg_arb, 1):
            avg_arb = market['arb_levels']['L1']['mean']
            max_arb = market['arb_levels']['L1']['max']
            records = market['record_count']
            print(f"{i:<4} {market['filename']:<45} {avg_arb*100:11.3f}% {max_arb*100:9.3f}% {records:9}")
        
        print("\n" + "="*100)
    
    def save_detailed_report(self, output_file='polyrec_analysis_report.json'):
        """Сохраняет детальный отчет в JSON"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_markets': len(self.results),
            'results': self.results,
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"💾 Детальный отчет сохранен: {output_file}")
        return output_file


def main():
    # Настройки
    LOGS_DIR = './logs'  # Путь к логам
    MIN_ARB_THRESHOLD = 0.015  # Минимальный прибыльный арбитраж
    
    print("="*100)
    print("🚀 POLYREC AUTOMATIC LOG ANALYZER")
    print("="*100)
    print(f"📂 Директория с логами: {LOGS_DIR}")
    print(f"💰 Порог прибыльности: ${MIN_ARB_THRESHOLD*100:.1f}%")
    print("="*100)
    
    # Создаем анализатор
    analyzer = PolyrecAnalyzer(logs_dir=LOGS_DIR)
    
    # Анализируем все логи
    results = analyzer.analyze_all_logs()
    
    if results:
        # Генерируем отчет
        analyzer.generate_summary_report()
        
        # Сохраняем детальный отчет
        analyzer.save_detailed_report()
        
        print("\n✅ Анализ завершен!")
    else:
        print("\n❌ Логи не найдены или содержат ошибки")


if __name__ == '__main__':
    main()
