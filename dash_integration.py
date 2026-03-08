"""
POLYREC DASH.PY INTEGRATION PATCH
Инструкции по интеграции системы алертов в dash.py
"""

# ============================================================================
# ШАГ 1: ДОБАВИТЬ ИМПОРТ В НАЧАЛО dash.py
# ============================================================================

"""
В начало файла dash.py (после других импортов) добавить:

from alert_system import AlertSystem
"""

# ============================================================================
# ШАГ 2: ИНИЦИАЛИЗИРОВАТЬ СИСТЕМУ АЛЕРТОВ
# ============================================================================

"""
После инициализации всех переменных в dash.py добавить:

# Инициализация системы алертов
alert_system = AlertSystem(
    arb_threshold=0.02,           # Порог алерта: 2%
    enable_sound=True,            # Звуковые алерты
    enable_telegram=False,        # Telegram (нужен токен)
    enable_console=True,          # Консольные алерты
    log_file='./alerts.log'       # Файл логов алертов
)

# Опционально: настроить Telegram
# alert_system.telegram_token = "YOUR_BOT_TOKEN"
# alert_system.telegram_chat_id = "YOUR_CHAT_ID"
# alert_system.telegram_available = True
"""

# ============================================================================
# ШАГ 3: ДОБАВИТЬ ПРОВЕРКУ АРБИТРАЖА
# ============================================================================

"""
В функцию обновления дашборда (обычно это функция, которая вызывается каждую секунду)
добавить проверку арбитража.

Найти место, где вычисляются данные стакана (orderbook), обычно это где-то рядом
с вычислением up_bid_1_price и down_bid_1_price.

Пример интеграции:

def update_dashboard():
    # ... существующий код ...
    
    # Получаем цены лучших бидов
    up_bid = up_orderbook['bids'][0]['price'] if up_orderbook['bids'] else 0
    down_bid = down_orderbook['bids'][0]['price'] if down_orderbook['bids'] else 0
    
    # Вычисляем арбитраж
    arb_l1 = 1.0 - (up_bid + down_bid)
    
    # Проверяем алерт
    if arb_l1 > alert_system.arb_threshold:
        market_data = {
            'up_bid': up_bid,
            'down_bid': down_bid,
            'seconds_till_end': seconds_till_end,
            'volume_spike': binance_volume_spike,
            'atr_5s': binance_atr_5s,
            'up_imbalance': pm_up_imbalance,
            'down_imbalance': pm_down_imbalance,
        }
        
        alert_system.trigger_alert(
            arb_value=arb_l1,
            market_data=market_data
        )
    
    # ... остальной код дашборда ...
"""

# ============================================================================
# ШАГ 4: ДОБАВИТЬ СЕКЦИЮ АЛЕРТОВ В ДАШБОРД (опционально)
# ============================================================================

"""
В отображение терминала добавить секцию статистики алертов:

def render_dashboard():
    # ... существующий код отрисовки ...
    
    # Добавить секцию алертов
    alert_stats = alert_system.get_stats()
    
    print(f"ALERTS    │ Total: {alert_stats['total_alerts']} │ "
          f"Avg: {alert_stats['avg_arb']:.2f}% │ "
          f"Max: {alert_stats['max_arb']:.2f}% │ "
          f"Last: {alert_stats['last_alert_time']}")
    
    # ... остальной код отрисовки ...
"""

# ============================================================================
# ПОЛНЫЙ ПРИМЕР ИНТЕГРАЦИИ
# ============================================================================

EXAMPLE_INTEGRATION = """
# В начале dash.py
from alert_system import AlertSystem

# После инициализации переменных
alert_system = AlertSystem(
    arb_threshold=0.02,
    enable_sound=True,
    enable_telegram=False,
    enable_console=True,
    log_file='./alerts.log'
)

# В функции обновления данных (там где обрабатывается orderbook)
def process_orderbook_data(up_orderbook, down_orderbook, market_context):
    # Существующий код обработки
    up_bid = up_orderbook['bids'][0]['price'] if up_orderbook['bids'] else 0
    down_bid = down_orderbook['bids'][0]['price'] if down_orderbook['bids'] else 0
    
    # НОВЫЙ КОД: Проверка арбитража и алерт
    arb_l1 = 1.0 - (up_bid + down_bid)
    
    if arb_l1 > alert_system.arb_threshold:
        alert_system.trigger_alert(
            arb_value=arb_l1,
            market_data={
                'up_bid': up_bid,
                'down_bid': down_bid,
                'seconds_till_end': market_context.get('seconds_till_end', 0),
                'volume_spike': market_context.get('volume_spike', 0),
                'atr_5s': market_context.get('atr_5s', 0),
                'up_imbalance': market_context.get('up_imbalance', 0),
                'down_imbalance': market_context.get('down_imbalance', 0),
            }
        )
    
    return {
        'up_bid': up_bid,
        'down_bid': down_bid,
        'arb_l1': arb_l1,
        # ... остальные данные
    }
"""

# ============================================================================
# НАСТРОЙКА TELEGRAM (ОПЦИОНАЛЬНО)
# ============================================================================

TELEGRAM_SETUP = """
1. Создать бота через @BotFather в Telegram
2. Получить токен бота
3. Запустить бота и отправить ему сообщение
4. Получить chat_id через: https://api.telegram.org/bot<TOKEN>/getUpdates

5. Добавить в dash.py:

alert_system = AlertSystem(
    arb_threshold=0.02,
    telegram_token="YOUR_BOT_TOKEN_HERE",
    telegram_chat_id="YOUR_CHAT_ID_HERE",
    enable_telegram=True,
    enable_sound=True,
)

Или использовать переменные окружения:

export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

И просто:
alert_system = AlertSystem(arb_threshold=0.02, enable_telegram=True)
"""

print(__doc__)
print("\n" + "="*80)
print("📝 ИНСТРУКЦИИ ПО ИНТЕГРАЦИИ")
print("="*80)
print(EXAMPLE_INTEGRATION)
print("\n" + "="*80)
print("📱 НАСТРОЙКА TELEGRAM")
print("="*80)
print(TELEGRAM_SETUP)
print("\n✅ Скопируйте необходимые части кода в ваш dash.py")
