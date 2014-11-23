#!/usr/bin/env python

from plasTeX.Renderers import Renderer as BaseRenderer
#from plasTeX import encoding
import textwrap
import re
import pdb
import string

import plasTeX as Base


class DeclareMathOperator(Base.Command):
    args = 'text:str'

    def invoke(self, tex):
        Base.Command.invoke(self, tex)

if False:
    pdb.set_trace()


class ScholarWikiRenderer(BaseRenderer):
    """ Renderer for plain text documents """

    outputType = unicode
    fileExtension = '.scholarwiki'
    lineWidth = 76
    imagePrefix = u''

    aliases = {
        'superscript': 'active::^',
        'subscript': 'active::_',
        'dollar': '$',
        'percent': '%',
        'opencurly': '{',
        'closecurly': '}',
        'underscore': '_',
        'ampersand': '&',
        'hashmark': '#',
        'space': ' ',
        'tilde': 'active::~',
        'at': '@',
        'backslash': '\\',
    }

    def __init__(self, *args, **kwargs):
        BaseRenderer.__init__(self, *args, **kwargs)

        # Load dictionary with methods
        for key in dir(self):
            if key.startswith('do__'):
                self[self.aliases[key[4:]]] = getattr(self, key)
            elif key.startswith('do_'):
                self[key[3:]] = getattr(self, key)

        self['default-layout'] = self['document-layout'] = self.default

        self.footnotes = []
        self.blocks = []

    def default(self, node):

        # not sure why do_document is not called directly
        if node.nodeName == 'document':
            return self.do_document(node)
        elif node.nodeName == 'DeclareMathOperator':
            return self.do_DeclareMathOperator(node)

        """ Rendering method for all non-text nodes """
        s = []

        # Handle characters like \&, \$, \%, etc.
        if len(node.nodeName) == 1 and node.nodeName not in string.letters:
            return self.textDefault(node.nodeName)

        # Start tag
        s.append('<%s><!--unknown tag-->' % node.nodeName)

        # See if we have any attributes to render
        if node.hasAttributes():
            s.append('<attributes>')
            for key, value in node.attributes.items():
                # If the key is 'self', don't render it
                # these nodes are the same as the child nodes
                if key == 'self':
                    continue
                s.append('<%s>%s</%s>' % (key, unicode(value), key))
            s.append('</attributes>')

        # Invoke rendering on child nodes
        s.append(unicode(node))

        # End tag
        s.append('</%s>' % node.nodeName)

        return u'\n'.join(s)

    def textDefault(self, node):
        """ Rendering method for all text nodes """
        return unicode(node)

