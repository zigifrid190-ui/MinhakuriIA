import random
import time
from datetime import datetime

# Registra a última vez que a Kuri falou proativamente para não ser irritante
last_proactive_time = time.time()
PROACTIVE_COOLDOWN = 1800 # 30 minutos de cooldown

PROACTIVE_TRIGGERS = [
    {
        "id": "morning_greeting",
        "hora_range": (8, 11),
        "chance": 0.3, # 30% chance se estiver no horário e cooldown tiver passado
        "prompt": "[SYSTEM_EVENT: morning_greeting] O usuário está em silêncio. Cumprimente-o de bom dia de forma natural e pergunte se precisa de algo."
    },
    {
        "id": "coffee_reminder",
        "hora_range": (14, 16),
        "chance": 0.2,
        "prompt": "[SYSTEM_EVENT: coffee_reminder] O usuário está em silêncio à tarde. Faça um comentário sobre tomar um café de forma sarcástica ou dramática."
    },
    {
        "id": "night_check",
        "hora_range": (23, 24),
        "chance": 0.2,
        "prompt": "[SYSTEM_EVENT: night_check] O usuário está acordado tarde. Faça um comentário sobre isso e pergunte se ele não vai dormir."
    },
    {
        "id": "night_check_2",
        "hora_range": (0, 3),
        "chance": 0.3,
        "prompt": "[SYSTEM_EVENT: night_check_2] O usuário está acordado de madrugada. Faça um comentário sobre isso de forma caótica."
    },
    {
        "id": "random_comment",
        "hora_range": (0, 24), # Qualquer hora
        "chance": 0.05, # 5% chance
        "prompt": "[SYSTEM_EVENT: random_comment] O usuário está em silêncio faz um tempo. Faça um comentário aleatório sobre o que você está 'fazendo' agora (jogando ranked, ouvindo rock, etc)."
    }
]

async def check_proactivity() -> str | None:
    """Verifica se a Kuri deve iniciar uma interação espontânea."""
    global last_proactive_time
    agora = time.time()
    
    if agora - last_proactive_time < PROACTIVE_COOLDOWN:
        return None
        
    hora_atual = datetime.now().hour
    
    # Testa os triggers válidos para o horário
    for trigger in PROACTIVE_TRIGGERS:
        start, end = trigger["hora_range"]
        # Lida com range que passa da meia-noite (ex: 23 a 2)
        in_range = False
        if start <= end:
            in_range = start <= hora_atual <= end
        else:
            in_range = hora_atual >= start or hora_atual <= end
            
        if in_range:
            if random.random() < trigger["chance"]:
                last_proactive_time = agora
                print(f"[ROUTINE] Trigger proativo acionado: {trigger['id']}")
                return trigger["prompt"]
                
    return None
