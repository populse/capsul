# -*- coding: utf-8 -*-
from jinja2 import Environment, PackageLoader, select_autoescape

from capsul.api import Capsul

env = Environment(
    loader=PackageLoader('capsul.web'),
    autoescape=select_autoescape()
)

capsul = Capsul()
template = env.get_template('dashboard.html')
print(template.render(capsul=capsul))
