#!/usr/bin/env python3
"""Bot Commands related to or interactin with the scp-wiki."""

###############################################################################
# Module Imports
###############################################################################

import arrow
import random as rand

from . import core, ext, parser, lex, stats, tools

###############################################################################
# Internal Methods
###############################################################################


def show_page(page, rating=True):
    attribution = page.build_attribution_string(
        templates=lex.show_page.templates._raw,
        group_templates=lex.show_page.group_templates._raw)
    out = lex.show_page.summary if rating else lex.show_page.nr_summary
    return out(page=page, attribution=attribution)


###############################################################################
# Find And Lookup Functions
###############################################################################


def show_search_results(inp, results):
    """Process page search results."""
    if not results:
        return lex.not_found.page
    elif len(results) == 1:
        return show_page(results[0])
    else:
        tools.save_results(inp, results, show_page)
        results = [p.title for p in results]
        head, tail = results[:3], results[3:]
        output = ', '.join('\x02{}\x02'.format(i) for i in head)
        if tail:
            output += ' and {} more...'.format(len(tail))
        return output


def show_search_summary(inp, results):
    if not results:
        return lex.not_found.page
    pages = ext.PageView(results).sorted('created')
    return lex.summary.search(
        count=pages.count,
        authors=len(pages.authors),
        rating=pages.rating,
        average=pages.average,
        first=arrow.get(pages[0].created).humanize(),
        last=arrow.get(pages[-1].created).humanize(),
        top_title=pages.sorted('rating')[-1].title,
        top_rating=pages.sorted('rating')[-1].rating)


def author_search(inp, func):
    """Find author via partial name, and process results."""
    text = (inp.text or inp.user).lower()
    authors = {i for p in core.pages for i in p.metadata}
    results = sorted(i for i in authors if text in i.lower())
    if not results:
        return lex.not_found.author
    elif len(results) == 1:
        return func(results[0])
    else:
        tools.save_results(inp, results, func)
        return tools.choose_input(results)


def find_pages(
        inp, pages, partial, exclude, strict,
        tags, author, rating, created, fullname, summary):
    if tags:
        pages = pages.tags(tags)
    if rating:
        pages = pages.with_rating(rating)
    if created:
        pages = pages.created(created)

    if author:
        pages = [
            p for p in pages if any(author in a.lower() for a in p.metadata)]
    if fullname:
        pages = [p for p in pages if p.title.lower() == fullname]
        return show_page(pages[0]) if pages else lex.not_found.page

    results = []
    for p in pages:
        words = p.title.lower().split()
        words = {''.join(filter(str.isalnum, w)) for w in words}

        if exclude and words & set(exclude):
            continue
        if strict and not words >= set(strict):
            continue
        if partial and not all(i in p.title.lower() for i in partial):
            continue

        results.append(p)

    func = show_search_summary if summary else show_search_results
    return func(inp, results)


@core.command
@parser.search
def search(inp, **kwargs):
    if not inp.text:
        return lex.input.incorrect
    return find_pages(inp, core.pages, **kwargs)


@core.command
@parser.search
def tale(inp, **kwargs):
    if not inp.text:
        return lex.input.incorrect
    return find_pages(inp, core.pages.tags('tale'), **kwargs)


@core.command
@parser.search
def wanderers_library(inp, **kwargs):
    if not inp.text:
        return lex.input.incorrect
    return find_pages(inp, core.wlpages, **kwargs)


@core.command
def tags(inp):
    return show_search_results(inp, core.pages.tags(inp.text))


@core.command
def name_lookup(inp):
    pages = [p for p in core.pages if p.url.split('/')[-1] == inp.text.lower()]
    return show_search_results(inp, pages)


@core.command
def author(inp):
    return author_search(inp, author_summary)


@core.command
def author_details(inp):
    return author_search(inp, stats.update_user)


###############################################################################
# Output Generation Functions
###############################################################################


def search_results(results):
    """Display search results."""
    results = [p.title for p in results]
    head, tail = results[:3], results[3:]
    output = ', '.join('\x02{}\x02'.format(i) for i in head)
    if tail:
        output += ' and {} more...'.format(len(tail))
    return output