#     def default(self, node):
#         """ Rendering method for all non-text nodes """
#         # Handle characters like \&, \$, \%, etc.
#         if (len(node.nodeName) == 1 and
#                 node.nodeName not in encoding.stringletters()):
#             return self.textDefault(node.nodeName)
#
#         # Render child nodes
#         return unicode(node)

    def processFileContent(self, document, s):
        # process the bibliography information

        s = BaseRenderer.processFileContent(self, document, s)

        # Put block level elements back in
        block_re = re.compile('(\\s*)\001\\[(\\d+)@+\\]')
        while 1:
            m = block_re.search(s)
            if not m:
                break

            space = ''
            before = m.group(1)
            if before is None:
                before = ''
            if '\n' in before:
                spaces = before.split('\n')
                space = spaces.pop()
                before = '\n'.join(spaces) + '\n'

            block = self.blocks[int(m.group(2))]
            block = space + block.replace('\n', u'\n%s' % space)

            s = block_re.sub('%s%s' % (before, block), s, 1)

        # Hack to allow eqref to work
        s = re.sub(r'(\\eqref) ([^\s,.]+)', r'\1{\2}', s)

        # Remove single spaces at beginning of lines
        # Some in-line equations are not handled correctly
        s1 = re.sub(r'^\s(\S)', r'\1', s, flags=re.MULTILINE)

        # Clean up newlines
        return re.sub(r'\s*\n\s*\n(\s*\n)+', r'\n\n\n', s1)

    def wrap(self, s, **kwargs):
        return textwrap.wrap(unicode(s), self.lineWidth,
                             break_long_words=False, **kwargs)

    def fill(self, s, **kwargs):
        return textwrap.fill(unicode(s), self.lineWidth,
                             break_long_words=False, **kwargs)

    # Alignment

    def center(self, text):
        return text

    def do_center(self, node):
        return self.center(unicode(node))

    do_centering = do_centerline = do_center
    do_flushright = do_flushleft = do_center
    do_raggedleft = do_llap = do_flushright

    # Arrays

    def do_array(self, node, cellspacing=(2, 1), render=unicode):
        # Render the table cells and get min and max column widths
        colwidths = []
        for r, row in enumerate(node):
            for c, cell in enumerate(row):
                if isinstance(render, basestring):
                    s = getattr(cell, render)().strip()
                else:
                    s = render(cell).strip()
                if s.strip():
                    maxlength = max([len(x) for x in s.split('\n')])
                    minlength = min([len(x) for x in s.split() if x.strip()])
                else:
                    minlength = maxlength = 0
                if r == 0:
                    colwidths.append([minlength, maxlength])
                else:
                    colwidths[c] = [max(minlength, colwidths[c][0]),
                                    max(maxlength, colwidths[c][1])]

        # Determine best column widths
        maxline = self.lineWidth - len(colwidths)*cellspacing[0]
        minwidths = [x[0] for x in colwidths]  # minimums
        maxwidths = [x[1] for x in colwidths]  # maximums
        if sum(maxwidths) < maxline:
            outwidths = maxwidths
        elif sum(minwidths) > maxline:
            outwidths = minwidths
        else:
            outwidths = list(maxwidths)
            # If the minimum is also the maximum, take it out of the
            # algorithm to determine lengths.
            for i, item in enumerate(maxwidths):
                if maxwidths[i] == minwidths[i]:
                    maxwidths[i] = -1
            # Iteratively subtract one from the longest line until the
            # table will fit within maxline.
            while sum(outwidths) > maxline:
                maxwidths[i] -= 1
                outwidths[i] -= 1
                if maxwidths[i] == minwidths[i]:
                    maxwidths[i] = -1

        # Render cells to correct widths
        rendered = []
        for r, row in enumerate(node):
            current = []
            rendered.append(current)
            for c, cell in enumerate(row):
                origwidth = self.lineWidth
                self.lineWidth = outwidths[c]
                if isinstance(render, basestring):
                    s = getattr(cell, render)().split('\n')
                else:
                    s = render(cell).strip().split('\n')
                if s and r == 0 and c == 0:
                    s[0] = s[0].lstrip()
                current.append((max([len(x) for x in s]), len(s), s))
                self.lineWidth = origwidth

        # Pad cells to fill out a block
        for r, row in enumerate(rendered):
            linesneeded = max([x[1] for x in row]) + cellspacing[1]
            for c, cell in enumerate(row):
                width, height, content = cell
                # Add the appropriate number of lines
                for i in range(linesneeded - len(content)):
                    content.append(' '*width)
                # Pad all lines to the same length
                for i, line in enumerate(content):
                    content[i] = (content[i] +
                                  ' '*(outwidths[c]-width+cellspacing[0]))
                rendered[r][c] = content

        # Piece all of the table parts together
        output = []
        for row in rendered:
            # Continue until cell content is empty (the last cell in this case)
            while row[-1]:
                for cell in row:
                    output.append(cell.pop(0))
                # Get rid of unneeded whitespace and put in a line break
                output[-1] = output[-1].strip()
                output.append('\n')

        return ''.join(output)

    do_tabular = do_tabularx = do_longtable = do_array

    def do_cline(self, node):
        return ''

    def do_multicolumn(self, node):
        return unicode(node)

    # Bibliography
    def do_thebibliography(self, node):
        output = ['', '= References =', '']
        regsp = re.compile(r'\s+')
        for item in node:
            # something converts tildes to spaces in the bibcite
            bibcite = regsp.sub(u'', unicode(item.bibcite))
            text = regsp.sub(u' ', unicode(item))
            output.append(u'* <span id="%s">%s</span>' % (bibcite, text))
        output.append('')
        return u'\n'.join(output)

    def do_bibliographystyle(self, node):
        return u''

    def do_bibliography(self, node):
        return self.default(node)

    def do_cite(self, node):
        output = []
        # look at node.bibitems[0][0].source
        for item in node.citation():
            if item == '[' or item == ']':
                continue
            if item == ', ':
                continue
            if len(unicode(item)) < 3:
                pdb.set_trace()

