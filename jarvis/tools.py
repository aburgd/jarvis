#!/usr/bin/env python3
"""Misc. bot commands."""

###############################################################################
# Module Imports
###############################################################################

import random
import re

from . import core, parser, lexicon

###############################################################################
# Internal Tools
###############################################################################

MEMORY = {}


def save_results(inp, items, func=None):
    MEMORY[inp.channel] = items, func


@core.command
@parser.showmore
def showmore(inp, *, index):
    if index is None:
        index = 1
    if index <= 0:
        return lexicon.input.bad_index
    if inp.channel not in MEMORY:
        return lexicon.not_found.generic
    items, func = MEMORY[inp.channel]
    if index > len(items):
        return lexicon.input.bad_index
    return func(items[index - 1]) if func else items[index - 1]


def choose_input(options):
    options = ['\x02{}\x02'.format(i) for i in options]
    if len(options) <= 5:
        head, tail = options[:-1], options[-1]
        msg = lexicon.input.options
    else:
        head, tail = options[:5], len(options[5:])
        msg = lexicon.input.cropped_options
    return msg.format(head=', '.join(head), tail=tail)


@core.command
def deprecate(inp, cmd):
    return 'This command is deprecated. Use "{}" instead.'.format(cmd)

###############################################################################
# Tools for users
###############################################################################


@core.command
def choose(inp):
    """Return one random comma-separated option."""
    if not inp.text:
        return lexicon.input.missing
    options = [i.strip() for i in inp.text.split(',') if i.strip()]
    return random.choice(options)


@core.command
def roll_dice(inp):
    """Return the result of rolling multiple dice."""
    if not inp.text:
        return lexicon.input.missing
    rolls = re.findall(r'([+-]?)([0-9]*)d([0-9]+|f)', inp.text)
    total = 0

    def roll_die(sign, count, sides):
        nonlocal total
        results = [random.randint(1, int(sides)) for _ in range(count)]
        if sign == '-':
            results = [-i for i in results]
        total += sum(results)
        return results

    def roll_fudge_die(count):
        nonlocal total
        results = [random.choice(['+1', '0', '-1']) for _ in range(count)]
        total += sum(map(int, results))
        return [i[0] for i in results]

    results = []
    for sign, count, sides in rolls:
        count = int(count) if count else 1
        if count > 5000:
            return lexicon.dice.too_many
        if sides == 'f':
            results.extend(roll_fudge_die(count))
        elif int(sides) < 2:
            return lexicon.dice.incorrect
        else:
            results.extend(roll_die(sign, count, sides))
    results = ', '.join(map(str, results))
    results = results.replace('+', '\x033+\x0F').replace('-', '\x034-\x0F')

    bonus = re.search(r'[+-][0-9]+$', inp.text)
    if bonus:
        total += int(bonus.group(0))

    return '{} ({}={})'.format(total, inp.text, results)


@core.command
def get_hugs(inp):
    return lexicon.silly.hugs


@core.command
def zyn(inp):
    return lexicon.silly.zyn


@core.command
def user(inp):
    user = inp.text.lower().replace(' ', '-')
    return 'http://www.wikidot.com/user:info/' + user


@core.command
def help(inp):
    url = 'http://scp-stats.wikidot.com/jarvis'
    return url if not inp.text else url + '#' + inp.text

###############################################################################
