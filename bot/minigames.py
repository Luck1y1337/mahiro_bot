from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import random

from utils.services import donation_system, trust_system, mood_system

router = Router()

@router.message(Command("flip"))
async def cmd_flip(message: Message):
    """Мини-игра: Подбросить монетку"""
    # Ставка 1 звезда, выигрыш 2 звезды (если угадал), иначе проигрыш 1 звезды
    args = message.text.split()
    if len(args) < 2 or args[1] not in ["орел", "решка"]:
        await message.answer("🪙 Игра 'Монетка'\nИспользование: /flip орел или /flip решка\nСтавка: 1 ⭐")
        return
        
    choice = args[1].lower()
    user_id = message.from_user.id
    
    # Проверяем баланс
    balance = await donation_system.get_balance(user_id)
    if balance < 1:
        await message.answer("У тебя нет звёзд для ставки! 😔\nИспользуй /donate чтобы получить звёзды.")
        return
        
    # Списываем 1 звезду
    # Для этого нужен метод update_balance в donation_system, либо прямой доступ.
    # Так как мы не меняли donation_system, просто сымитируем через прямую запись (если есть) или добавим метод.
    # В donations.py пока нет метода для прямого списания. Но можно сделать.
    await message.answer("🪙 *Монетка подбрасывается...*", parse_mode="Markdown")
    
    result = random.choice(["орел", "решка"])
    
    # Для простоты, пока без реальных ставок на Stars (по правилам Telegram Stars нельзя использовать как валюту казино)
    # Поэтому мы сделаем игру чисто развлекательной (без изменения баланса звезд)
    
    if result == choice:
        await trust_system.increment_trust(user_id)
        await mood_system.set_mood(user_id, "счастливая")
        await message.answer(f"🎉 Выпал **{result}**! Ты угадал!\nМахиро радостно хлопает в ладоши! 😊", parse_mode="Markdown")
    else:
        await message.answer(f"😔 Выпал **{result}**... Ты не угадал.\nМахиро сочувствующе смотрит на тебя.", parse_mode="Markdown")


@router.message(Command("rps"))
async def cmd_rps(message: Message):
    """Мини-игра: Камень, ножницы, бумага"""
    args = message.text.split()
    valid_choices = ["камень", "ножницы", "бумага"]
    
    if len(args) < 2 or args[1].lower() not in valid_choices:
        await message.answer("✌️ Камень, ножницы, бумага\nИспользование: /rps <камень|ножницы|бумага>")
        return
        
    user_choice = args[1].lower()
    bot_choice = random.choice(valid_choices)
    user_id = message.from_user.id
    
    emojis = {"камень": "✊", "ножницы": "✌️", "бумага": "✋"}
    
    await message.answer(f"Ты выбрал: {emojis[user_choice]}\nМахиро выбрала: {emojis[bot_choice]}")
    
    if user_choice == bot_choice:
        await message.answer("Ничья! 😐")
    elif (user_choice == "камень" and bot_choice == "ножницы") or \
         (user_choice == "ножницы" and bot_choice == "бумага") or \
         (user_choice == "бумага" and bot_choice == "камень"):
        await trust_system.increment_trust(user_id)
        await mood_system.set_mood(user_id, "грустная")
        await message.answer("Ты победил! Махиро немного расстроена... 😔")
    else:
        await mood_system.set_mood(user_id, "счастливая")
        await message.answer("Махиро победила! Ура! 😊")