#             source = node.bibitems[0][0].source
#             au = None
#             authors = None
#             quote = re.search(r'["\']', source)
#             if quote and quote.start() > 0:
#                 au_src = source[0:quote.start()]
#                 au_m = re.findall(r'(\w{2,})', au_src)
#                 total_len = sum(len(s) for s in au_m)
#                 print(au_m)
#                 pdb.set_trace()
#                 if total_len >= len(item.textContent):
#                     authors = au_m
#             y = re.findall(r'\((\d\d\d\d)\)', source)
#             if y and len(y) == 1 and authors:
#                 au = u', '.join(authors)
#                 content = u'%s %s' % (au, y[0])
#             elif y:
#                 content = u'%s %s' % (item.textContent, y[0])
#             else:
#                 content = item.textContent
#
            output.append(u'[[#%s|%s]]' % (item.textContent, item.textContent))
        return u'(%s)' % u', '.join(output)

    def do_bibliographyref(self, node):
        return self.default(node)

    # Boxes

    do_mbax = do_makebox = do_fbox = do_framebox = do_parbox = default
    do_minipage = do_raisebox = do_rule = default

    # Breaking

    def do_linebreak(self, node):
        return u'\n\n'

    do_newline = do_pagebreak = do_newpage = \
        do_clearpage = do_cleardoublepage = do_linebreak

    # Crossref

    def do_ref(self, node):
        return unicode(node.idref['label'].ref)

    def do_pageref(self, node):
        return u'*'

    def do_label(self, node):
        return u''

    # Floats

    def do_figure(self, node):
        output = []
        figs = []
        caps = []
        regfig = re.compile(r'\[\[File:(.*)]]')
        for item in node:
            s = unicode(item)
            fit = regfig.finditer(s)
            was_match = False
            for m in fit:
                figs.append(m.group(1))
                was_match = True
            if not was_match:
                caps.append(s)
            output.append(s)
        if len(figs) == 1:
            return u'[[File:%s|thumb|400px|%s]]' % (figs[0], u' '.join(caps))
        else:
            return u'<figure>%s</figure>' % s

    do_table = do_marginpar = do_figure

    def do_caption(self, node):
        return unicode(node)

    def do_symbol(self, node):
        return u'*'

    # Font Selection
    def do_textbf(self, node):
        return u"'''%s'''" % unicode(node)

    do_bf = do_textbf

    def do_textit(self, node):
        return u"''%s''" % unicode(node)

    do_em = do_it = do_textit

    def do_bgroup(self, node):
        return u'%s' % unicode(node)

    def do_breve(self, node):
        return u'&#774;%s' % node

    do_u = do_breve

    def do_textsuperscript(self, node):
        return u'<sup>%s</sup>' % node

    # Footnotes
    def do_footnote(self, node):
        mark = u'[%s]' % (len(self.footnotes)+1)
        self.footnotes.append(
            self.fill(node, initial_indent='%s ' % mark,
                      subsequent_indent=' ' * (len(mark)+1)).strip())
        return mark

    def do_footnotetext(self, node):
        self.do_footnote(self, node)
        return ''

    def do_footnotemark(self, node):
        return u'[%s]' % (len(self.footnotes)+1)

    # Index

    def do_theindex(self, node):
        return u''

    do_printindex = do_index = do_theindex

    # Lists

    def do_itemize(self, node):
        output = []
        for item in node:
            output.append(u'* <span>%s</span>' % unicode(item).strip())
        return u'\n'.join(output)

    def do_enumerate(self, node):
        output = []
        for i, item in enumerate(node):
            bullet = '# '
            bulletlen = len(bullet)
            output.append(self.fill(item, initial_indent=bullet,
                                    subsequent_indent=' '*bulletlen))
        return u'\n'.join(output)

    def do_description(self, node):
        output = []
        for item in node:
            bullet = '   %s - ' % item.attributes.get('term', '')
            output.append(self.fill(item, initial_indent=bullet,
                                    subsequent_indent='      '))
        return u'\n'.join(output)

    do_list = do_trivlist = do_description

    # Math

    def do_math(self, node):
        s = re.sub(r'\s*(_|\^)\s*', r'\1', node.source)
        s = re.sub(r'^\$(.*)\$$', r'\1', s)
        return u'<math>%s</math>' % s

    def do_subequations(self, node):
        # not sure why node[0].source includes "\begin{subequations}"
        s = re.sub(r'\s*(_|\^)\s*', r'\1', node[0][0].source)
        s = re.sub(r'^\$(.*)\$$', r'\1', s)
        return u'<math>%s</math>' % s

    do_ensuremath = do_math

    def do_equation(self, node):
        s = u'   %s' % re.compile(r'^\s*\S+\s*(.*?)\s*\S+\s*$',
                                  re.S).sub(r'\1', node.source)
        s = re.sub(r'\s*(_|\^)\s*', r'\1', s)
        return u'<math>%s</math>' % s

    do_displaymath = do_equation

    def do_eqnarray(self, node):
        def render(node):
            s = re.compile(r'^\$\\displaystyle\s*(.*?)\s*\$\s*$',
                           re.S).sub(r'\1', node.source)
            return re.sub(r'\s*(_|\^)\s*', r'\1', s)
        s = self.do_array(node, cellspacing=(1, 1), render=render)
        output = []
        for line in s.split('\n'):
            output.append('   %s' % line)
        return u'\n'.join(output)

    do_align = do_gather = do_falign = do_multiline = do_eqnarray
    do_multline = do_alignat = do_split = do_eqnarray

    def do_eqref(self, node):
        return node.source

    def do_DeclareMathOperator(self, node):
        pdb.set_trace()
        return node.source

    # Misc

    def do_def(self, node):
        return u''

    do_title = do_def
    do_tableofcontents = do_input = do_protect = do_let = do_def
    do_newcommand = do_hfill = do_hline = do_openout = do_renewcommand = do_def
    do_write = do_hspace = do_appendix = do_global = do_noindent = do_def
    do_include = do_markboth = do_setcounter = do_refstepcounter = do_def
    do_medskip = do_smallskip = do_def
    do_parindent = do_indent = do_setlength = do_def
    do_settowidth = do_addtolength = do_nopagebreak = do_newwrite = do_def
    do_newcounter = do_typeout = do_sloppypar = do_def
    do_hfil = do_thispagestyle = do_def

    def do_egroup(self, node):
        return u''

    # Pictures

    def do_includegraphics(self, node):
        fn = self.imagePrefix + node.getAttribute('file') + u'.png'
        return u'[[File:%s]]\n' % (fn)

    # Primitives

    def do_par(self, node):
        numchildren = len(node.childNodes)
        if numchildren == 1 and not isinstance(node[0], basestring):
            return u'%s\n\n' % unicode(node)
        elif numchildren == 2 and isinstance(node[1], basestring) and \
                not node[1].strip():
            return u'%s\n\n' % unicode(node)
        s = '%s\n\n' % unicode(node)
        if not s.strip():
            return u''
        return s

    def do__superscript(self, node):
        return self.default(node)

    def do__subscript(self, node):
        return self.default(node)

    # Quotations

    def do_quote(self, node):
        backslash = self['\\']
        self['\\'] = lambda *args: u'\001'
        #res = [x.strip() for x in unicode(node).split(u'\001')]
        output = []
        for par in [x.strip() for x in unicode(node).split(u'\n\n')]:
            for item in [x.strip() for x in par.split(u'\001')]:
                output.append(self.fill(item, initial_indent='   ',
                              subsequent_indent='      '))
            output.append('')
        output.pop()
        self['\\'] = backslash
        return u'\n'.join(output)

    do_quotation = do_verse = do_quote

    # Sectioning

    def do_document(self, node):
        content = unicode(node).rstrip()
        footnotes = u'\n\n'.join(self.footnotes).rstrip()
        if footnotes:
            content = u'%s\n\n\n%s' % (content, footnotes)
        return u'%s\n\n' % content

    def do_section(self, node):
        if node.tagName == 'section':
            fmt = u'='
        elif node.tagName == 'subsection':
            fmt = u'=='
        elif node.tagName == 'subsubsection':
            fmt = u'==='
        else:
            fmt = u'===='

        return u'\n\n\n%s %s %s\n\n%s' % (fmt, node.title, fmt, node)
        # return u'\n\n\n%s' % (u'%s\n\n%s' %
        #                       (self.fill(node.fullTitle), node)).strip()

    do_subsection = do_subsubsection = do_section
    #do_part = do_chapter =
    #do_paragraph = do_subparagraph = do_subsubparagraph = do_section

    def do_title(self, node):
        return u''

    do_author = do_date = do_thanks = do_maketitle = do_title

    def do_abstract(self, node):
        return self.center(node)

    # Sentences

    def do__dollar(self, node):
        return u'$'

    def do__percent(self, node):
        return u'%'

    def do__opencurly(self, node):
        return u'{'

    def do__closecurly(self, node):
        return u'}'

    def do__underscore(self, node):
        return u'_'

    def do__ampersand(self, node):
        return u'&'

    def do__hashmark(self, node):
        return u'#'

    def do__space(self, node):
        return u' '

    def do_LaTeX(self, node):
        return u'LaTeX'

    def do_TeX(self, node):
        return u'TeX'

    def do_emph(self, node):
        return self.default(node)

    do_em = do_emph

    def do__tilde(self, node):
        return u' '

    def do_enspace(self, node):
        return u' '

    do_quad = do_qquad = do_enspace

    def do_enskip(self, node):
        return u''

    do_thinspace = do_enskip

    def do_underbar(self, node):
        return self.default(node)

    # Space

    def do_hspace(self, node):
        return u' '

    def do_vspace(self, node):
        return u''

    do_bigskip = do_medskip = do_smallskip = do_vspace

    # Tabbing - not implemented yet

    # Verbatim

    def do_verbatim(self, node):
        return re.sub(r'^\s*\n', r'', unicode(node)).rstrip()

    do_alltt = do_verbatim

    def do_mbox(self, node):
        return self.default(node)

    def do__at(self, node):
        return u''

    def do__backslash(self, node):
        return u'\\'

Renderer = ScholarWikiRenderer
