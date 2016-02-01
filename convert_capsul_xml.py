# Temporary script to ease pipeline conversion. It will be removed when
# Capsul XML 2.0 is validated.

import sys
import re
import xmltodict
import subprocess
from StringIO import StringIO
import tempfile
from collections import OrderedDict
import codecs
from ast import literal_eval

type_map = {
    'Int': 'int',
    'Float': 'float',
    'Str': 'string',
    'String': 'string',
    'Bool': 'bool',
    'Any': 'any',
    'File': 'file',
    'Directory': 'directory',
    'List_File': 'list_file',
}
def get_type(type, dict):
    if type in type_map:
        return type_map[type]
    elif type == 'List':
        return 'list_%s' % get_type(dict.pop('@content'), None)
    elif type.startswith('['):
        return '|'.join(get_type(i, {}) for i in literal_eval(type))
    else:
        raise ValueError('Unsuported parameter type: %s' % type)                
    
    
def convert_unit(unit):
    process = OrderedDict((('@capsul_xml', '2.0'),))
    result = {'process': process}
    
    for tag, content in unit['unit'].iteritems():
        if not isinstance(content,list):
            content = [content]
        if tag in ('input', 'output'):
            elems = process.setdefault(tag,[])
            for c in content:
                elem = {'@name': c.pop('@name')}
                elems.append(elem)
                type = c.pop('@type')
                elem['@type'] = get_type(type, c)
                optional = c.pop('@optional', None)
                if optional is not None:
                    elem['@optional'] = ('true' if  optional == 'True' else 'false')
                doc = c.pop('@description', None)
                if doc is None:
                    doc = c.pop('@desc', None)
                if doc:
                    doc = ' '.join(doc.split())
                    elem['@doc'] = doc
                if c:
                    raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        else:
            raise ValueError('Invalid key in <unit>: %s' % tag)
    return result

