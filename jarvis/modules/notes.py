#!/usr/bin/env python3

###############################################################################
# Module Imports
###############################################################################

import sopel
import jarvis

###############################################################################


def setup(bot):
    jarvis.notes.init()
    sopel.bot.Sopel.SopelWrapper.send = send


def send(bot, text, private=False, force=False):
    tr = bot._trigger
    if tr.sender in bot.config.core.channels:
        text = '{}: {}'.format(tr.nick, text)
        jarvis.notes.log_message(bot.config.core.nick, tr.sender, text)

    def say(text, recipient):
        lines = [text[i:i + 400] for i in range(0, len(text), 400)]
        try:
            bot.sending.acquire()
            for line in lines:
                bot.write(('PRIVMSG', recipient), line)
        finally:
            bot.sending.release()

    (say if force else bot.say)(text, tr.nick if private else tr.sender)


###############################################################################


@sopel.module.rule('.*')
@sopel.module.priority('low')
def chat_activity(bot, tr):
    jarvis.notes.log_message(tr.nick, tr.sender, tr.group(0))
    tells = jarvis.notes.get_tells(tr.nick)
    if tells:
        bot.notice('You have {} new messages'.format(len(tells)), tr.nick)
    for t in tells:
        bot.send(t, private=True, force=True)
    for alert in jarvis.notes.get_alerts(tr.nick):
        bot.notice(alert, tr.nick)


@sopel.module.commands('tell')
def tell(bot, tr):
    """
    Send a message to the user.

    The message will be delivered the next time the user is active in any
    of the channels where the bot is present.
    """
    bot.send(jarvis.notes.send_tell(tr.group(2), tr.nick))


@sopel.module.commands('showtells', 'showt', 'st')
def get_tells(bot, tr):
    """
    Show messages sent to you by other users.

    IRC notice is issued in the channel stating the number of queued messages.
    This notice is visible only to the recipient of the messages.

    The tells themselves are delivered via irc private messages.
    """
    tells = list(jarvis.notes.get_tells(tr.nick))
    if not tells:
        bot.notice(jarvis.lexicon.tell.no_new, tr.nick)
    else:
        bot.notice('You have {} new messages'.format(len(tells)), tr.nick)
        for t in tells:
            bot.send(t, private=True, force=True)


@sopel.module.commands('notdelivered', 'nd')
def get_outbound_tells_count(bot, tr):
    bot.notice(jarvis.notes.get_outbound_tells_count(tr.nick), tr.nick)


@sopel.module.commands('purgetells')
def purge_outbound_tells(bot, tr):
    bot.notice(jarvis.notes.purge_outbound_tells(tr.nick), tr.nick)


@sopel.module.commands('seen')
def get_user_last_seen(bot, tr):
    """
    Check when the user was last seen.

    Results are channel specific. You must issue the command in the same
    channel where you want to check for the user.
    """
    bot.send(jarvis.notes.get_user_seen(tr.group(2), tr.sender))


@sopel.module.commands('firstseen', 'fseen')
def get_user_first_seen(bot, tr):
    bot.send(jarvis.notes.get_user_seen(tr.group(2), tr.sender, False))


def channel_quotes_enabled(bot, tr):
    sssc = bot.channels.get(bot.config.scp.sssc)
    if tr.sender in bot.config.scp.quotes:
        return tr.sender
    elif sssc and tr.sender in sssc.users:
        return sssc.name
    else:
        return


@sopel.module.require_admin(message='Nope')
@sopel.module.commands('qw')
def qw(bot, tr):
    with open('quotes.txt') as file:
        quotes = [i for i in file]
    for q in quotes:
        jarvis.notes.quote(q, bot.config.scp.sssc)
    bot.send('FINISHED ADDING {}'.format(len(quotes)))


@sopel.module.commands('quote', 'q')
def quote(bot, tr):
    channel = channel_quotes_enabled(bot, tr)
    if channel:
        bot.send(jarvis.notes.dispatch_quote(tr.group(2), channel))


@sopel.module.commands('rem')
def rem(bot, tr):
    channel = channel_quotes_enabled(bot, tr)
    if channel:
        bot.send(jarvis.notes.remember_user(tr.group(2), channel))


@sopel.module.rule(r'^\?([\w\d-]+)$')
def get_rem(bot, tr):
    channel = channel_quotes_enabled(bot, tr)
    if channel:
        bot.send(jarvis.notes.recall_user(tr.group(1), channel))


@sopel.module.commands('subscribe')
def subscribe_to_topic(bot, tr):
    bot.send(jarvis.notes.subscribe_to_topic(
        tr.nick, tr.group(2), tr.sender == bot.config.scp.sssc))


@sopel.module.commands('unsubscribe')
def unsubscribe_from_topic(bot, tr):
    bot.send(jarvis.notes.unsubscribe_from_topic(tr.nick, tr.group(2)))


@sopel.module.commands('restrict')
def restrict_topic(bot, tr):
    bot.send(jarvis.notes.restrict_topic(
        tr.group(2), tr.sender == bot.config.scp.sssc))


@sopel.module.commands('unrestrict')
def unrestrict_topic(bot, tr):
    bot.send(jarvis.notes.unrestrict_topic(
        tr.group(2), tr.sender == bot.config.scp.sssc))


@sopel.module.commands('topics')
def get_topics_count(bot, tr):
    bot.notice(jarvis.notes.get_topics_count(tr.nick), tr.nick)


@sopel.module.commands('alert')
def set_alert(bot, tr):
    bot.send(jarvis.notes.set_alert(tr.nick, tr.group(2)))