def author_summary(name):
    """Compose author summary."""
    pages = core.pages.related(name)
    url = pages.tags('author')[0].url if pages.tags('author') else None
    url = ' ({})'.format(url) if url else ''
    pages = pages.articles
    if not pages:
        return lex.not_found.author
    template = '\x02{1.count}\x02 {0}'.format
    tags = ', '.join(template(*i) for i in pages.split_page_type().items())
    rels = ', '.join(template(*i) for i in pages.split_relation(name).items())
    last = sorted(pages, key=lambda x: x.created, reverse=True)[0]
    return lex.summary.author(
        name=name, url=url, pages=pages, rels=rels, tags=tags,
        primary=pages.primary(name), last=last)

###############################################################################
# Misc
###############################################################################


@core.multiline
@core.command
def errors(inp):
    if inp.channel != core.config['irc']['sssc']:
        yield lex.denied
        return

    pages = []
    lp = core.wiki.list_pages

    def report(errp, msg):
        errp = list(errp)
        if not errp:
            return
        pages.extend(errp)
        errp = [p.url.split('/')[-1] for p in errp]
        errp = map('\x02{}\x02'.format, sorted(errp))
        yield msg(pages=', '.join(errp))

    yield from report(lp(tags='-'), lex.errors.no_tags)

    title = core.pages.tags('scp').pages
    title.extend(lp(name='scp-*', created_at='last 3 hours'))
    title = [
        i for i in title if
        core.wiki.titles().get(i.url) == '[ACCESS DENIED]']
    title = [i for i in title if 'scp-1848' not in i.url]
    yield from report(title, lex.errors.no_title)

    yield from report(lp(category='deleted'), lex.errors.improperly_deleted)

    yield from report(lp(
        tags='-in-deletion -archived -author',
        rating='<-10', created_at='older than 24 hours'),
        lex.errors.need_deletion_vote)

    urls = [p.url for p in core.pages]
    titles = [
        k for k, v in core.wiki.titles().items()
        if k not in urls and v != '[ACCESS DENIED]']
    yield from report(map(core.wiki, titles), lex.errors.orphaned_title)

    if not pages:
        yield lex.errors.none
    else:
        tools.save_results(inp, pages, show_page)
        yield lex.errors.done


@core.command
@parser.search
def random(inp, **kwargs):
    pages = core.pages if not inp.text else find_pages(core.pages, **kwargs)
    if pages:
        return show_page(rand.choice(pages))
    else:
        return lex.not_found.page


@core.command
@core.multiline
def lastcreated(inp, cooldown={}, **kwargs):
    kwargs = dict(
        body='title created_by created_at rating',
        order='created_at desc',
        limit=3)
    now = arrow.now()

    if inp.channel not in cooldown:
        pass
    elif (now - cooldown[inp.channel]).seconds < 120:
        yield lex.spam
        return

    cooldown[inp.channel] = now

    pages = core.wiki.list_pages(**kwargs)
    yield from [show_page(p, rating=False) for p in pages]


@core.command
@parser.unused
def unused(inp, *, random, last, count, prime, palindrome, divisible):
    numbers = range(2, 3000)

    if prime:
        numbers = [i for i in numbers if all(i % k for k in range(2, i))]
    if palindrome:
        numbers = [
            i for i in numbers if str(i).zfill(3) == str(i).zfill(3)[::-1]]
    if divisible:
        numbers = [i for i in numbers if i % divisible == 0]

    slots = ['scp-{:03d}'.format(i) for i in numbers]
    used_slots = {p._body['fullname'] for p in core.pages.tags('scp')}
    unused_slots = [i for i in slots if i not in used_slots]

    if not unused_slots:
        return lex.not_found.unused

    if count:
        return lex.unused.count(count=len(unused_slots))

    if random:
        result = rand.choice(unused_slots)
    elif last:
        result = unused_slots[-1]
    else:
        result = unused_slots[0]

    return 'http://www.scp-wiki.net/' + result


@core.command
def staff(inp, staff={}):
    if not inp.text:
        return 'http://www.scp-wiki.net/meet-the-staff'

    cats = {'Admin': 1, 'Mod': 2, 'Staff': 3}

    if not staff:
        for key in cats:
            staff[key] = {}

        soup = core.wiki('meet-the-staff')._soup
        for k, v in cats.items():
            for i in soup(class_='content-panel')[v]('p'):
                staff[k][i.strong.text.lower()] = i.text

    for cat in cats:
        for k, v in staff[cat].items():
            if inp.text.lower() in k:
                return '[{}] {}'.format(cat, v)

    return lex.not_found.staff