def convert_pipeline(source_pipeline):
    #return source_pipeline
    pipeline = OrderedDict((('@capsul_xml', '2.0'),))
    result = {'pipeline': pipeline}
    
    for tag, content in source_pipeline['pipeline'].iteritems():
        if not isinstance(content,list):
            content = [content]
        if tag == 'docstring':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            pipeline['doc'] = content[0]
        elif tag == 'units':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            c = content[0]
            
            unit = c.pop('unit')
            if not isinstance(unit, list):
                unit = [unit]
            processes = []
            for u in unit:
                module = u.pop('module')
                if module.endswith('.xml'):
                    module = module[:-4]
                process = OrderedDict((
                    ('@name', u.pop('@name')),
                    ('@module', module)))
                processes.append(process)
                
                set = u.pop('set',[])
                if not isinstance(set, list):
                    set = [set]
                for s in set:
                    name = s.pop('@name')
                    process.setdefault('set',[]).append({'@name': name, '@value': s.pop('@value')})
                    copyfile = s.pop('@copyfile', None)
                    usedefault = s.pop('@usedefault', None)
                    nipype = OrderedDict((('@name', name),))
                    if copyfile:
                        if copyfile == 'True':
                            nipype['@copyfile'] = 'true'
                        elif copyfile == 'Temp':
                            nipype['@copyfile'] = 'discard'
                        else:
                            raise 'Invalid copyfile value: %s' % copyfile
                    if usedefault:
                        if usedefault == 'True':
                            nipype['@usedefault'] = 'true'
                        else:
                            raise 'Invalid usedefault value: %s' % usedefault
                    if copyfile or usedefault:
                        process.setdefault('nipype',[]).append(nipype)
                    if s:
                        raise ValueError('Invalid keys in <set>: %s' % ', '.join(s.keys()))
                iterinput = u.pop('iterinput', [])
                if not isinstance(iterinput, list):
                    iterinput = [iterinput]
                iteroutput = u.pop('iteroutput', [])
                if not isinstance(iteroutput, list):
                    iteroutput = [iteroutput]
                iteration = [i['@name'] for i in iterinput] + [i['@name'] for i in iteroutput]
                if iteration:
                    process['iterate'] = [{'@name': i} for i in iteration]
                if u:
                    raise ValueError('Invalid keys in <unit>: %s' % ', '.join(u.keys()))
            pipeline.setdefault('process',[]).extend(processes)

            switch = c.pop('switch', None)
            if switch:
                if not isinstance(switch, list):
                    switch = [switch]
                selections = pipeline.setdefault('processes_selection',[])
                for s in switch:
                    selection = {'@name': s.pop('@name')}
                    selections.append(selection)
                    path = s.pop('path',[])
                    if not isinstance(path, list):
                        path = [path]
                    groups = selection.setdefault('processes_group', [])
                    for p in path:
                        group = {'@name': p.pop('@name')}
                        groups.append(group)
                        unit = p.pop('unit',[])
                        if not isinstance(unit, list):
                            unit = [unit]
                        processes = group.setdefault('process', [])
                        for u in unit:
                            processes.append({'@name': u.pop('@name')})
                            if u:
                                raise ValueError('Invalid keys in <unit> (inside <path>): %s' % ', '.join(u.keys()))
                        if p:
                            raise ValueError('Invalid keys in <path>: %s' % ', '.join(p.keys()))
                    if s:
                        raise ValueError('Invalid keys in <switch>: %s' % ', '.join(c.keys()))
            if c:
                raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        elif tag == 'links':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            c = content[0]
            link = c.pop('link')
            if not isinstance(link, list):
                link = [link]
            for p in link:
                p['@dest'] = p.pop('@destination')
            
            pipeline.setdefault('link',[]).extend(link)
            if c:
                raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        elif tag == 'positions':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            c = content[0]
            position = c.pop('position')
            if not isinstance(position, list):
                position = [position]
            for p in position:
                p['@name'] = p.pop('@unit')
            pipeline.setdefault('gui',{})['position'] = position
            if c:
                raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        elif tag =='scale':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            c = content[0]
            factor = c.pop('@factor')
            pipeline.setdefault('gui',{}).setdefault('zoom',{})['@level'] = factor
            if c:
                raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        elif tag =='zoom':
            if len(content) > 1:
                raise ValueError('Only one <%s> allowed' % tag)
            c = content[0]
            level = c.pop('@level')
            pipeline.setdefault('gui',{}).setdefault('zoom',{})['@level'] = level
            if c:
                raise ValueError('Invalid keys in <%s>: %s' % (tag, ', '.join(c.keys())))
        elif tag == '@version':
            pass
        else:
            raise ValueError('Invalid key in <pipeline>: %s' % tag)
    return result

def process_file(input_file_name, output_file_name, main_tag, conversion_function, indent=''):
    file_content = codecs.open(input_file_name, encoding='utf-8').read()
    result = []
    last_end = 0
    for match in re.finditer(r'<{0}.*?</{0}>'.format(main_tag), file_content, re.DOTALL):
        unit = xmltodict.parse(file_content[match.start():match.end()])
        xml = xmltodict.unparse(conversion_function(unit))
        
        # Prettify XML with xmllint command
        tmp = tempfile.mktemp()
        open(tmp,'w').write(xml)
        xml = subprocess.check_output(['xmllint', '--pretty', '1', tmp])
        xml = xml[xml.find('\n'):].replace('\n', '\n%s'% indent)
        
        result.append(file_content[last_end:match.start()])
        result.append(xml)
        last_end = match.end()
    result.append(file_content[last_end:])
    output_file = codecs.open(output_file_name, 'w', encoding='utf-8')
    output_file.write(''.join(result))

if sys.argv[1].endswith('.py'):
    process_file(sys.argv[1], sys.argv[2], 'unit', convert_unit, indent='    ')
elif sys.argv[1].endswith('.xml'):
    process_file(sys.argv[1], sys.argv[2], 'pipeline', convert_pipeline)
