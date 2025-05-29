import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PHOTO, TITLES, BUTTONS, CHANNEL, CONFIRM = range(5)
FORWARDING = 5

BOT_TOKEN = "7703662144:AAFfcyNT3g5RczNZzn8BSStFuoIalXLIJQE"
OWNER_ID = 6761808245
ADMINS = set()

def is_authorized(user_id):
    return user_id == OWNER_ID or user_id in ADMINS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📸 Send photo/video to create post\n"
        "/cancel to stop"
    )
    return PHOTO

async def create_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create new post with buttons"""
    if update.message.photo:
        context.user_data['media'] = update.message.photo[-1].file_id
        context.user_data['type'] = 'photo'
    elif update.message.video:
        context.user_data['media'] = update.message.video.file_id
        context.user_data['type'] = 'video'
    else:
        await update.message.reply_text("❌ Send photo/video first")
        return PHOTO

    await update.message.reply_text(
        "📝 Send post details:\n"
        "Title - https://example.com\n"
        "Channel - https://channel.com"
    )
    return TITLES

async def process_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process post metadata"""
    try:
        title, channel = update.message.text.split('\n')
        title_text, title_url = title.split('-', 1)
        channel_text, channel_url = channel.split('-', 1)
        
        context.user_data.update({
            'title': title_text.strip(),
            'title_url': title_url.strip(),
            'channel': channel_text.strip(),
            'channel_url': channel_url.strip()
        })
        
        await update.message.reply_text(
            "🔘 Now send buttons:\n"
            "Season 1\n"
            "1 - https://ep1.com | 2 - https://ep2.com"
        )
        return BUTTONS
    except Exception:
        await update.message.reply_text("❌ Invalid format! Try again")
        return TITLES

async def process_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create buttons and show preview"""
    button_rows = []
    for line in update.message.text.split('\n'):
        line = line.strip()
        if line.lower().startswith('season'):
            button_rows.append([InlineKeyboardButton(line, callback_data='header')])
        else:
            row = []
            for part in line.split('|'):
                if '-' in part:
                    label, url = part.split('-', 1)
                    row.append(InlineKeyboardButton(label.strip(), url=url.strip()))
            if row:
                button_rows.append(row)
    
    context.user_data['buttons'] = button_rows
    
    # Show preview
    keyboard = [
        [InlineKeyboardButton(context.user_data['title'], url=context.user_data['title_url'])],
        [InlineKeyboardButton(context.user_data['channel'], url=context.user_data['channel_url'])]
    ] + button_rows
    
    markup = InlineKeyboardMarkup(keyboard)
    
    if context.user_data['type'] == 'photo':
        msg = await update.message.reply_photo(
            photo=context.user_data['media'],
            reply_markup=markup
        )
    else:
        msg = await update.message.reply_video(
            video=context.user_data['media'],
            reply_markup=markup
        )
    
    context.user_data['preview_msg_id'] = msg.message_id
    
    await update.message.reply_text("📢 Enter the channel username where to post (e.g., @channelname)")
    return CHANNEL

async def process_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process channel input and verify bot admin status"""
    channel = update.message.text.strip()
    if not channel.startswith('@'):
        channel = '@' + channel
    
    context.user_data['target_channel'] = channel
    
    try:
        # Check if bot is admin in the channel
        chat = await context.bot.get_chat(channel)
        admins = await context.bot.get_chat_administrators(channel)
        bot_id = (await context.bot.get_me()).id
        is_admin = any(admin.user.id == bot_id for admin in admins)
        
        if not is_admin:
            await update.message.reply_text(f"❌ Bot is not admin in {channel}. Please make bot admin first.")
            return CHANNEL
        
        confirm_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Post", callback_data="post"),
             InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ])
        await update.message.reply_text(f"Post to {channel}?", reply_markup=confirm_markup)
        return CONFIRM
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}\nPlease check the channel username and try again.")
        return CHANNEL

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle post confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'post':
        try:
            channel = context.user_data['target_channel']
            
            keyboard = [
                [InlineKeyboardButton(context.user_data['title'], url=context.user_data['title_url'])],
                [InlineKeyboardButton(context.user_data['channel'], url=context.user_data['channel_url'])]
            ] + context.user_data['buttons']
            
            markup = InlineKeyboardMarkup(keyboard)
            
            if context.user_data['type'] == 'photo':
                await context.bot.send_photo(
                    chat_id=channel,
                    photo=context.user_data['media'],
                    reply_markup=markup
                )
            else:
                await context.bot.send_video(
                    chat_id=channel,
                    video=context.user_data['media'],
                    reply_markup=markup
                )
            
            await query.edit_message_text(f"✅ Posted to {channel}")
        except Exception as e:
            await query.edit_message_text(f"❌ Failed: {str(e)}")
    else:
        await query.edit_message_text("❌ Cancelled")
    
    return ConversationHandler.END

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle forwarded posts from channel"""
    if not is_authorized(update.effective_user.id):
        await update.message.reply_text("❌ Unauthorized!")
        return ConversationHandler.END
    
    if not update.message.forward_from_chat or not update.message.reply_markup:
        await update.message.reply_text("🔍 Forward a channel post WITH buttons")
        return
    context.user_data.update({
        'original_sender': update.message.forward_from_chat.title,
        'forwarded_msg': update.message
    })
    
    await update.message.reply_text("📌 Please Send channel username (@name)")
    return FORWARDING

async def forward_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Repost message to another channel"""
    dest_channel = update.message.text.strip()
    if not dest_channel.startswith('@'):
        dest_channel = '@' + dest_channel
    
    try:
        chat = await context.bot.get_chat(dest_channel)
        admins = await context.bot.get_chat_administrators(dest_channel)
        bot_id = (await context.bot.get_me()).id
        is_admin = any(admin.user.id == bot_id for admin in admins)
        
        if not is_admin:
            await update.message.reply_text(f"❌ Bot is not admin in {dest_channel}. Please make bot admin first.")
            return FORWARDING

        buttons = []
        for row in context.user_data['forwarded_msg'].reply_markup.inline_keyboard:
            new_row = []
            for btn in row:
                if btn.url:
                    new_row.append(InlineKeyboardButton(btn.text, url=btn.url))
            if new_row:
                buttons.append(new_row)
        
        if not buttons:
            raise ValueError("No usable buttons")
        
        markup = InlineKeyboardMarkup(buttons)
        
        if context.user_data['forwarded_msg'].photo:
            await context.bot.send_photo(
                chat_id=dest_channel,
                photo=context.user_data['forwarded_msg'].photo[-1].file_id,
                caption=f"🔗 From: {context.user_data['original_sender']}",
                reply_markup=markup
            )
        elif context.user_data['forwarded_msg'].video:
            await context.bot.send_video(
                chat_id=dest_channel,
                video=context.user_data['forwarded_msg'].video.file_id,
                caption=f"🔗 From: {context.user_data['original_sender']}",
                reply_markup=markup
            )
        
        await update.message.reply_text(f"✅ Reposted to {dest_channel}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation"""
    await update.message.reply_text("❌ Operation cancelled")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    create_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            PHOTO: [MessageHandler(filters.PHOTO | filters.VIDEO, create_post)],
            TITLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_titles)],
            BUTTONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_buttons)],
            CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_channel)],
            CONFIRM: [CallbackQueryHandler(confirm_post, pattern='^(post|cancel)$')]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    forward_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.FORWARDED & (filters.PHOTO | filters.VIDEO), handle_forward)],
        states={
            FORWARDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, forward_to_channel)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    app.add_handler(create_handler)
    app.add_handler(forward_handler)
    
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()