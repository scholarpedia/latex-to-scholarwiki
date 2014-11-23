from render.scholarwiki import Renderer
#from render.xml import Renderer  # useful for adding new constructs
from plasTeX.TeX import TeX

# Instantiate a TeX processor and parse the input text
#tex = TeX(file='examples/Mesoscopic_transport_and_quantum_chaos.tex')
tex = TeX(file='examples/Organic_superconductivity-v7.tex')

tex.ownerDocument.config['files']['split-level'] = -100
tex.ownerDocument.config['files']['filename'] = 'test.scholarwiki'
document = tex.parse()

# Render the document
renderer = Renderer()
#renderer.imagePrefix = u'MesoscopicTransport-'
renderer.imagePrefix = u''

renderer.render(document)

#
