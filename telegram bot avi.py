from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
import logging
import random
import tracemalloc

tracemalloc.start()

BOT_TOKEN = '7248809373:AAFZiQP3m_f44ZRZLh8SOH9TnzyfGRbh8os'

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

dare_pool = []
defender_chats = []
color_dare_map = {}

CHOOSE_ROLE, COLLECT_DARE, DEFENDER_PICK = range(3)

async def start(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info(f"User {user.username} ({user.id}) started the conversation.")
    
    keyboard = [
        [InlineKeyboardButton("Attacker", callback_data='attacker')],
        [InlineKeyboardButton("Defender", callback_data='defender')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Choose your role:", reply_markup=reply_markup)
    return CHOOSE_ROLE

async def choose_role(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    await query.answer()
    role = query.data

    context.user_data['role'] = role
    logger.info(f"User {query.from_user.username} ({query.from_user.id}) chose role: {role}")

    if role == 'attacker':
        await query.edit_message_text(text="You're an Attacker! Please submit a dare.")
        return COLLECT_DARE
    else:
        defender_chats.append(query.from_user.id)
        logger.info(f"Defender {query.from_user.username} ({query.from_user.id}) added to the list.")
        await query.edit_message_text(text="You're a Defender! Waiting for attackers to submit their dares.")
        return DEFENDER_PICK  # Fixed the state transition here

async def collect_dare(update: Update, context: CallbackContext) -> int:
    if context.user_data.get('role') == 'attacker':
        dare = update.message.text
        dare_pool.append(dare)
        logger.info(f"Dare submitted: {dare}. Total dares in pool: {len(dare_pool)}")

        if len(dare_pool) >= 2:
            await notify_defenders(context)
            logger.info(f"Notified all defenders. Total defenders: {len(defender_chats)}")
            return ConversationHandler.END 
        else:
            await update.message.reply_text(f"Dare submitted. Waiting for more dares. ({len(dare_pool)}/2)")
            return COLLECT_DARE
    else:
        await update.message.reply_text("You're a Defender. Please wait for attackers to submit their dares.")
        return DEFENDER_PICK  # Changed to correct state

async def notify_defenders(context: CallbackContext) -> None:
    if len(dare_pool) < 2:
        logger.warning("Not enough dares to notify defenders.")
        return

    random.shuffle(dare_pool)

    colors = ['Red', 'Blue', 'Green', 'Yellow']
    available_colors = colors[:len(dare_pool)]
    global color_dare_map
    color_dare_map = dict(zip(available_colors, dare_pool))

    logger.info(f"Shuffled dares and colors: {color_dare_map}")

    keyboard = [
        [InlineKeyboardButton(color, callback_data=color) for color in available_colors]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in defender_chats:
        try:
            await context.bot.send_message(chat_id, "Defenders, choose a color to reveal your dare:", reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Failed to send message to defender {chat_id}: {e}")

async def reveal_dare(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()

    chosen_color = query.data
    dare = color_dare_map.get(chosen_color)

    if dare:
        await query.edit_message_text(text=f"You chose {chosen_color}! Your dare is: {dare}")
        logger.info(f"Defender chose {chosen_color}. Dare revealed: {dare}")
    else:
        await query.edit_message_text(text="No dare found for the chosen color. Please try again.")
        logger.error(f"Defender chose {chosen_color} but no dare was found.")

async def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info(f"User {user.username} ({user.id}) canceled the conversation.")
    
    await update.message.reply_text("Conversation canceled. Type /start to begin again.")
    return ConversationHandler.END

def main() -> None:
    dp = Application.builder().token(BOT_TOKEN).build()

    cards_of_dare_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSE_ROLE: [CallbackQueryHandler(choose_role)],
            COLLECT_DARE: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_dare)],
            DEFENDER_PICK: [CallbackQueryHandler(reveal_dare)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    dp.add_handler(cards_of_dare_handler)

    dp.run_polling()

if __name__ == '__main__':
    main()
