from plasTeX.Renderers import Renderer as BaseRenderer
import re
import pdb
import string


class BibWikiRenderer(BaseRenderer):

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
        """ Rendering method for all non-text nodes """

        # Handle characters like \&, \$, \%, etc.
        if len(node.nodeName) == 1 and node.nodeName not in string.letters:
            return self.textDefault(node.nodeName)

        # Invoke rendering on child nodes
        return unicode(node)

    def textDefault(self, node):
        """ Rendering method for all text nodes """
        return node.replace(
            '&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    # Bibliography
    def do_thebibliography(self, node):
        pdb.set_trace()
        output = ['', '= References =', '']
        regsp = re.compile(r'\s+')
        for item in node:
            # something converts tildes to spaces in the bibcite
            bibcite = regsp.sub(u'', unicode(item.bibcite))
            text = regsp.sub(u' ', unicode(item))
            output.append(u'* <cite id="%s">%s</cite>' % (bibcite, text))
        output.append('')
        return u'\n'.join(output)

    def do_bibliographystyle(self, node):
        return u''

    def do_bibliography(self, node):
        return self.default(node)

    def do_cite(self, node):
        output = []
        for item in node.citation():
            if item == '[' or item == ']':
                continue
            if item == ', ':
                continue
            if len(unicode(item)) < 3:
                pdb.set_trace()
            output.append(u'[[#%s|%s]]' % (item.textContent, item.textContent))
        return u'(%s)' % u', '.join(output)

    def do_bibliographyref(self, node):
        return self.default(node)
